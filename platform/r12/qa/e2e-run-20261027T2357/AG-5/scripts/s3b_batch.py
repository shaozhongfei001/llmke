#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 追加两项：① 3 个文件并发上传（已知缺陷点：建索引冲突会静默丢文件）
                  ② 上传中断（客户端超时，标注"注入"）后能否得到可读错误并可重试

判据：
  ① 不看"上传接口 success"，逐个文件查 3 件事：DB 行存在 + ES 有该 file_id 的块 + 文件终态成功
     3 个里有任何一个丢了 → FAIL（并把丢的那个 uid/文件名写清）
  ② 中断必须产生可读错误（客户端异常类型 + 服务端无 0 条成功登记），重试后必须成功
"""
import concurrent.futures as cf
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, FIXTURES, es_docs, file_rows,
                     file_status, fstatus_name, login, now, parse_tasks, upload)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
IDX = [f"kb_{KB_ID}", f"table_chunks_kb_{KB_ID}", f"table_summary_kb_{KB_ID}"]
TAG = time.strftime("%H%M%S")


def cross_count(fid):
    out, total = {}, 0
    for idx in IDX:
        j = es_docs(idx, size=200, query={"term": {"metadata.file_id": int(fid)}})
        if "error" in j:
            out[idx] = "ERR"
            continue
        n = j.get("hits", {}).get("total", {}).get("value") or 0
        out[idx] = n
        total += n
    return out, total


def poll_until_terminal(s, token, fid, max_wait=240):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        code, body = file_status(s, token, fid)
        st = body.get("data") if isinstance(body, dict) else body
        if st in (FILE_OK, FILE_FAIL):
            return st, round(time.time() - t0, 1)
        time.sleep(2)
    return None, round(time.time() - t0, 1)


def main():
    s, token = login()
    out = {"ts": now(), "kb_id": KB_ID, "batch": {}, "interrupt": {}}

    # ---------- ① 3 并发 ----------
    batch = [
        (f"AG5-BATCH1-pdf-{TAG}.pdf", FIXTURES["pdf_digital"]),
        (f"AG5-BATCH2-docx-{TAG}.docx", FIXTURES["docx_plain"]),
        (f"AG5-BATCH3-xlsx-{TAG}.xlsx", FIXTURES["xlsx"]),
    ]

    def one(fname, path):
        return upload(s, token, KB_ID, path, fname=fname)

    t0 = time.time()
    results = []
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(one, fn, p) for fn, p in batch]
        for (fn, p), f in zip(batch, futs):
            code, body, meta = f.result()
            data = (body.get("data") or []) if isinstance(body, dict) else []
            fid = data[0].get("id") if data and isinstance(data[0], dict) else None
            results.append({"fname": fn, "uid": meta["uid"], "http": code,
                            "api_success": bool(isinstance(body, dict) and body.get("success")),
                            "file_id": fid,
                            "resp_msg": (data[0].get("message") if data and isinstance(data[0], dict) else None),
                            "body": json.dumps(body, ensure_ascii=False)[:900]})
    out["batch"]["concurrent_elapsed"] = round(time.time() - t0, 2)

    for r in results:
        if not r["file_id"]:
            r["verdict"] = "FAIL(无file_id)"
            continue
        st, waited = poll_until_terminal(s, token, r["file_id"])
        idx, total = cross_count(r["file_id"])
        rows = file_rows([r["file_id"]]).get("rows") or []
        tasks = parse_tasks([r["file_id"]]).get("tasks") or []
        r.update({"file_status": st, "status_name": fstatus_name(st), "waited": waited,
                  "es": idx, "es_total": total, "db_row": rows,
                  "task": [(t["task_id"], t["status_name"]) for t in tasks]})
        r["verdict"] = "PASS" if (st == FILE_OK and total > 0 and rows) else "FAIL"
    out["batch"]["files"] = results
    out["batch"]["ingested"] = sum(1 for r in results if r.get("verdict") == "PASS")
    out["batch"]["sent"] = len(results)

    # ---------- ② 上传中断（注入：客户端 0.1s 超时） ----------
    intr_path = FIXTURES["pptx"]
    fname = f"AG5-INTR-{TAG}.pptx"
    param_tpl = {"kbId": KB_ID,
                 "fileList": [{"fileName": fname, "type": "OVERWRITE", "uid": f"ag5-intr-{TAG}"}],
                 "fileListType": 1, "isParse": True, "isExtract": False, "isGraphParse": False,
                 "chunking": True, "needChunk": True, "saveTxt": True, "platform": "rag-qa"}
    rec_intr = {"label": "注入（客户端 timeout=0.1s 主动中断，非服务端故障）", "fname": fname}
    try:
        with open(intr_path, "rb") as f:
            requests.post(f"http://127.0.0.1:8088/index/knowledgeBase/file/uploadFileList",
                          data={"uploadFileParam": json.dumps(param_tpl, ensure_ascii=False)},
                          files=[("files", (fname, f, "application/octet-stream"))],
                          headers={"Authorization": token, "X-Platform": "rag-qa"},
                          timeout=0.1)
        rec_intr["client_error"] = "none（未触发超时，需换更大文件）"
        rec_intr["readable"] = False
    except requests.exceptions.RequestException as e:
        rec_intr["client_error"] = f"{type(e).__name__}: {str(e)[:160]}"
        rec_intr["readable"] = True
    time.sleep(2)
    # 中断后是否留下半成品登记？
    code, body, _meta = upload(s, token, KB_ID, intr_path, fname=fname, uid=f"ag5-intr-retry-{TAG}")
    data = (body.get("data") or []) if isinstance(body, dict) else []
    fid = data[0].get("id") if data and isinstance(data[0], dict) else None
    rec_intr["retry"] = {"http": code, "api_success": bool(isinstance(body, dict) and body.get("success")),
                         "file_id": fid, "body": json.dumps(body, ensure_ascii=False)[:600]}
    if fid:
        st, waited = poll_until_terminal(s, token, fid)
        idx, total = cross_count(fid)
        rec_intr["retry"].update({"file_status": st, "status_name": fstatus_name(st),
                                  "es": idx, "es_total": total})
        rec_intr["verdict"] = "PASS" if (rec_intr["readable"] and st == FILE_OK and total > 0) else "FAIL"
    else:
        rec_intr["verdict"] = "FAIL"
    out["interrupt"] = rec_intr

    p = os.path.join(EVID, "S3", f"S3b-batch-interrupt-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"batch": {k: v for k, v in out["batch"].items() if k != "files"},
                      "batch_files": [{k: r.get(k) for k in
                                       ("fname", "file_id", "api_success", "file_status",
                                        "status_name", "es_total", "verdict", "resp_msg")}
                                      for r in results],
                      "interrupt": {k: rec_intr.get(k) for k in
                                    ("client_error", "verdict", "retry")}},
                     ensure_ascii=False, indent=1))
    print("[evidence]", p)


if __name__ == "__main__":
    main()
