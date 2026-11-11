#!/usr/bin/env python3
"""社区/global 报告真实运行：载荷 → 断言层 → 标准事实导出 → 社区 → 报告（+可选叙述）。

只消费经校验的事实导出，不读引擎内部图结构（设计 §6.4）。
叙述（`--narrate`）用回答段配置的模型，输出附带来源；事实与引用以结构化报告为准。

用法：
  /path/hipporag-venv/bin/python scripts/v2_community_report.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json \
      --save-dir /tmp/hippo-cjk --cjk-compat --skip-build --out /tmp/community.json
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.assertions import SourceRef  # noqa: E402
from graph_engine_adapter.community import build_report, narrate  # noqa: E402
from graph_engine_adapter.engine_hipporag import HippoRAGEngine  # noqa: E402
from graph_engine_adapter.mapping import SourceMap  # noqa: E402
from graph_engine_adapter.normalize import build_store
from graph_engine_adapter import entity_link  # noqa: E402


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"text": chunk["page_content"], "file_id": str(meta.get("file_id", "")),
                         "source": meta.get("source", ""), "seq": meta.get("chunk_index", 0)})
    return docs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--save-dir", default="/tmp/hippo-cjk")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--narrate", action="store_true", help="用回答段模型给社区写说明")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    compat = {"installed": False}
    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import (install_cjk_text_processing,
                                                          is_patched)
        compat = install_cjk_text_processing()
        compat["effective"] = is_patched()

    docs = load_payloads(args.payloads)
    if not docs:
        print(json.dumps({"status": "NO_CHUNKS"}, ensure_ascii=False))
        return 2

    # 事实来源按 chunk 键回指：这里只需要 SourceMap 的键→来源能力
    sm = SourceMap()
    from graph_engine_adapter.mapping import InputUnit, native_key  # noqa: E402
    for i, d in enumerate(docs):
        sm.add(InputUnit(d["text"], content_uid="c" * 64, parse_artifact_id="a" * 64, seq=i,
                         source_ref={"file_id": d["file_id"], "source": d["source"],
                                     "seq": d["seq"]}))

    def to_refs(raw):
        return [SourceRef(file_id=s.get("file_id", ""), artifact_id="a" * 64,
                          channel=s.get("channel", "text"), locator=str(s.get("seq", "")))
                for s in raw]

    engine = HippoRAGEngine(save_dir=args.save_dir, llm_base_url=args.llm,
                            embedding_base_url=args.embed)
    norm = build_store(engine.openie_docs(), lambda idx: to_refs(sm.sources_for(idx)))
    norm["store"] = entity_link.apply_linking(norm["store"])[0]
    known = {d["file_id"] for d in docs}
    report = build_report(norm["store"], known_files=known)

    narrative = None
    if args.narrate:
        from graph_engine_adapter.llm_config import make_llm_call
        narrative = narrate(report, make_llm_call())

    out = {"schema": "llmke.community-run.v1", "cjk_compat": compat,
           "normalize": norm["stats"], "known_files": sorted(known),
           "report": report, "narrative": narrative}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({"status": report["status"], "export": report["export"],
                      "communities": len(report["communities"]),
                      "invalid_citations": len(report["citations"]["invalid"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
