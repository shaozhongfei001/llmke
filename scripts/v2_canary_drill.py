#!/usr/bin/env python
"""灰度开关演练：同一进程内改配置 → 下一次重建换路径 → 回退后再换回来。

为什么不用真引擎：这条验的是**调度决策**（走 full 还是 delta、改配置是否即时生效），
不是抽取质量。用假 builder 可以在 1 秒内反复切换，而真引擎一次要几十秒，
反而看不清"到底哪次走了哪条路"。

四个断言（缺一不可）：
1. 灰度内的 KB：请求 delta，实际也 delta（`requested_mode == effective_mode == delta`）；
2. 灰度外的 KB：同一份配置下仍然 full；
3. 改配置文件后**不重建进程**，下一次重建即按新配置执行（这就是"不重启回退"）；
4. 回退后读路径仍能读到快照（指针有效、文档数正确），不是"回退就失联"。
"""

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services/rag-alg/index_data_service"))


def docs(*pairs):
    return [{"file_id": fid, "text": text} for fid, text in pairs]


def full_build(live, target):
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "graph.json"), "w", encoding="utf-8") as fh:
        json.dump({"chunks": [d["text"] for d in live]}, fh)
    return {"chunks": len(live)}


def delta_apply(target, texts):
    with open(os.path.join(target, "graph.json"), encoding="utf-8") as fh:
        current = json.load(fh)
    current["chunks"] = list(texts)
    with open(os.path.join(target, "graph.json"), "w", encoding="utf-8") as fh:
        json.dump(current, fh)
    return {"deleted": 0, "added": 0, "chunks": len(texts)}


def write_policy(path, scope, mode="delta"):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"scope": scope, "mode": mode, "default": "full"}, fh)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/tmp/canary-drill")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    from graph_engine_adapter.canary import load as load_policy
    from graph_engine_adapter.fence import FenceState
    from graph_engine_adapter.rebuild import (read_pointer, rebuild_by_policy,
                                              rebuild)

    if os.path.isdir(args.root):
        shutil.rmtree(args.root)
    os.makedirs(args.root)
    policy_path = os.path.join(args.root, "canary.json")
    fence = FenceState()
    problems, steps = [], []

    # 先做一次全量：delta 需要基准快照（没有基准时策略应明确报错，不静默回退）
    base_docs = docs(("1", "a"), ("2", "b"))
    rebuild(args.root, fence, base_docs, full_build, fencing=1)

    # 1) 灰度内 KB：delta
    write_policy(policy_path, ["kb-1"], "delta")
    policy = load_policy(policy_path)
    out = rebuild_by_policy(args.root, fence, docs(("1", "a"), ("2", "c")),
                            "kb-1", policy, full_build, delta_apply, fencing=1)
    steps.append({"step": "canary-delta", "requested": out["requested_mode"],
                  "effective": out["effective_mode"],
                  "pointer_mode": read_pointer(args.root).get("mode")})
    if not (out["requested_mode"] == out["effective_mode"] == "delta"):
        problems.append(f"灰度内未走 delta：{out['requested_mode']} → {out['effective_mode']}")

    # 2) 灰度外 KB：同一配置仍是 full
    out2 = rebuild_by_policy(args.root, fence, docs(("1", "a"), ("2", "c"), ("3", "d")),
                             "kb-2", policy, full_build, delta_apply, fencing=1)
    steps.append({"step": "outside-full", "requested": out2["requested_mode"],
                  "effective": out2["effective_mode"],
                  "pointer_mode": read_pointer(args.root).get("mode")})
    if out2["effective_mode"] != "full":
        problems.append(f"灰度外被影响：effective={out2['effective_mode']}")

    # 3) 热改配置：把 kb-1 移出灰度，同一进程立刻回到 full
    write_policy(policy_path, [], "delta")
    policy2 = load_policy(policy_path)          # 重新 load，不重启进程
    out3 = rebuild_by_policy(args.root, fence, docs(("1", "a"), ("2", "c"), ("3", "e")),
                             "kb-1", policy2, full_build, delta_apply, fencing=1)
    steps.append({"step": "reverted-full", "requested": out3["requested_mode"],
                  "effective": out3["effective_mode"],
                  "pointer_mode": read_pointer(args.root).get("mode")})
    if out3["effective_mode"] != "full":
        problems.append(f"回退未生效：effective={out3['effective_mode']}")

    # 4) 回退后读路径仍可用
    pointer = read_pointer(args.root)
    graph_file = os.path.join(pointer["dir"], "graph.json")
    readable = os.path.isfile(graph_file)
    chunks = json.load(open(graph_file, encoding="utf-8"))["chunks"] if readable else []
    if not readable:
        problems.append("回退后指针指向的快照不可读")
    if pointer.get("documents") != len(chunks):
        problems.append(f"指针 documents={pointer.get('documents')} 与实际块数 {len(chunks)} 不符")

    report = {"status": "OK" if not problems else "FAIL", "steps": steps,
              "policy": policy2.describe(), "problems": problems,
              "pointer": {"mode": pointer.get("mode"), "documents": pointer.get("documents"),
                          "generation": pointer.get("generation")},
              "read_after_revert": {"readable": readable, "chunks": len(chunks)}}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"status": report["status"],
                      "modes": [s["effective"] for s in steps],
                      "problems": problems}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
