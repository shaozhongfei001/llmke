#!/usr/bin/env python3
"""A03 业务推导（任务书 §5.2 A03）。

判据：总额 8000 与信用分项 1000 不反转；甲适用 A 则加 30BP，不套 B 的减 30BP。
反例（任一条命中即 FAIL）：
  N1 答案把 1000 万说成"最高额度"（语义反转）
  N2 图里存在 (智造贷, 最高额度, 1000万元) —— 存储层就把分项当成了总额度
  N3 (智造贷, 最高额度) 上同时存在 8000万 与 1000万 两个值
"""
import re

import common as C

ID = "A03"
TITLE = "业务推导：8000万总额与1000万信用分项不反转，评级加点有前提"
WRITES = False

Q = "智造贷最高额度是多少？"
TOTAL, SUB = "8000万", "1000万"


def run():
    checks = []
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]

    # 存储层：最高额度谓词上的取值集合
    # R15 判据修正：原实现用 `"最高额度" in p`，会把**分项谓词**也算成总额——
    # `信用部分最高额度`、`信用方式最高额度` 明确是分项（A03 要查的是"总额度上出现分项值"），
    # 把它们算进来会让正确的分项事实被判成语义反转。这里排除含分项标记的谓词。
    ITEM_MARKERS = ("信用", "分项", "部分", "单项", "其中")
    def _is_total(pred):
        return "最高额度" in pred and not any(m in pred for m in ITEM_MARKERS)
    top = [(e["o"], e["fid"]) for e in vis if e["s"] == "智造贷" and _is_total(e["p"])]
    vals = sorted({C.norm_num(v) for v, _ in top})
    checks.append(C.chk("正例：图中存在 智造贷-最高额度->8000万元",
                        any(C.has_amount(v, TOTAL) for v, _ in top),
                        f"最高额度取值={vals}"))
    checks.append(C.chk("N2 反例：最高额度上不出现分项 1000万",
                        not any(C.has_amount(v, SUB) for v, _ in top),
                        f"最高额度上的 1000万 事实={[t for t in top if C.has_amount(t[0], SUB)]}"))
    only_sub = any(C.has_amount(v, "1000万") for v, _ in top) and \
        not any(C.has_amount(v, "8000万") for v, _ in top)
    checks.append(C.chk("N3 反例：最高额度不出现新旧/总额-分项两值并存", not only_sub,
                        f"取值集合={vals}（8000万与1000万并存即判反转）"))

    # 答案层
    a = C.ask(Q)
    ans = a["answer"]
    checks.append(C.chk("正例：答案给出总额 8000万", C.has_amount(ans, TOTAL),
                        f"http={a['http']} 耗时={a['elapsed']}s 答案={ans[:160]!r}"))
    bad = [s for s in C.sentences(ans)
           if "最高额度" in s and C.has_amount(s, SUB) and not C.has_amount(s, TOTAL)
           and "分项" not in s and "信用" not in s]
    checks.append(C.chk("N1 反例：答案未把 1000万 当最高额度", not bad,
                        f"反转句={bad[:2]}"))
    checks.append(C.chk("正例：答案把 1000万 标为信用分项",
                        ("信用" in ans or "分项" in ans) and C.has_amount(ans, SUB),
                        f"答案含信用/分项={('信用' in ans or '分项' in ans)}"))

    # 评级加点前提：甲适用 A → 加 30BP；不得套 B 的减 30BP
    bp = [(e["s"], e["p"], e["o"]) for e in vis if "BP" in e["o"] or "基点" in e["o"]]
    has_rule = bool(bp)
    checks.append(C.chk("评级加点事实存在（推导前提可查）", has_rule,
                        f"加点类事实={bp[:3]}"))
    neg_b = [x for x in bp if "减" in x[1] and ("智造贷" in x[0] or "智造贷" in x[2])]
    checks.append(C.chk("N4 反例：智造贷未被套用减项规则",
                        not (has_rule and neg_b), f"减项事实={neg_b[:3]}"))

    reason = "" if has_rule else "A04 前置：kb_9 无 D2/D3/D4 评级加点夹具，甲+30/乙-30 只能报组件级（F10）"
    return C.verdict(ID, TITLE, checks, skip_reason=reason or None, writes=WRITES)
