#!/usr/bin/env python3
"""R12 端到端验收驱动（真实网关 / 真实模型 / 真实索引，不用 Mock）。

覆盖场景（对应 R12 指令"七、本轮强制验收"）：
  S1 登录与菜单
  S2 建库
  S3 上传（PDF/DOCX/XLSX/PPTX/扫描图片 + 复杂/失败样本）
  S4 处理状态查询
  S5 换措辞提问 -> 真实模型流式回答
  S6 引用 -> 服务端取回原文并核对（不随请求传正文）
  S7 历史对话恢复
  S8 负例（无 token / 伪造 token / 坏文件 / 越权）
产出：platform/r12/qa/evidence/<ts>/ 下每场景一个 json + summary.md
用法：python3 platform/r12/qa/acceptance.py [--only S1,S2] [--tag run1]
"""
import argparse
import json
import subprocess
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r12_client import GATEWAY, UA, api, login  # noqa: E402

import requests  # noqa: E402

R12 = "/home/szf/data/dev/llmke-r12/platform/r12"
SAMPLES = "/home/szf/data/dev/coordination/samples"
TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
EVID = os.path.join(R12, "qa", "evidence", TS)
KB_NAME = "R14-BASELINE-KB"      # R14：独立验收库（严禁复用 kb_9 / "R12验收主链"）
RESULTS = []


def record(scene, case, ok, detail, extra=None, state=None):
    """三态记账（TL 要求）：PASS / FAIL / TIMEOUT。

    TIMEOUT 专指"用例未在时限内到达可判状态"（可能产品卡住、也可能环境慢），
    与 FAIL（断言不成立）分开记——两者排查方向正好相反：
      记 FAIL   -> 报告会写"S4 失败"，读者去查解析能力；
      记 TIMEOUT-> 报告写"文件永远停在 98"，读者去查重试/调度。
    """
    st = state or ("PASS" if ok else "FAIL")
    row = {"scene": scene, "case": case, "ok": bool(ok), "state": st, "detail": detail}
    if extra is not None:
        row["extra"] = extra
    RESULTS.append(row)
    print(f"{st:<7} [{scene}] {case}: {detail}")
    return ok


def dump(name, obj):
    os.makedirs(EVID, exist_ok=True)
    with open(os.path.join(EVID, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- S1 登录/菜单
def s1(s):
    code, body = api(s, "GET", "/auth/resource/getMenusByUser", s.token)
    menus = (body.get("data") if isinstance(body, dict) else None) or []
    record("S1", "登录并取菜单", code == 200 and isinstance(body, dict) and body.get("success"),
           f"http={code} menus={len(menus)}", {"menus": menus[:5]})
    code, body = api(s, "GET", "/auth/user/getUserInfo", s.token)
    name = ((body.get("data") or {}) if isinstance(body, dict) else {}).get("userName")
    record("S1", "取当前用户信息", code == 200 and name == "admin", f"http={code} user={name}")


# ---------------------------------------------------------------- S2 建库
def s2(s, kb_name=None, scene="S2"):
    """R14-F01d：**不再复用固定库名**。
    原实现按名字复用 "R12验收主链"，而该库就是 kb_9 —— 每次 S2/S3 都会把 kb_9 整批 OVERWRITE，
    实测打掉了 C 建的 V0/V1 多版本夹具（V1 行被置 status=0、ES 按 source 先删后插）。
    现在：使用独立验收库 KB_NAME，且**每次运行先删后建**，保证基线独立、可重复、不碰别人的数据。
    """
    kb_name = kb_name or KB_NAME
    code, body = api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=50", s.token)
    olds = [r for r in (((body.get("data") or {}).get("records") or [])
                        if isinstance(body, dict) else [])
            if isinstance(r, dict) and r.get("kbName") == kb_name]
    for r in olds:
        c2, b2 = api(s, "DELETE", f"/index/knowledgeBase/delete?id={r['id']}", s.token)
        record(scene, "删除上一轮验收库（保证基线独立可重复）",
               c2 in (200, 404), f"kbId={r['id']} kbName={kb_name} http={c2}")
    payload = {"kbName": kb_name, "kbDes": "R14 严格断言基线验收库（独立于 kb_9）", "fileType": "naive",
               "chunkSize": 512, "chunkOverlap": 50, "embeddingModelName": "bge-m3",
               "privateKb": 0, "platform": "rag-qa"}
    code, body = api(s, "POST", "/index/knowledgeBase/create", s.token, json=payload)
    data = (body.get("data") or {}) if isinstance(body, dict) else {}
    kb_id = data.get("id")
    ok = code == 200 and bool(kb_id)
    record(scene, "创建独立验收库", ok,
           f"http={code} kbId={kb_id} kbName={kb_name} primitive={data.get('primitiveName')} "
           f"旧库清理={len(olds)}", {"resp": body})
    return data


# ---------------------------------------------------------------- S3 上传
def upload(s, kb_id, path, uid=None, is_parse=True):
    fname = os.path.basename(path)
    param = {
        "kbId": int(kb_id),
        "fileList": [{"fileName": fname, "type": "OVERWRITE", "uid": uid or f"r12-{int(time.time()*1000)}"}],
        "fileListType": 1, "isParse": is_parse, "isExtract": False, "isGraphParse": False,
        "chunking": True, "needChunk": True, "saveTxt": True, "platform": "rag-qa",
    }
    with open(path, "rb") as f:
        files = [("files", (fname, f, "application/octet-stream"))]
        r = requests.post(
            f"{GATEWAY}/index/knowledgeBase/file/uploadFileList",
            data={"uploadFileParam": json.dumps(param, ensure_ascii=False)},
            files=files,
            headers={"Authorization": s.token, "X-Platform": "rag-qa", "User-Agent": UA},
            timeout=300)
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]
    return r.status_code, body


def s3(s, kb_id, scene="S3"):
    FIX = os.path.join(R12, "qa", "fixtures")
    cases = [
        (os.path.join(FIX, "R12FIX-product-loan.docx"), "中文 DOCX 业务夹具"),
        (os.path.join(FIX, "R12FIX-credit-ledger.xlsx"), "中文 XLSX 业务夹具"),
        (os.path.join(FIX, "R12FIX-product-intro.pptx"), "中文 PPTX 业务夹具"),
        ("pdf-digital.pdf", "PDF 数字版"),
        ("docx-plain.docx", "DOCX 纯文本"),
        ("docx-table.docx", "DOCX 含表格"),
        ("pdf-scanned.pdf", "PDF 扫描件(OCR)"),
    ]
    uploaded = []
    for fname, label in cases:
        path = fname if os.path.isabs(fname) else os.path.join(SAMPLES, fname)
        fname = os.path.basename(path)
        if not os.path.exists(path):
            record(scene, f"上传 {label}", False, f"样本缺失 {path}")
            continue
        code, body = upload(s, kb_id, path)
        data = body.get("data") if isinstance(body, dict) else None
        file_id = None
        if isinstance(data, list) and data:
            file_id = data[0].get("id")
        elif isinstance(data, dict):
            file_id = data.get("id")
        ok = code == 200 and isinstance(body, dict) and body.get("success")
        record(scene, f"上传 {label}", ok, f"http={code} fileId={file_id} name={fname}",
               {"resp": body if not ok else {"fileId": file_id}})
        if ok and file_id:
            uploaded.append({"fileId": file_id, "name": fname, "label": label})
    # 失败样本：加密 PDF 必须被明确拒绝/标记失败，而不是假装成功
    enc = os.path.join(SAMPLES, "pdf-encrypted.pdf")
    if os.path.exists(enc):
        code, body = upload(s, kb_id, enc)   # 上传允许成功：拒绝应发生在解析阶段
        fid = None
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, list) and data:
            fid = data[0].get("id")
        elif isinstance(data, dict):
            fid = data.get("id")
        record(scene, "加密 PDF 已入库待解析", code == 200 and fid, f"http={code} fileId={fid}")
        if fid:
            uploaded.append({"fileId": fid, "name": "pdf-encrypted.pdf",
                             "label": "加密 PDF(应解析失败)", "expect": "fail"})
    return uploaded


# ---------------------------------------------------------------- S4 状态
SLOW = []          # R14-P2：耗时 >SLOW_S 但最终成功的用例（独立观察量，不判 FAIL）


def s4_verdict(final_status, elapsed, expect="ok", poll_timeout=1200, slow=600):
    """S4 判据（TL 定口径 C：判"能不能解析完"，耗时单列）。

    为什么不再用"600s 内必须完成"：
      同一脚本同一文件的历史耗时 27s / 21s / 567s / 900s（波动 30 倍），
      约束不在产品而在环境（模型服务/GC/IO/并发）。把它当 FAIL 等于用环境判产品死。
    判据：
      功能：轮询至最终状态（上限 poll_timeout=1200s），status=3 → PASS；status=4 → FAIL（正例）
      性能：elapsed > slow(600s) 但成功 → 记 SLOW（独立观察量，PASS 但必须在报告出数）
      失败：最终 status=4（正例）或 超过 poll_timeout 仍未终态 → FAIL
    """
    if expect == "fail":
        if final_status == 4:
            return True, "PASS", f"负例 最终状态=4(失败·正确终态) 耗时={int(elapsed)}s"
        # 负例也可能"等不到终态"（如 98 无限重试）——那是 TIMEOUT，不是 FAIL：
        # 记 FAIL 会让人去查"加密 PDF 为什么解析不出来"，记 TIMEOUT 才会去查"为什么永远不结束"。
        if elapsed >= poll_timeout:
            return False, "TIMEOUT", (f"负例 超时 {poll_timeout}s 仍未终态"
                                      f"（最后状态={final_status}，期望 4）")
        return False, "FAIL", f"负例 最终状态={final_status}(期望 4) 耗时={int(elapsed)}s"
    if final_status == 3:
        tag = "PASS_SLOW" if elapsed > slow else "PASS"
        return True, tag, f"最终状态=3 耗时={int(elapsed)}s" + (" ← SLOW(>600s)" if elapsed > slow else "")
    if final_status == 4:
        return False, "FAIL", f"最终状态=4(解析失败) 耗时={int(elapsed)}s"
    if elapsed >= poll_timeout:
        # 未达可判状态 ≠ 断言不成立：可能是产品卡住（如 98 无限重试），也可能是环境慢
        return False, "TIMEOUT", f"超时 {poll_timeout}s 仍未终态（最后状态={final_status}）"
    return False, "TIMEOUT", f"未终态 最终状态={final_status} 耗时={int(elapsed)}s"


def s4(s, uploaded, timeout_s=1200, scene="S4"):
    done = []
    for f in uploaded:
        fid = f["fileId"]
        t0 = time.time()
        last = None
        while time.time() - t0 < timeout_s:
            code, body = api(s, "GET", f"/index/knowledgeBase/file/getFileStatusById?fileId={fid}", s.token)
            st = body.get("data") if isinstance(body, dict) else None
            if st != last:
                print(f"    status {f['name']} -> {st}")
                last = st
            if st == 3 or (f.get("expect") == "fail" and st == 4):
                break
            time.sleep(3)
        expect = f.get("expect", "ok")
        elapsed = time.time() - t0
        ok, tag, why = s4_verdict(last, elapsed, expect, timeout_s)
        label = "负例按预期失败" if expect == "fail" else "解析完成"
        record(scene, f"{label} {f['label']}", ok, f"fileId={fid} {why}",
               state=tag)
        # SLOW 是"耗时观察量"，正例/负例都记（负例加密 PDF 实测 975s，同样是慢）
        if ok and elapsed > 600:
            SLOW.append({"fileId": fid, "label": f["label"], "elapsed": int(elapsed),
                         "expect": expect})
        if ok and expect != "fail":
            done.append(f)
    dump("s4_status.json", done)
    return done


# ---------------------------------------------------------------- S5 提问
def ask(s, session_id, query_id, content, config_id=None, extra=None):
    payload = {"sessionId": session_id, "queryId": query_id, "content": content,
               "type": "text", "sysType": "KNO_INDEX"}
    if config_id:
        payload["configId"] = config_id
    if extra:
        payload.update(extra)
    r = requests.post(f"{GATEWAY}/qa/ai/question_re", json=payload,
                      headers={"Authorization": s.token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=600)
    r.encoding = "utf-8"
    frames, text = [], []
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue          # 只认 SSE data 帧；其余（event:/注释/续行）忽略，避免把协议文本当答案
        line = raw[5:].strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        frames.append(obj)
        reply = obj.get("reply") or {}
        if isinstance(reply, dict) and reply.get("content"):
            text.append(reply["content"])
    return r.status_code, "".join(text), frames


def s5(s, kb_name, question, session="r12-sess-1", scene="S5", config_id=None):
    qid = f"q-{int(time.time()*1000)}"
    code, answer, frames = ask(s, kb_name, qid, question, config_id=config_id)
    ok = code == 200 and len(answer.strip()) > 10
    ref = []
    for fr in frames:
        r = fr.get("reference")
        if r:
            try:
                ref = json.loads(r) if isinstance(r, str) else r
            except Exception:
                pass
    record(scene, f"真实模型回答（{len(question)}字问题）", ok,
           f"http={code} 帧数={len(frames)} 答案长度={len(answer)}",
           {"answer_head": answer[:200], "frames_head": frames[:2]})
    record(scene, "回答带引用", bool(ref), f"引用条数={len(ref) if isinstance(ref, list) else 'n/a'}",
           {"reference_head": (ref[:2] if isinstance(ref, list) else ref)})
    dump("s5_answer.json", {"question": question, "answer": answer, "frames": frames[:6],
                            "reference": ref if isinstance(ref, list) else []})
    return answer, ref, qid


# ---------------------------------------------------------------- S6 原文
EXPECT_FACTS = ["5000", "1000", "三年", "3年", "授信额度"]


def s6(s, kb_id, file_id, ref, answer=""):
    code, body = api(s, "GET", f"/index/knowledgeBase/file/getFileChunks?kbId={kb_id}&docId={file_id}&pageNo=1&pageSize=5", s.token)
    chunks = (body.get("data") or {}).get("records") if isinstance(body, dict) else None
    # R14-F01：原实现取 pageContent/page_content，而服务实际返回 content 字段，
    # 导致"首块长度=0"却判通过。现在按真实字段取值，并要求正文非空。
    def _body_of(rec):
        return rec.get("content") or rec.get("pageContent") or rec.get("page_content") or ""
    head = _body_of(chunks[0]) if chunks else ""
    ok = code == 200 and bool(chunks) and len(head.strip()) > 0
    record("S6", "服务端可独立取回原文（不随请求传正文）", ok,
           f"http={code} chunk数={len(chunks or [])} 首块长度={len(head)}" +
           ("" if ok else " ← 空原文不算通过"),
           {"chunk_head": head[:200], "raw_keys": list(chunks[0].keys())[:8] if chunks else []})
    # 引用里的 source 指向文件对象，核对可读
    srcs = []
    for r in (ref or []):
        md = r.get("metadata") or {}
        if isinstance(md, dict) and md.get("source"):
            srcs.append(md["source"])
    record("S6", "引用携带文件与定位信息", bool(srcs),
           f"引用 source 数={len(srcs)} 示例={srcs[:2]}")
    # 答案要点必须能在被引用的原文块里找到支撑（不用整句字符匹配）
    all_chunks = []
    for r in (ref or []):
        md = r.get("metadata") or {}
        fid = md.get("file_id")
        if not fid:
            continue
        c2, b2 = api(s, "GET",
                     f"/index/knowledgeBase/file/getFileChunks?kbId={kb_id}&docId={fid}&pageNo=1&pageSize=50", s.token)
        for rec in ((b2.get("data") or {}).get("records") or []) if isinstance(b2, dict) else []:
            all_chunks.append(rec.get("content") or "")
    corpus = "\n".join(all_chunks)
    hit_ans = [f for f in EXPECT_FACTS if f in (answer or "")]
    hit_src = [f for f in hit_ans if f in corpus]
    record("S6", "答案要点可在引用原文中找到支撑",
           bool(hit_ans) and len(hit_src) >= max(1, len(hit_ans) // 2),
           f"答案命中要点={hit_ans} 其中被原文支撑={hit_src} 引用块数={len(all_chunks)}",
           {"corpus_head": corpus[:300]})
    dump("s6_chunks.json", {"chunks": chunks, "sources": srcs})


# ---------------------------------------------------------------- S7 历史
def s7(s, session=None, qid=None):
    # R14-F01b：默认值彻底去掉。原默认 "r12-sess-1" 是一个**从未创建的会话**，
    # 任何"忘了传 session"的调用都会稳定拿到 data=None；配上旧断言就变成恒真/恒假的陷阱。
    if not session:
        record("S7", "历史对话可恢复", False,
               "未指定会话 id：禁止用默认值（旧默认 r12-sess-1 不存在，会掩盖真实问题）")
        return
    code, body = api(s, "GET", f"/qa/dialogue/getDialogBySessionId?sessionId={session}", s.token)
    # R14-F01：原断言只看 success=true，`data: None` 也通过（实测如此）。
    # R14-F01b（本轮修正，实测依据见 evidence/R14-BASELINE-*/summary.md）：
    #   ① 会话 id 错配：S5 提问用的 sessionId 是知识库 primitiveName(kb_9)，本函数却查固定串
    #      r12-sess-1 —— 该会话从未创建，getDialogBySessionId 必然返回 data=None。属**夹具缺陷**。
    #   ② 返回结构取错：服务真实返回 data={label,sessionId,gmtModified,queryReplyPairList:[{query,reply}]}，
    #      原实现只遍历 list 形态并读 content/question/answer 字段，对 dict 恒不命中 → **恒假**。
    # R14-F01c（再收紧）：仅"历史里问答对数>0"仍会被旧记录蒙过（kb_9 会话已积累 30+ 组）。
    #      传入本轮 S5 的 queryId 后，必须命中**本轮**这一问且该问有非空回答，才证明本次写入落库。
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, list):
        pairs = data
    elif isinstance(data, dict):
        pairs = data.get("queryReplyPairList") or []
    else:
        pairs = []

    def _content(node, alt):
        if isinstance(node, dict):
            return (node.get("content") or node.get(alt) or "").strip()
        return ""

    has_text = False
    hit_this_round = False
    for p in pairs:
        if not isinstance(p, dict):
            continue
        qn, rn = p.get("query"), p.get("reply")
        q, a = _content(qn, "question"), _content(rn, "answer")
        if q and a:
            has_text = True
        got_qid = (qn or {}).get("queryId") if isinstance(qn, dict) else None
        if qid and got_qid == qid and a:
            hit_this_round = True
        if has_text and (hit_this_round or not qid):
            break
    ok = (code == 200 and len(pairs) > 0 and has_text
          and (not qid or hit_this_round))
    record("S7", "历史对话可恢复", ok,
           f"http={code} session={session} 问答对数={len(pairs)} 问与答均有正文={has_text} "
           f"本轮queryId={qid} 命中={hit_this_round}"
           + ("" if ok else " ← 空历史/缺答案/未命中本轮提问 不算通过"))
    code, body = api(s, "GET", "/qa/dialogue/list?pageNo=1&pageSize=10", s.token)
    record("S7", "会话列表可查", code == 200, f"http={code}")
    dump("s7_history.json", body)


# ---------------------------------------------------------------- S8 负例
def s8(s, kb_id):
    # 无 token
    r = requests.get(f"{GATEWAY}/index/knowledgeBase/list?pageNo=1&pageSize=5", timeout=20)
    record("S8", "无 token 被拒绝", r.status_code in (401, 403), f"http={r.status_code}")
    # 伪造 token
    for fake in ["Bearer forged.token.value", "eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9."]:
        r = requests.get(f"{GATEWAY}/index/knowledgeBase/list?pageNo=1&pageSize=5",
                         headers={"Authorization": fake}, timeout=20)
        record("S8", f"伪造 token 被拒绝({fake[:12]}…)", r.status_code in (401, 403), f"http={r.status_code}")
    # 坏文件（非文档内容）
    bad = "/tmp/r12-bad.bin"
    open(bad, "wb").write(b"\x00\x01\x02NOTADOC" * 100)
    code, body = upload(s, kb_id, bad)
    fid = None
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, list) and data:
        fid = data[0].get("id")
    elif isinstance(data, dict):
        fid = data.get("id")
    if not (code == 200 and fid):
        record("S8", "坏文件被网关/服务直接拒绝", True, f"http={code} resp={str(body)[:120]}")
    else:
        # 上传收下了，则必须由解析阶段明确失败；否则记 BLOCKED（不制造假绿）
        t0, last = time.time(), None
        while time.time() - t0 < 120:
            c2, b2 = api(s, "GET", f"/index/knowledgeBase/file/getFileStatusById?fileId={fid}", s.token)
            last = b2.get("data") if isinstance(b2, dict) else None
            if last in (3, 4):
                break
            time.sleep(3)
        record("S8", "坏文件解析阶段明确失败", last == 4,
               f"fileId={fid} 最终状态={last}（4=解析失败；3=竟然成功；99/2=未处理）")
    # 越权：删除不存在的知识库
    # R13 语义升级（R13-FIX-API-02）：不存在现在明确返回 404 + success=false，且无任何副作用。
    # 断言从"success 为 true 但 data 为 false"（R12-FIX-API-01 记录的历史缺陷）改为"被明确拒绝 + 无副作用"，
    # 这是把缺陷修好后的正确断言，不是放宽标准。
    code, body = api(s, "DELETE", "/index/knowledgeBase/delete?id=999999", s.token)
    no_side_effect = not (isinstance(body, dict) and body.get("data") is True)
    explicit_reject = code == 404 or (isinstance(body, dict) and body.get("success") is False)
    record("S8", "删除不存在的知识库被明确拒绝且无副作用", no_side_effect and explicit_reject,
           f"http={code} errorCode={body.get('errorCode') if isinstance(body,dict) else '?'} "
           f"data={body.get('data') if isinstance(body,dict) else '?'}")


# ---------------------------------------------------------------- 独立库助手配置
MYSQL_CLI = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]
CFG_NAME = "R14-BASELINE-CFG"


def _sql(q):
    out = subprocess.run(MYSQL_CLI + [q], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"mysql 失败: {out.stderr.strip()[:200]}")
    return out.stdout.strip()


def ensure_kb_config(kb_name):
    """让 admin 拥有一条 knowledge_base_name 指向**本轮独立验收库**的助手配置。

    为什么必须：`question_re` 里 sessionId 被当作知识库 primitiveName 用（查该库下的文件），
    而检索/对象级授权用的是 `config.knowledge_base_name`。两者不一致时（默认助手仍指向 kb_9），
    实测直接 403（没有足够权限）——这不是产品缺陷，是我方夹具没配齐。
    配置行固定名 R14-BASELINE-CFG、is_default=0，每轮 update 指向当轮库，不新增行、不影响系统默认。
    """
    raw = _sql("select config_json from gienrag.search_config where id=1")
    cfg = json.loads(raw)
    cfg["knowledge_base_name"] = kb_name
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("\\", "\\\\").replace("'", "\\'")
    hit = _sql("select id from gienrag.search_config where create_by='admin' and name='%s' "
               "and is_del=1 order by id limit 1" % CFG_NAME)
    if hit:
        cid = int(hit.split()[0])
        _sql("update gienrag.search_config set config_json='%s', gmt_modified=now() where id=%d"
             % (cfg_json, cid))
        return cid
    _sql("insert into gienrag.search_config(status,is_default,config_json,name,des,create_by,"
         "gmt_create,gmt_modified,enabled_faq,depend_on_kb,is_del) values"
         "(1,0,'%s','%s','R14 基线夹具：admin 自有助手，指向本轮独立验收库','admin',"
         "now(),now(),1,0,1)" % (cfg_json, CFG_NAME))
    return int(_sql("select id from gienrag.search_config where create_by='admin' and name='%s' "
                    "and is_del=1 order by id desc limit 1" % CFG_NAME).split()[0])


SCENES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
QUESTION = "我们这种做汽车零部件的中型企业，最多能借多少钱、能借多久？"


def plan(only):
    """R14-F01d：`--only` 选中的场景必须**真的执行**。
    返回 (按固定顺序的待执行场景, 未知场景)。空 --only = 全量。
    旧实现的缺陷：`want()` 只用于分支选择，S6/S7 的调用嵌在 S3→S4→S5 分支里，
    `--only S6,S7` 时一个分支都不进 → 0 用例、exit 0（"空用例也算过"）。
    """
    want = {x.strip().upper() for x in (only or "").split(",") if x.strip()}
    if not want:
        return list(SCENES), []
    unknown = sorted(want - set(SCENES))
    return [x for x in SCENES if x in want], unknown


def check_coverage(want, executed, unknown=None):
    """选中但未执行 = 失败；--only 里有不存在的场景 = 失败。返回 (ok, detail)。"""
    missing = [x for x in want if x not in executed]
    unknown = list(unknown or [])
    ok = (not missing) and (not unknown)
    return ok, (f"选中={want} 实际执行={sorted(executed)} 未执行={missing} "
                f"未知场景={unknown}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    want, unknown = plan(args.only)

    s, token, _ = login()
    s.token = token
    print(f"== R12 验收 {TS}  plan={want}  未知场景={unknown} ==")
    executed = set()
    ctx = {}
    for u in unknown:
        record(u, "选中的场景不存在", False, f"--only 里的 {u!r} 不是有效场景；有效值={SCENES}")
    try:
        if "S1" in want:
            s1(s)
            executed.add("S1")

        # S2 及之后都需要知识库：一律用独立验收库（先删后建），不碰 kb_9
        if set(want) & {"S2", "S3", "S4", "S5", "S6", "S7", "S8"}:
            kb = s2(s, scene=("S2" if "S2" in want else "PREP"))
            if "S2" in want:
                executed.add("S2")
            ctx["kb_id"] = (kb or {}).get("id")
            ctx["kb_name"] = (kb or {}).get("primitiveName") or KB_NAME
            ctx["cfg"] = None
            if ctx["kb_name"]:
                try:
                    ctx["cfg"] = ensure_kb_config(ctx["kb_name"])
                    record("PREP", "独立库助手配置就绪", True,
                           f"kbName={ctx['kb_name']} configId={ctx['cfg']}（{CFG_NAME}）")
                except Exception as _e:                      # noqa: BLE001
                    record("PREP", "独立库助手配置就绪", False,
                           f"kbName={ctx['kb_name']} 失败: {type(_e).__name__}: {_e}")

        # S3 上传：凡"要提问"或"要对账原文"的场景都依赖库里有解析完成的文档，
        # 否则 S5 的"回答带引用"会在空库上 FAIL —— 那是自造的红，不是产品缺陷。
        need_upload = bool(set(want) & {"S3", "S4", "S5", "S6", "S7"})
        if need_upload and ctx.get("kb_id"):
            up = s3(s, ctx["kb_id"], scene=("S3" if "S3" in want else "PREP"))
            dump("s3_uploaded.json", up)
            if "S3" in want:
                executed.add("S3")
            ctx["uploaded"] = up
            need_parse = bool(set(want) & {"S4", "S5", "S6", "S7"})
            if need_parse:
                ok_files = s4(s, up, scene=("S4" if "S4" in want else "PREP"))
                if "S4" in want:
                    executed.add("S4")
                ctx["files"] = ok_files

        # S5 提问：S6/S7 依赖同一轮问答（S7 还要用本轮 queryId 命中）
        if set(want) & {"S5", "S6", "S7"}:
            answer, ref, qid = s5(s, ctx["kb_name"], QUESTION,
                                  scene=("S5" if "S5" in want else "PREP"),
                                  config_id=ctx.get("cfg"))
            if "S5" in want:
                executed.add("S5")
            ctx.update(answer=answer, ref=ref, qid=qid)

        if "S6" in want:
            fid = None
            if isinstance(ctx.get("ref"), list) and ctx["ref"]:
                fid = (ctx["ref"][0].get("metadata") or {}).get("file_id")
            if not fid and ctx.get("files"):
                fid = ctx["files"][0]["fileId"]
            if fid:
                s6(s, ctx["kb_id"], fid, ctx.get("ref") or [], ctx.get("answer") or "")
            else:
                record("S6", "服务端取回原文", False, "引用与解析结果都没有 file_id，无法核对原文")
            executed.add("S6")

        if "S7" in want:
            s7(s, ctx["kb_name"], ctx.get("qid"))
            executed.add("S7")

        if "S8" in want and ctx.get("kb_id"):
            s8(s, ctx["kb_id"])
            executed.add("S8")
    except Exception as e:
        record("ERR", "执行异常", False, f"{e}\n{traceback.format_exc()[:800]}")

    ok_cov, cov_detail = check_coverage(want, executed, unknown)
    record("COVERAGE", "选中的场景均已真实执行", ok_cov, cov_detail)

    passed = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)
    fails = [r for r in RESULTS if not r["ok"] and r.get("state") != "TIMEOUT"]
    timeouts = [r for r in RESULTS if r.get("state") == "TIMEOUT"]
    os.makedirs(EVID, exist_ok=True)
    dump("results.json", RESULTS)
    dump("s4_slow.json", SLOW)
    slow_txt = (f"SLOW(>600s 但成功) {len(SLOW)} 项: "
                + ", ".join(f"{x['label']}({x['elapsed']}s)" for x in SLOW)) if SLOW else "SLOW(>600s) 0 项"
    lines = [f"# R12 验收 {TS}", "", f"计划场景：{want}（未知：{unknown}）",
             f"总计 {passed}/{total} PASS ｜ FAIL {len(fails)} ｜ TIMEOUT {len(timeouts)}", slow_txt,
             "", "| 场景 | 用例 | 结果 | 说明 |", "|---|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['scene']} | {r['case']} | {r.get('state', 'PASS' if r['ok'] else 'FAIL')} | {r['detail']} |")
    open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\n== {passed}/{total} PASS == FAIL {len(fails)} / TIMEOUT {len(timeouts)} {slow_txt} "
          f"覆盖判定={'OK' if ok_cov else 'FAIL'} 证据: {EVID}")
    for r in timeouts:
        print(f"   TIMEOUT: {r['scene']} {r['case']} -> {r['detail']}")
    return 0 if (passed == total) else 1


if __name__ == "__main__":
    sys.exit(main())
