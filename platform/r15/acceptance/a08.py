#!/usr/bin/env python3
"""A08 local/global 与两条入口（任务书 §5.2 A08）。

判据：页面（question_re）与 question 同输入 → 实际通路可证、global_answer 被正确消费、
两入口语义一致、无静默二次生成。
反例：
  N1 任一入口答成 5000万（旧值）或把 1000万 当最高额度 → 语义反转
  N2 两入口答案在关键数值上不一致 → 说明一条链路没消费 global 结果
  N3 答案没有任何检索标记/引用 → 通路不可证（不能只凭"答案像对的"就判通过）
  N4 local 图检索对"图里确实存在的实体"返回空 → local 通路不通（有实体却取不到）
  N6 某入口丢掉"信用分项"约束 → 限制条件在一条通路上丢了

N6 的判定口径见 README §8.2（2026-10-29T22:52:22+0800 冻结）：单次采样定生死不成立，
改为**同一入口固定 k=3 次**（两入口共 6 次），第 2/3 次强制绕过缓存做独立采样；
每个入口 3 次中 ≥2 次带分项**且** 6 次里无一次反转 → 通过。
"""
import re

import common as C

ID = "A08"
TITLE = "local/global 与两入口：question 与 question_re 语义一致、local/global 通路都可证"
WRITES = False

Q = "智造贷最高额度是多少？"
TOTAL, SUB, OLD = "8000万", "1000万", "5000万"

K = 3                     # 每个入口固定采样次数（README §8.2）
NEED_SUB = 2              # k 次里至少几次带分项才算"保留分项"
SNIPPET = 40              # detail 里每次答案的摘要长度
EP_RE = "/qa/ai/question_re"
EP_Q = "/qa/ai/question"


def _reversal(ans):
    return [s for s in C.sentences(ans)
            if "最高额度" in s and C.has_amount(s, SUB) and not C.has_amount(s, TOTAL)]


def _sample(endpoint):
    """同一入口固定采样 k 次；第 1 次可复用进程内缓存，第 2/3 次强制绕过缓存（独立采样）。"""
    return [C.ask(Q, endpoint, nocache=(i > 0)) for i in range(K)]


def _snippet(r):
    """原始答案摘要：去掉引用标签与空白后取前 SNIPPET 字。"""
    a = re.sub(r"\[/?retrive-tag[^\]]*\]|\[\d+\]", "", r.get("answer") or "")
    a = "".join(a.split())
    return a[:SNIPPET] + ("…" if len(a) > SNIPPET else "")


def run():
    checks = []
    samples = {"question_re": _sample(EP_RE), "question": _sample(EP_Q)}
    rep, qq = samples["question_re"][0], samples["question"][0]

    for name, r in (("question_re", rep), ("question", qq)):
        checks.append(C.chk(f"P1 {name} 可用且有非空答案",
                            r["http"] == 200 and len(r["answer"].strip()) > 10,
                            f"http={r['http']} 帧={len(r['frames'])} 耗时={r['elapsed']}s "
                            f"答案={r['answer'][:120]!r}"))
        checks.append(C.chk(f"P2 {name} 流未中途断开（半截答案不算完成）",
                            not r.get("stream_error"),
                            f"stream_error={r.get('stream_error') or '无'}；"
                            f"6 次采样 http={[x['http'] for v in samples.values() for x in v]}"))

    checks.append(C.chk("N2 反例：两入口关键数值一致（都答 8000万）",
                        C.has_amount(rep["answer"], TOTAL) and C.has_amount(qq["answer"], TOTAL),
                        f"question_re 含8000万={C.has_amount(rep['answer'], TOTAL)}"
                        f"（{rep['frame_semantics']}帧）；"
                        f"question 含8000万={C.has_amount(qq['answer'], TOTAL)}"
                        f"（{qq['frame_semantics']}帧）；"
                        f"6 次采样含8000万数="
                        f"{ {k: sum(C.has_amount(x['answer'], TOTAL) for x in v) for k, v in samples.items()} }"))

    # N1/N5 对 6 次全采样判定（比第一轮的单次更严）
    all_ans = [(ep, i, x) for ep, v in samples.items() for i, x in enumerate(v, 1)]
    rev = [(ep, i, _reversal(x["answer"])[:1]) for ep, i, x in all_ans if _reversal(x["answer"])]
    checks.append(C.chk("N1 反例：6 次采样均未把 1000万 当最高额度", not rev,
                        f"反转采样={rev}；"
                        f"（判据：同一句里 最高额度 + 1000万 而不含 8000万）"))

    old = [(ep, i) for ep, i, x in all_ans
           if C.has_amount(x["answer"], OLD) and "最高" in x["answer"]]
    checks.append(C.chk("N5 反例：6 次采样均未使用旧代数值 5000万 作最高额度", not old,
                        f"出现旧值的采样={old}"))

    # N6：k=3 固定采样 + 先写死的阈值（README §8.2）
    sub_cnt = {ep: sum(C.has_amount(x["answer"], SUB) for x in v) for ep, v in samples.items()}
    detail6 = "；".join(f"{ep}#{i}「{_snippet(x)}」"
                       for ep, v in samples.items() for i, x in enumerate(v, 1))
    if rev:
        n6_note = "→ 出现反转（硬 FAIL，反转优先于比例）"
        n6_ok = False
    elif all(n >= NEED_SUB for n in sub_cnt.values()):
        n6_note = f"→ 两入口均 ≥{NEED_SUB}/{K} 带分项，且无反转：通过"
        n6_ok = True
    elif any(n == 0 for n in sub_cnt.values()):
        n6_note = f"→ {[ep for ep, n in sub_cnt.items() if n == 0]} 3/3 全不带分项：稳定性问题，非采样问题"
        n6_ok = False
    else:
        n6_note = (f"→ {[ep for ep, n in sub_cnt.items() if n < NEED_SUB]} "
                   f"{[n for n in sub_cnt.values() if n < NEED_SUB]}/{K} 低于 {NEED_SUB}/{K} 阈值（不稳定）")
        n6_ok = False
    checks.append(C.chk(
        f"N6 反例：两入口 k={K} 采样均保留信用分项（分项次数 {sub_cnt}，阈值 ≥{NEED_SUB}/{K} 且无反转）{n6_note}",
        n6_ok,
        f"带分项次数={sub_cnt}（分母 k={K}）；反转采样={[(_ep, _i) for _ep, _i, _ in rev]}；"
        f"6 次原始答案摘要（各 {SNIPPET} 字）：{detail6}"))

    tagged = bool(C.cited_ids(rep["answer"])) or bool(rep["refs"])
    checks.append(C.chk("N3 反例：通路可证（检索标记或引用非空）", tagged,
                        f"引用 id={C.cited_ids(rep['answer'])[:3]}；refs={len(rep['refs'])} 条"))

    # N4：local 图检索。智造贷在 Nebula 里确实存在（前面已核对 VID=名称），
    # 因此 local 通路返回空不能解释为"库里没有"，只能算通路不通。
    # 重试一次：图服务可能正在重启（本轮实测就遇到 22:21 重启），
    # 不能把"连接没通"当成"业务空"，也不能反过来把"业务空"当成"服务没起"。
    code, body, blocks, reason = 0, {}, [], None
    for _ in range(2):
        code, body = C.graph_post("/query_graph_data",
                                  {"space_name": C.KB, "query": "智造贷", "model_info": C.MODEL_INFO,
                                   "depth": 2, "top_k": 5}, timeout=120)
        data = (body or {}).get("data") or {}
        blocks, reason = data.get("result_data") or [], data.get("reason")
        if code == 200:
            break
    if code != 200:
        checks.append(C.chk("N4 反例：local 图检索可用", False,
                            f"两次请求均未打通 http={code}（图服务不可用，不能据此判业务语义）"))
    else:
        checks.append(C.chk("N4 反例：local 图检索能取到已存在实体的事实", len(blocks) > 0,
                            f"http={code} 返回块={len(blocks)} reason={reason} "
                            f"msg={str((body or {}).get('msg'))[:80]!r}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES)
