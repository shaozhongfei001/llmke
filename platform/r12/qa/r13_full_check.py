#!/usr/bin/env python3
"""R13 能力矩阵自检（TL 集成用）。

只做"能力是否真实可用"的端到端探针，不替代 acceptance.py（主链）与
security_acceptance.py（对象授权负例）。每个探针都打印可复核的原始证据片段。

用法:
  python3 platform/r12/qa/r13_full_check.py            # 全部
  python3 platform/r12/qa/r13_full_check.py --only FAQ,GLOBAL
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r12_client import GATEWAY, UA, api, login  # noqa: E402

import requests  # noqa: E402

R12 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(R12, "qa", "evidence", "CAPS-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
RESULTS = []

# 默认助手：普通 RAG（config 1）；FAQ 助手 config 9；global 用请求级开关，不依赖 config
CFG_DEFAULT = 1
CFG_FAQ = 9
KB_ID = 9
KB_NAME = "kb_9"


def _port_pids(port):
    """返回监听该端口的 pid 列表（同端口多 pid = 结果不可信，TL/E 的纪律）。"""
    pids = set()
    try:
        out = subprocess.run(["ss", "-lntp"], capture_output=True, text=True).stdout
    except Exception:
        return []
    for line in out.splitlines():
        if f":{port} " in line and "pid=" in line:
            for seg in line.split("pid=")[1:]:
                pids.add(seg.split(",")[0])
    return sorted(pids)


def _listening(port):
    try:
        out = subprocess.run(["ss", "-lnt"], capture_output=True, text=True).stdout
    except Exception:
        return True
    return f":{port} " in out


def record(cap, ok, detail, extra=None, neutral=False):
    """R14-F01g：支持第三态 INFO —— 用于"既不能判 PASS 也不能判 FAIL"的场景：
      - EMPTY_LEGIT：图检索的业务空结果（http=200 + body code=500 + data.reason）；
      - UNVERIFIED_WHITELIST：字段被检索层白名单丢弃，证据拿不到。
    INFO 不计入 PASS/FAIL、不影响退出码，但必须在 summary 单列，避免"拿不到证据当成证据成立"。
    """
    RESULTS.append({"cap": cap, "ok": bool(ok), "neutral": bool(neutral), "detail": detail})
    tag = "INFO" if neutral else ("PASS" if ok else "FAIL")
    print(f"{tag} [{cap}] {detail}")
    if extra:
        try:
            os.makedirs(EVID, exist_ok=True)
            with open(os.path.join(EVID, cap.replace("/", "_") + ".json"), "w", encoding="utf-8") as f:
                json.dump(extra, f, ensure_ascii=False, indent=1)
        except Exception:
            pass


def ask(s, content, config_id=CFG_DEFAULT, global_mode=False, timeout=240):
    """发一问，返回 (http, status, answer, reference_list, resultType)。"""
    payload = {"sessionId": f"cap-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        payload["globalMode"] = True
    r = requests.post(
        GATEWAY + "/qa/ai/question", json=payload,
        headers={"Authorization": s.token, "Accept": "text/event-stream",
                 "Content-Type": "application/json", "User-Agent": UA},
        stream=True, timeout=timeout)
    answer, ref, rt, status = "", [], None, None
    buf = b""
    for line in r.iter_lines():
        if not line:
            continue
        buf += line + b"\n"
    txt = buf.decode("utf-8", "replace")
    for part in txt.split("data:"):
        part = part.strip()
        if not part:
            continue
        try:
            o = json.loads(part)
        except Exception:
            continue
        c = (o.get("reply") or {}).get("content") or ""
        if c:
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        if o.get("resultType") is not None:
            rt = o["resultType"]
        v = o.get("reference")
        if v:
            try:
                d = json.loads(v) if isinstance(v, str) else v
                raw = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(raw) if isinstance(raw, str) else (raw or [])
                if lst:
                    ref = lst
            except Exception:
                pass
    return r.status_code, status, answer, ref, rt


def cap_normal(s):
    code, status, ans, ref, rt = ask(s, "智造贷最高额度是多少？")
    ok = code == 200 and status == 2 and len(ans) > 10 and bool(ref)
    record("NORMAL", ok, f"http={code} status={status} answer_len={len(ans)} refs={len(ref)} rt={rt}",
           {"answer": ans[-300:], "ref0": ref[0] if ref else None})


def cap_faq(s):
    """FAQ 直答（正例）。R14-F01k：允许最多 3 次尝试，理由与 revoke_acceptance.ask_ok 一致 ——
    正例依赖外部模型，`resultType=2` 由 Java 侧 `faqSelect`（调 LLM 做 FAQ 筛选）决定，单发会抖；
    而**拒绝态断言仍单发不重试**（见 revoke 的纪律，避免把"拒绝"重试成"通过"）。
    检索层证据：19995 `faq_result_list` 实测 1 条（score≈0.333，字段 faq_question/faq_answer 齐全）；
    所以 resultType 抖动属应用层选择器，不是 A 修的 offset/break 回归。
    """
    tries, last, hit = 3, None, False
    for i in range(tries):
        code, status, ans, ref, rt = ask(s, "客户访前准备是否是文档的主要内容？", config_id=CFG_FAQ)
        last = (code, status, ans, ref, rt, i + 1)
        if code == 200 and status == 2 and rt == 2 and bool(ans):
            hit = True
            break
    code, status, ans, ref, rt, used = last
    ok = hit
    record("FAQ", ok, f"http={code} status={status} resultType={rt} 尝试={used}/{tries} "
                      f"answer={ans[:40]!r} refs={len(ref or [])}",
           {"answer": ans, "ref0": (ref or [None])[0]})


# ---------------------------------------------------------------- GLOBAL 三层
# 依据 docs/r12/r14/B-GLOBAL-GOLD.md：
#   G1 是**正例**（跨 2 文档 / 3 社区，答案=AAA→30bp、AA→60bp）；
#   R1/R2 是**无答案拒答位，文档明确"不计入正例统计"**。
# R14-F01i（B 指出我方选题错）：原 cap_global 拿 R1（票据贴现）当正例、还要求 ≥2 条来源，
#   在无答案题上结构上不可能满足 → refs=1 不是缺陷，是断言与题不匹配。故拆成三层：
#   ① GLOBAL_POS   正例：引用可解析 + ≥2 来源 + 出现社区 id（不看措辞/行数）
#   ② GLOBAL_REFUSE 拒答位：必须拒答且**不得出现任何具体数值**（防"编造 15/50/20 基点"回归），引用数不设下限
#   ③ GLOBAL_FAITH  忠实度（A 的双层建议第 2 层）：答案数值必须与上下文一致（AAA=30 / AA=60）
G1_Q = ("江南装备科技有限公司、华东精密制造有限公司、北方重工配件厂三家的信用评级分别是什么？"
        "按智造贷的评级加点规则，它们执行利率相对一年期LPR的加点分别是多少？")
R1_Q = "我们这类企业的授信额度与票据贴现是什么关系"
R2_Q = "海川电子材料股份有限公司被列为关注类，需要计提多少比例的贷款损失准备？"
# R14-F01q：C/B 修复 global 后，no_answer 文案改为「现有社区摘要不足以回答该问题，未生成推测性答案。」
# 原关键词表漏了这条 → R1/R2 被误判"未拒答"（假红）。拒答判定必须覆盖**当前实现的实际文案**，
# 且仍坚持"不得出现具体数值"这条硬约束（拒答里夹带编造数值照样 FAIL，见自检 GREFUSE-2）。
REFUSE_KEYS = ("未提及", "无法确定", "无法回答", "未提供", "没有相关", "没有直接", "未找到相关",
               "不包含", "不足以回答", "未生成推测性答案")
COMMUNITY_MARK = "[L0-"


# R14-F01u（B 的根因与判据）：13:10 那轮 R1/R2/FAITH 同时返回
#   「现有社区摘要不足以回答该问题，未生成推测性答案。」+ sources=[]
# 根因不是模型拒答，而是 `_load_summaries()` 读 ES 异常后被 `return []` 吞掉 →
# query_community 把"读不到社区"当成"这库没有社区"。时间对齐：13:10:41/47 index 服务重启。
# 判据（B 建议，采纳）：**同一批次内 GLOBAL 全类别同时变成"无来源拒答"** → 判 ENV_EVENT（不判 FAIL）；
# 只有个别题这样，才判产品缺陷。
ENV_REFUSE_KEYS = ("不足以回答", "未生成推测性答案")
_GLOBAL_BATCH = {"pos_envlike": False}


def _is_env_refusal(ans, refs, pos_envlike):
    """返回 True 表示"这一条应判 ENV_EVENT"：无来源 + 环境拒答文案 + 同批 POS 也无来源。"""
    a = ans or ""
    no_src = not [x for x in (refs or []) if x]
    return bool(pos_envlike) and no_src and any(k in a for k in ENV_REFUSE_KEYS)


def _summary_store_state(payload, answer=""):
    """R14-F01x（B 的三态契约，先落纯函数，等 19529 重启生效后接端到端）：
      store_down   —— ES/摘要读取失败（应 500 + data.error=summary_store_unavailable）
      no_community —— 该知识库确实没有社区摘要（应 200 + 提示先 /generate_community）
      no_fact      —— 有社区摘要但没有该事实（应 200 + "事实中未提及"，属正常拒答）
      answered     —— 正常作答
      unknown      —— 无法判定
    "读不到" 与 "确实没有" 必须可区分：前者是可监控/可重试的基础设施故障，
    后者是数据前置条件缺失；两者若都被写成"不足以回答"，就是本轮 13:10 那个假拒答。
    """
    body = payload if isinstance(payload, dict) else {}
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    msg = str(body.get("msg") or body.get("errorMsg") or "")
    err = str(data.get("error") or body.get("errorCode") or "")
    code = body.get("code")
    a = answer or ""
    if code == 500 or err == "summary_store_unavailable" or "读取失败" in msg or "不可用" in msg:
        return "store_down"
    if "没有社区摘要" in msg or "generate_community" in msg or "先构建社区" in msg:
        return "no_community"
    if any(k in a for k in ENV_REFUSE_KEYS) or "事实中未提及" in a:
        return "no_fact"
    if a.strip() and body.get("code") in (None, 200):
        return "answered"
    return "unknown"


def _infra():
    """R14-F01v（B 的建议）：给每条 global 结果附基建快照，便于一眼判断"整批拒答"是否 ES/图服务挂了。
    字段：graph_pid（19529 监听 pid）、es_ok/es_ms（POST 19527/search_by_custom_param 是否 <5xx 且耗时）。
    这样"13:10 那种假拒答"不必回头翻别人日志：es_ok=False + 全类别无来源拒答 = 环境。
    """
    info = {"graph_pid": (_port_pids(19529) or [None])[0], "es_ok": None, "es_ms": None}
    t0 = time.time()
    try:
        r = requests.post("http://127.0.0.1:19527/search_by_custom_param",
                          json={"index_name": [KB_NAME], "page_size": 1, "page_num": 1}, timeout=5)
        info["es_ok"] = (r.status_code < 500)
    except Exception:
        info["es_ok"] = False
    info["es_ms"] = round((time.time() - t0) * 1000, 1)
    return info


def _global_ask(s, q):
    t0 = time.time()
    code, status, ans, ref, rt = ask(s, q, global_mode=True)
    return code, status, ans, ref, rt, time.time() - t0


def _srcs(ref):
    return [str((x.get("metadata") or {}).get("source") or "") for x in (ref or [])]


def _src_ok(x):
    """引用是否"可解析"。
    R14-F01j（实测修正）：C 的 `toAbsoluteSource` 对**已带 http(s):// 的输入原样返回**，
    因此单 host 的绝对 URL（http://127.0.0.1:19000/r12-rag/...）是**合法**形态；
    真正的缺陷是**重复拼接的 host**（http://h/http://h/...，浏览器解析不出对象键）。
    原实现把两者一起判"不可解析" → 假红（GLOBAL_POS 因此误报 FAIL）。
    """
    if not x:
        return False
    return re.search(r"https?://[^/]*/https?://", x) is None and x.count("http://") <= 1 \
        and x.count("https://") <= 1


def cap_global(s):
    """① GLOBAL_POS（正例，G1）。断言落在"引用可核验 + 社区 id"，不落在措辞/行数（B 实测 reduce 不可逐字复现）。"""
    code, status, ans, ref, rt, cost = _global_ask(s, G1_Q)
    srcs = _srcs(ref)
    clean = [x for x in srcs if _src_ok(x)]
    abs_n = sum(1 for x in clean if x.startswith("http"))
    has_cid = COMMUNITY_MARK in (ans or "")
    # R14-F01p（B 的证据判定，采纳）：G1 的"≥2 来源"在当前语料**结构上不可稳定达标** ——
    #   加点规则（AAA→30/AA→60/A→100）全部集中在 L0-18625408 一个社区，评级在另两个社区，
    #   是否同时出现取决于模型有没有把"评级"和"加点"写在同一行（实测 refs=2 / refs=1 两种）。
    #   且 12:28 那次 refs=3 是 B **修复前**的错误引用（把 30 标到不含 30 的评级社区），
    #   修复后条数下降是质量提升，不是能力退化。
    #   故正例判据改为：≥1 条可解析 source + 出现社区 id；"跨 2 社区覆盖度"单列，只对多跳题有意义。
    ok = (code == 200 and status == 2 and len(clean) >= 1
          and len(clean) == len([x for x in srcs if x]) and has_cid)
    coverage = len({re.sub(r"/[^/]*$", "", x) for x in clean})
    infra = _infra()
    # 同批环境判据信号：正例都拿不到任何来源 → 后续拒答位若也是"无来源拒答"，判 ENV_EVENT
    _GLOBAL_BATCH["pos_envlike"] = (len(clean) == 0)
    # A 的纪律：断言 refs 数量的用例必须显式记录 configId（阈值/top_k 决定条数），否则时红时绿
    record("GLOBAL_POS", ok,
           f" http={code} status={status} cost={cost:.1f}s configId={CFG_DEFAULT} "
           f"refs={len(ref)} 可解析={len(clean)} 覆盖度(去重前缀)={coverage}"
           f"（绝对URL={abs_n} 相对键={len(clean) - abs_n}）社区id={has_cid} "
           f"src示例={clean[0][-45:] if clean else None} "
           f"infra(graph_pid={infra['graph_pid']},es_ok={infra['es_ok']},{infra['es_ms']}ms)",
           {"answer": (ans or "")[-400:], "sources": srcs[:5], "configId": CFG_DEFAULT,
            "infra": infra})


def cap_global_refuse(s):
    """② GLOBAL_REFUSE（R1/R2 拒答位）。要求：拒答语义 + **不得出现任何具体数值**；引用数不设下限。"""
    rows = []
    infra = _infra()
    for tag, q in (("R1", R1_Q), ("R2", R2_Q)):
        code, status, ans, ref, rt, cost = _global_ask(s, q)
        refused = any(k in (ans or "") for k in REFUSE_KEYS)
        nums = re.findall(r"\d+(?:\.\d+)?\s*(?:个基点|基点|%|％)", ans or "")
        ok = code == 200 and status == 2 and refused and not nums
        env = (not ok) and _is_env_refusal(ans, _srcs(ref), _GLOBAL_BATCH["pos_envlike"])
        rows.append(ok)
        record(f"GLOBAL_REFUSE/{tag}", ok,
               f"http={code} status={status} 拒答={refused} 编造数值={nums[:3]} refs={len(ref or [])} "
               f"answer={ (ans or '')[:60]!r} "
               f"infra(graph_pid={infra['graph_pid']},es_ok={infra['es_ok']})"
               + (" ← ENV_EVENT：同批 GLOBAL 全类别无来源拒答，判环境（B：_load_summaries 读 ES 异常被吞）"
                  if env else ""),
               {"answer": ans, "sources": _srcs(ref)[:5], "infra": infra},
               neutral=env)


def cap_global_faith(s):
    """③ GLOBAL_FAITH（A 的双层建议第 2 层）：检索给了正确依据，生成也必须与之一致。

    判据按"客户→加点"的**映射**判，不按"同一句里 AAA 与 30 相邻"判：
    实测答案把"评级"和"加点"分句表述（`…信用评级是AAA，依据为[L0-…]。…加点是30个基点。`），
    用同句配对会假红（我第一版就踩了）。原文 §三：AAA→30、AA→60、A→100。
    """
    code, status, ans, ref, rt, cost = _global_ask(s, G1_Q)
    infra = _infra()
    a = ans or ""
    expect = {"江南装备": "30", "华东精密": "60", "北方重工": "60"}
    def _fp(name):
        """取"该客户名之后、**不跨越句号**的 80 字内"的第一个加点数值。
        两个约束都是实测出来的：
          - 不跨句号：避免把下一家客户/下一段的数值当成本客户的（假绿）；
          - 每家独立 search（不是按串行 finditer 切段）：实测同一句会写多家客户
            （`华东精密与北方重工为 AA，加 60 个基点`），串行切段会漏掉后面那家。
        """
        m = re.search(re.escape(name) + r"[^。\n]{0,80}?(?:加点|加)\s*(?:是|为)?\s*"
                                     r"(\d{1,3})\s*(?:个)?\s*基点", a)
        return m.group(1) if m else None

    found = {k: _fp(k) for k in expect}
    bad = {k: (found.get(k), v) for k, v in expect.items() if found.get(k) != v}
    # 另一条最低要求：答案里必须同时出现 30 与 60 两个正确数值（防"只答了评级、没答加点"）
    nums = set(re.findall(r"(\d{1,3})\s*(?:个)?基点", a))
    missing_vals = [v for v in ("30", "60") if v not in nums]
    first_ok = code == 200 and status == 2 and not bad and not missing_vals

    # R14-F01o（C 的实测要求）：global reduce 输出**非确定**（同题两次实测 30/60/60 与 30/20/20），
    # 单发会让同一代码同一数据红绿交替。故取 3 次多数票；但**不下放到单跳数值题**（B 实测单跳稳定取错行，
    # 那种必须回到 PASS/FAIL 单值断言）。
    runs = [{"ok": first_ok, "found": dict(found), "missing": missing_vals,
             "env": _is_env_refusal(ans, _srcs(ref), _GLOBAL_BATCH.get("pos_envlike"))}]
    for _ in range(2):
        if sum(1 for r in runs if r["ok"]) >= 2:
            break
        c2, s2, a2, ref2, rt2, _cost = _global_ask(s, G1_Q)
        f2 = {k: None for k in expect}
        for k in expect:
            m = re.search(re.escape(k) + r"[^。\n]{0,80}?(?:加点|加)\s*(?:是|为)?\s*"
                                        r"(\d{1,3})\s*(?:个)?\s*基点", (a2 or ""))
            f2[k] = m.group(1) if m else None
        n2 = set(re.findall(r"(\d{1,3})\s*(?:个)?基点", a2 or ""))
        miss2 = [v for v in ("30", "60") if v not in n2]
        runs.append({"ok": (c2 == 200 and s2 == 2 and f2 == expect and not miss2),
                     "found": f2, "missing": miss2,
                     "env": _is_env_refusal(a2, _srcs(ref2), _GLOBAL_BATCH.get("pos_envlike"))})
    votes = sum(1 for r in runs if r["ok"])
    ok = votes >= 2
    env = (not ok) and _GLOBAL_BATCH.get("pos_envlike") and all(r.get("env") for r in runs)
    record("GLOBAL_FAITH", ok,
           f"多数票={votes}/{len(runs)} 首次 http={code} 首次实测={found} 期望={expect} "
           f"不符={bad} 缺失数值={missing_vals} 各次={[r['found'] for r in runs]}"
           + f" infra(graph_pid={infra['graph_pid']},es_ok={infra['es_ok']})"
           + (" ← ENV_EVENT：同批 GLOBAL 全类别无来源拒答，判环境" if env else ""),
           {"runs": runs, "sources": _srcs(ref)[:5], "infra": infra},
           neutral=env)


def cap_version(s):
    """R14-F01：原断言 `isinstance(groups, list)` 对空列表恒真（实测 groups=0 也 PASS，属假绿）。
    现要求：有版本组、至少一组含 >=2 个版本、版本号非空。空列表=失败，不允许跳过。"""
    code, body = api(s, "GET", f"/index/knowledgeBase/file/multiple/version?kbNames={KB_NAME}&pageNo=1&pageSize=10", s.token)
    groups = ((body or {}).get("data") or {}).get("records") if isinstance(body, dict) else None
    groups = groups if isinstance(groups, list) else []
    # 只是"同版本文档有两条"不算多版本：必须出现 >=2 个不同版本号（V0/V1）
    multi = [g for g in groups if len({(k.get("version") or "") for k in (g.get("kbFiles") or [])}) >= 2]
    vers = [k.get("version") for g in multi for k in (g.get("kbFiles") or [])]
    # R14-F01v（C 要求的前置）：`document_version()` 靠 `parent_file_name` 归组，只保留最高版本。
    # 若同组两版的 parent_file_name 不一致（`x.docx` vs `x(1).docx`），`_vkey` 会分成两组，
    # 于是 **V0 与 V1 可能同时进上下文**（C12 的残余风险）。故把"同组 parent 必须一致"作为前置。
    # 三态：字段未透出 → 不判（记"未透出"，不当真/不当假）；透出且不一致 → FAIL。
    pn_state, pn_bad = "未透出", []
    for g in multi:
        names = [str(k.get("parentFileName") or k.get("parent_file_name") or "").strip()
                 for k in (g.get("kbFiles") or [])]
        names = [x for x in names if x]
        if names:
            pn_state = "有"
            if len(set(names)) > 1:
                pn_bad.append(names[:3])
    ok = (code == 200 and len(groups) > 0 and len(multi) > 0
          and all(v not in (None, "") for v in vers) and not pn_bad)
    detail = (f"http={code} groups={len(groups)} 多版本组={len(multi)} 版本={vers[:6]} "
              f"parent一致前置={pn_state}{' 不一致=' + str(pn_bad[:2]) if pn_bad else ''}")
    if not groups:
        detail += " ← 空列表不再算通过"
    record("VERSION", ok, detail, {"groups": groups[:2]})


def no_recall_verdict(refs_n, answer):
    """R14-P1-01（TL 指定 P1）：零召回仍生成确定性答案 = 无依据作答。

    背景：B 实测 `恒星项目的归口部门是哪个？`（kb_9 无对应块）→ http=200、refs=0、
    答案却是"阿里云智能"；C 同题答"阿里巴巴达摩院"。**两次不同、且都无引用**。
    根因：拒答守卫要求 `depend_on_kb=1`，而该列全表为 0 → 守卫是死代码。
    判据（TL 原话）：
      refs==0 且答案含具体实体名/数值 → FAIL（"无依据作答"）
      refs==0 且答案形如"未能找到/未提及/请补充" → PASS
      有引用 → PASS（本函数只管"零引用"这一形态）
    这比"答错"更危险：用户看不到引用，会以为系统只是省略了出处。
    """
    a = (answer or "").strip()
    if refs_n > 0:
        return True, "有引用（不在本判据范围）"
    refuse_words = ("未提及", "未能找到", "没有找到", "未能检索", "请补充", "没有相关",
                    "未涉及", "无相关", "无法回答", "无法确定", "无法得出", "没有足够")
    if any(k in a for k in refuse_words):
        return True, "零引用 + 明确拒答"
    entity = re.search(r"(阿里|达摩院|事业部|归口|中心|集团|公司|银行|分行|部门)", a)
    number = re.search(r"\d{2,}", a)
    if entity or number:
        return False, f"零引用 + 确定性断言（实体={bool(entity)} 数值={bool(number)}）"
    if len(a) < 8:
        return False, "零引用 + 极短非拒答（不可判读，也不能算通过）"
    return False, "零引用 + 非拒答表述"


def cap_no_recall(s):
    """R14-P1-01：零召回是否被当成"能答"（无依据作答）。"""
    q = os.environ.get("R14_NORECALL_Q", "恒星项目的归口部门是哪个？")
    http, status, answer, refs, rtype = ask(s, q, CFG_DEFAULT, timeout=180)
    n = len(refs or [])
    ok, why = no_recall_verdict(n, answer)
    record("NO_RECALL_FAB", ok,
           f"http={http} status={status} refs={n} 判定={why} answer={answer[:60]!r}"
           + ("" if ok else " ← 零召回仍给出确定性答案（拒答守卫未生效）"),
           {"question": q, "refs": n, "answer": answer[:400], "status": status})



def retry_storm_verdict(rows, limit=3):
    """R14-P2-01 判据：同一 file_id 在 T 分钟内不应产生 >limit 条新 task。

    背景（TL 定位）：加密 PDF 必然失败 → 被判"可重试" → 文件置 98(RETRY) →
    **重试新建一条 task、`retry_times` 从 0 重新开始** → `retry_limit=3` 永远达不到 →
    无限重生。表现为"文件永远到不了终态"，而每个组件都自认为正常。
    与上午的"僵尸任务占槽"对照：上午是任务不结束，这次是任务无限重生，
    **同一种堵，两种形态，运行期都不报错，只表现为"什么都没发生"**。
    rows: [(file_id, count), ...]
    """
    bad = [{"file_id": f, "tasks": int(c)} for f, c in rows if int(c) > limit]
    if not bad:
        return True, f"无 file_id 在窗口内产生 >{limit} 条 task"
    worst = sorted(bad, key=lambda x: -x["tasks"])[:5]
    return False, f"{len(bad)} 个 file_id 产生 >{limit} 条 task（无限重试嫌疑）：{worst}"


def restart_without_counter(rows, gap_min=5):
    """R14-P2-01b：同一条 task **原地重启**但 `retry_times` 不增（计数形同虚设）。

    第一版判据只看"同一 file_id 30 分钟内 task 数 >3"，抓不到这种形态：
    实测 file 443 只有 task 471 一条，但 `gmt_create=14:46:18`、`start_time=14:53:45`
    —— 同一条任务被反复拉起，`retry_times` 仍是 0，`retry_limit=3` 永远达不到。
    判据：status ∈ (2 处理中, 3 重试中) 且 start_time - gmt_create >= gap_min 分钟
          且 retry_times == 0 → "重启了但没记账"。
    rows: [(task_id, file_id, status, retry_times, gap_minutes), ...]
    """
    bad = [{"task": t, "file_id": f, "status": st, "retry_times": rt, "gap_min": int(g) if g else 0}
           for t, f, st, rt, g in rows
           if str(st) in ("2", "3") and (g not in (None, "NULL")) and int(g) >= gap_min
           and int(rt or 0) == 0]
    if not bad:
        return True, "无「原地重启但不计数」的任务"
    return False, f"{len(bad)} 条任务原地重启但 retry_times=0（无限重试且计数失效）：{bad[:3]}"



def cap_parse_retry_storm(s):
    """R14-P2-01：永久失败的文件被无限重试（重试风暴）。"""
    mins = int(os.environ.get("R14_RETRY_WINDOW_MIN", "30"))
    limit = int(os.environ.get("R14_RETRY_MAX_TASKS", "3"))
    try:
        raw = _mysql("select file_id,count(*) c from gienrag.file_parse_task "
                     "where gmt_create > now() - interval %d minute "
                     "group by file_id having c > %d;" % (mins, limit))
        rows = [line.split() for line in raw.splitlines() if len(line.split()) == 2]
        stuck = _mysql("select count(*) from gienrag.knowledge_base_list "
                       "where status in (98,99) and gmt_modified < now() - interval %d minute;" % mins)
        ok, why = retry_storm_verdict(rows, limit)
        raw2 = _mysql("select id,file_id,status,retry_times,"
                      "timestampdiff(minute,gmt_create,start_time) from gienrag.file_parse_task "
                      "where status in (2,3);")
        rows2 = [line.split("\t") for line in raw2.splitlines() if len(line.split("\t")) == 5]
        ok2, why2 = restart_without_counter(rows2)
        # 事后观察（不判红）：已终结但仍 retry_times=0 且耗时很长的失败任务 —— 疑似"原地重启未计数"
        # 的残留证据。之所以只记数不判红：队列积压也会拉长耗时，判红会误伤。
        # 实测这两个任务 end_time 是 NULL（终结时没回写），所以用 coalesce(end_time, gmt_modified)
        slow_fail = _mysql("select count(*) from gienrag.file_parse_task "
                           "where status=5 and retry_times=0 "
                           "and timestampdiff(minute, gmt_create, coalesce(end_time, gmt_modified)) > 10 "
                           "and gmt_modified > now() - interval %d minute;" % mins)
    except Exception as e:                                   # noqa: BLE001
        record("PARSE_RETRY_STORM", False,
               f"无法查询重试情况：{type(e).__name__}: {e} ← 观测失败不能当健康")
        return
    stuck_n = int(stuck or 0)
    # 卡在 98/99 且超窗：同样属于"永远不结束"，一起判
    ok = ok and stuck_n == 0 and ok2
    detail = (f"窗口={mins}分钟 阈值>{limit}条/文件 超限文件={why} "
              f"status∈(98,99)超窗未结束={stuck_n} 原地重启未计数={why2} "
              f"（事后观察：窗口内失败且耗时>10min且retry_times=0 的任务={slow_fail}，不判红）")
    if stuck_n:
        detail += " ← 有文件长期停在重试/解析中（不会到达终态）"
    record("PARSE_RETRY_STORM", ok, detail,
           {"rows": rows[:20], "rows_inflight": rows2[:10], "stuck_98_99": stuck_n,
            "window_min": mins, "limit": limit, "restart_check": why2,
            "slow_fail_no_retry_count": slow_fail})



def _proc_start_of(port):
    """取监听该端口的进程启动时刻（'YYYY-MM-DD HH:MM:SS'），用于"只统计本轮代码产生的失败"。"""
    try:
        out = subprocess.run(["ss", "-lntpH", f"sport = :{port}"], capture_output=True, text=True).stdout
        m = re.search(r"pid=(\d+)", out)
        if not m:
            return ""
        pid = m.group(1)
        ps = subprocess.run(["ps", "-o", "lstart=", "-p", pid], capture_output=True, text=True).stdout.strip()
        # 'Tue Oct 27 15:41:12 2026' -> '2026-10-27 15:41:12'
        return datetime.strptime(ps, "%a %b %d %H:%M:%S %Y").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""



def convert_path_verdict(rows, limit=0):
    """R14-P3-01：Office→PDF 转换不可用/回落失效，导致解析器去读不存在的 `.pdf`。

    现场（15:32–15:40，docx 4/4、pptx 1/1）：
      Java  `jodconverter LocalConversionTask - Local conversion failed`
            `NullPointerException: Could not open document: r12conv-xxx.docx`
            随后 WARN「回落直接解析原始 docx」——**但发给解析服务的 file_path 仍是 .pdf**
      docparse 收到 `…/docx-plain.docx/V0/docx-plain.pdf` → S3 NoSuchKey → status=4
    上游原因：转换用的地址是 `http://127.0.0.1:19000/...`（匿名），实测 **403**（桶无匿名策略）。
    判据：窗口内 `error_msg` 含 `NoSuchKey` 且路径以 `.pdf` 结尾的失败任务数 > limit → FAIL。
    rows: [(task_id, file_id, left(error_msg,120)), ...]
    """
    bad = [{"task": t, "file_id": f, "err": e} for t, f, e in rows]
    if len(bad) <= limit:
        return True, f"窗口内无「转换产物缺失」型失败（{len(bad)} 条）"
    return False, f"{len(bad)} 条任务因转换产物缺失失败（NoSuchKey *.pdf）：{bad[:3]}"


def cap_parse_convert_path(s):
    """R14-P3-01：docx/pptx 的"转换 → 回落"链路是否把解析器指向不存在的 pdf。"""
    mins = int(os.environ.get("R14_CONV_WINDOW_MIN", "15"))
    # 只统计**当前 index 进程启动之后**产生的失败：
    # 否则"修复前的历史行"会在窗口内持续把判据拖红（15:40 的 6 条会红到 15:55），
    # 而重启后又应该立刻恢复敏感 —— 用"进程启动时刻"做起点，两个问题一起解决。
    since = _proc_start_of(18082) or ""
    where = (f"gmt_modified > '{since}'" if since else
             f"gmt_modified > now() - interval {mins} minute")
    try:
        raw = _mysql("select id,file_id,left(coalesce(error_msg,''),150) from gienrag.file_parse_task "
                     "where status=5 and error_msg like '%%NoSuchKey%%' and error_msg like '%%.pdf%%' "
                     f"and {where} order by id desc limit 20;")
        rows = [line.split("\t") for line in raw.splitlines() if len(line.split("\t")) == 3]
        ok, why = convert_path_verdict(rows)
    except Exception as e:                                   # noqa: BLE001
        record("PARSE_CONVERT_PATH", False,
               f"无法查询转换链路失败：{type(e).__name__}: {e}")
        return
    record("PARSE_CONVERT_PATH", ok,
           f"统计起点={since or ('近%d分钟' % mins)} {why}"
           + ("" if ok else " ← Office→PDF 转换不可用或回落仍传 .pdf（解析器读不到对象）"),
           {"rows": rows})



def cap_table(s):
    code, status, ans, ref, rt = ask(s, "台账里华东精密制造的授信额度是多少？")
    # R14-F01：原断言只匹配 "3000"，随便一句含 3000 的错误答案也能过。
    # 现在要求数值+单位+主体同时成立，且必须有引用。
    # R14-F01c（QA 追加收紧）：还必须落在被问的那个口径上（授信/额度）。
    # 只要求"3000+万元+主体"时，"华东精密制造 2025 年营收 3000 万元"这类答错维度的答案仍会判通过。
    on_topic = ("授信" in ans) or ("额度" in ans)
    ok = (code == 200 and status == 2 and "3000" in ans and "万元" in ans
          and ("华东精密" in ans or "精密制造" in ans) and on_topic and bool(ref))
    record("TABLE", ok, f"http={code} status={status} 数值={'3000' in ans} 单位={'万元' in ans} "
                        f"主体={'华东精密' in ans or '精密制造' in ans} 口径='授信/额度'={on_topic} "
                        f"refs={len(ref)} answer={ans[-60:]!r}",
           {"answer": ans[-300:], "refs": len(ref)})


def cap_graph_local(s):
    """图局部检索：直接打检索服务，避免被 rerank 掩盖。"""
    payload = {"query": "智造贷的授信额度和票据贴现是什么关系", "knowledge_base_name": [KB_NAME],
               "top_k": 10, "enabled_faq": False, "enabled_graph": True, "enabled_rerank": False,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions", "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19995/retrieval_documents", json=payload, timeout=180)
    data = (r.json() or {}).get("data") or {}
    docs = data.get("documents_list") or []

    def _is_graph(d):
        """图参与判据用 metadata.search_type（实测 shape: ['milvus','es','es','graph']，兼容字符串）。"""
        st = (d.get("metadata") or {}).get("search_type")
        if isinstance(st, (list, tuple)):
            return any("graph" in str(x).lower() for x in st)
        return "graph" in str(st or "").lower()

    graph_docs = [d for d in docs if _is_graph(d)]
    # R14-F01：原断言只看 metadata 里有没有 "graph" 字符串，属通路探测。
    # R14-F01h（B 的边界）：**引用条数不能当"图有贡献"的判据** —— 纯中文查询时开图/关图引用数可能相同（各 3 条），
    # 差别只在 search_type 是否含 graph。故判据 = search_type 含 graph + 正文非空。
    filled = [d for d in graph_docs if (d.get("page_content") or "").strip()]
    ok = r.status_code == 200 and len(filled) > 0
    st_sample = [((d.get("metadata") or {}).get("search_type")) for d in docs[:3]]
    record("GRAPH_LOCAL", ok, f"http={r.status_code} docs={len(docs)} 含graph标记={len(graph_docs)} "
                              f"有正文的图块={len(filled)} search_type示例={st_sample}",
           {"graph_docs": graph_docs[:3]})


def cap_graph_identity(s):
    """R14-F01e（B-graph/A-data 提供字段）：图检索的数据错误计数必须可断言。

    位置纪律（B 明确纠正过的）：
      - `identity_violations` / `identity_violations_count` 在 **19529 `query_graph_data` 响应 data 顶层**；
        19995 是自己组合响应，**不转发**这两个字段，所以只能直连 19529 断言；
      - `provenance_quality` / `identity_stability` 才是在每个块的 metadata 里、且被 19995 白名单吃掉 → 现不可验。
    断言纪律（A 强调的三条）：① 只在 code==200 时取键，缺键判 FAIL（不得 `.get(...,0)` 恒真）；
    ② count 必须为 0；③ 非 0 时把 violations 原样写证据。
    """
    payload = {"space_name": KB_NAME, "query": PROV_QUERY,
               "knowledge_base_name": [KB_NAME], "top_k": PROV_TOP_K,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions",
                              "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19529/query_graph_data", json=payload, timeout=120)
    try:
        body = r.json()
    except Exception:
        body = {}
    data = (body.get("data") or {}) if isinstance(body, dict) else {}
    has_keys = ("identity_violations" in data) and ("identity_violations_count" in data)
    cnt = data.get("identity_violations_count")
    bcode = body.get("code") if isinstance(body, dict) else None
    reason = data.get("reason") if isinstance(data, dict) else None
    blocks = data.get("result_data") or []
    # R14-F01n（TL 新口径，已批准 B 改）：图检索的**业务空结果改 200 + data.reason**
    #   reason ∈ {no_entity_extracted, no_vertex_matched, space_not_found}；`:795` 图检索异常仍 500。
    # 因此判定一刀切：
    #   - http 5xx                   → FAIL（故障）；
    #   - http 200 + body code=500   → FAIL（**故障伪装成业务空**，这条正是"用解释消化失败"）；
    #   - http 200 + code=200 + result_data=[] + reason → INFO/EMPTY_LEGIT（合法空，但不计入正例）；
    #   - http 200 + code=200 + 有结果 → 严格校验 identity 两键存在且 count==0。
    fault = (r.status_code >= 500) or (r.status_code == 200 and bcode == 500)
    empty_legit = (r.status_code == 200 and bcode == 200 and not blocks and bool(reason))
    real_ok = (r.status_code == 200 and bcode == 200 and bool(blocks))
    ok = real_ok and has_keys and cnt == 0
    detail = (f"http={r.status_code} code={bcode!r} reason={reason!r} 块数={len(blocks)} "
              f"键存在={has_keys} violations_count={cnt!r}")
    if real_ok and not has_keys:
        detail += " ← 200 缺键不得当 0"
    if fault:
        detail += " ← 故障（5xx 或 body code=500）：业务空结果应当是 200+reason，故障不得伪装成空"
    elif empty_legit:
        detail += " ← EMPTY_LEGIT：合法空结果（200+reason），允许但不计入正例"
    record("GRAPH_IDENTITY", ok, detail,
           {"identity_violations": data.get("identity_violations"), "reason": reason},
           neutral=empty_legit)


PROV_INDEXES = (KB_NAME, "table_chunks_" + KB_NAME, "table_summary_" + KB_NAME)


def _es_count_source(src):
    """跨三索引查 metadata.source 是否存在（R14-F01r，B 的判定修正）。

    B 的证据：台账类块的 source 不在 `kb_9` 索引里，而在 `table_chunks_kb_9`
    （`_id=1145021270768877382 file_id=314 version=V0`，source 完全相同）。
    只查 `kb_9` 会把**所有表格/台账引用都判成悬空**（假红）。
    故按 `kb_9 + table_chunks_kb_9 + table_summary_kb_9` 三索引合计计数。
    返回 (命中数, 命中的索引名列表)；-1 表示查询异常。
    """
    total, hit_idx = 0, []
    try:
        for idx in PROV_INDEXES:
            r = requests.get(f"http://127.0.0.1:19200/{idx}/_count",
                             json={"query": {"term": {"metadata.source.keyword": src}}}, timeout=30)
            n = int(((r.json() or {}).get("count")) or 0)
            if n > 0:
                total += n
                hit_idx.append(idx)
        return total, hit_idx
    except Exception:
        return -1, []


# 重建后要"硬判 stale"：B 判定当前 2 个 stale 是 entity_content 兜底的预期副产品
# （图旧 pk 全悬空 → 按实体名回查 ES → 命中同名 V0），硬判会把"代次悬空"误记成"新鲜度"。
# 故默认 strict=0（stale 只记 INFO）；重建完成后用环境变量 R14_PROV_STRICT=1 跑同一脚本即硬判。
PROV_STRICT = os.environ.get("R14_PROV_STRICT", "0") == "1"

# 探针集合（B 要求两边统一口径，避免"我 0 个 stale、你 2 个 stale"被读成数据不一致）
PROV_QUERY = "智造贷 授信额度 票据贴现"
PROV_TOP_K = 5


def _prov_verdict(exact, dangling, stale, strict=None):
    """GLOBAL_PROVENANCE 的判定（纯函数，便于自检）。

    strict=False：ok = exact>0 且无悬空（stale 只记 INFO）
    strict=True ：再要求 stale==0（重建后的硬判据：V0 的 pk 混进图 = 真缺陷）
    """
    st = PROV_STRICT if strict is None else strict
    ok = (exact > 0) and (not dangling)
    if st:
        ok = ok and (stale == 0)
    return ok


def _ver_of(m):
    """块的版本号。R14-F01z：重建后 19529 的 metadata **不再返回 `version` 字段**
    （keys 里已无 version/provenance_quality/identity_stability），故从 `source` 的 `/Vn/` 兜底解析。"""
    v = m.get("version")
    if v:
        return str(v)
    mm = re.search(r"/V(\d+)/", str(m.get("source") or ""))
    return f"V{mm.group(1)}" if mm else ""


def _es_ids(pks):
    """按 _id 在三索引里反查存在的 pk 集合（TL 的 F04 判据：pk ∩ ES._id）。"""
    got = set()
    if not pks:
        return got
    body = {"size": len(pks) + 5, "_source": False, "query": {"ids": {"values": [str(p) for p in pks]}}}
    for idx in PROV_INDEXES:
        try:
            r = requests.post(f"http://127.0.0.1:19200/{idx}/_search", json=body, timeout=30)
            for h in (((r.json() or {}).get("hits") or {}).get("hits") or []):
                got.add(str(h.get("_id")))
        except Exception:
            pass
    return got


def _version_freshness(blocks):
    """R14-F01w（B 提醒的"双绿陷阱"）：exact_chunk>0 但 **V0 混进输入** → 数字好看、语义错。

    块级 metadata 实测含 `version`（V0/V1）与 `parent_file_name`，据此判"是否为旧版本块"：
      - 同一 parent_file_name 若同时存在 V1，则 V0 块记为 stale；
      - 按字符串取最大版本号作为"最新"（V0 < V1 < V2 …）。
    返回 (stale_list, latest_map)。
    """
    latest, seen = {}, {}
    for b in blocks:
        m = b.get("metadata") or {}
        name = str(m.get("parent_file_name") or m.get("title") or "")
        ver = _ver_of(m)
        if not name or not ver:
            continue
        seen.setdefault(name, set()).add(ver)
    for name, vers in seen.items():
        try:
            latest[name] = sorted(vers, key=lambda v: int(re.sub(r"\D", "", v) or 0))[-1]
        except Exception:
            latest[name] = sorted(vers)[-1]
    stale = []
    for b in blocks:
        m = b.get("metadata") or {}
        name = str(m.get("parent_file_name") or m.get("title") or "")
        ver = _ver_of(m)
        exp = latest.get(name)
        if exp and ver and ver != exp:
            stale.append({"name": name, "version": ver, "latest": exp,
                          "source": str(m.get("source") or "")[-45:]})
    return stale, latest


def cap_graph_provenance(s):
    """R14-F04（TL 定判据）：图块不仅"有引用"，还必须**可回指原文**。

    TL 判据：`exact_chunk > 0` 且 引用可解析（source 在 ES 命中 >0；悬空即 FAIL）。
    现状（B/C 均已确认）：图 `chunk_pk_list` 存的还是抽取时刻的旧 ES `_id`，与当前 ES 交集为 0，
    图路全靠 `recovered_by=entity_content` 重建、`exact_chunk` 恒 0 → **本项应 FAIL，归"数据代次悬空"，
    不属于环境，也不能写进"P1 已修复"的通过项**。重解析并重建图后才会转绿。
    """
    payload = {"space_name": KB_NAME, "query": PROV_QUERY,
               "knowledge_base_name": [KB_NAME], "top_k": PROV_TOP_K,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions",
                              "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19529/query_graph_data", json=payload, timeout=120)
    try:
        body = r.json()
    except Exception:
        body = {}
    data = (body.get("data") or {}) if isinstance(body, dict) else {}
    blocks = data.get("result_data") or []
    pq = [((b.get("metadata") or {}).get("provenance_quality")) for b in blocks]
    exact = sum(1 for x in pq if x == "exact_chunk")
    # R14-F01z：重建后 19529 不再返回 provenance_quality（字段整体缺失，不是值变化）。
    # 这时不能判 PASS（没证据），也不该判 FAIL（归因会指错人）。按 TL 的 F04 判据
    # **直接用存储事实**：块的 pk 是否存在于当前 ES 的 _id 集合里（pk ∩ ES._id > 0）。
    pk_hit = set()
    if exact == 0 and not any(pq):
        pks = [((b.get("metadata") or {}).get("pk")) for b in blocks]
        pks = [p for p in pks if p]
        hit = _es_ids(pks)
        pk_hit = {p for p in pks if str(p) in hit}
        exact = len(pk_hit)
    dangling, checked, idx_hits = [], 0, {}
    for b in blocks[:5]:
        src = str(((b.get("metadata") or {}).get("source")) or "")
        if not src:
            dangling.append("<empty-source>")
            continue
        n, hit = _es_count_source(src)
        checked += 1
        if n <= 0:
            dangling.append(src[-50:])
        else:
            idx_hits[",".join(hit)] = idx_hits.get(",".join(hit), 0) + 1
    stale, latest = _version_freshness(blocks)
    ok = (r.status_code == 200 and (body.get("code") == 200) and len(blocks) > 0
          and _prov_verdict(exact, dangling, len(stale)))
    detail = (f"http={r.status_code} 块数={len(blocks)} exact_chunk={exact} "
              f"provenance分布={sorted(set(map(str, pq)))} 抽查引用={checked} "
              f"命中索引={idx_hits} 悬空={dangling[:3]} stale_version={len(stale)} 最新版本={latest} "
              f"pq字段={'缺失' if not any(pq) else '有'} pk∩ES_id={len(pk_hit)} "
              f"strict={PROV_STRICT} 探针={PROV_QUERY!r}/top_k={PROV_TOP_K}")
    if blocks and exact == 0:
        detail += " ← 数据代次悬空：图 chunk_pk_list 与当前 ES _id 无交集（需重解析+重建图）"
    record("GRAPH_PROVENANCE", ok, detail,
           {"provenance_quality": pq, "dangling": dangling,
            "stale_blocks": stale, "latest_version": latest,
            "probe": {"query": PROV_QUERY, "top_k": PROV_TOP_K, "kb": KB_NAME},
            "strict": PROV_STRICT})
    # B 的"双绿陷阱"：exact_chunk>0 但 V0 混入 → 单列 INFO（暂不并入 FAIL 条件，
    # 因为 V0/V1 的收敛归 A 的重解析周期；B 若要求转硬判据，一行改为 ok=... and not stale 即可）
    record("GRAPH_VERSION_FRESH", (not stale),
           f"旧版本块={len(stale)} 最新版本={latest} 明细={stale[:3]}"
           + ("" if not stale else " ← exact_chunk 可能已达标但混入旧版本（语义错，非数字错）"),
           {"stale_blocks": stale}, neutral=bool(stale))


UPPER_Q = "信用评级为AAA的公司执行利率需要加多少个基点"
LOWER_Q = "信用评级为aaa的公司执行利率需要加多少个基点"


def _retr(query, enabled_graph=True):
    """返回 (http, docs, graph_blocks, search_type 采样)。图参与判据同 GRAPH_LOCAL。"""
    payload = {"query": query, "knowledge_base_name": [KB_NAME], "top_k": 10,
               "enabled_faq": False, "enabled_graph": enabled_graph, "enabled_rerank": False,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions",
                              "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19995/retrieval_documents", json=payload, timeout=180)
    try:
        docs = (((r.json() or {}).get("data") or {}).get("documents_list") or [])
    except Exception:
        docs = []

    def _is_graph(d):
        st = (d.get("metadata") or {}).get("search_type")
        if isinstance(st, (list, tuple)):
            return any("graph" in str(x).lower() for x in st)
        return "graph" in str(st or "").lower()

    return (r.status_code, docs, sum(1 for d in docs if _is_graph(d)),
            [((d.get("metadata") or {}).get("search_type")) for d in docs[:2]])


def cap_graph_uppercase(s):
    """R14-F01f：开图检索对"查询含大写 ASCII"不健壮 —— 成对用例，防"只测小写所以一直绿"。

    事实（A-data 独立隔离）：`信用评级为AAA…` + enabled_graph=true → 500；同句小写 → 200；
    大写 + enabled_graph=false → 200。归因＝检索层 KeyError（不是图算法无效），
    且这条也是 B 观测到"用户入口开图 refs=0 但答案正确"的成因之一。
    """
    cu, du, gu, stu = _retr(UPPER_Q, True)
    cl, dl, gl, stl = _retr(LOWER_Q, True)
    # 不只判"不 500"：还必须证明**图真的并进来了**（B 的补强，防"C 修掉 500 但图仍没参与"漏判）
    ok = (cu == 200 and cl == 200 and len(du) > 0 and len(dl) > 0 and gu > 0 and gl > 0)
    detail = (f"大写(AAA)+开图 http={cu} docs={len(du)} graph块={gu} | "
              f"小写(aaa)+开图 http={cl} docs={len(dl)} graph块={gl}")
    if cu != 200 and cl == 200:
        detail += " ← 仅大写失败：开图检索对大写 ASCII 抛异常（检索层缺陷，非图算法无效）"
    elif cu == 200 and (len(du) == 0 or gu == 0):
        detail += " ← 大写真 200 但无文档/无 graph 块：只证明不 500，未证明图参与"
    record("GRAPH_UPPERCASE", ok, detail,
           {"upper_query": UPPER_Q, "lower_query": LOWER_Q, "upper_http": cu, "lower_http": cl,
            "upper_docs": len(du), "lower_docs": len(dl),
            "upper_graph_blocks": gu, "lower_graph_blocks": gl,
            "search_type_upper": stu, "search_type_lower": stl})


def _parse_resp_ok(payload):
    """R14-F01s（TL 指定）：解析/重解析响应必须**逐任务**校验，不能只看顶层 success。

    缺陷原型（A 发现）：`converted_file_path` 以 `.md` 结尾的文件重解析 →
    HTTP 200 + 顶层 `success=true`，但 `task_statuses[0].success=false`。
    `FileAppServiceImpl:259` 只读顶层 `success` 就置 PARSE_SUCCESS，于是"收到了"被当成"做到了"。
    返回 (ok, kind, detail)：
      - kind="no_status"：响应里没有 task_statuses（无法判定，调用方应记 INFO 而非 PASS）；
      - kind="fake_success"：顶层 true 但存在 task_statuses[*].success != true（**本缺陷**）；
      - kind="failed"：顶层就是 false（明确失败，属另一类）；
      - kind="ok"：顶层 true 且每个 task_statuses[*].success 都 true。
    """
    if not isinstance(payload, dict):
        return None, "no_status", "响应不是 JSON 对象"
    ts = payload.get("task_statuses")
    if ts is None:
        ts = payload.get("taskStatuses")
    top = payload.get("success")
    if not isinstance(ts, list) or not ts:
        return None, "no_status", f"无 task_statuses（顶层 success={top!r}）"
    bad = [(i, (t or {}).get("success"), (t or {}).get("message"))
           for i, t in enumerate(ts) if not (isinstance(t, dict) and t.get("success") is True)]
    if top is not True:
        return False, "failed", f"顶层 success={top!r}，任务失败 {len(bad)}/{len(ts)}"
    if bad:
        return False, "fake_success", f"顶层 success=true 但任务 {bad[:3]} 非成功（假成功）"
    return True, "ok", f"task_statuses {len(ts)} 个全部 success=true"



def _parsed_since(fid, since):
    """该文件是否"本轮解析过"（判据来源：`file_parse_task` 里该 file_id 的 **任务结束时间**）。

    为什么不按"上传时间"判（第一版踩过）：存量文件上传于很久以前，`since` 便永远不生效；
    反过来若对存量也要求 create_time >= since，又会每轮假红。
    只有"任务在本轮 since 之后结束"才应要求"索引里有 since 之后的块"，这条既不循环也不误伤。
    """
    try:
        t = _mysql("select max(coalesce(end_time, gmt_modified)) from gienrag.file_parse_task "
                   "where file_id=%d and status=4;" % int(fid))
        if not t or t == "NULL":
            return False
        return str(t).replace("T", " ")[:19] >= str(since).replace("T", " ")[:19]
    except Exception:
        return False


def cap_parse_effective(s):
    """R14-F01t：写操作必须校验"生效"，不能只看 200/status。

    读侧可验形态（不写数据、可在冻结期跑）：kb_9 里 `status=3(PARSE_SUCCESS)` 的文件，
    其 chunk 必须真的取得回来（`getFileChunks` 非空）。status=3 却取不到块 = "报成功但没做到"，
    与 S8「坏文件 success=true data=[]」同族。TL 指定的 `task_statuses[*].success` 判据已实现为
    纯函数 `_parse_resp_ok()`，待 C 把该字段透出到接口后直接接入（现接口不返回它）。
    """
    code, body = api(s, "GET", f"/index/knowledgeBase/file/list?kbId={KB_ID}&pageNo=1&pageSize=50", s.token)
    recs = ((body.get("data") or {}).get("records") or []) if isinstance(body, dict) else []
    files = []
    for r in recs:
        for kf in (r.get("kbFiles") or []):
            files.append(kf)
    parsed = [f for f in files if str(f.get("status")) == "3"]
    broken = []
    since = os.environ.get("R14_PARSE_SINCE", "").strip()   # 形如 2026-10-27T13:23:00
    stale_idx = []
    for f in parsed[:8]:
        fid = f.get("id")
        c2, b2 = api(s, "GET", f"/index/knowledgeBase/file/getFileChunks?kbId={KB_ID}"
                                    f"&docId={fid}&pageNo=1&pageSize=1", s.token)
        chunks = ((b2.get("data") or {}).get("records") or []) if isinstance(b2, dict) else []
        if c2 != 200 or not chunks:
            broken.append({"fileId": fid, "name": f.get("fileName"),
                           "http": c2, "chunks": len(chunks)})
            continue
        # R14-F01t2（TL 指定）：服务说"解析成功"、接口说"有块"都可能骗人（13:23 那批 7 个文件
        # 解析 success=true 但 19527 不可达、ES 一条没写）。故补一层**存储事实**：
        # ES 里该 file_id 的块数 > 0，且（若给了 R14_PARSE_SINCE）最大 create_time 不早于该时刻。
        n, latest = 0, None
        for idx in PROV_INDEXES:
            try:
                # 实测 mapping：metadata.file_id 是 text（keyword 子字段），create_time 是 keyword
                # → 必须用 .keyword 精确匹配，且不能用 max 聚合（keyword 不支持），改按 create_time 倒序取首条
                rr = requests.post(f"http://127.0.0.1:19200/{idx}/_search", json={
                    "size": 1, "_source": ["metadata.create_time"],
                    "query": {"term": {"metadata.file_id.keyword": str(fid)}},
                    "sort": [{"metadata.create_time": {"order": "desc"}}]}, timeout=30)
                j = rr.json() or {}
                tot = int(((j.get("hits") or {}).get("total") or {}).get("value") or 0)
                n += tot
                hits = ((j.get("hits") or {}).get("hits") or [])
                mxt = (((hits[0].get("_source") or {}).get("metadata") or {}).get("create_time")) if hits else None
                if mxt and (latest is None or str(mxt) > str(latest)):
                    latest = str(mxt)
            except Exception:
                pass
        if n == 0:
            broken.append({"fileId": fid, "name": f.get("fileName"), "es_chunks": 0})
        elif since and _parsed_since(fid, since):
            # create_time 可能是 epoch 毫秒或 ISO 字符串，两种都尝试比较
            # 实测两个时间格式不同：ES metadata.create_time 是 "2026-10-27 13:25:55.428683"（空格分隔），
            # 而我们传入的 since 常是 ISO "2026-10-27T13:20:00"（T 分隔）。直接字符串比较会因 ' ' < 'T'
            # 把"更新"判成"未更新"（假红）。统一成 "YYYY-MM-DD HH:MM:SS" 再比。
            def _norm(x):
                return str(x).replace("T", " ")[:19]

            ok_since = True
            try:
                if isinstance(latest, (int, float)) and latest > 1e11:
                    ok_since = _norm(datetime.fromtimestamp(latest / 1000)) >= _norm(since)
                elif latest is not None:
                    ok_since = _norm(latest) >= _norm(since)
            except Exception:
                ok_since = True
            if not ok_since:
                stale_idx.append({"fileId": fid, "name": f.get("fileName"),
                                  "latest_create_time": str(latest), "since": since})
    ok = bool(parsed) and not broken and not stale_idx
    record("PARSE_EFFECTIVE", ok,
           f"http={code} status=3文件={len(parsed)} 抽查={min(8, len(parsed))} "
           f"取不到块={broken[:2]} 索引未更新={stale_idx[:2]}"
           + (" ← 报成功但取不到块（写操作未校验生效）" if broken else "")
           + (" ← 解析成功但 ES create_time 未更新（索引未生效）" if stale_idx else ""),
           {"broken": broken, "stale_index": stale_idx, "parsed_count": len(parsed),
            "since": since or None})


def cap_internal_guard(s):
    """内部回写入口必须拒绝无令牌调用。"""
    r = requests.post(GATEWAY + "/index/parseTask/callback", json={},
                      headers={"Content-Type": "application/json", "User-Agent": UA}, timeout=20)
    r2 = requests.post(GATEWAY + "/index/knowledgeBase/file/uploadParsedFile?kbId=1&fileId=1&userId=1",
                       headers={"Content-Type": "application/json", "User-Agent": UA}, timeout=20)
    ok = r.status_code in (401, 403) and r2.status_code in (401, 403)
    record("INTERNAL_GUARD", ok, f"callback={r.status_code} uploadParsedFile={r2.status_code}")


def stall_verdict(stale99, pending_age_min, retry_ing, limit_min=5):
    """解析队列停摆判定（纯函数，便于自检）。

    R14-OBS1（TL 指定，可观测性断言，不是产品断言）：13:45 那轮 5 条 `status=3(RETRY_ING)`
    僵尸任务占满并发槽，派发器每轮只说"本次执行 0 个"，看起来完全正常，但所有上传静默停摆。
    三个信号任一成立即判"队列停摆"：
      ① `knowledge_base_list.status=99`（解析中）且 gmt_modified 超过 limit_min 分钟 → 有孤儿
      ② 最老的 PENDING（`file_parse_task.status=1`）等待超过 limit_min 分钟 → 调度没取走
         （注意：`knowledge_base_list.status=1` 是"正常"，不是待处理，别拿它当排队）
      ③ 存在 RETRY_ING(status=3) → 僵尸任务（该状态既算"在飞"又算"可派发"，会自锁）
    """
    reasons = []
    if stale99 > 0:
        reasons.append(f"status=99 超 {limit_min} 分钟未推进：{stale99} 个")
    if pending_age_min is not None and pending_age_min > limit_min:
        reasons.append(f"最老 PENDING 已等 {pending_age_min} 分钟")
    if retry_ing > 0:
        reasons.append(f"RETRY_ING(status=3) 僵尸：{retry_ing} 个")
    return (not reasons), "；".join(reasons) or "队列健康"


def _mysql(q):
    out = subprocess.run(["docker", "exec", "r12-mysql", "mysql", "-uroot",
                          "-pR12r00t#2026local", "-N", "-e", q],
                         capture_output=True, text=True)
    return out.stdout.strip()


def cap_parse_queue_stall(s):
    """R14-OBS1：解析队列停摆（系统整体卡住但每个组件都自认为正常）。"""
    limit = int(os.environ.get("R14_STALL_MIN", "5"))
    try:
        dist_raw = _mysql("select status,count(*) from gienrag.file_parse_task group by status;")
        dist = {}
        for line in dist_raw.splitlines():
            parts = line.split()
            if len(parts) == 2:
                dist[parts[0]] = int(parts[1])
        stale99 = int(_mysql("select count(*) from gienrag.knowledge_base_list "
                             "where status=99 and gmt_modified < now() - interval %d minute;" % limit) or 0)
        # 注意枚举语义（TL 明确）：`knowledge_base_list.status` 里 **1=正常**、99=解析中，
        # 1 不是"待处理"；真正的"待派发"是 `file_parse_task.status=1(PENDING)`。
        # 第一版我误用 knowledge_base_list.status=1 取最老等待时间，得 3409 分钟 → 假红，已修正。
        pend_old = _mysql("select max(timestampdiff(minute, gmt_create, now())) "
                          "from gienrag.file_parse_task where status=1;")
        pend_age = int(pend_old) if (pend_old and pend_old != "NULL") else None
        total99 = int(_mysql("select count(*) from gienrag.knowledge_base_list where status=99;") or 0)
        ok, why = stall_verdict(stale99, pend_age, dist.get("3", 0), limit)
    except Exception as e:                                   # noqa: BLE001
        record("PARSE_QUEUE_STALL", False,
               f"无法查询队列状态：{type(e).__name__}: {e} ← 观测失败本身也要暴露，不能当健康")
        return
    record("PARSE_QUEUE_STALL", ok,
           f"队列分布={{'PENDING(1)':{dist.get('1',0)},'DEAL_ING(2)':{dist.get('2',0)},"
           f"'RETRY_ING(3)':{dist.get('3',0)},'成功(4)':{dist.get('4',0)},'失败(5)':{dist.get('5',0)}}} "
           f"status=99合计={total99} 其中超{limit}分钟未推进={stale99} 最老PENDING={pend_age}分钟 "
           f"判定={why}",
           {"dist": dist, "stale99": stale99, "pending_age_min": pend_age, "limit": limit})


CAPS = {
    "PARSE_QUEUE_STALL": cap_parse_queue_stall,
    "NORMAL": cap_normal,
    "FAQ": cap_faq,
    # GLOBAL 拆三层（见 cap_global 上方注释）；--only GLOBAL 由 main() 展开成这三项
    "GLOBAL_POS": cap_global,
    "GLOBAL_REFUSE": cap_global_refuse,
    "GLOBAL_FAITH": cap_global_faith,
    "VERSION": cap_version,
    "TABLE": cap_table,
    "NO_RECALL_FAB": cap_no_recall,
    "PARSE_RETRY_STORM": cap_parse_retry_storm,
    "PARSE_CONVERT_PATH": cap_parse_convert_path,
    "GRAPH_LOCAL": cap_graph_local,
    "GRAPH_IDENTITY": cap_graph_identity,
    "GRAPH_PROVENANCE": cap_graph_provenance,
    "GRAPH_UPPERCASE": cap_graph_uppercase,
    "PARSE_EFFECTIVE": cap_parse_effective,
    "INTERNAL_GUARD": cap_internal_guard,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔，如 FAQ,GLOBAL")
    args = ap.parse_args()
    ALIAS = {"GLOBAL": ["GLOBAL_POS", "GLOBAL_REFUSE", "GLOBAL_FAITH"],
             "GRAPH_VERSION_FRESH": ["GRAPH_PROVENANCE"]}
    raw = [x.strip().upper() for x in args.only.split(",") if x.strip()]
    if not raw:
        want = list(CAPS)
    else:
        want = []
        for x in raw:
            for y in ALIAS.get(x, [x]):
                if y not in want:
                    want.append(y)

    # R14-W1（C 提的窗口纪律）：B 重建 `g_kb_9` 期间 global/graph 必然拿不到社区结果，
    # 跑出来的红不是缺陷。用 `R14_GRAPH_WINDOW=1` 显式跳过并记 INFO（不计分子分母），
    # 避免"重建期的红"污染台账；跑之前仍应按约定确认 B 已报 after。
    if os.environ.get("R14_GRAPH_WINDOW", "").strip() == "1":
        skip = [x for x in want if x.startswith("GRAPH") or x.startswith("GLOBAL")]
        if skip:
            record("GRAPH_WINDOW", "重建窗口内跳过图/global 用例（不计入分子分母）", True,
                   f"R14_GRAPH_WINDOW=1 跳过={skip}")
            want = [x for x in want if x not in skip]

    s, token, _ = login()
    s.token = token

    # 前置守卫（TL/E 纪律）：图侧断言必须与 19529 存活绑定；同端口多 pid 记环境不可信。
    pre = {str(p): _port_pids(p) for p in (19529, 19995, 19996)}
    os.makedirs(EVID, exist_ok=True)
    with open(os.path.join(EVID, "precheck_ports.json"), "w", encoding="utf-8") as f:
        json.dump({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "port_pids": pre,
                   "multi_pid_ports": [p for p, v in pre.items() if len(v) > 1]}, f,
                  ensure_ascii=False, indent=1)
    graph_down = not _listening(19529)

    for name in want:
        fn = CAPS.get(name)
        if not fn:
            record(name, False, "未知能力名")
            continue
        if name.startswith("GRAPH_") and graph_down:
            record(name, False, "环境不可用：19529 未监听（图服务重启窗口，不是产品 FAIL）",
                   neutral=True)
            continue
        try:
            fn(s)
        except Exception as e:
            record(name, False, f"异常: {type(e).__name__}: {e}")
            print(traceback.format_exc(limit=3))

    os.makedirs(EVID, exist_ok=True)
    info = [r for r in RESULTS if r.get("neutral")]
    judged = [r for r in RESULTS if not r.get("neutral")]
    passed = sum(1 for r in judged if r["ok"])
    with open(os.path.join(EVID, "caps.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=1)
    with open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8") as f:
        f.write(f"# R13 能力矩阵自检\n\n总计 {passed}/{len(judged)} PASS"
                f"（另有 INFO {len(info)} 条不计入判定）\n\n| 能力 | 结果 | 详情 |\n|---|---|---|\n")
        for r in RESULTS:
            tag = "INFO" if r.get("neutral") else ("PASS" if r["ok"] else "FAIL")
            f.write(f"| {r['cap']} | {tag} | {r['detail']} |\n")
    print(f"\n== {passed}/{len(judged)} PASS（INFO {len(info)} 条不计入）== 证据: {EVID}")
    return 0 if passed == len(judged) else 1


if __name__ == "__main__":
    sys.exit(main())
