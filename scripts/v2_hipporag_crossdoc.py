#!/usr/bin/env python3
"""C1 扩量：真实投影块上跑 HippoRAG，做**跨文档**检索并回指来源。

与 `v2_hipporag_smoke.py` 的差别：输入是 `ingest_pipeline` 产出的真实 payload（多文件），
不是手写短句；查询跨文件，断言命中能解析回各自的 source/file_id。

同时记录两件真实风险：
1. 引擎按正文合并 → 多文件同文会共用 chunk，映射表必须仍能给出多个来源；
2. `phrase_weights /= number_of_occurs` 的 invalid-divide 警告在大样本上是否出现/是否影响排序。

用法：
  /home/szf/data/dev/hipporag-toolenv/bin/python scripts/v2_hipporag_crossdoc.py \
      --payloads /tmp/ingest-999011.json /tmp/ingest-333.json --out /tmp/hippo-cross.json
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter import SourceMap, native_key, units_from_chunks  # noqa: E402

QUERIES = [
    "实体类型体系里对别名的处理规则是什么",
    "产品的最高额度和利率基准",
    "额度分项与总额度的关系",
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--queries", nargs="*", default=QUERIES)
    ap.add_argument("--out", default=None)
    ap.add_argument("--save-dir", default=None,
                    help="默认每次新建目录；沿用旧目录会把历史 chunk 一起检索出来")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--max-docs", type=int, default=0, help=">0 时只取前 N 块，用于控时")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args(argv)

    chunks = []
    for path in args.payloads:
        chunks.extend((json.loads(open(path, encoding="utf-8").read()).get("chunks") or []))
    if args.max_docs:
        chunks = chunks[:args.max_docs]
    if not chunks:
        print(json.dumps({"status": "NO_INPUT"}, ensure_ascii=False))
        return 2

    sm = SourceMap().extend(units_from_chunks(chunks))
    texts = [c["page_content"] for c in chunks]
    expect = len({native_key(t) for t in texts})

    os.environ.setdefault("OPENAI_API_KEY", "sk-local")
    from hipporag import HippoRAG
    from hipporag.utils.config_utils import BaseConfig

    # 引擎是持久化存储：沿用旧目录会命中历史 chunk（实测 66 输入却读出 68 块）
    if not args.save_dir:
        import time as _t
        args.save_dir = f"/tmp/hippo-cross-{_t.strftime('%H%M%S')}"
    config = BaseConfig(save_dir=args.save_dir, llm_name="qwen2.5-7b-instruct",
                        llm_base_url=args.llm, embedding_model_name="text-embedding-bge-m3",
                        embedding_base_url=args.embed, openie_mode="online")
    hp = HippoRAG(global_config=config)
    hp.index(texts)

    results, problems = [], []
    for query in args.queries:
        sols = hp.retrieve([query], num_to_retrieve=args.top_k)
        hits = []
        for sol in (sols or []):
            for doc_text in (getattr(sol, "docs", None) or []):
                key = native_key(doc_text)
                hits.append({"native_key": key, "text": doc_text[:50],
                             "sources": sm.sources_for(key)})
        resolved = [h for h in hits if h["sources"]]
        unmapped = [h["native_key"] for h in hits if not h["sources"]]
        results.append({"query": query, "hits": len(hits), "resolved": len(resolved),
                        "unmapped": unmapped,
                        "files": sorted({s["file_id"] for h in resolved for s in h["sources"]})})
        if hits and not resolved:
            problems.append(f"query 无法回指来源: {query}")

    engine_rows = hp.chunk_embedding_store.get_all_id_to_rows()
    report = {"status": "OK", "save_dir": args.save_dir,
              "entities": len(hp.entity_embedding_store.get_all_id_to_rows()),
              "facts": len(hp.fact_embedding_store.get_all_id_to_rows()),
              "input": {"chunks": len(chunks), "unique_texts": expect,
                        "engine_chunks": len(engine_rows),
                        "merged": len(texts) - len(engine_rows)},
              "mapping": sm.stats(), "queries": results,
              "src_files": sorted({s["file_id"] for k in sm._by_native for s in sm.sources_for(k)})}
    if len(engine_rows) != expect:
        problems.append(f"引擎 chunk 数 {len(engine_rows)} != 去重正文数 {expect}")
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
