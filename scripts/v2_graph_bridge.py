#!/usr/bin/env python3
"""端到端接线：真实投影载荷 → HippoRAG 索引 → 抽取归一 → 断言层 → 检索（带路线 trace）。

必须用 hipporag 环境跑（模型与引擎在那里）。与 `v2_hipporag_smoke.py` 的区别：
- smoke 只证明"引擎能索引/检索"；
- 本脚本把**抽取结果归一成平台断言**，再用 `pipeline.retrieve` 走"路线判定 → 引擎 → 引用收口"，
  并对照 `planned_route` 与引擎真实 `executed_route`。两者不一致要能被看见。

用法：
  /path/hipporag-venv/bin/python scripts/v2_graph_bridge.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json \
      --queries "产品甲的额度是多少" --require-graph --out /tmp/graph-bridge.json
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.assertions import SourceRef  # noqa: E402
from graph_engine_adapter.engine_hipporag import EngineRetriever, HippoRAGEngine  # noqa: E402
from graph_engine_adapter.mapping import InputUnit, SourceMap, native_key  # noqa: E402
from graph_engine_adapter.normalize import build_store  # noqa: E402
from graph_engine_adapter.pipeline import retrieve  # noqa: E402


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({
                "text": chunk["page_content"],
                "file_id": str(meta.get("file_id", "")),
                "source": meta.get("source", ""),
                "seq": meta.get("chunk_index", 0),
                "artifact_id": str(meta.get("parse_artifact_id") or ""),
                "channel": meta.get("channel", "text"),
            })
    return docs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--queries", nargs="+", required=True)
    ap.add_argument("--save-dir", default="/tmp/hippo-bridge")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--require-graph", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    docs = load_payloads(args.payloads)
    if not docs:
        print(json.dumps({"status": "NO_CHUNKS"}, ensure_ascii=False))
        return 2

    sm = SourceMap()
    for i, d in enumerate(docs):
        sm.add(InputUnit(d["text"], content_uid="c" * 64,
                         parse_artifact_id=d["artifact_id"] or "a" * 64, seq=i,
                         source_ref={"file_id": d["file_id"], "source": d["source"],
                                     "seq": d["seq"], "channel": d["channel"]},
                         channel=d["channel"]))

    def to_refs(raw_sources):
        return [SourceRef(file_id=s.get("file_id", ""),
                          artifact_id=str(s.get("artifact_id") or ""),
                          channel=s.get("channel", "text"),
                          locator=str(s.get("seq", ""))) for s in raw_sources]

    engine = HippoRAGEngine(save_dir=args.save_dir, llm_base_url=args.llm,
                            embedding_base_url=args.embed)
    build = {"skipped": True}
    if not args.skip_build:
        build = engine.build([d["text"] for d in docs])

    openie = engine.openie_docs()
    norm = build_store(openie, lambda idx: to_refs(sm.sources_for(idx)))
    store = norm["store"]

    retriever = EngineRetriever(
        engine, source_lookup=lambda text: to_refs(sm.sources_for(native_key(text))))

    known_files = {d["file_id"] for d in docs}
    results = []
    for query in args.queries:
        out = retrieve(query, store=store, retriever=retriever,
                       require_graph=args.require_graph, top_k=args.top_k,
                       known_files=known_files)
        engine_call = retriever.calls[-1] if retriever.calls else {}
        results.append({
            "query": query,
            "planned_route": out["route"], "planned_reason": out["reason"],
            "executed_route": engine_call.get("executed_route"),
            "engine_trace": engine_call.get("trace"),
            "route_matches": out["route"] == engine_call.get("executed_route"),
            "hit_count": out["hit_count"],
            "citations": out["citations"][:3],
            "invalid_citations": out["invalid_citations"][:3],
            "passed": out["passed"],
        })

    report = {"schema": "llmke.graph-engine.bridge.v1",
              "build": build, "normalize": norm["stats"],
              "corpus": {"chunks": len(docs), "files": len(known_files)},
              "results": results}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")

    summary = {"status": "OK", "normalize": norm["stats"],
               "routes": [{"q": r["query"], "planned": r["planned_route"],
                           "executed": r["executed_route"], "passed": r["passed"]}
                          for r in results]}
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
