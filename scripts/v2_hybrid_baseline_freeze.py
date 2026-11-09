#!/usr/bin/env python
"""HybridRetrieval 阶段 0 基线冻结：记录 kb_9/kb_1004 召回快照（只读，不改任何存储）。

用途
----
在「统一向量库 + 混合检索收敛」改造前，固化两条知识库的检索现状，作为阶段 5
「全量重建 + E2E 回归」的对比基准。本脚本只读：
- ES doc 数（kb_9 / kb_1004）；
- 19995 legacy 检索服务 `/retrieval_documents` 的召回结果（含 pk/search_type/score/文本摘要）；
- 直接查 ES 记录 `_id` 与 `_source.metadata.pk` 的真值，供阶段 1「来源身份对齐」验收对比。

诚实边界
--------
- 记录的是「现状」而非「目标」：若某精确关键词召回为 0、或 metadata.pk 为 None，
  一律如实写入，不改写、不粉饰——基线就是对照物，粉饰会让阶段 5 的「无回退」判断失真。
- 精确关键词以验收标准第 4 条为准：AAA档 / 5000万 / T-CORE-001。实测「5000万」单查
  ES 命中 0（数据里是「5000万元」），本脚本按原词记录 0 条，并额外记录「5000万元」变体。

运行
----
    python3 scripts/v2_hybrid_baseline_freeze.py --out docs/dispatch/evidence/hybrid-baseline-0.json
"""

import argparse
import json
import sys
import time
import urllib.request

RETRIEVAL_URL = "http://127.0.0.1:19995/retrieval_documents"
ES_URL = "http://127.0.0.1:19200"
KBS = ["kb_9", "kb_1004"]

# 5 条典型 query：前 3 条是验收标准第 4 条的精确关键词，后 2 条是普通业务问句。
QUERIES = ["AAA档", "5000万", "T-CORE-001", "授信额度是多少", "流动资金贷款期限"]

# kb_1004 是英文语料库（DK 园艺书 Allotment month by month），中文 query 天然 0 命中；
# 为它单独补英文 query，否则阶段 5 对 kb_1004 的「无回退」无法测量。
QUERIES_KB_1004_EN = ["allotment", "vegetable", "gardening", "compost", "sowing"]


def http_json(url, payload=None, timeout=60):
    req = urllib.request.Request(
        url, data=(json.dumps(payload).encode("utf-8") if payload is not None else None),
        headers={"Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def es_count(index):
    try:
        d = http_json(f"{ES_URL}/{index}/_count", timeout=10)
        return d.get("count")
    except Exception as exc:  # noqa: BLE001 - 读不到就是读不到，如实记录
        return f"ERROR:{type(exc).__name__}"


def es_pk_truth(index):
    """直接查 ES 一条文档，记录 _id 与 _source.metadata.pk 真值。"""
    try:
        d = http_json(f"{ES_URL}/{index}/_search?size=1", timeout=10)
        hits = d.get("hits", {}).get("hits") or []
        if not hits:
            return {"hits": 0}
        h = hits[0]
        src = h.get("_source") or {}
        meta = src.get("metadata") or {}
        return {"_id": h.get("_id"), "metadata_pk": meta.get("pk"),
                "file_id": meta.get("file_id"), "chunk_index": meta.get("chunk_index"),
                "page_head": (src.get("page_content") or "")[:60]}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def retrieval(kb, query):
    payload = {
        "query": query,
        "knowledge_base_name": [kb],
        "top_k": 5,
        "top_n": 5,
        "enabled_graph": False,
        "enabled_faq": False,
        "enabled_rerank": True,
    }
    started = time.time()
    try:
        d = http_json(RETRIEVAL_URL, payload, timeout=120)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    docs = (d.get("data") or {}).get("documents_list") or []
    rows = []
    for x in docs:
        meta = x.get("metadata") or {}
        # pk 在返回结果的**顶层 `pk` 字段**（process_return_results 第 762 行），
        # metadata 里没有 pk。图检索（retrieval_graph）的 pk 却在 metadata.pk ——
        # 这是阶段 1「来源身份对齐」要统一的位置不一致，基线如实记录两处。
        rows.append({
            "pk": x.get("pk"),
            "metadata_pk": meta.get("pk"),
            "search_type": meta.get("search_type"),
            "score": meta.get("score"),
            "file_id": meta.get("file_id"),
            "chunk_index": meta.get("chunk_index"),
            "text": (x.get("page_content") or "")[:120].replace("\n", " "),
        })
    return {"code": d.get("code"), "msg": d.get("msg"),
            "hits": len(rows), "seconds": round(time.time() - started, 2), "docs": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/dispatch/evidence/hybrid-baseline-0.json")
    args = ap.parse_args(argv)

    report = {
        "schema": "llmke.hybrid-retrieval-baseline.v1",
        "stage": 0,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "retrieval_url": RETRIEVAL_URL,
        "es": {kb: {"count": es_count(kb), "pk_truth": es_pk_truth(kb)} for kb in KBS},
        "queries": {},
    }
    for kb in KBS:
        for q in QUERIES:
            report["queries"][f"{kb}::{q}"] = retrieval(kb, q)
        # 额外记录「5000万元」变体（数据里真实形态），避免基线漏掉可命中的精确词
        report["queries"][f"{kb}::5000万元"] = retrieval(kb, "5000万元")
        # kb_1004 英文库补英文 query，否则该库基线恒 0 无法做「无回退」测量
        if kb == "kb_1004":
            for q in QUERIES_KB_1004_EN:
                report["queries"][f"{kb}::en::{q}"] = retrieval(kb, q)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    # 控制台摘要
    print(f"基线快照写入 {args.out}")
    print(f"ES doc 数: " + ", ".join(
        f"{kb}={report['es'][kb]['count']}" for kb in KBS))
    for kb in KBS:
        truth = report["es"][kb]["pk_truth"]
        print(f"{kb} ES 真值: _id={truth.get('_id')} metadata.pk={truth.get('metadata_pk')}")
    for key, row in report["queries"].items():
        if "error" in row:
            print(f"  {key}: ERROR {row['error']}")
        else:
            pks = [d.get("pk") for d in row.get("docs", [])]
            print(f"  {key}: hits={row.get('hits')} pk={pks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
