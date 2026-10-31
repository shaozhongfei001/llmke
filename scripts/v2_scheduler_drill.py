#!/usr/bin/env python3
"""调度器真实演练：后台循环 + 突发请求合并 + 优雅停机。

判据是**行为**不是耗时：
1. 3 条突发请求只产生 1 次真实构建；
2. 再 1 条请求产生第 2 次构建；
3. 停机后循环退出、不再构建，指针代次与快照文档数正确、新鲜度通过。

用法：
  /path/hipporag-venv/bin/python scripts/v2_scheduler_drill.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json --cjk-compat --out /tmp/scheduler.json
"""

import argparse
import json
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.fence import FenceState  # noqa: E402
from graph_engine_adapter.rebuild import check_freshness, read_pointer, rebuild  # noqa: E402
from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator  # noqa: E402
from graph_engine_adapter.rebuild_scheduler import RebuildScheduler  # noqa: E402


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")), "text": chunk["page_content"]})
    return docs


def wait_for(predicate, timeout=180, interval=0.2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", default=f"/tmp/hippo-scheduler-{int(time.time())}")
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

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine

    builds = []

    def build_once(batch):
        result = rebuild(args.root, fence, docs,
                         lambda items, target: HippoRAGEngine(
                             save_dir=target, llm_base_url=args.llm,
                             embedding_base_url=args.embed).build([d["text"] for d in items]))
        builds.append(result["current"]["documents"])
        return {"documents": result["current"]["documents"]}

    coord = RebuildCoordinator(build_once, max_pending=50)
    sched = RebuildScheduler(coord, debounce=0.5, idle_poll=0.2)

    stop = threading.Event()
    thread = threading.Thread(target=sched.run, args=(stop,), daemon=True)
    thread.start()

    for i in range(3):
        coord.request("upload", files=[f"f{i}"])
    first_ok = wait_for(lambda: coord.stats()["builds"] >= 1)

    coord.request("upload", files=["f3"])
    second_ok = wait_for(lambda: coord.stats()["builds"] >= 2)

    stop.set()
    thread.join(timeout=15)
    stopped = not thread.is_alive()
    builds_after_stop = coord.stats()["builds"]
    time.sleep(1.0)
    no_extra_build = coord.stats()["builds"] == builds_after_stop

    pointer = read_pointer(args.root) or {}
    fresh = check_freshness(pointer, docs, fence)
    expected_docs = len([d for d in docs if not fence.is_revoked(d["file_id"])])

    passed = (first_ok and second_ok and stopped and no_extra_build
              and builds == [expected_docs, expected_docs]
              and pointer.get("documents") == expected_docs
              and fresh["stale"] is False)
    report = {"schema": "llmke.scheduler-drill.v1",
              "first_batch_ok": first_ok, "second_batch_ok": second_ok,
              "builds": builds, "stats": sched.stats(),
              "stopped_cleanly": stopped, "no_build_after_stop": no_extra_build,
              "pointer": pointer, "freshness": fresh,
              "expected_documents": expected_docs, "passed": passed}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"passed": passed, "builds": builds,
                      "stopped": stopped, "no_build_after_stop": no_extra_build,
                      "documents": pointer.get("documents"),
                      "debounce_waits": sched.stats()["debounce_waits"],
                      "idle": sched.stats()["idle"]}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
