#!/usr/bin/env python3
"""A08 local/global 与两条入口（任务书 §5.2 A08）。

判据：页面（question_re）与 question 同输入 → 实际通路可证、global_answer 被正确消费、
两入口语义一致、无静默二次生成。
反例：
  N1 任一入口答成 5000万（旧值）或把 1000万 当最高额度 → 语义反转
  N2 两入口答案在关键数值上不一致 → 说明一条链路没消费 global 结果
  N3 答案没有任何检索标记/引用 → 通路不可证（不能只凭"答案像对的"就判通过）
  N4 local 图检索对"图里确实存在的实体"返回空 → local 通路不通（有实体却取不到）
"""
import common as C

ID = "A08"
TITLE = "local/global 与两入口：question 与 question_re 语义一致、local/global 通路都可证"
WRITES = False

Q = "智造贷最高额度是多少？"
TOTAL, SUB, OLD = "8000万", "1000万", "5000万"


def _reversal(ans):
    return [s for s in C.sentences(ans)
            if "最高额度" in s and C.has_amount(s, SUB) and not C.has_amount(s, TOTAL)]


def run():
    checks = []
    rep = C.ask(Q, "/qa/ai/question_re")
    qq = C.ask(Q, "/qa/ai/question")

    for name, r in (("question_re", rep), ("question", qq)):
        checks.append(C.chk(f"P1 {name} 可用且有非空答案",
                            r["http"] == 200 and len(r["answer"].strip()) > 10,
                            f"http={r['http']} 帧={len(r['frames'])} 耗时={r['elapsed']}s "
                            f"答案={r['answer'][:120]!r}"))
        checks.append(C.chk(f"P2 {name} 流未中途断开（半截答案不算完成）",
                            not r.get("stream_error"),
                            f"stream_error={r.get('stream_error') or '无'}"))

    checks.append(C.chk("N2 反例：两入口关键数值一致（都答 8000万）",
                        C.has_amount(rep["answer"], TOTAL) and C.has_amount(qq["answer"], TOTAL),
                        f"question_re 含8000万={C.has_amount(rep['answer'], TOTAL)}；"
                        f"question 含8000万={C.has_amount(qq['answer'], TOTAL)}"))

    checks.append(C.chk("N1 反例：两入口都未把 1000万 当最高额度",
                        not _reversal(rep["answer"]) and not _reversal(qq["answer"]),
                        f"question_re 反转句={_reversal(rep['answer'])[:1]}；"
                        f"question 反转句={_reversal(qq['answer'])[:1]}"))

    old = [n for n, r in (("question_re", rep), ("question", qq))
           if C.has_amount(r["answer"], OLD) and "最高" in r["answer"]]
    checks.append(C.chk("N5 反例：答案未使用旧代数值 5000万 作最高额度", not old,
                        f"出现旧值的入口={old}"))

    tagged = bool(C.cited_ids(rep["answer"])) or bool(rep["refs"])
    checks.append(C.chk("N3 反例：通路可证（检索标记或引用非空）", tagged,
                        f"引用 id={C.cited_ids(rep['answer'])[:3]}；refs={len(rep['refs'])} 条"))

    # N4：local 图检索。智造贷在 Nebula 里确实存在（前面已核对 VID=名称），
    # 因此 local 通路返回空不能解释为"库里没有"，只能算通路不通。
    code, body = C.graph_post("/query_graph_data",
                              {"space_name": C.KB, "query": "智造贷", "model_info": C.MODEL_INFO,
                               "depth": 2, "top_k": 5}, timeout=120)
    data = (body or {}).get("data") or {}
    blocks = data.get("result_data") or []
    checks.append(C.chk("N4 反例：local 图检索能取到已存在实体的事实", len(blocks) > 0,
                        f"http={code} 返回块={len(blocks)} reason={(data or {}).get('reason')} "
                        f"msg={str((body or {}).get('msg'))[:80]!r}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)
