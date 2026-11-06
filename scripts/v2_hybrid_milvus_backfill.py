#!/usr/bin/env python
"""HybridRetrieval 阶段 2：把 RAG chunk 的 bge-m3 向量回灌 Milvus。

流程
----
从 ES（19200）读取 kb_9/kb_1004 的**全部 chunk**（`_source.metadata.pk` 是整数主键），
构造 document_list 调向量服务（19526）`/insert_vector_documents_custom`，由向量服务：
1. 自动创建 collection（逻辑名 kb_9 → 实际 `_kb_9`，见 `generate_collection_name_uuid`）；
2. 用 bge-m3（1024 维，IP metric）计算向量（**只算一次**，不自己再算，HR-03）；
3. 写入 Milvus，pk 用 metadata 的整数 pk（与 ES `_id` 一一对齐，HR-04）。

为什么走 19526 而非直连 Milvus：向量服务是唯一有权生成 collection schema / embedding 的
受控入口，直连会绕过字段白名单与"先删旧代再写"的幂等逻辑，导致 pk 漂移或重复。

诚实边界
--------
- 只回灌 kb_9/kb_1004 的正文与表格 chunk，不碰 faq_/table_chunks_/community_summary_ 等派生集合；
- 首次回灌后 doc 数必须等于 ES `_count`；任一 collection doc 数与 ES 不一致即 FAIL（HR-04）。

运行
----
    # 先看数据量（只读，不写）
    python3 scripts/v2_hybrid_milvus_backfill.py --dry-run
    # 小规模验证（只回灌前 10 条）
    python3 scripts/v2_hybrid_milvus_backfill.py --limit 10
    # 全量回灌 + 校验
    python3 scripts/v2_hybrid_milvus_backfill.py
"""

import argparse
import json
import sys
import time
import urllib.request

ES_URL = "http://127.0.0.1:19200"
VECTOR_URL = "http://127.0.0.1:19526"
# 向量服务（19526）连的是 r12-milvus（宿主机 19630）的 rag_knowledge_base 库，
# 不是 19530（那是 yuxi-milvus-1 的 default 库，与检索链路无关）。
MILVUS_URL = "http://127.0.0.1:19630"
MILVUS_DB = "rag_knowledge_base"
KBS = ["kb_9", "kb_1004"]
MODEL = "bge-m3"


def _post(url, payload, timeout=120):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def es_scroll(index, size=500):
    """遍历 ES 一个索引的全部文档，yield (pk, page_content, metadata)。"""
    scroll = "2m"
    body = {"query": {"match_all": {}}, "size": size}
    resp = _post(f"{ES_URL}/{index}/_search?scroll={scroll}", body, timeout=60)
    scroll_id = resp.get("_scroll_id")
    while True:
        hits = resp["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            src = h.get("_source") or {}
            meta = dict(src.get("metadata") or {})
            yield h.get("_id"), src.get("page_content") or "", meta
        resp = _post(f"{ES_URL}/_search/scroll",
                     {"scroll": scroll, "scroll_id": scroll_id}, timeout=60)
        scroll_id = resp.get("_scroll_id")


def insert_batch(collection_name, docs, model=MODEL, timeout=900):
    """调 19526 /insert_vector_documents_custom 写入一批。

    duplicate_flag 必须为 False：首次回灌 Milvus 为空，无需按 source 去重；
    且 add_doc_custom 的「按 source 整文件替换」在跨文件分批时会把上一批同 source
    数据误删（实测 kb_1004 整本书 4520 chunk 共用一个 source，导致互相删除 → 0 条）。
    """
    payload = {
        "collection_name": collection_name,
        "document_list": docs,
        "model_name": model,
        "duplicate_flag": False,
    }
    return _post(f"{VECTOR_URL}/insert_vector_documents_custom", payload, timeout=timeout)


def flush_collection(collection_name):
    """flush Milvus collection，把 growing segment 持久化（batch_insert_async 不 flush）。"""
    return _post(f"{MILVUS_URL}/v2/vectordb/collections/flush",
                 {"collectionName": collection_name, "dbName": MILVUS_DB}, timeout=60)


def milvus_collection_row_count(collection_name):
    """查 Milvus collection 实际行数（collection 名已含 `_` 前缀，在 rag_knowledge_base 库）。"""
    try:
        d = _post(f"{MILVUS_URL}/v2/vectordb/entities/query",
                  {"collectionName": collection_name, "dbName": MILVUS_DB,
                   "limit": 16384, "outputFields": ["pk"]}, timeout=60)
        data = d.get("data")
        if isinstance(data, list):
            return len(data)
        return None
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{type(exc).__name__}:{exc}"


def _insert_with_retry(collection_name, docs, retries=3):
    """插入一批，embed 失败（code!=200）时重试；返回 (成功与否, 响应)。"""
    last = None
    for attempt in range(retries):
        resp = insert_batch(collection_name, docs)
        if resp.get("code") in (None, 200):
            return True, resp
        last = resp
        print(f"  第 {attempt + 1} 次插入失败: {resp.get('msg')}，重试...", file=sys.stderr)
        time.sleep(2 * (attempt + 1))
    return False, last


def backfill(index, collection_name, batch_size=200, limit=None, dry_run=False):
    count = 0
    inserted = 0
    actual_name = "_" + collection_name
    docs = []
    for pk, text, meta in es_scroll(index):
        if not text.strip():
            continue
        # pk 用 ES _source.metadata.pk（整数）；缺失时退回 _id（同为整数主键）
        if meta.get("pk") is None:
            try:
                meta["pk"] = int(pk)
            except (TypeError, ValueError):
                meta["pk"] = None
        docs.append({"page_content": text, "metadata": meta})
        count += 1
        if len(docs) >= batch_size:
            if not dry_run:
                ok, resp = _insert_with_retry(collection_name, docs)
                if not ok:
                    print(f"  写入失败（重试耗尽）: {resp.get('msg')}", file=sys.stderr)
                    return count, inserted, False
                flush_collection(actual_name)
                inserted += len(docs)
            docs = []
        if limit and count >= limit:
            break
    if docs and not dry_run:
        ok, resp = _insert_with_retry(collection_name, docs)
        if not ok:
            print(f"  写入失败（重试耗尽）: {resp.get('msg')}", file=sys.stderr)
            return count, inserted, False
        flush_collection(actual_name)
        inserted += len(docs)
    return count, inserted, True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kbs", nargs="+", default=KBS)
    ap.add_argument("--dry-run", action="store_true", help="只读 ES 统计 chunk 数，不写 Milvus")
    ap.add_argument("--limit", type=int, default=None, help="每个库只回灌前 N 条（测试用）")
    ap.add_argument("--batch-size", type=int, default=200)
    args = ap.parse_args(argv)

    report = {"schema": "llmke.hybrid-milvus-backfill.v1", "stage": 2,
              "model": MODEL, "dry_run": args.dry_run,
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kbs": {}}

    for kb in args.kbs:
        es_count = _post(f"{ES_URL}/{kb}/_count", {}, timeout=30).get("count")
        print(f"== {kb}: ES doc 数 = {es_count} ==")
        if args.dry_run:
            n = sum(1 for _ in es_scroll(kb))
            print(f"   dry-run 遍历 chunk 数 = {n}")
            report["kbs"][kb] = {"es_count": es_count, "scanned": n}
            continue
        t0 = time.time()
        count, inserted, ok = backfill(kb, kb, batch_size=args.batch_size,
                                       limit=args.limit, dry_run=False)
        # 实际 collection 名 = "_" + 逻辑名（generate_collection_name_uuid 加前缀）
        actual_name = "_" + kb
        # flush 是异步的：最后再 flush 一次并等待，确保 growing segment 全部落盘可见
        flush_collection(actual_name)
        time.sleep(3)
        milvus_count = milvus_collection_row_count(actual_name)
        print(f"   回灌 chunk={count} 插入={inserted} 用时={time.time()-t0:.1f}s "
              f"Milvus[{actual_name}] rows={milvus_count}")
        report["kbs"][kb] = {"es_count": es_count, "scanned": count,
                             "inserted": inserted, "ok": ok,
                             "milvus_collection": actual_name,
                             "milvus_rows": milvus_count}

    # 硬校验：非 dry-run 且非 limit 时，Milvus rows 必须等于 ES count（HR-04）
    status = "OK"
    if not args.dry_run and args.limit is None:
        for kb in args.kbs:
            r = report["kbs"].get(kb, {})
            if r.get("milvus_rows") != r.get("es_count"):
                status = "FAIL"
                print(f"[FAIL] {kb}: Milvus rows={r.get('milvus_rows')} != ES count={r.get('es_count')}",
                      file=sys.stderr)
    report["status"] = status
    print(f"== 阶段 2 回灌 {status} ==")
    return 0 if status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
