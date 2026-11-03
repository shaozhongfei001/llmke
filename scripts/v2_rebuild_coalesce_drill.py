#!/usr/bin/env python3
"""重建合并演练：3 次快速变更只触发 1 次真实重建，再来一次才触发第 2 次。

要点：合并的意义是**省重建次数**，不是"看起来更快"。所以判据是
"构建次数 == 预期批次" + "快照覆盖全部存活文档"，而不是耗时。

用法：
  /path/hipporag-venv/bin/python scripts/v2_rebuild_coalesce_drill.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json --cjk-compat --out /tmp/coalesce.json
"""

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.fence import FenceState  # noqa: E402
from graph_engine_adapter.rebuild import check_freshness, read_pointer, rebuild  # noqa: E402
from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator  # noqa: E402


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")), "text": chunk["page_content"]})
    return docs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--revoke", nargs="*", default=[])
    ap.add_argument("--root", default="/tmp/hippo-coalesce")
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
    if args.revoke:
        fence.revoke(args.revoke)

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine

    builds = []

    def build_once(batch):
        files = sorted({f for item in batch for f in item["files"]})
        result = rebuild(args.root, fence, docs,
                         lambda items, target: HippoRAGEngine(
                             save_dir=target, llm_base_url=args.llm,
                             embedding_base_url=args.embed).build([d["text"] for d in items]))
        builds.append({"requested_files": files, "documents": result["current"]["documents"]})
        return {"documents": result["current"]["documents"]}

    coord = RebuildCoordinator(build_once)

    # 三次快速变更（模拟连续上传/编辑）
    t0 = time.time()
    for i in range(3):
        coord.request("upload", files=[f"f{i}"])
    first = coord.run_once()
    elapsed_first = round(time.time() - t0, 1)

    pointer1 = read_pointer(args.root)
    live_docs = [d for d in docs if not fence.is_revoked(d["file_id"])]
    fresh1 = check_freshness(pointer1, docs, fence)

    # 再来一次变更
    coord.request("upload", files=["f3"])
    second = coord.run_once()
    fresh2 = check_freshness(read_pointer(args.root), docs, fence)

    stats = coord.stats()
    passed = (first["status"] == "BUILT" and first["requests"] == 3
              and second["status"] == "BUILT" and second["requests"] == 1
              and stats["builds"] == 2 and len(builds) == 2
              and pointer1["documents"] == len(live_docs)
              and not fresh1["stale"] and not fresh2["stale"])

    report = {"schema": "llmke.rebuild-coalesce.v1",
              "first_run": {"status": first["status"], "requests": first["requests"],
                            "elapsed_s": elapsed_first},
              "second_run": {"status": second["status"], "requests": second["requests"]},
              "builds": builds, "stats": stats,
              "snapshot_documents": pointer1["documents"],
              "expected_documents": len(live_docs),
              "freshness_after_first": fresh1, "freshness_after_second": fresh2,
              "passed": passed}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"passed": passed, "builds": stats["builds"],
                      "first_requests": first["requests"],
                      "documents": pointer1["documents"],
                      "fresh1": fresh1["stale"], "fresh2": fresh2["stale"]}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
