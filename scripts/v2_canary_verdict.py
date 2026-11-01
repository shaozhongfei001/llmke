#!/usr/bin/env python
"""灰度判定：把 C2（结构/抽取）与 C3（检索）合成**一个**结论，而不是三份 JSON。

为什么需要它：
增量重建现在有三份彼此割裂的证据——
  * C2 `v2_dual_build_diff`：块集合 + openie 事实；
  * C3 `v2_retrieval_equivalence`：top-k 命中与排序；
  * 基线噪声：同一语料两份全量快照必须一致，否则"差异"无法归因。
灰度切换前需要的是"能不能切"，不是让人肉对着三个 JSON 做心算。
本脚本**只做汇总判定**，比较逻辑一律复用上面两个模块（不重写、不复制口径）。

判据（每一条为什么这么定，见 judge() 内注释）：
  SAFE   ：基线稳定 + 块集合一致 + 事实一致 + 检索 top1/集合/顺序全一致；
  REVIEW ：结构与检索都一致，但事实有差异 —— 差异**没传导到用户可见层**，
           但必须人工看差在哪些事实（C2 已实测 delta 多 1 条，正属此类）；
  UNSAFE ：基线不稳、块集合不同、检索证据缺失、top1/路线/命中集合不一致。

退出码：SAFE=0、REVIEW=1、UNSAFE=2 —— 非 0 即"未批准切换"，可直接接 CI。

诚实边界：REVIEW 不等于"可以切"，它等于"现有证据既不能否决也不能放行"；
SAFE 也只是"在这些 query、这个 top_k 上的 SAFE"，不是全库结论。
"""

import argparse
import gc
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# 以脚本方式运行时 sys.path[0] 已是 scripts/；但被测试用 importlib 加载时不是，
# 这里显式补上，保证 `from v2_dual_build_diff import diff` 在两种入口下都成立。
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from v2_dual_build_diff import diff as dual_diff                      # noqa: E402
from v2_retrieval_equivalence import (                                # noqa: E402
    DEFAULT_QUERIES, compare as retrieval_compare, run_queries)

SCHEMA = "llmke.canary-verdict.v1"
# INCONCLUSIVE 与 UNSAFE 必须分开：UNSAFE = "查出了缺陷，别切"；
# INCONCLUSIVE = "基线自己都不稳，这个实验测不出结论"。
# 把噪声记成缺陷，运维会去修一个不存在的问题，下次就没人信这个判定。
EXIT_CODES = {"SAFE": 0, "REVIEW": 1, "UNSAFE": 2, "INCONCLUSIVE": 3}


# ---------------------------------------------------------------- 纯判定层
def _is_rate(value):
    """一致率必须是真数值。bool 是 int 的子类，要单独排除（True 不能当 1.0 用）。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _count(value):
    """事实差异既可能是次数也可能是明细列表，两种都收。"""
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return int(value)


def _baseline_problems(baseline):
    """基线（a vs a2，同一语料两份全量）必须完全一致，否则差异无从归因。

    这是**前置条件**而不是并列判据：基线本身就在抖，后面的任何"不同"
    都无法区分"实现差异"和"随机抖动"，此时给出 SAFE/REVIEW 都是误导。
    """
    if not isinstance(baseline, dict):
        return ["缺少 a vs a2 基线对照"]

    problems = []
    if baseline.get("chunks_identical") is not True:
        problems.append(f"块集合不一致（only_a={_count(baseline.get('only_a'))} "
                        f"only_b={_count(baseline.get('only_b'))}）")

    facts_a = _count(baseline.get("facts_only_a"))
    facts_b = _count(baseline.get("facts_only_b"))
    if facts_a or facts_b:
        problems.append(f"抽取事实不一致（only_a={facts_a} only_b={facts_b}）")

    # 检索基线与事实基线同等重要：若两次全量检索都不一致，
    # 那么 a vs b 的检索差异同样归因不了。
    ret = baseline.get("retrieval")
    if isinstance(ret, dict):
        top1, ordered, jacc = ret.get("top1_rate"), ret.get("ordered_rate"), ret.get("avg_jaccard")
        if not (_is_rate(top1) and _is_rate(ordered) and _is_rate(jacc)):
            problems.append("检索基线字段缺失，无法确认检索本身是否稳定")
        elif min(top1, ordered, jacc) < 1.0:
            problems.append(f"检索结果不一致（top1={top1} ordered={ordered} "
                            f"jaccard={jacc}）")
    return problems


def judge(chunks=None, facts=None, retrieval=None, baseline=None):
    """纯函数：只吃已算好的统计，不碰文件、不加载引擎。

    入参形状（缺字段一律按"证据不足"处理，绝不默认成"一致"）：
      chunks    : {"identical": bool, "only_a": n|list, "only_b": n|list}
      facts     : {"only_a": n|list, "only_b": n|list}
      retrieval : {"top1_rate": float, "ordered_rate": float, "avg_jaccard": float,
                   "route_changed": [query, ...]（可选）}
      baseline  : {"chunks_identical": bool, "only_a": n, "only_b": n,
                   "facts_only_a": n, "facts_only_b": n, "retrieval": {...}|None}
    """
    hard, soft = [], []

    # ---- 0) 基线先行：基线不稳就没有"归因"这回事，短路返回，不再给结论
    baseline_problems = _baseline_problems(baseline)
    if baseline_problems:
        reasons = ["基线不稳定，无法归因（同一语料两份全量快照本身不一致）：" + p
                   for p in baseline_problems]
        return {"verdict": "INCONCLUSIVE", "exit_code": EXIT_CODES["INCONCLUSIVE"],
                "reasons": reasons, "hard": reasons, "soft": []}

    # ---- 1) 结构层（chunks）：块集合不同 = 两条路径看的就不是同一批文本，
    #         后面比事实/检索都没有意义，属硬否决。
    if not isinstance(chunks, dict) or "identical" not in chunks:
        hard.append("结构层（chunks）证据缺失，无法确认块集合一致")
    elif chunks.get("identical") is not True:
        hard.append(f"块集合不一致：only_a={_count(chunks.get('only_a'))} "
                    f"only_b={_count(chunks.get('only_b'))}")

    # ---- 2) 检索层（retrieval）：用户感知的是检索结果，不是 openie 条数。
    #         缺检索证据不能放行——C3 的教训是"抽取一致 ≠ 用户看到一致"。
    if not isinstance(retrieval, dict):
        hard.append("检索层证据缺失：抽取一致不等于用户看到一致，缺检索证据不得放行")
    else:
        top1 = retrieval.get("top1_rate")
        ordered = retrieval.get("ordered_rate")
        jacc = retrieval.get("avg_jaccard")

        routes = retrieval.get("route_changed") or []
        if routes:
            # 路线变化意味着走的是不同检索分支（GRAPH vs DENSE_FALLBACK 等），
            # 命中恰好相同也只是巧合，不能当等价。
            hard.append(f"检索路线变化：{len(routes)} 条 query（{list(routes)[:3]}）")

        if not _is_rate(top1):
            hard.append("检索层 top1_rate 缺失或非数值，无法判定")
        elif top1 < 1.0:
            # top1 不同 = 用户第一眼看到的东西变了，这是最直接的降质信号。
            hard.append(f"检索 top1 不一致：top1_rate={top1}")

        if not _is_rate(jacc):
            hard.append("检索层 avg_jaccard 缺失或非数值，无法判定")
        elif jacc < 1.0:
            # top1 相同但集合不同：第一眼一样、往下翻就变了，仍属用户可见差异。
            hard.append(f"检索命中集合不同：avg_jaccard={jacc}")

        if not _is_rate(ordered):
            hard.append("检索层 ordered_rate 缺失或非数值，无法判定")
        elif jacc == 1.0 and top1 == 1.0 and ordered < 1.0:
            # 集合与首条都一致，只有名次不同——用户能看到的信息相同，
            # 但排序不同可能影响后续引用与上下文拼装，因此降到 REVIEW 而非 SAFE。
            soft.append(f"命中集合一致但排序不同：ordered_rate={ordered}")

    # ---- 3) 事实层（facts）：只有它差异时才可能是"差异未传导"。
    #         这是最容易被误判成 SAFE 的一类：结构一致 + 检索一致，
    #         但抽取结果确实不同，必须留人工核对清单。
    if not isinstance(facts, dict) or "only_a" not in facts or "only_b" not in facts:
        soft.append("事实层（facts）证据缺失，无法确认抽取结果一致")
    else:
        only_a, only_b = _count(facts.get("only_a")), _count(facts.get("only_b"))
        if only_a or only_b:
            soft.append(f"抽取事实存在差异：only_a={only_a} only_b={only_b}"
                        f"（检索未见差异，需人工核对差异清单）")

    verdict = "UNSAFE" if hard else ("REVIEW" if soft else "SAFE")
    if verdict == "SAFE":
        reasons = ["基线稳定；块集合、抽取事实、检索命中集合与排序在 a/a2/b 之间全部一致"]
    else:
        reasons = hard + soft

    return {"verdict": verdict, "exit_code": EXIT_CODES[verdict],
            "reasons": reasons, "hard": hard, "soft": soft}


# ---------------------------------------------------------------- 采集层
def collect_structure(a_dir, b_dir):
    """复用 C2 的比较结果，只做字段映射（不重算口径）。"""
    raw = dual_diff(a_dir, b_dir)
    return raw


def structure_view(raw):
    chunks = raw.get("chunks") or {}
    facts = raw.get("facts") or {}
    only_a = _count(chunks.get("only_a"))
    only_b = _count(chunks.get("only_b"))
    facts_only_a = _count(facts.get("only_a"))
    facts_only_b = _count(facts.get("only_b"))
    shared = facts.get("shared") or 0
    return {
        "chunks": {"identical": bool(chunks.get("identical")),
                   "shared": chunks.get("shared"),
                   "only_a": only_a, "only_b": only_b,
                   "count_a": (raw.get("a") or {}).get("chunks"),
                   "count_b": (raw.get("b") or {}).get("chunks")},
        "facts": {"only_a": facts_only_a, "only_b": facts_only_b,
                  "shared": shared,
                  # count 取并集大小：差异事实单独计数，避免"条数对得上"的错觉
                  "count": shared + facts_only_a + facts_only_b,
                  "attribution": raw.get("attribution") or {},
                  "samples": raw.get("samples") or []},
        # 判定入参单独给，避免展示字段（含 samples）影响判据
        "_judge_chunks": {"identical": bool(chunks.get("identical")),
                          "only_a": only_a, "only_b": only_b},
        "_judge_facts": {"only_a": facts_only_a, "only_b": facts_only_b},
    }


def retrieval_view(rows_a, rows_b, top_k):
    """复用 C3 的 compare()，抽成判定需要的几个数。"""
    if len(rows_a) != len(rows_b):
        return {"queries": max(len(rows_a), len(rows_b)),
                "top1_rate": None, "ordered_rate": None, "avg_jaccard": None,
                "route_changed": [],
                "problems": [f"query 数不一致：{len(rows_a)} vs {len(rows_b)}"]}, True

    raw = retrieval_compare(rows_a, rows_b, top_k)
    route_changed = [d["query"] for d in raw.get("details") or []
                     if (d.get("route") or [None, None])[0] != (d.get("route") or [None, None])[1]]
    view = {"queries": raw.get("queries"),
            "top1_rate": raw.get("top1_rate"),
            "ordered_rate": raw.get("ordered_rate"),
            "avg_jaccard": raw.get("avg_jaccard"),
            "route_changed": route_changed,
            # 只留不一致的 query 明细，避免 JSON 膨胀
            "mismatches": [d for d in raw.get("details") or []
                           if not d.get("top1_same") or not d.get("ordered_same")
                           or d.get("only_a") or d.get("only_b")]}
    return view, False


def _safe_structure(a_dir, b_dir):
    try:
        return structure_view(collect_structure(a_dir, b_dir)), None
    except (SystemExit, Exception) as exc:  # fail-closed：读不了快照就不放行
        return None, f"无法读取快照 {a_dir} vs {b_dir}：{exc}"


def _safe_retrieval(a_dir, b_dir, queries, top_k, llm, embed):
    try:
        rows_a = run_queries(a_dir, queries, top_k, llm, embed)
        gc.collect()
        rows_b = run_queries(b_dir, queries, top_k, llm, embed)
        gc.collect()
        return retrieval_view(rows_a, rows_b, top_k)[0], None
    except (SystemExit, Exception) as exc:
        return None, f"检索对比失败（{a_dir} vs {b_dir}）：{exc}"


def build_report(a_dir, a2_dir, b_dir, top_k=5, queries=None,
                 llm="http://127.0.0.1:18092/v1", embed="http://127.0.0.1:18090/v1",
                 baseline_retrieval=True):
    """a=当前全量，a2=同语料第二份全量（基线），b=待切快照。"""
    queries = list(queries or DEFAULT_QUERIES)
    t0 = time.time()
    errors = []

    base_struct, err = _safe_structure(a_dir, a2_dir)
    if err:
        errors.append(err)
    main_struct, err = _safe_structure(a_dir, b_dir)
    if err:
        errors.append(err)

    base_ret = None
    if baseline_retrieval:
        base_ret, err = _safe_retrieval(a_dir, a2_dir, queries, top_k, llm, embed)
        if err:
            errors.append(err)

    main_ret, err = _safe_retrieval(a_dir, b_dir, queries, top_k, llm, embed)
    if err:
        errors.append(err)

    # 基线：结构必须完全一致；检索基线是可选的（--no-baseline-retrieval）
    if base_struct is None:
        baseline = None
    else:
        baseline = {"a2": a2_dir,
                    "chunks_identical": base_struct["chunks"]["identical"],
                    "only_a": base_struct["chunks"]["only_a"],
                    "only_b": base_struct["chunks"]["only_b"],
                    "facts_only_a": base_struct["facts"]["only_a"],
                    "facts_only_b": base_struct["facts"]["only_b"],
                    "retrieval": base_ret if base_ret else None}
        baseline["stable"] = not _baseline_problems(baseline)

    verdict_in = judge(
        chunks=(main_struct or {}).get("_judge_chunks"),
        facts=(main_struct or {}).get("_judge_facts"),
        retrieval=main_ret,
        baseline=baseline,
    )

    if errors:
        # 采集失败本身就是证据不足：任何一条失败都不能让结论漂向 SAFE
        verdict_in = {"verdict": "UNSAFE", "exit_code": EXIT_CODES["UNSAFE"],
                      "reasons": list(verdict_in["reasons"]) + errors,
                      "hard": list(verdict_in["hard"]) + errors,
                      "soft": verdict_in["soft"]}

    report = {
        "schema": SCHEMA,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "elapsed_s": round(time.time() - t0, 1),
        "inputs": {"a": a_dir, "a2": a2_dir, "b": b_dir,
                   "top_k": top_k, "queries": queries,
                   "baseline_retrieval": bool(baseline_retrieval)},
        "chunks": (main_struct or {}).get("chunks") or {"identical": None},
        "facts": (main_struct or {}).get("facts") or {"only_a": None, "only_b": None,
                                                      "count": None},
        "retrieval": main_ret or {"top1_rate": None, "ordered_rate": None,
                                  "avg_jaccard": None},
        "baseline": baseline,
        "verdict": verdict_in["verdict"],
        "exit_code": verdict_in["exit_code"],
        "reasons": verdict_in["reasons"],
        "errors": errors,
    }
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="灰度判定：C2+C3+基线合成单一结论")
    ap.add_argument("--a", required=True, help="当前全量快照目录")
    ap.add_argument("--a2", required=True, help="同语料的第二份全量快照（基线噪声）")
    ap.add_argument("--b", required=True, help="待切快照目录（如 delta）")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--queries", nargs="+", default=DEFAULT_QUERIES)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--no-baseline-retrieval", action="store_true",
                    help="跳过 a vs a2 的检索基线段（省一次引擎加载），"
                         "结构/事实基线仍会采集")
    ap.add_argument("--json", dest="json_out", default=None, help="完整报告输出路径")
    ap.add_argument("--quiet", action="store_true", help="不在 stdout 打印摘要")
    args = ap.parse_args(argv)

    report = build_report(args.a, args.a2, args.b, top_k=args.top_k,
                          queries=args.queries, llm=args.llm, embed=args.embed,
                          baseline_retrieval=not args.no_baseline_retrieval)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)

    if not args.quiet:
        print(json.dumps({
            "verdict": report["verdict"],
            "exit_code": report["exit_code"],
            "chunks": report["chunks"],
            "facts": {k: report["facts"].get(k) for k in ("only_a", "only_b", "count")},
            "retrieval": {k: report["retrieval"].get(k) for k in
                          ("queries", "top1_rate", "ordered_rate", "avg_jaccard")},
            "baseline": None if report["baseline"] is None else {
                "chunks_identical": report["baseline"].get("chunks_identical"),
                "facts_only_a": report["baseline"].get("facts_only_a"),
                "facts_only_b": report["baseline"].get("facts_only_b"),
                "stable": report["baseline"].get("stable")},
            "reasons": report["reasons"],
        }, ensure_ascii=False))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
