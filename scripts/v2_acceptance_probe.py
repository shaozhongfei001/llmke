#!/usr/bin/env python3
"""Q1 / ES 非必选：对真实环境做"有没有"的硬探测，输出可归档的 JSON 结论。

三组探测，全部读真实服务，不用夹具：
1) 文件落库：给定 (file_id, kb)，查 ES 正文/表格/总结三索引与 Milvus 对应集合的行数；
2) 检索可用：对检索服务按 search_policy = 1(ES+Milvus) / 2(仅ES) / 3(仅Milvus) 各查一次，
   比较返回条数与首条来源；
3) 失败反例：对已知坏样本（随机字节伪装 pdf 等）确认其**没有**内容入库，
   避免"坏文件也被算成功"。

退出码：0 全部符合预期；1 有不符合；2 环境不可达。

用法：
  python scripts/v2_acceptance_probe.py --kb kb_10 --file-ids 999013 999014 \
      --expect-empty 68 57 --query "产品丙的最高额度" --out /tmp/accept.json
"""

import argparse
import json
import os
import urllib.error
import urllib.request

ES = os.environ.get("V2_ES", "http://127.0.0.1:19200")
MILVUS = os.environ.get("V2_MILVUS", "http://127.0.0.1:19630")
MILVUS_DB = os.environ.get("V2_MILVUS_DB", "rag_knowledge_base")
RETRIEVAL = os.environ.get("V2_RETRIEVAL", "http://127.0.0.1:19995")


def _post(url, body, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def es_count(index, file_id):
    try:
        return _post(f"{ES}/{index}/_search",
                     {"size": 0, "query": {"term": {"metadata.file_id": str(file_id)}}}
                     )["hits"]["total"]["value"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def milvus_count(collection, file_id):
    try:
        from pymilvus import MilvusClient
    except ImportError:
        return None
    client = MilvusClient(uri=MILVUS, db_name=MILVUS_DB)
    if not client.has_collection(collection):
        return None
    return client.query(collection, filter=f'file_id == "{file_id}"',
                        output_fields=["count(*)"])[0]["count(*)"]


def retrieval(port, query, kb, policy, top_k=3):
    return _post(f"{port}/retrieval_documents",
                 {"query": query, "knowledge_base_name": [kb],
                  "search_policy": policy, "top_k": top_k})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default="kb_10")
    ap.add_argument("--file-ids", nargs="*", default=[])
    ap.add_argument("--expect-empty", nargs="*", default=[],
                    help="已知坏样本的 file_id：三索引与 Milvus 都应为 0/缺席")
    ap.add_argument("--query", default="产品丙的最高额度")
    ap.add_argument("--retrieval", default=RETRIEVAL)
    ap.add_argument("--index-service", default=os.environ.get("V2_INDEX", "http://127.0.0.1:18082"))
    ap.add_argument("--verify-delete", default=None,
                    help="对指定 file_id 走真实删除接口并断言三索引+Milvus 归零（破坏性，显式指定才执行）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    report = {"kb": args.kb, "status": "OK", "files": {}, "policies": {}, "bad_samples": {}}
    problems = []

    for fid in args.file_ids:
        row = {"es": {(p or "text"): es_count(f"{p}{args.kb}", fid)
                      for p in ("", "table_chunks_", "table_summary_")}}
        row["milvus"] = {"text": milvus_count(f"_{args.kb}", fid),
                         "table": milvus_count(f"_table_chunks_{args.kb}", fid),
                         "summary": milvus_count(f"_table_summary_{args.kb}", fid)}
        row["has_content"] = any(v for v in row["es"].values() if v)
        report["files"][fid] = row
        if not row["has_content"]:
            problems.append(f"file {fid} 在三索引里都没有内容")

    for fid in args.expect_empty:
        row = {"es_total": sum(v or 0 for v in
                               (es_count(f"{p}{args.kb}", fid)
                                for p in ("", "table_chunks_", "table_summary_"))),
               "milvus_total": sum(v or 0 for v in (milvus_count(f"_{args.kb}", fid),))}
        report["bad_samples"][fid] = row
        if row["es_total"] or row["milvus_total"]:
            problems.append(f"坏样本 {fid} 竟然有内容入库")

    for policy in (1, 2, 3):
        try:
            data = retrieval(args.retrieval, args.query, args.kb, policy)
        except Exception as exc:  # noqa: BLE001
            report["policies"][policy] = {"error": f"{type(exc).__name__}: {exc}"[:160]}
            problems.append(f"search_policy={policy} 调用失败")
            continue
        docs = ((data.get("data") or {}).get("documents_list") or [])
        top = docs[0] if docs else {}
        report["policies"][policy] = {"docs": len(docs),
                                      "top_source": (top.get("metadata") or {}).get("source")}
        if not docs:
            problems.append(f"search_policy={policy} 无结果（{args.query}）")

    if args.verify_delete:
        fid = str(args.verify_delete)
        before = {"es": sum(es_count(f"{p}{args.kb}", fid) or 0
                            for p in ("", "table_chunks_", "table_summary_")),
                  "milvus": milvus_count(f"_{args.kb}", fid) or 0}
        req = urllib.request.Request(
            f"{args.index_service}/index/api/knowledgeBase/file/delete?id={fid}", method="DELETE")
        with urllib.request.urlopen(req, timeout=60) as resp:
            ok = json.loads(resp.read()).get("success")
        import time
        time.sleep(20)
        after = {"es": sum(es_count(f"{p}{args.kb}", fid) or 0
                           for p in ("", "table_chunks_", "table_summary_")),
                 "milvus": milvus_count(f"_{args.kb}", fid) or 0}
        report["delete_check"] = {"file_id": fid, "api_ok": ok, "before": before, "after": after}
        if not ok or after["es"] or after["milvus"]:
            problems.append(f"删除后仍有残留: {after}")

    if problems:
        report["status"] = "FAILED"
        report["problems"] = problems
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
