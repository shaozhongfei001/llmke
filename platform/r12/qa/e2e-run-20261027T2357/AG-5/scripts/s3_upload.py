#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 上传：全格式串行上传 + 负例（加密/改后缀/截断）。

判据（每条都自己算，不看接口 200）：
  A1 接口 success=true 且 data[0].id 存在
  A2 响应里若存在 task_statuses → 逐项 success 必须 true（不存在则记"该路径不返回"，不以空集当通过）
  A3 文件状态终态 == 4（SUCCESS）；!=5（FAIL）；不长期停在 1/2/3/99
  A4 该 file_id 在 ES 里确实有 chunk，且 create_time 晚于本次请求时刻（证明是新写入，不是旧残留）
  A5 文件接口 /file/getFileChunks 取得到正文（非空）
负例：
  B1 加密 PDF 必须失败（文件状态 5 或接口 success=false / message 可读），不得"成功且 0 chunk"
  B2 改后缀伪造文件必须失败，不得"成功但 0 条"
  B3 截断 docx：记录真实行为（成功/失败都要有可见依据，不许 0 条还标成功）
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_TERMINAL, FIXTURES, api, chunks, dump,
                     es_count, es_docs, file_rows, file_status, fstatus_name, kb_list, login,
                     now, parse_tasks, pids, tstatus_name, upload)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
ES_IDX = f"kb_{KB_ID}"
MAX_WAIT = int(os.environ.get("AG5_MAX_WAIT", "300"))
POLL = 2.0

FIX = os.path.join(EVID, "fixtures")

CASES = [
    # (case_id, 说明, 路径, 显示名)
    ("docx-plain",  "纯文本 docx", FIXTURES["docx_plain"], None),
    ("docx-table",  "含表格 docx", FIXTURES["docx_table"], None),
    ("xlsx-ledger", "台账 xlsx",   FIXTURES["xlsx"], None),
    ("pptx-intro",  "PPTX",        FIXTURES["pptx"], None),
    ("pdf-digital", "数字版 PDF",  FIXTURES["pdf_digital"], None),
    ("pdf-scanned", "扫描版 PDF",  FIXTURES["pdf_scanned"], None),
    ("docx-loan",   "业务 docx",   FIXTURES["docx_loan"], None),
]

NEG_CASES = [
    ("neg-encrypted-pdf", "加密 PDF（user_pw=123456）", os.path.join(FIX, "encrypted.pdf")),
    ("neg-bad-pdf",       "纯文本改后缀 .pdf",           os.path.join(FIX, "bad-renamed.pdf")),
    ("neg-bad-docx",      "随机字节改后缀 .docx",        os.path.join(FIX, "bad-renamed.docx")),
    ("neg-truncated-docx", "合法 docx 截断 60%",          os.path.join(FIX, "truncated.docx")),
]


def es_file_chunks(file_id):
    j = es_docs(ES_IDX, size=500, query={"term": {"metadata.file_id": file_id}})
    if "error" in j:
        return {"error": j["error"]}
    hits = j.get("hits", {}).get("hits", [])
    total = j.get("hits", {}).get("total", {}).get("value")
    cts = sorted([h["_source"].get("metadata", {}).get("create_time") for h in hits])
    return {"total": total, "got": len(hits), "min_create_time": cts[0] if cts else None,
            "max_create_time": cts[-1] if cts else None,
            "sample_pk": [h["_source"].get("metadata", {}).get("pk") for h in hits[:3]],
            "sample_head": (hits[0]["_source"].get("page_content", "")[:120] if hits else None)}


def poll_status(s, token, file_id, max_wait=MAX_WAIT):
    """轮询文件状态，记录全部变化与时刻。"""
    t0 = time.time()
    seen, last = [], None
    while time.time() - t0 < max_wait:
        code, body = file_status(s, token, file_id)
        st = body.get("data") if isinstance(body, dict) else body
        if st != last:
            seen.append({"t": round(time.time() - t0, 1), "status": st,
                         "status_name": fstatus_name(st), "http": code})
            last = st
        # 终态来自 KbFileStatusEnums：3=解析成功 4=解析失败（注意与任务枚举 3=RETRY_ING 不同义）
        if st in FILE_TERMINAL:
            break
        time.sleep(POLL)
    return {"elapsed": round(time.time() - t0, 1), "transitions": seen, "final": last,
            "final_name": fstatus_name(last), "timed_out": last not in FILE_TERMINAL,
            "enum": "file:0删除/1正常/2解析中/3成功/4失败/5重向量/98重试/99排队"}


def run_case(s, token, cid, desc, path, fname=None, expect_fail=False, is_parse=True):
    rec = {"case": cid, "desc": desc, "file": os.path.basename(path),
           "bytes": os.path.getsize(path), "expect_fail": expect_fail}
    code, body, meta = upload(s, token, KB_ID, path, fname=fname, is_parse=is_parse)
    rec["upload"] = {"http": code, "elapsed": meta["elapsed"], "req_time": meta["req_time"],
                     "req_epoch": meta["req_epoch"], "body": body}
    data = (body.get("data") or []) if isinstance(body, dict) else []
    rec["api_success"] = bool(isinstance(body, dict) and body.get("success"))
    rec["items"] = data if isinstance(data, list) else []
    fid = data[0].get("id") if data and isinstance(data[0], dict) else None
    rec["file_id"] = fid
    rec["resp_message"] = (data[0].get("message") if data and isinstance(data[0], dict) else None)
    rec["resp_status"] = (data[0].get("status") if data and isinstance(data[0], dict) else None)
    rec["resp_task_statuses"] = body.get("task_statuses") if isinstance(body, dict) else None
    rec["has_task_statuses_key"] = isinstance(body, dict) and "task_statuses" in body

    if fid:
        rec["status_poll"] = poll_status(s, token, fid)
        rec["db_file_row"] = file_rows([fid])
        rec["db_parse_tasks"] = parse_tasks([fid])
        rec["es_chunks"] = es_file_chunks(int(fid))
        cc, cb = chunks(s, token, KB_ID, fid)
        rec["chunks_api"] = {"http": cc,
                             "n": len((cb.get("data") or {}).get("records") or [])
                             if isinstance(cb, dict) and isinstance(cb.get("data"), dict)
                             else (len(cb.get("data")) if isinstance(cb, dict) and isinstance(cb.get("data"), list) else None),
                             "sample": json.dumps(cb, ensure_ascii=False)[:400]}
    return rec


def main():
    s, token = login()
    out = {"ts": now(), "kb_id": KB_ID, "es_index": ES_IDX, "pids_open": pids(),
           "es_before": es_count(ES_IDX), "cases": {}, "neg_cases": {}}
    print(f"[start] kb={KB_ID} es_before={out['es_before']}")

    for cid, desc, path, fname in CASES:
        rec = run_case(s, token, cid, desc, path, fname=fname)
        rec["verdict"] = judge_positive(rec)
        out["cases"][cid] = rec
        print(f"[{cid}] http={rec['upload']['http']} api={rec['api_success']} "
              f"fid={rec['file_id']} final={rec.get('status_poll', {}).get('final')} "
              f"chunks={rec.get('es_chunks', {}).get('total')} -> {rec['verdict']}")
        dump(f"S3-case-{cid}.json", rec, sub="S3")

    for cid, desc, path in NEG_CASES:
        rec = run_case(s, token, cid, desc, path, expect_fail=True)
        rec["verdict"] = judge_negative(rec)
        out["neg_cases"][cid] = rec
        print(f"[{cid}] http={rec['upload']['http']} api={rec['api_success']} "
              f"fid={rec['file_id']} final={rec.get('status_poll', {}).get('final')} "
              f"chunks={rec.get('es_chunks', {}).get('total')} msg={rec['resp_message']!r} -> {rec['verdict']}")
        dump(f"S3-case-{cid}.json", rec, sub="S3")

    out["es_after"] = es_count(ES_IDX)
    p = dump(f"S3-summary-{now().replace(' ', 'T').replace(':', '')}.json", out, sub="S3")
    print("[es_after]", out["es_after"])
    print("[evidence]", p)
    print("\n== 判定汇总 ==")
    for k, v in {**out["cases"], **out["neg_cases"]}.items():
        print(f"{k:22s} {v['verdict']}")


def judge_positive(rec):
    """正例判定：四条同时成立才算 PASS。返回结构化结论（含每条依据）。"""
    checks = {}
    checks["A1_接口success"] = rec["api_success"] and rec["file_id"] is not None
    if rec["has_task_statuses_key"]:
        tss = rec["resp_task_statuses"] or []
        checks["A2_task_statuses全true"] = bool(tss) and all(
            (t or {}).get("success") for t in tss)
        checks["A2_note"] = f"响应含 task_statuses，条数={len(tss)}"
    else:
        checks["A2_task_statuses全true"] = "N/A（该端点响应不含 task_statuses 键）"
    sp = rec.get("status_poll") or {}
    checks["A3_文件终态=解析成功(3)"] = sp.get("final") == FILE_OK
    tasks = (rec.get("db_parse_tasks") or {}).get("tasks") or []
    checks["A3b_任务级终态=SUCCESS(4)"] = bool(tasks) and all(t.get("status") == 4 for t in tasks)
    checks["A3_note"] = {"file_final": sp.get("final_name"), "tasks": tasks,
                         "注意": "文件枚举 3=解析成功；任务枚举 4=SUCCESS；两者数值不同义"}
    ec = rec.get("es_chunks") or {}
    req_epoch = rec["upload"]["req_epoch"]
    later = None
    if ec.get("min_create_time"):
        later = ec["min_create_time"] >= time.strftime("%Y-%m-%d %H:%M:%S",
                                                      time.localtime(req_epoch))
    checks["A4_有chunk且create_time晚于请求"] = bool(ec.get("total")) and bool(later)
    checks["A4_detail"] = {"total": ec.get("total"), "min_create_time": ec.get("min_create_time"),
                           "req_time": rec["upload"]["req_time"], "later": later}
    n = (rec.get("chunks_api") or {}).get("n")
    checks["A5_正文可取"] = bool(n)
    hard = [v for k, v in checks.items() if k.startswith(("A1", "A3_", "A3b", "A4_有", "A5"))]
    ok = all(hard)
    return {"verdict": "PASS" if ok else "FAIL", "checks": checks}


def judge_negative(rec):
    """负例判定：必须失败且可见；「成功但 0 条」判 FAIL。"""
    checks = {}
    api_ok = rec["api_success"]
    sp = rec.get("status_poll") or {}
    final = sp.get("final")
    ec = rec.get("es_chunks") or {}
    total = ec.get("total") or 0
    msg = rec.get("resp_message") or ""
    checks["接口拒绝或文件终态=解析失败(4)"] = (not api_ok) or final == FILE_FAIL
    checks["不是成功但0条"] = not (api_ok and final != FILE_FAIL and total == 0)
    checks["可见原因"] = bool(msg) or bool(rec.get("body_error")) or final == FILE_FAIL
    tasks = (rec.get("db_parse_tasks") or {}).get("tasks") or []
    checks["任务级终态"] = [{"task": t["task_id"], "status": t["status_name"],
                            "retry": f"{t['retry_times']}/{t['retry_limit']}",
                            "error_msg": t["error_msg"]} for t in tasks]
    checks["detail"] = {"api_success": api_ok, "file_final_status": final,
                        "es_chunks": total, "resp_message": msg,
                        "resp_status": rec.get("resp_status")}
    ok = (checks["接口拒绝或文件终态=解析失败(4)"] and checks["不是成功但0条"])
    return {"verdict": "PASS" if ok else "FAIL", "checks": checks}


if __name__ == "__main__":
    main()
