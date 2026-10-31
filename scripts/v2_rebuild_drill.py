#!/usr/bin/env python3
"""撤权→隔离重建→切读 的真实演练。

流程（与设计 §5 一致：先挡读、再重建）：
1. fence 撤权某文件；
2. 用**存活文件**在**新目录**建快照（build_fn = HippoRAGEngine.build）；
3. 指针切换并带上 fence 代次；
4. 验证三件事：
   a. 新快照里没有已撤权文件的正文；
   b. 旧快照（代次 0）在 fence 生效后被拒绝读；
   c. 新快照（代次 1）可以正常读。

用法：
  /path/hipporag-venv/bin/python scripts/v2_rebuild_drill.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json \
      --revoke 329 --root /tmp/hippo-rebuild --out /tmp/rebuild-drill.json
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.engine_hipporag import HippoRAGEngine  # noqa: E402
from graph_engine_adapter.fence import FenceState, StaleIndexError  # noqa: E402
from graph_engine_adapter.rebuild import read_pointer, rebuild  # noqa: E402


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")),
                         "text": chunk["page_content"]})
    return docs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--revoke", nargs="+", default=["329"])
    ap.add_argument("--root", default="/tmp/hippo-rebuild")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    docs = load_payloads(args.payloads)
    fence = FenceState()
    revoked_gen = fence.revoke(args.revoke)

    def build_fn(items, target):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.build([d["text"] for d in items])

    out = rebuild(args.root, fence, docs, build_fn)
    pointer = read_pointer(args.root)
    new_dir = pointer["dir"]

    # a. 新快照里不应出现已撤权文件的正文
    engine_new = HippoRAGEngine(save_dir=new_dir, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
    rows = engine_new.hp.chunk_embedding_store.get_all_id_to_rows()
    contents = [str(r.get("content", "")) for r in rows.values()]
    revoked_texts = [d["text"] for d in docs if d["file_id"] in args.revoke]
    leaked = [t[:30] for t in revoked_texts if any(t[:30] in c for c in contents)]

    # b/c. 旧代次被拒、新代次可读（这里只验代次判定，不重复跑检索）
    stale_blocked = False
    try:
        from graph_engine_adapter.fence import assert_index_fresh
        assert_index_fresh(0, fence)
    except StaleIndexError:
        stale_blocked = True
    fresh_ok = True
    try:
        from graph_engine_adapter.fence import assert_index_fresh
        assert_index_fresh(pointer["generation"], fence)
    except StaleIndexError:
        fresh_ok = False

    report = {"schema": "llmke.rebuild-drill.v1",
              "revoked": args.revoke, "fence_generation": revoked_gen,
              "pointer": pointer, "snapshot_chunks": len(rows),
              "new_snapshot_has_revoked_text": leaked,
              "stale_index_blocked": stale_blocked, "fresh_index_allowed": fresh_ok,
              "build_result": out.get("build_result"),
              "passed": bool(not leaked and stale_blocked and fresh_ok)}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("fence_generation", "snapshot_chunks",
                                             "new_snapshot_has_revoked_text",
                                             "stale_index_blocked", "fresh_index_allowed",
                                             "passed")}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
