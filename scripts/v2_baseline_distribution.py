#!/usr/bin/env python
"""同一语料多次独立构建的**波动分布**：给灰度判定一个可量化的容差。

为什么需要：实测 10 块语料上，"同一语料两份全量快照"的抽取事实就不同（6 vs 5），
检索 top1 只有 0.667。这意味着任何 full-vs-delta 的单次对比都无法归因——
差异到底是"改坏了"还是"这一次抽得不一样"，只有**同一个语料自身的分布**能回答。

做法：把 N 份同语料快照两两比较，统计 facts 差异与检索一致率的分布，
给出 `tolerance`（观测到的最大事实差异、最小 top1/ordered/jaccard）。
灰度判定应把 a-vs-b 的差异放进这个区间里看，而不是跟"0 差异"比。

诚实边界：N 小（默认 3）只能给出**下界性质的**容差；语料越大波动越大，
换语料必须重跑，这里的数字不能跨语料复用。
"""

import argparse
import itertools
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
sys.path.insert(0, os.path.join(HERE, "services", "rag-alg", "index_data_service"))

from v2_dual_build_diff import diff as struct_diff                    # noqa: E402
from v2_retrieval_equivalence import compare, run_queries            # noqa: E402

SCHEMA = "llmke.baseline-distribution.v1"


def _count(value):
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return int(value or 0)


def pair_stats(a_dir, b_dir, queries, top_k, llm, embed):
    """一份对比：结构差异 + 检索一致率。任一环节失败都如实记 error，不猜。"""
    out = {"a": a_dir, "b": b_dir}
    try:
        s = struct_diff(a_dir, b_dir)
        out["chunks_only_a"] = _count(s["chunks"]["only_a"])
        out["chunks_only_b"] = _count(s["chunks"]["only_b"])
        out["facts_only_a"] = _count(s["facts"]["only_a"])
        out["facts_only_b"] = _count(s["facts"]["only_b"])
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"structural: {type(exc).__name__}: {exc}"
        return out
    try:
        rows_a = run_queries(a_dir, queries, top_k, llm, embed)
        rows_b = run_queries(b_dir, queries, top_k, llm, embed)
        cmp = compare(rows_a, rows_b, top_k)
        route_changes = sum(1 for d in cmp["details"] if d["route"][0] != d["route"][1])
        out.update({"top1_rate": cmp["top1_rate"], "ordered_rate": cmp["ordered_rate"],
                    "avg_jaccard": cmp["avg_jaccard"], "queries": cmp["queries"],
                    "route_changes": route_changes})
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"retrieval: {type(exc).__name__}: {exc}"
    return out


def summarize(pairs):
    """把两两对比压成容差：取观测到的最坏情况，而不是平均值。"""
    ok = [p for p in pairs if "error" not in p]
    if not ok:
        return {"samples": 0, "tolerance": None, "errors": [p.get("error") for p in pairs]}
    facts = [max(p["facts_only_a"], p["facts_only_b"]) for p in ok]
    top1 = [p["top1_rate"] for p in ok]
    routes = [p.get("route_changes", 0) for p in ok]
    return {"samples": len(ok),
            "route_changes": {"max": max(routes), "values": routes},
            "facts_diff": {"max": max(facts), "median": statistics.median(facts),
                           "values": facts},
            "top1_rate": {"min": min(top1), "median": statistics.median(top1), "values": top1},
            "ordered_rate": {"min": min(p["ordered_rate"] for p in ok),
                             "values": [p["ordered_rate"] for p in ok]},
            "jaccard": {"min": min(p["avg_jaccard"] for p in ok),
                        "values": [p["avg_jaccard"] for p in ok]},
            # 灰度判定的建议口径：事实差异 <= max 且 top1 >= min 才算"噪声范围内"
            # 路线翻转也计入噪声：抽取本身不稳时，同一语料两次构建都可能
            # "一次走图、一次回退稠密"，按路线变化一票否决会让判定永远 INCONCLUSIVE。
            "tolerance": {"facts_diff_max": max(facts), "top1_min": min(top1),
                          "route_change_max": max(routes)},
            "errors": [p.get("error") for p in pairs if p.get("error")]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(HERE, ".artifacts", "artifacts.json"))
    ap.add_argument("--set", default="stress", help="清单里的语料组名")
    ap.add_argument("--build-extra", type=int, default=0,
                    help="额外再建几份同语料全量（每份约 1 分钟）")
    ap.add_argument("--queries", nargs="+", default=None)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    from v2_retrieval_equivalence import DEFAULT_QUERIES
    queries = args.queries or DEFAULT_QUERIES

    manifest = json.loads(open(args.manifest, encoding="utf-8").read())
    entry = (manifest.get("sets") or {}).get(args.set) or {}
    dirs = [d for d in (entry.get("full"),
                        (manifest["sets"].get(args.set + "_b") or {}).get("full")) if d]
    if not dirs:
        print(json.dumps({"ok": False, "why": f"清单里没有 {args.set} 的全量快照"},
                         ensure_ascii=False))
        return 1

    built = []
    if args.build_extra:
        from v2_build_artifacts import build_pair
        payloads = manifest.get("payloads") if args.set == "standard" else \
            [os.path.join(manifest["root"], "stress-payloads", "stress-1.json")]
        for i in range(args.build_extra):
            name = f"{args.set}_extra{i}"
            got = build_pair(name, payloads, manifest["root"])
            if got.get("ok"):
                built.append(got["full"])

    dirs.extend(built)
    if len(dirs) < 2:
        print(json.dumps({"ok": False, "why": "至少需要两份快照才能算分布"}, ensure_ascii=False))
        return 1

    started = time.time()
    pairs = [pair_stats(a, b, queries, args.top_k, args.llm, args.embed)
             for a, b in itertools.combinations(dirs, 2)]
    report = {"schema": SCHEMA, "set": args.set, "snapshots": dirs,
              "elapsed_s": round(time.time() - started, 1),
              "summary": summarize(pairs), "pairs": pairs}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"ok": True, "set": args.set, "snapshots": len(dirs),
                      "summary": report["summary"]["tolerance"],
                      "facts": report["summary"].get("facts_diff"),
                      "top1": report["summary"].get("top1_rate")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
