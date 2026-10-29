#!/usr/bin/env python3
"""A12 全局语义与贡献（任务书 §5.2 A12）。

判据：无实体名主题问、同义改写、多跳、无答案和冲突题各有正确结果；trace 证明图/社区有贡献。
反例：
  N1 对"库里有支持"的问题答成"无相关信息/无法回答" → 覆盖不足被当成正常
  N2 答案里的金额不在图里出现 → 凭空生成（模型先验冒充证据）
  N3 同义改写换了说法就答不出关键数值 → 只能靠实体全名匹配
"""
import re

import common as C

ID = "A12"
TITLE = "全局语义：同义改写与无实体名主题问有覆盖、无凭空数值"
WRITES = False

Q_SYNONYM = "智造贷最多能借多少钱？"
Q_TOPIC = "制造业中小微企业的贷款产品在额度上有什么限制？"
AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万元|亿元)")
NO_ANSWER = ("无相关信息", "无法回答", "抱歉", "没有找到", "未找到相关")


def run():
    checks = []
    graph_amounts = set()
    for e in C.edges():
        for v in (e["s"], e["o"]):
            for n, u in AMOUNT_RE.findall(v):
                graph_amounts.add(C.norm_num(f"{n}{u}"))

    for name, q in (("同义改写", Q_SYNONYM), ("无实体名主题问", Q_TOPIC)):
        r = C.ask(q)
        ans = r["answer"]
        checks.append(C.chk(f"P1 {name} 有非空答案", r["http"] == 200 and len(ans.strip()) > 10,
                            f"http={r['http']} 耗时={r['elapsed']}s 答案={ans[:120]!r}"))
        checks.append(C.chk(f"P2 {name} 流未中途断开（半截答案不算完成）",
                            not r.get("stream_error"),
                            f"stream_error={r.get('stream_error') or '无'}；收帧={len(r['frames'])}"))
        checks.append(C.chk(f"N1 反例：{name} 未被判为无答案",
                            not any(x in ans for x in NO_ANSWER),
                            f"命中无答案话术={[x for x in NO_ANSWER if x in ans]}"))
        nums = {C.norm_num(f"{n}{u}") for n, u in AMOUNT_RE.findall(ans)}
        fake = sorted(x for x in nums if x not in graph_amounts)
        checks.append(C.chk(f"N2 反例：{name} 金额均来自图事实", not fake,
                            f"答案金额={sorted(nums)}；图内金额={sorted(graph_amounts)}；凭空={fake}"))

    checks.append(C.chk("N3 反例：同义改写后仍给出关键额度",
                        C.has_amount(C.ask(Q_SYNONYM)["answer"], "8000万"),
                        f"答案={C.ask(Q_SYNONYM)['answer'][:120]!r}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="受控关闭图/社区的对照实验需改检索配置（写操作），本轮不执行")
