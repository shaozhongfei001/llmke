#!/usr/bin/env python3
"""双实例演练：两个进程争同一份租约，同一时刻只有一个真正重建。

用法（由外壳脚本起两个进程）：
  python v2_lease_drill.py --owner inst-A --root /tmp/hippo-lease --lease /tmp/hippo-lease/lease.json
  python v2_lease_drill.py --owner inst-B --root /tmp/hippo-lease --lease /tmp/hippo-lease/lease.json

判据：两个进程各自报告自己的 builds；合计必须为 1（不是 2）。
每个进程都真的会请求重建，靠租约分流——不是靠"另一个没请求"来假装协调。

为了制造重叠窗口，构建里人为 sleep `--build-sleep` 秒（默认 1.5）。
"""

import argparse
import json
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.lease import FileLease, lease_guard  # noqa: E402
from graph_engine_adapter.rebuild import rebuild_if_stale  # noqa: E402
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--lease", required=True)
    ap.add_argument("--duration", type=float, default=90.0)
    ap.add_argument("--build-sleep", type=float, default=1.5)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    docs = load_payloads(args.payloads)
    from graph_engine_adapter.fence import FenceState
    from graph_engine_adapter.engine_hipporag import HippoRAGEngine

    fence = FenceState()
    builds = []
    skipped = []

    def build_once(batch):
        # 续租必须覆盖**整段构建**（含引擎初始化与抽取），只包住 sleep 等于没包：
        # 实测就是漏在外面，长构建超过 TTL 后租约过期，另一个实例合法接管，出现两次构建。
        with lease_guard(sched_lease, interval=3.0):
            time.sleep(args.build_sleep)             # 人为拉长窗口，让两个实例真的重叠
            result = rebuild_if_stale(
                args.root, fence, docs, fencing=sched.lease_fencing,
                build_fn=lambda items, target: HippoRAGEngine(
                    save_dir=target, llm_base_url=args.llm,
                    embedding_base_url=args.embed).build([d["text"] for d in items]))
        if result["status"] == "SKIPPED_FRESH":
            skipped.append(1)
            return {"skipped": True}
        builds.append(result["current"]["documents"])
        return {"documents": result["current"]["documents"]}

    coord = RebuildCoordinator(build_once)
    sched = RebuildScheduler(coord, debounce=0.2, idle_poll=0.2,
                             lease=FileLease(args.lease, owner=args.owner, ttl=30))
    sched_lease = sched.lease

    stop = threading.Event()
    thread = threading.Thread(target=sched.run, args=(stop,), daemon=True)
    thread.start()
    coord.request("upload", files=[f"from-{args.owner}"])

    # 等到"协调器记录到一次成功构建"再收尾：只看本地 builds 列表会在构建还没返回时误判为 0
    deadline = time.time() + args.duration
    while time.time() < deadline and coord.stats()["builds"] == 0:
        time.sleep(0.2)
    time.sleep(1.0)                                 # 给"抢到却失败"的路径一个暴露窗口
    stop.set()
    thread.join(timeout=60)

    try:
        lease_obj = sched.lease
        if lease_obj is not None:
            lease_obj.release()                     # 主动交还，避免 TTL 内挡住另一个实例
    except Exception:  # noqa: BLE001
        pass

    # fencing 校验：用一个落后于当前指针的值模拟"被接管的旧主晚到"，必须被拒
    stale_blocked = None
    try:
        from graph_engine_adapter.rebuild import StaleFencingError
        from graph_engine_adapter.rebuild import rebuild as _rebuild
        from graph_engine_adapter.rebuild import read_pointer
        cur = int((read_pointer(args.root) or {}).get("fencing", 0) or 0)
        # 只有指针里已有 fencing 时才谈"落后"：用 cur-1 模拟旧主晚到
        if cur >= 1:
            _rebuild(args.root, fence, docs, lambda i, t: {"ok": 1}, fencing=cur - 1)
            stale_blocked = False
        else:
            stale_blocked = None
    except Exception as exc:  # noqa: BLE001
        stale_blocked = type(exc).__name__ == "StaleFencingError"

    report = {"owner": args.owner, "builds": len(builds), "skipped_fresh": len(skipped),
              "fencing": sched.lease_fencing, "stale_write_blocked": stale_blocked,
              "documents": builds,
              "stats": sched.stats(), "stopped": not thread.is_alive()}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"owner": args.owner, "builds": len(builds),
                      "not_leader": sched.stats()["not_leader"],
                      "lost_lease": sched.stats()["lost_lease"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
