#!/usr/bin/env python3
"""R14-F05 权限域对照（对象级授权的"跨域"边界）。

要回答的问题不是"拒绝时返回了什么码"，而是：
  授权的知识库之外的内容，能不能通过**引用**或**答案**漏出来。
R13/R14 既有用例只覆盖"无授权账号被 403"，不覆盖：
  - 有 kb_9 只读授权的账号，问同一问题会不会顺带带出 kb_9 之外（kb_10 等）的片段；
  - 给该账号一个"配置只指向 kb_10"的助手，问 kb_9 专属事实，会不会照样答出来（无引用也算泄露）。

两个部分（全部真实网关 / 真实检索 / 真实模型，不 Mock）：
  A 同问对照：admin(configId=1, kb_9) 与 r13_reader(自有配置, kb_9) 问同一问题。
    判据：reader 的引用必须 100% 落在 kb_9；答案不得出现 kb_9 之外知识库才有的标记。
  B 跨域提问：为 r13_reader 建一条 config_json 只指向 kb_10 的自有配置，问 kb_9 专属事实。
    判据：必须 403，或（200 但引用为 0/kb_10 且答案不含 kb_9 专属事实）。
    "答得出但没有引用"= 泄露，判 FAIL。

夹具与边界（如实登记）：
  - r13_reader 及其模型使用权限、默认配置由 security_acceptance.py / revoke_acceptance.py 建立；
    本脚本只**新增一条**自有配置（is_default=0，create_by=r13_reader，指向 kb_10），
    结束时软删（is_del=-1）并留痕，不改动既有配置与授权行。
  - kb_9 专属事实取 docx-plain.docx 的"日均存款 2,983,333.33 元"（该文件仅在 kb_9，
    kb_10 的 7 个文件中不含 docx-plain.docx）——判据依赖"文件集合事实"，不依赖模型措辞。
  - 只做单发请求，不对拒绝态重试。

用法：python3 platform/r12/qa/permission_domain_scope.py
产出：platform/r12/qa/evidence/R14-F05-<UTC>/{summary.md,detail.json}
退出码：0=全部 PASS；1=有 FAIL
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r12_client import GATEWAY, UA, api, login  # noqa: E402

import requests  # noqa: E402

R12 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
EVID = os.path.join(R12, "qa", "evidence", f"R14-F05-{TS}")
MYSQL = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]

READER = "r13_reader"
READER_PWD = "R13@Test2026"
ADMIN_CONFIG = 1          # 系统默认助手：knowledge_base_name=kb_9
KB9, KB10 = "kb_9", "kb_10"
KB9_ONLY_FILE = "docx-plain.docx"

# kb_9 专属事实（来源 fileId=303 docx-plain.docx，仅在 kb_9 存在）
KB9_FACT = "2,983,333.33"
Q_SHARED = "客户访前准备的日均存款是多少？"

RESULTS = []
FIXTURE = []


def sql(q):
    out = subprocess.run(MYSQL + [q], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"mysql 失败: {out.stderr.strip()[:300]}")
    return out.stdout.strip()


def record(cid, ok, detail, extra=None):
    row = {"id": cid, "ok": bool(ok), "detail": detail}
    if extra is not None:
        row["extra"] = extra
    RESULTS.append(row)
    print(("PASS " if ok else "FAIL ") + f"[{cid}] {detail}")


def ask(s, content, config_id=None, timeout=300):
    """走网关 /qa/ai/question（与生产前端同一入口），返回 (http, status, answer, refs, resultType)。"""
    payload = {"sessionId": f"f05-{int(time.time()*1000)}", "queryId": f"f05q-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX"}
    if config_id:
        payload["configId"] = config_id
    r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                      headers={"Authorization": s.token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=timeout)
    answer, ref, rt, status, buf = "", [], None, None, b""
    try:
        for line in r.iter_lines():
            if line:
                buf += line + b"\n"
    except requests.exceptions.RequestException as e:
        return 0, None, "", [], None, f"transport_error: {type(e).__name__}: {e}"
    for part in buf.decode("utf-8", "replace").split("data:"):
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
    return r.status_code, status, answer, ref, rt, None


def _error_code(s, content, config_id=None):
    """裸 POST 取 errorCode：ask() 只解析 SSE 帧，拒绝态的 JSON 错误体拿不到。"""
    payload = {"sessionId": f"f05e-{int(time.time()*1000)}",
               "queryId": f"f05eq-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX"}
    if config_id:
        payload["configId"] = config_id
    try:
        r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                          headers={"Authorization": s.token,
                                   "Accept": "text/event-stream, application/json",
                                   "Content-Type": "application/json", "User-Agent": UA},
                          timeout=60)
        body = r.json()
        return body.get("errorCode") if isinstance(body, dict) else None
    except Exception:
        return None


def _error_body(s, content, config_id=None):
    """裸 POST 取完整拒绝体 (http, errorCode, message, contentType)。

    R14-F05t（TL/C 裁决后的契约）：`缺少默认助手配置` 必须是 **400 + errorCode=4014**，
    且**不得复用越权码 30016**；更不得退化成 500 空体（那样"已拒绝"无处可依）。
    """
    payload = {"sessionId": f"f05b-{int(time.time()*1000)}",
               "queryId": f"f05bq-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX"}
    if config_id is not None:
        payload["configId"] = config_id
    try:
        r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                          headers={"Authorization": s.token,
                                   "Accept": "text/event-stream, application/json",
                                   "Content-Type": "application/json", "User-Agent": UA},
                          timeout=60)
        raw = (b"".join(r.iter_lines())).decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = None
        code = body.get("errorCode") if isinstance(body, dict) else None
        msg = (body.get("message") or body.get("msg") or raw) if body else raw
        return r.status_code, code, str(msg or "")[:200], r.headers.get("Content-Type"), raw[:200]
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}", None, ""


def deny_verdict(http, code, msg):
    """把"缺少助手"的拒绝体判成 PASS/FAIL，返回 (ok, why)。

    通过条件（二者其一）：
      a) 400 + errorCode=4014 + 文案可读（C 定的新契约）
      b) 401/403（历史拒绝语义）且 errorCode 不是 30016
    任何 5xx 一律 FAIL；复用 30016 一律 FAIL。
    """
    if http is None:
        return False, "transport_error"
    if 500 <= http <= 599:
        return False, f"5xx 不是拒绝（http={http}）"
    if http == 400 and str(code) == "4014":
        return True, "400+4014（新契约）"
    if http in (401, 403) and str(code) != "30016":
        return True, f"{http}（历史拒绝语义）code={code}"
    if str(code) == "30016":
        return False, "复用了越权码 30016（缺参与越权不可混）"
    return False, f"不可判读的拒绝：http={http} code={code} msg={msg[:60]!r}"

    return [str((x.get("metadata") or {}).get("source") or "") for x in (refs or [])]


def sources(refs):
    return [str((x.get("metadata") or {}).get("source") or "") for x in (refs or [])]


def out_of_domain(src_list, allowed=KB9):
    """返回落在授权域之外的引用。source 为空视为"FAQ 直答命中/无文件来源"，
    不计入跨域（域外判定要求 source 里出现别的 kb 名），但会在明细里单独计数。"""
    bad = []
    for s in src_list:
        if not s:
            continue
        if "kb_" in s and allowed not in s:
            bad.append(s)
    return bad


def reader_config():
    """r13_reader 的自有助手配置 id（指向 kb_9）。

    R14-F01l：11:58 之后 search_config 有函数唯一索引 `uk_search_config_default`
    （全局只允许一行 is_default=1 and is_del=1），所以夹具**不能**再占用 is_default=1；
    显式传 configId 时只校验配置属主（create_by）或配置级权限，不需要默认位。
    找不到就按系统默认配置复制一条 is_default=0 的。
    """
    hit = sql("select id from gienrag.search_config where create_by='%s' and is_del=1 "
              "order by id limit 1" % READER)
    if hit:
        return int(hit.split()[0])
    sql("insert into gienrag.search_config(status,is_default,config_json,name,des,create_by,"
        "gmt_create,gmt_modified,enabled_faq,depend_on_kb,is_del) "
        "select 1,0,config_json,'R14-F05-READER-CFG-KB9','R14-F05 夹具：reader 指向 kb_9（is_default=0）',"
        "'%s',now(),now(),1,0,1 from gienrag.search_config where id=1" % READER)
    hit = sql("select id from gienrag.search_config where create_by='%s' and is_del=1 "
              "order by id desc limit 1" % READER)
    return int(hit.split()[0]) if hit else None


def classify_5xx(code):
    """5xx 不是拒绝：错误页渲染失败的 500 空 body 会让'已拒绝'变成假绿。"""
    return isinstance(code, int) and 500 <= code <= 599


def ensure_kb10_config():
    """为 r13_reader 建一条只指向 kb_10 的自有配置；返回 (configId, action)。"""
    hit = sql("select id from gienrag.search_config where create_by='%s' and name='R14-F05-KB10-ONLY' "
              "and is_del=1 order by id limit 1" % READER)
    if hit:
        return int(hit.split()[0]), "已存在（复用）"
    raw = sql("select config_json from gienrag.search_config where id=%d" % ADMIN_CONFIG)
    cfg = json.loads(raw)
    cfg["knowledge_base_name"] = KB10           # 唯一改动：把助手指向 kb_10
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("\\", "\\\\").replace("'", "\\'")
    sql("insert into gienrag.search_config(status,is_default,config_json,name,des,create_by,"
        "gmt_create,gmt_modified,enabled_faq,depend_on_kb,is_del) values"
        "(1,0,'%s','R14-F05-KB10-ONLY','R14-F05 夹具：reader 自有配置，仅指向 kb_10（用后软删）',"
        "'%s',now(),now(),1,0,1)" % (cfg_json, READER))
    new_id = int(sql("select id from gienrag.search_config where create_by='%s' "
                     "and name='R14-F05-KB10-ONLY' and is_del=1 order by id desc limit 1" % READER).split()[0])
    return new_id, "新建"


def main():
    os.makedirs(EVID, exist_ok=True)
    detail = {"ts_utc": TS, "fixture": FIXTURE, "rows": []}

    admin, admin_tok, _ = login()
    admin.token = admin_tok
    reader, reader_tok, _ = login(READER, READER_PWD)
    reader.token = reader_tok
    FIXTURE.append(f"{READER} 登录成功（口令来自 security_acceptance 夹具，非新建）")

    # ---------------- A 同问对照 ----------------
    ca, sa, ans_a, ref_a, rt_a, ea = ask(admin, Q_SHARED, ADMIN_CONFIG)
    src_a = sources(ref_a)
    record("F05-A0 前置：admin 在 kb_9 上可回答该问题",
           ca == 200 and sa == 2 and bool(ref_a),
           f"http={ca} status={sa} refs={len(ref_a or [])} err={ea}")
    out_a = out_of_domain(src_a)
    record("F05-A1 前置：admin 引用不含 kb_9 之外的来源（否则对照组无意义）",
           bool(src_a) and not out_a,
           f"refs={len(src_a)} 空source={sum(1 for x in src_a if not x)} 域外={out_a[:3]}")

    cfg_reader = reader_config()
    FIXTURE.append(f"{READER} 自有配置 configId={cfg_reader}（指向 kb_9，is_default=0；由 security/revoke 夹具建立或本脚本补齐）")
    cr, sr, ans_r, ref_r, rt_r, er = ask(reader, Q_SHARED, cfg_reader)
    src_r = sources(ref_r)
    in_kb9 = [x for x in src_r if KB9 in x]
    out_r = out_of_domain(src_r)
    record("F05-A2 r13_reader 在 kb_9 上可正常回答（授权域内可用，显式自有配置）",
           cr == 200 and sr == 2 and bool(ans_r.strip()),
           f"http={cr} status={sr} configId={cfg_reader} answer_len={len(ans_r)} refs={len(src_r)} err={er}")
    record("F05-A3 r13_reader 引用 100% 落在 kb_9（跨域引用=泄露）",
           cr == 200 and bool(in_kb9) and not out_r,
           f"refs={len(src_r)} 含kb_9={len(in_kb9)} 空source={sum(1 for x in src_r if not x)} 域外={out_r[:3]}")
    leaked_kb10 = [x for x in src_r if KB10 in x]
    record("F05-A4 r13_reader 答案与引用中不含 kb_10 痕迹",
           cr == 200 and not leaked_kb10 and KB10 not in ans_r,
           f"引用含 kb_10={leaked_kb10[:2]} 答案含'kb_10'={KB10 in ans_r}")

    # A5：不传 configId 的语义（team-lead 已裁：**允许回落系统默认助手**；无默认时 400+明确文案且 ≠30016）
    # 现状有系统默认（search_config id=1），所以本用例断言"回落成功"；无默认分支需删默认才能造，
    # 会破坏所有人的回落链，故记 UNVERIFIED（见 summary），不伪造成通过。
    c0, s0, ans0, ref0, rt0, e0 = ask(admin, Q_SHARED, None)
    fallback_ok = (c0 == 200 and s0 == 2 and bool(ans0.strip()))
    eh, ecode, emsg, etype, ebody = (None, None, "", None, "")
    deny_ok, deny_why = False, ""
    if not fallback_ok:
        eh, ecode, emsg, etype, ebody = _error_body(admin, Q_SHARED, None)
        deny_ok, deny_why = deny_verdict(eh, ecode, emsg)
    record("F05-A5 不传 configId：要么回落默认助手作答，要么给出**可判读的拒绝**（400+4014，不得 5xx/空体）",
           fallback_ok or deny_ok,
           f"http={c0} status={s0} answer_len={len(ans0)} err={e0} | 裸POST http={eh} errorCode={ecode!r} "
           f"判定={deny_why or ('回落成功' if fallback_ok else '')} body={ebody[:80]!r}"
           + ("  ← 5xx/空体：拒绝态不可判定" if isinstance(eh, int) and 500 <= eh <= 599 else ""))
    # A6：即使拒绝，"缺少助手"也不得复用越权码 30016（否则遥测分不清越权/少参数）
    record("F05-A6 拒绝态不得把『缺少助手』复用成越权码 30016，且必须带可读文案",
           fallback_ok or (deny_ok and str(ecode) != "30016" and "缺少默认助手" in emsg),
           f"http={eh} errorCode={ecode!r} 文案含'缺少默认助手'={'缺少默认助手' in emsg} msg={emsg[:60]!r}"
           + ("" if fallback_ok else "  ← 新契约：400 + errorCode=4014 + 可读文案"))

    # ---------------- B 跨域提问 ----------------
    cfg10, action = ensure_kb10_config()
    FIXTURE.append(f"助手配置 fixture configId={cfg10}（create_by={READER}, is_default=0, "
                   f"knowledge_base_name={KB10}）: {action}")
    cb, sb, ans_b, ref_b, rt_b, eb = ask(reader, f"《{KB9_ONLY_FILE}》里客户访前准备的日均存款是多少？", cfg10)
    src_b = sources(ref_b)
    denied = cb in (401, 403)
    # 200 也不算通过：必须证明没有取到 kb_9 内容（引用为空/不含 kb_9 且答案不含 kb_9 专属事实）
    kb9_ref_b = [x for x in src_b if KB9 in x]
    has_kb9_fact = KB9_FACT in ans_b
    record("F05-B1 配置只指向 kb_10 时，kb_9 专属提问被拒绝或明确无召回",
           denied or (cb == 200 and not kb9_ref_b and not has_kb9_fact),
           f"http={cb} status={sb} denied={denied} refs={len(src_b)} 引用含kb_9={kb9_ref_b[:2]} "
           f"答案含kb_9专属事实({KB9_FACT})={has_kb9_fact} answer_len={len(ans_b)} err={eb}"
           + ("  ← 5xx 不是拒绝" if classify_5xx(cb) else ""))
    record("F05-B2 不存在'答得出但无引用'的跨域泄露形态（答案含 kb_9 事实即判泄露）",
           not (cb == 200 and has_kb9_fact),
           f"http={cb} 答案长度={len(ans_b)} 引用数={len(src_b)} 答案含kb_9专属事实={has_kb9_fact}")

    # 清理：软删本脚本新建的配置（留痕，不物理删）
    sql("update gienrag.search_config set is_del=-1,name='R14-F05-KB10-ONLY-DELETED' where id=%d" % cfg10)
    FIXTURE.append(f"已软删 fixture configId={cfg10}（is_del=-1，改名留痕；未改任何既有配置/授权行）")

    detail["rows"] = RESULTS
    detail["samples"] = {
        "Q": Q_SHARED,
        "admin": {"http": ca, "status": sa, "answer": ans_a[-400:], "sources": src_a[:5]},
        "reader": {"http": cr, "status": sr, "answer": ans_r[-400:], "sources": src_r[:5]},
        "kb10_only_config": {"http": cb, "status": sb, "answer": ans_b[-400:], "sources": src_b[:5]},
    }
    with open(os.path.join(EVID, "detail.json"), "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=1)

    passed = sum(1 for r in RESULTS if r["ok"])
    with open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8") as f:
        f.write(f"# R14-F05 权限域对照 {TS}\n\n总计 {passed}/{len(RESULTS)} PASS\n\n")
        f.write(f"- 问题：{Q_SHARED}\n- kb_9 专属事实标记：{KB9_FACT}（来源 {KB9_ONLY_FILE}，仅存在于 kb_9）\n\n")
        f.write("| 用例 | 结果 | 说明 |\n|---|---|---|\n")
        for r in RESULTS:
            f.write(f"| {r['id']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |\n")
        f.write("\n## 夹具动作\n\n")
        for x in FIXTURE:
            f.write(f"- {x}\n")
        f.write("\n## 边界\n\n- 本脚本只验证\"授权域外内容不得经引用/答案泄露\"，不重复 SEC/REVOKE 的 403 全矩阵。\n"
                "- kb_10 内容与 kb_9 高度重叠（同名 product-loan/ledger 均存在），故 kb_9 专属标记"
                f"只取 `{KB9_ONLY_FILE}` 的日均存款数值，属文件集合事实，不依赖模型措辞。\n"
                "- 多版本（V0/V1）维度的跨域对照依赖 C 的多版本夹具，本脚本未覆盖。\n")
    print(f"\n== {passed}/{len(RESULTS)} PASS == 证据: {EVID}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
