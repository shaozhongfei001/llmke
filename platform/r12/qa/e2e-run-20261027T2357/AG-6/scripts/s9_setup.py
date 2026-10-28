#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 / S9 开工：建自建库（id 取自响应）→ 串行上传语料 → 解析 → FAQ 抽取 → 建确定性问答对。

每一步都落证据；不硬编码任何 id；只写自建库。
"""
import json
import os
import time

import ag6_lib as L

FILE_TERMINAL = (3, 4)   # 文件级：3=解析成功 4=解析失败（KbFileStatusEnums）
EXTRACT_OK, EXTRACT_FAIL = 3, 4


def wait_file(s, token, fid, timeout=600, tag=""):
    t0 = time.time()
    seen = []
    while time.time() - t0 < timeout:
        code, body, _ = L.file_status(s, token, fid)
        st = body.get("data") if isinstance(body, dict) else None
        if isinstance(st, dict):
            st = st.get("status")
        seen.append({"t": round(time.time() - t0, 1), "status": st})
        if st in FILE_TERMINAL:
            return {"final": st, "waited": round(time.time() - t0, 1), "samples": seen}
        time.sleep(2)
    return {"final": None, "waited": round(time.time() - t0, 1), "samples": seen}


def wait_extract(s, token, fid, timeout=900, tag=""):
    t0 = time.time()
    seen = []
    while time.time() - t0 < timeout:
        code, body, _ = L.faq_extract_status(s, token, fid)
        st = body.get("data") if isinstance(body, dict) else None
        if isinstance(st, dict):
            st = st.get("faqExtractStatus") or st.get("status")
        seen.append({"t": round(time.time() - t0, 1), "faqExtractStatus": st})
        if st in (EXTRACT_OK, EXTRACT_FAIL):
            return {"final": st, "waited": round(time.time() - t0, 1), "samples": seen}
        time.sleep(3)
    return {"final": None, "waited": round(time.time() - t0, 1), "samples": seen}


def main():
    hhmm = time.strftime("%H%M")
    kb_name = f"R14-E2E-AG6-{hhmm}"
    st = L.load_state()
    s, token = L.login()

    # ---- 1) 建库（id 从响应取）
    code, body, el = L.kb_create(s, token, kb_name)
    kb_id = None
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, (int, str)):
            kb_id = int(data)
        elif isinstance(data, dict):
            kb_id = data.get("id") or data.get("kbId")
    ev = {"time": L.now(), "kb_name": kb_name, "create_http": code, "create_body": body,
          "kb_id_from_response": kb_id, "elapsed": el}
    L.dump("S9-0-kb-create.json", ev, "S9")
    if not kb_id:
        raise SystemExit(f"建库失败或无法从响应取 id: {code} {body}")
    print(f"[kb] name={kb_name} id={kb_id}")

    # 确认 primitiveName（FAQ 索引 = faq_<primitiveName>）
    code, kb, _ = L.api(s, "GET", f"/index/knowledgeBase/getKbById?id={kb_id}", token)
    primitive = (kb.get("data") or {}).get("primitiveName") if isinstance(kb, dict) else None
    print(f"[kb] primitiveName={primitive}")

    # ---- 2) 串行上传业务语料（FAQ 抽取源）
    up_ev = []
    files = []
    for key in ("docx_loan", "docx_plain"):
        path = L.FIXTURES[key]
        code, body, meta = L.upload(s, token, kb_id, path)
        item = {"key": key, "http": code, "body": body, "meta": meta}
        up_ev.append(item)
        print(f"[upload] {key} http={code} body={json.dumps(body, ensure_ascii=False)[:200]}")
        time.sleep(1)  # 串行，绝不并发（QA-SPEC §5-9）
    L.dump("S3-upload.json", up_ev, "S9")

    # ---- 3) 等解析 + 拿 file_id / file_path
    code, fl, _ = L.file_list(s, token, kb_id)
    rows = ((fl.get("data") or {}).get("records")
            if isinstance(fl, dict) and isinstance(fl.get("data"), dict) else None) or []
    if not rows and isinstance(fl, dict) and isinstance(fl.get("data"), list):
        rows = fl["data"]
    L.dump("S9-0-filelist.json", fl, "S9")
    for r in rows:
        fid = r.get("id") or r.get("fileId")
        fr = wait_file(s, token, fid)
        files.append({"file_id": fid, "file_name": r.get("fileName") or r.get("parentFileName"),
                      "version": r.get("version"), "file_path": r.get("filePath"),
                      "converted": r.get("convertedFilePath"),
                      "size": r.get("size") or r.get("fileSize"),
                      "parse": fr})
        print(f"[file] id={fid} name={files[-1]['file_name']} parse={fr['final']} "
              f"waited={fr['waited']}s")

    st.update({"kb_name": kb_name, "kb_id": kb_id, "primitive": primitive, "files": files})
    L.save_state(st)

    # ---- 4) FAQ 抽取（前端 FAQ抽取 tab 走 extractFQA，files[] 消费）
    ok_file = next((f for f in files if f["parse"]["final"] == 3), None)
    if not ok_file:
        raise SystemExit("没有解析成功的文件，无法抽取 FAQ")

    before = L.faq_list(s, token, kb_id, page_no=1, page_size=10)
    before_total = ((before[1].get("data") or {}).get("total")
                    if isinstance(before[1], dict) and isinstance(before[1].get("data"), dict)
                    else None)
    es_before = L.es_count(f"faq_{primitive}")

    ex_code, ex_body, ex_el = L.faq_extract(
        s, token, kb_id, primitive, ok_file["file_id"], ok_file["file_path"],
        file_size=str(ok_file.get("size") or "0MB"))
    ex_wait = wait_extract(s, token, ok_file["file_id"])

    after = L.faq_list(s, token, kb_id, page_no=1, page_size=100)
    after_data = after[1].get("data") if isinstance(after[1], dict) else None
    after_total = after_data.get("total") if isinstance(after_data, dict) else None
    es_after = L.es_count(f"faq_{primitive}")

    ext_ev = {
        "time": L.now(), "kb_id": kb_id, "primitive": primitive,
        "source_file": ok_file,
        "extract_http": ex_code, "extract_body": ex_body, "extract_elapsed": ex_el,
        "extract_status_poll": ex_wait,
        "faq_total_before": before_total, "faq_total_after": after_total,
        "es_faq_index": f"faq_{primitive}", "es_before": es_before, "es_after": es_after,
        "faq_after_sample": (after_data or {}).get("records", [])[:5]
        if isinstance(after_data, dict) else None,
    }
    L.dump("S9-2-faq-extract.json", ext_ev, "S9")
    print("[extract]", json.dumps({"http": ex_code, "body": ex_body,
                                   "status": ex_wait["final"], "waited": ex_wait["waited"],
                                   "total_before": before_total, "total_after": after_total,
                                   "es_before": es_before, "es_after": es_after},
                                  ensure_ascii=False))

    # ---- 5) 建确定性问答对（分页/编辑/启停/删除/直答 的稳定夹具）
    made = []
    stamp = time.strftime("%H%M%S")
    for i in range(1, 13):
        q = f"AG6Q-{stamp}-{i:03d}：智造贷的最高授信额度是多少？"
        a = f"AG6A-{stamp}-{i:03d}：最高授信额度为 8000 万元。"
        code, body, _ = L.faq_create(s, token, kb_id, [{"question": q, "answer": a}])
        rec = None
        if isinstance(body, dict):
            d = body.get("data")
            if isinstance(d, list) and d:
                rec = d[0]
            elif isinstance(d, dict):
                rec = d
        made.append({"i": i, "http": code, "resp": body, "rec": rec})
        time.sleep(0.2)
    L.dump("S9-0-faq-create.json", made, "S9")
    st["faq_created"] = made
    st["stamp"] = stamp
    L.save_state(st)
    print("[create]", [(m["i"], m["http"], (m["rec"] or {}).get("pk")) for m in made])

    after2 = L.faq_list(s, token, kb_id, page_no=1, page_size=10)
    d2 = after2[1].get("data") if isinstance(after2[1], dict) else None
    print("[list] total =", d2.get("total") if isinstance(d2, dict) else None,
          "records_len =", len(d2.get("records") or []) if isinstance(d2, dict) else None)


if __name__ == "__main__":
    main()
