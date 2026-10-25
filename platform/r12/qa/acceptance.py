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
RESULTS = []


def record(scene, case, ok, detail, extra=None):
    row = {"scene": scene, "case": case, "ok": bool(ok), "detail": detail}
    if extra is not None:
        row["extra"] = extra
    RESULTS.append(row)
    print(("PASS " if ok else "FAIL ") + f"[{scene}] {case}: {detail}")
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
def s2(s, kb_name="R12验收主链"):
    code, body = api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=50", s.token)
    for r in ((body.get("data") or {}).get("records") or []) if isinstance(body, dict) else []:
        if r.get("kbName") == kb_name:
            record("S2", "知识库已存在（复用）", True, f"kbId={r['id']} primitive={r.get('primitiveName')}")
            return r
    payload = {"kbName": kb_name, "kbDes": "R12 真实主链验收", "fileType": "naive",
               "chunkSize": 512, "chunkOverlap": 50, "embeddingModelName": "bge-m3",
               "privateKb": 0, "platform": "rag-qa"}
    code, body = api(s, "POST", "/index/knowledgeBase/create", s.token, json=payload)
    data = (body.get("data") or {}) if isinstance(body, dict) else {}
    kb_id = data.get("id")
    ok = code == 200 and kb_id
    record("S2", "创建知识库", ok, f"http={code} kbId={kb_id} primitive={data.get('primitiveName')}",
           {"resp": body})
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


def s3(s, kb_id):
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
            record("S3", f"上传 {label}", False, f"样本缺失 {path}")
            continue
        code, body = upload(s, kb_id, path)
        data = body.get("data") if isinstance(body, dict) else None
        file_id = None
        if isinstance(data, list) and data:
            file_id = data[0].get("id")
        elif isinstance(data, dict):
            file_id = data.get("id")
        ok = code == 200 and isinstance(body, dict) and body.get("success")
        record("S3", f"上传 {label}", ok, f"http={code} fileId={file_id} name={fname}",
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
        record("S3", "加密 PDF 已入库待解析", code == 200 and fid, f"http={code} fileId={fid}")
        if fid:
            uploaded.append({"fileId": fid, "name": "pdf-encrypted.pdf",
                             "label": "加密 PDF(应解析失败)", "expect": "fail"})
    return uploaded


# ---------------------------------------------------------------- S4 状态
def s4(s, uploaded, timeout_s=600):
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
        if expect == "fail":
            ok = last == 4       # 4 = 解析失败
            record("S4", f"负例按预期失败 {f['label']}", ok,
                   f"fileId={fid} 最终状态={last}(4=失败) 耗时={int(time.time()-t0)}s")
        else:
            ok = last == 3       # 3 = 解析成功
            record("S4", f"解析完成 {f['label']}", ok,
                   f"fileId={fid} 最终状态={last} 耗时={int(time.time()-t0)}s")
            if ok:
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


def s5(s, kb_name, question, session="r12-sess-1"):
    qid = f"q-{int(time.time()*1000)}"
    code, answer, frames = ask(s, kb_name, qid, question)
    ok = code == 200 and len(answer.strip()) > 10
    ref = []
    for fr in frames:
        r = fr.get("reference")
        if r:
            try:
                ref = json.loads(r) if isinstance(r, str) else r
            except Exception:
                pass
    record("S5", f"真实模型回答（{len(question)}字问题）", ok,
           f"http={code} 帧数={len(frames)} 答案长度={len(answer)}",
           {"answer_head": answer[:200], "frames_head": frames[:2]})
    record("S5", "回答带引用", bool(ref), f"引用条数={len(ref) if isinstance(ref, list) else 'n/a'}",
           {"reference_head": (ref[:2] if isinstance(ref, list) else ref)})
    dump("s5_answer.json", {"question": question, "answer": answer, "frames": frames[:6],
                            "reference": ref if isinstance(ref, list) else []})
    return answer, ref, qid


# ---------------------------------------------------------------- S6 原文
EXPECT_FACTS = ["5000", "1000", "三年", "3年", "授信额度"]


def s6(s, kb_id, file_id, ref, answer=""):
    code, body = api(s, "GET", f"/index/knowledgeBase/file/getFileChunks?kbId={kb_id}&docId={file_id}&pageNo=1&pageSize=5", s.token)
    chunks = (body.get("data") or {}).get("records") if isinstance(body, dict) else None
    ok = code == 200 and bool(chunks)
    head = (chunks[0].get("pageContent") or chunks[0].get("page_content") or "") if chunks else ""
    record("S6", "服务端可独立取回原文（不随请求传正文）", ok,
           f"http={code} chunk数={len(chunks or [])} 首块长度={len(head)}", {"chunk_head": head[:200]})
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
def s7(s, session="r12-sess-1"):
    code, body = api(s, "GET", f"/qa/dialogue/getDialogBySessionId?sessionId={session}", s.token)
    ok = code == 200 and isinstance(body, dict) and body.get("success")
    record("S7", "历史对话可恢复", ok, f"http={code} resp={str(body)[:160]}")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    only = set(x.strip().upper() for x in args.only.split(",") if x.strip())

    def want(name):
        return (not only) or (name in only)

    s, token, _ = login()
    s.token = token
    print(f"== R12 验收 {TS} ==")
    try:
        if want("S1"):
            s1(s)
        kb = s2(s) if (want("S2") or want("S3") or want("S5") or want("S6")) else None
        kb_id = (kb or {}).get("id")
        kb_name = (kb or {}).get("primitiveName")
        if want("S5") and kb_name and not want("S3"):
            q = "我们这种做汽车零部件的中型企业，最多能借多少钱、能借多久？"
            answer, ref, qid = s5(s, kb_name, q)
            if want("S6"):
                fid = None
                if isinstance(ref, list) and ref:
                    fid = (ref[0].get("metadata") or {}).get("file_id")
                if fid:
                    s6(s, kb_id, fid, ref, answer)
                else:
                    record("S6", "服务端取回原文", False, "引用中无 file_id，无法核对原文")
            if want("S7"):
                s7(s)
        if want("S3") and kb_id:
            up = s3(s, kb_id)
            dump("s3_uploaded.json", up)
            if want("S4"):
                ok_files = s4(s, up)
                if ok_files and (want("S5")):
                    q = "我们这种做汽车零部件的中型企业，最多能借多少钱、能借多久？"
                    answer, ref, qid = s5(s, kb_name, q)
                    if want("S6") and ref:
                        fid = (ref[0].get("metadata") or {}).get("file_id")
                        s6(s, kb_id, fid or ok_files[0]["fileId"], ref, answer)
                    if want("S7"):
                        s7(s)
        if want("S8") and kb_id:
            s8(s, kb_id)
    except Exception as e:
        record("ERR", "执行异常", False, f"{e}\n{traceback.format_exc()[:800]}")

    passed = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)
    os.makedirs(EVID, exist_ok=True)
    dump("results.json", RESULTS)
    lines = [f"# R12 验收 {TS}", "", f"总计 {passed}/{total} PASS", "",
             "| 场景 | 用例 | 结果 | 说明 |", "|---|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['scene']} | {r['case']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\n== {passed}/{total} PASS == 证据: {EVID}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
