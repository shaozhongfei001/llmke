#!/usr/bin/env python3
"""端到端：真实载荷 → HippoRAG（可选中日文补丁）→ 断言层 → 检索 → 回答 + 引用核验。

与 `v2_graph_bridge.py` 的区别：bridge 停在"检索到候选"，这里继续走回答组装，
并且**核验引用**（file_id 在上下文里 + quote 是原文子串）。核验不过就判失败，不给假引用。

用法：
  /path/hipporag-venv/bin/python scripts/v2_answer_e2e.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json \
      --queries "多指标对账口径是什么" --save-dir /tmp/hippo-cjk --cjk-compat \
      --require-graph --out /tmp/answer-e2e.json
"""

import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.answer import assemble  # noqa: E402
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
            docs.append({"text": chunk["page_content"], "file_id": str(meta.get("file_id", "")),
                         "source": meta.get("source", ""), "seq": meta.get("chunk_index", 0),
                         "artifact_id": str(meta.get("parse_artifact_id") or ""),
                         "channel": meta.get("channel", "text")})
    return docs


def make_llm_call(url, model, timeout=180):
    def _call(messages, **kw):
        body = json.dumps({"model": model, "messages": messages, "temperature": 0,
                           "max_tokens": kw.get("max_tokens", 512)}).encode()
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    return _call


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--queries", nargs="+", required=True)
    ap.add_argument("--save-dir", default="/tmp/hippo-cjk")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--model", default="qwen2.5-7b-instruct")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--require-graph", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    compat = {"installed": False}
    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import (install_cjk_text_processing,
                                                          is_patched)
        compat = install_cjk_text_processing()
        compat["effective"] = is_patched()

    docs = load_payloads(args.payloads)
    sm = SourceMap()
    for i, d in enumerate(docs):
        sm.add(InputUnit(d["text"], content_uid="c" * 64,
                         parse_artifact_id=d["artifact_id"] or "a" * 64, seq=i,
                         source_ref={"file_id": d["file_id"], "source": d["source"],
                                     "seq": d["seq"], "channel": d["channel"]},
                         channel=d["channel"]))

    def to_refs(raw):
        return [SourceRef(file_id=s.get("file_id", ""), artifact_id=str(s.get("artifact_id") or ""),
                          channel=s.get("channel", "text"), locator=str(s.get("seq", "")))
                for s in raw]

    engine = HippoRAGEngine(save_dir=args.save_dir, llm_base_url=args.llm,
                            embedding_base_url=args.embed)
    build = {"skipped": True}
    if not args.skip_build:
        build = engine.build([d["text"] for d in docs])

    norm = build_store(engine.openie_docs(), lambda idx: to_refs(sm.sources_for(idx)))
    store = norm["store"]
    retriever = EngineRetriever(
        engine, source_lookup=lambda text: to_refs(sm.sources_for(native_key(text))))
    llm_call = make_llm_call(f"{args.llm}/chat/completions", args.model)

    results = []
    for query in args.queries:
        got = retrieve(query, store=store, retriever=retriever, require_graph=args.require_graph,
                       top_k=args.top_k, known_files={d["file_id"] for d in docs})
        ans = assemble(query, store=store, retrieval=got, llm_call=llm_call,
                       require_graph=args.require_graph)
        results.append({"query": query, "route": got["route"],
                        "executed_route": got["executed_route"],
                        "retrieval_passed": got["passed"],
                        "answer": ans["answer"], "answer_reason": ans["reason"],
                        "citations": ans["citations"], "invalid_citations": ans["invalid_citations"],
                        "answer_passed": ans["passed"]})

    report = {"schema": "llmke.graph-engine.answer-e2e.v1", "cjk_compat": compat,
              "build": build, "normalize": norm["stats"], "results": results}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"results": [{k: r[k] for k in ("query", "executed_route",
                                                     "answer_reason", "answer_passed")}
                                  for r in results]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
