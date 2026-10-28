#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 追加：**全新库**首次 3 并发上传（真正的建索引竞争窗口）。

为什么要单独做：kb_36 已有索引，3 并发上传时索引早就建好，竞争窗口已经不存在，
在已有库上做并发只会得到"3/3 都成功"的假绿。已知缺陷（建索引 400 被吞 → 文件静默丢失）
只可能在"索引尚不存在 + 多文件同时建索引"的窗口里出现。

判据：3 个文件逐个确认 DB 行 + ES 块（跨三索引）+ 文件终态；丢任何一个即 FAIL。
"""
import concurrent.futures as cf
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FIXTURES, es_count, es_docs, file_rows,
                     file_status, fstatus_name, kb_create, kb_list, login, now, parse_tasks,
                     upload)

TAG = time.strftime("%H%M")
KB_NAME = f"R14-E2E-AG5-{TAG}-C"


def cross(idx_names):
    return [es_count(i) for i in idx_names]


def main():
    s, token = login()
    code, body = kb_list(s, token)
    recs = ((body.get("data") or {}).get("records") or [])
    exist = [r for r in recs if r.get("kbName") == KB_NAME]
    if exist:
        kb_id = exist[0]["id"]
        create = {"reused": True, "kb": exist[0]}
    else:
        c, b = kb_create(s, token, KB_NAME, "R14 E2E AG-5 全新库并发上传窗口验收（用完即删）")
        kb_id = ((b.get("data") or {}) if isinstance(b, dict) else {}).get("id")
        create = {"http": c, "body": b}
    idxs = [f"kb_{kb_id}", f"table_chunks_kb_{kb_id}", f"table_summary_kb_{kb_id}"]
    out = {"ts": now(), "kb_name": KB_NAME, "kb_id": kb_id, "create": create,
           "es_before": cross(idxs), "note": "全新库：三个索引均未创建，首次上传才建"}
    print("[kb]", KB_NAME, kb_id, out["es_before"])

    files = [
        (f"AG5-CONC1-pdf-{TAG}.pdf", FIXTURES["pdf_digital"]),
        (f"AG5-CONC2-docx-{TAG}.docx", FIXTURES["docx_table"]),
        (f"AG5-CONC3-xlsx-{TAG}.xlsx", FIXTURES["xlsx"]),
    ]

    def one(fname, path):
        return fname, upload(s, token, kb_id, path, fname=fname)

    t0 = time.time()
    results = []
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(one, fn, p) for fn, p in files]
        for f in cf.as_completed(futs):
            fname, (code, body, meta) = f.result()
            data = (body.get("data") or []) if isinstance(body, dict) else []
            fid = data[0].get("id") if data and isinstance(data[0], dict) else None
            results.append({"fname": fname, "http": code, "uid": meta["uid"],
                            "api_success": bool(isinstance(body, dict) and body.get("success")),
                            "file_id": fid,
                            "resp": json.dumps(body, ensure_ascii=False)[:1200]})
    out["concurrent_elapsed"] = round(time.time() - t0, 2)
    out["es_after_upload_immediate"] = cross(idxs)

    for r in results:
        if not r["file_id"]:
            r["verdict"] = "FAIL(无file_id/未入库)"
            continue
        t0 = time.time()
        st = None
        while time.time() - t0 < 240:
            c, b = file_status(s, token, r["file_id"])
            v = b.get("data") if isinstance(b, dict) else b
            if v in (FILE_OK, FILE_FAIL):
                st = v
                break
            time.sleep(2)
        total = 0
        per = {}
        for idx in idxs:
            j = es_docs(idx, size=200, query={"term": {"metadata.file_id": int(r["file_id"])}})
            n = 0 if "error" in j else (j.get("hits", {}).get("total", {}).get("value") or 0)
            per[idx] = n
            total += n
        rows = file_rows([r["file_id"]]).get("rows") or []
        r.update({"file_status": st, "status_name": fstatus_name(st), "es": per,
                  "es_total": total, "db_row": rows,
                  "tasks": [(t["task_id"], t["status_name"], t["error_msg"][-140:])
                            for t in (parse_tasks([r["file_id"]]).get("tasks") or [])]})
        r["verdict"] = "PASS" if (st == FILE_OK and total > 0 and rows) else "FAIL"

    out["files"] = results
    out["sent"] = len(results)
    out["ingested"] = sum(1 for r in results if r["verdict"] == "PASS")
    out["es_after"] = cross(idxs)
    p = os.path.join(EVID, "S3", f"S3c-freshkb-concurrent-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("kb_id", "es_before", "concurrent_elapsed",
                                         "sent", "ingested", "es_after")},
                     ensure_ascii=False, indent=1))
    for r in results:
        print(" ", r["fname"], r.get("file_id"), r.get("status_name"), "es", r.get("es"),
              "->", r["verdict"])
    print("[evidence]", p)


if __name__ == "__main__":
    main()
