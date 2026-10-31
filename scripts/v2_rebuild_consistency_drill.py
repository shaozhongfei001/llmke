#!/usr/bin/env python3
"""重建一致性演练：写并发（重建期间新增文件）与多进程读者。

两件事，都是"撤权不出窗口"在多副本/写入侧的延伸：

C. **写并发**：重建开始后新增文件 → 本次快照必然不含它。
   正确行为是**报告 stale（数据缺失）**，而不是假装已覆盖；再跑一次重建应当变成 fresh。
   注意语义：缺文件 ≠ 越权，所以不阻断读；越权由 fence 管。两者混在一起会让无关故障变成整体不可用。

D. **多进程读者**：4 个独立进程在重建窗口内反复"打开索引"，必须全部被拒；
   重建完成后必须全部放行且代次一致（不能出现某个进程还用旧指针）。

窗口延长：真实重建在 5 个块上只要 <1s，采样不到，所以构建函数里**人为 sleep 2s**，
这段等待写进结论里，不假装是真实耗时。

用法：
  /path/hipporag-venv/bin/python scripts/v2_rebuild_consistency_drill.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json --cjk-compat --out /tmp/consistency.json
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.fence import FenceState, StaleIndexError, assert_index_fresh  # noqa: E402
from graph_engine_adapter.rebuild import (check_freshness, read_pointer,  # noqa: E402
                                          rebuild)

WINDOW_SECONDS = 2.0


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")), "text": chunk["page_content"]})
    return docs


def reader_probe(root, fence_generation, deadline, done, queue):
    """独立进程：窗口内尽量多次"打开索引"，记录放行/拒绝次数。

    用 mp.Event 收尾而不是固定时长：真实重建耗时不可预估（要调用模型），
    按秒数猜窗口会把"完成后"的采样算进窗口，得出假结论。
    """
    allowed = blocked = 0
    seen = []
    while not done.is_set() and time.time() < deadline:
        pointer = read_pointer(root)
        seen.append((pointer or {}).get("generation"))
        fence = FenceState(generation=fence_generation)
        try:
            assert_index_fresh((pointer or {}).get("generation"), fence)
            allowed += 1
        except StaleIndexError:
            blocked += 1
        time.sleep(0.01)
    queue.put({"pid": os.getpid(), "allowed": allowed, "blocked": blocked,
               "final_generation": (read_pointer(root) or {}).get("generation"),
               "max_seen": max([g for g in seen if g is not None], default=None),
               "iterations": len(seen)})


def scenario_write_concurrent(root, docs):
    """C：重建期间新增文件 → stale；再重建 → fresh。"""
    fence = FenceState()
    added = {}

    def slow_build(items, target):
        os.makedirs(target, exist_ok=True)
        time.sleep(WINDOW_SECONDS)
        # 模拟"重建进行中用户上传了新文件"：docs 列表被追加，但本次快照已经切片，不会包含它
        added["doc"] = {"file_id": "340", "text": "重建期间新增的文档正文"}
        docs.append(added["doc"])
        return {"built": len(items)}

    rebuild(root, fence, docs, slow_build)
    pointer = read_pointer(root)
    stale = check_freshness(pointer, docs)

    # 第二次重建（此时 docs 已含新文件）应恢复 fresh
    rebuild(root, fence, docs, lambda items, target: os.makedirs(target, exist_ok=True) or {"ok": 1})
    fresh = check_freshness(read_pointer(root), docs)
    return {"first_snapshot_stale": stale,
            "second_snapshot_fresh": fresh,
            "documents_in_first": pointer.get("documents"),
            "documents_in_second": (read_pointer(root) or {}).get("documents")}


def scenario_multi_reader(root, docs, build_fn):
    """D：多进程读者在窗口内全被拒，完成后全部放行且代次一致。"""
    fence = FenceState()
    rebuild(root, fence, docs, lambda items, target: os.makedirs(target, exist_ok=True) or {"ok": 1})
    fence.revoke(["329"])                       # 代次 1

    queue = mp.Queue()
    done = mp.Event()
    deadline = time.time() + 300            # 防挂死；正常由 done 收尾
    procs = [mp.Process(target=reader_probe,
                        args=(root, fence.generation, deadline, done, queue))
             for _ in range(4)]
    for p in procs:
        p.start()
    time.sleep(0.5)                          # 让读者先进入采样
    rebuild(root, fence, docs, build_fn)
    done.set()
    for p in procs:
        p.join(timeout=30)

    results = [queue.get(timeout=10) for _ in procs]
    # 读者看到的代次要覆盖"完成后"，所以单独从主进程确认一次
    final_pointer = read_pointer(root) or {}
    after = check_freshness(final_pointer, docs, fence)
    return {"readers": results,
            "all_blocked_in_window": all(r["blocked"] > 0 and r["allowed"] == 0 for r in results),
            "generations_consistent": len({r["final_generation"] for r in results}) == 1,
            "pointer_generation_after": final_pointer.get("generation"),
            "fence_generation": fence.generation,
            "after": after,
            "window_seconds": WINDOW_SECONDS}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", default="/tmp/hippo-consistency")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine

    def real_slow_build(items, target):
        time.sleep(WINDOW_SECONDS)
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.build([d["text"] for d in items])

    docs_c = load_payloads(args.payloads)
    c = scenario_write_concurrent(os.path.join(args.root, "write"), docs_c)

    docs_d = load_payloads(args.payloads)
    d = scenario_multi_reader(os.path.join(args.root, "readers"), docs_d, real_slow_build)

    passed = (c["first_snapshot_stale"]["stale"] and not c["second_snapshot_fresh"]["stale"]
              and d["all_blocked_in_window"] and d["generations_consistent"]
              and d["pointer_generation_after"] == 1        # 重建后指针代次已提升
              and d["after"]["stale"] is False)
    report = {"schema": "llmke.rebuild-consistency.v1",
              "write_concurrent": c, "multi_reader": d,
              "caveat": f"重建窗口被人为 sleep {WINDOW_SECONDS}s 以便采样，不代表真实耗时",
              "passed": passed}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"passed": passed,
                      "write": {"first_stale": c["first_snapshot_stale"]["stale"],
                                "second_fresh": not c["second_snapshot_fresh"]["stale"],
                                "missing": c["first_snapshot_stale"]["missing"]},
                      "readers": d["readers"],
                      "all_blocked": d["all_blocked_in_window"],
                      "gen_consistent": d["generations_consistent"]}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
