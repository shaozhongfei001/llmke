#!/usr/bin/env python3
"""A05 幂等与来源累积（任务书 §5.2 A05）。

判据：重试同文件不重复、另一文件支持同一事实则来源累积、删除一个来源不误删仍有支持的事实。
写操作边界：本断言的核心动作是"重试上传 → 再上传另一文件 → 删除一个来源"三步写操作，
本轮**不触发**（不改库、不重启、不写业务数据），只做只读前置：
  P1 同一 (头,谓词,尾) 被 ≥2 个不同 file_id 支持 → 来源已按并集累积（不是字典覆盖）
  N1 某事实的全部来源都来自失效文件（status!=3）→ 事实仍留在图里 = 幽灵支持
  N2 同一 file_id 内同一事实重复出现 ≥2 次 → 重试产生了重复（幂等被破坏）
"""
import collections

import common as C

ID = "A05"
TITLE = "幂等与来源：来源并集累积、不重复、不误删"
WRITES = True


def run():
    checks = []
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]
    active = C.active_fids()

    by_fact = collections.defaultdict(set)
    for e in vis:
        by_fact[(e["s"], e["p"], e["o"])].add(e["fid"])
    multi = {k: v for k, v in by_fact.items() if len(v) >= 2}
    # 观测项（不参与 hard 判定）：当前库里没有"同一事实被两个文件同时支持"的数据，
    # 因此"来源并集累积"这一能力在本数据集上无法被正例覆盖 → 如实记为未覆盖。
    cov = (f"多来源事实 {len(multi)} 条（0 条 = 来源累积能力未被真实数据覆盖）")

    ghost = {k: v for k, v in by_fact.items() if v and not (v & active)}
    checks.append(C.chk("N1 反例：不存在「全部来源失效却仍可见」的事实", not ghost,
                        f"幽灵支持 {len(ghost)} 条，示例={list(ghost.items())[:2]}"))

    dup = collections.Counter((e["s"], e["p"], e["o"], e["fid"]) for e in vis)
    repeated = {k: n for k, n in dup.items() if n > 1}
    checks.append(C.chk("N2 反例：同一来源内同一事实不重复入图", not repeated,
                        f"重复入图 {len(repeated)} 条，示例={list(repeated.items())[:2]}"))

    # 同一文件被重复解析时"边数是否翻倍"只能靠重试写操作验证 → 如实 SKIP
    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason=f"只读前置无反例（{cov}）；核心动作需重试上传/再上传/删来源三步写操作，本轮不执行")


if __name__ == "__main__":
    print(run())
