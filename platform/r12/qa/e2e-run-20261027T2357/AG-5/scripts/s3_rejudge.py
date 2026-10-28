#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 判定复核（判据 v2）：修正两处判据缺陷后重算全部用例结论。

判据 v1 的两个缺陷（自曝，写入报告）：
  ① 状态枚举读反：把文件级 3 当成任务级 3(RETRY_ING)，实际文件级 3=解析成功。
     → 若不改，正例会被整片判成"重试中/超时"的假红。
  ② 只查主索引：表格类文件（xlsx/docx-表格）的块落在 table_chunks_*/table_summary_*，
     只查 kb_<id> 会把成功判成"成功但 0 条"的假红（QA-SPEC §1.6 明确警告过）。

判据 v2：
  A4 = 主索引 ∪ table_chunks ∪ table_summary 任一有该 file_id 的块，且 create_time 晚于请求
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, TASK_STATUS, dump, es_docs, now)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
IDX = [f"kb_{KB_ID}", f"table_chunks_kb_{KB_ID}", f"table_summary_kb_{KB_ID}"]


def count_for_file(file_id):
    out = {}
    for idx in IDX:
        j = es_docs(idx, size=500, query={"term": {"metadata.file_id": int(file_id)}})
        if "error" in j:
            out[idx] = {"error": str(j["error"])[:120]}
            continue
        hits = j.get("hits", {}).get("hits", [])
        cts = sorted([h["_source"].get("metadata", {}).get("create_time") for h in hits
                      if h["_source"].get("metadata", {}).get("create_time")])
        out[idx] = {"total": j.get("hits", {}).get("total", {}).get("value"),
                    "got": len(hits),
                    "min_create_time": cts[0] if cts else None,
                    "pks": [h["_source"].get("metadata", {}).get("pk") for h in hits]}
    return out


def main():
    files = sorted(glob.glob(os.path.join(EVID, "S3", "S3-case-*.json")))
    res = {"ts": now(), "judge_version": "v2", "kb_id": KB_ID, "cases": {}}
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        cid = rec["case"]
        fid = rec.get("file_id")
        cross = count_for_file(fid) if fid else {}
        total = sum((v.get("total") or 0) for v in cross.values())
        cts = [v.get("min_create_time") for v in cross.values() if v.get("min_create_time")]
        req = rec["upload"]["req_time"][:19]
        later = bool(cts) and min(cts) >= req
        sp = rec.get("status_poll") or {}
        final = sp.get("final")
        tasks = (rec.get("db_parse_tasks") or {}).get("tasks") or []
        api_ok = rec.get("api_success")
        msg = (rec.get("resp_message") or "")
        # 失败原因（任务级，取最新一条）
        err = tasks[-1]["error_msg"] if tasks else ""

        if rec.get("expect_fail"):
            ok = ((not api_ok) or final == FILE_FAIL) and not (api_ok and final != FILE_FAIL and total == 0)
            verdict = "PASS" if ok else "FAIL"
        else:
            ok = (api_ok and final == FILE_OK and total > 0 and later
                  and all(t.get("status") == 4 for t in tasks))
            verdict = "PASS" if ok else "FAIL"
        res["cases"][cid] = {
            "verdict": verdict, "expect_fail": rec.get("expect_fail"),
            "file_id": fid, "http": rec["upload"]["http"], "api_success": api_ok,
            "file_final": final, "file_final_name": FILE_STATUS.get(final, "?"),
            "task_status": [(t["task_id"], TASK_STATUS.get(t["status"], "?")) for t in tasks],
            "req_time": rec["upload"]["req_time"], "resp_message": msg,
            "error_msg_tail": err[-260:],
            "es_cross_index": cross, "es_total_cross": total,
            "create_time_after_req": later,
            "elapsed_upload": rec["upload"]["elapsed"],
            "poll_elapsed": sp.get("elapsed"), "poll_timed_out": sp.get("timed_out"),
            "transitions": [f"{t['status']}({t['status_name']})@{t['t']}s"
                            for t in (sp.get("transitions") or [])],
        }
        print(f"{cid:20s} {verdict:4s} fid={fid} file={FILE_STATUS.get(final,'?'):6s} "
              f"es_total={total:3d} later={later} tasks={[t['status_name'] for t in tasks]}")
    p = dump(f"S3-final-summary-{now().replace(' ', 'T').replace(':', '')}.json", res, sub="S3")
    print("[evidence]", p)


if __name__ == "__main__":
    main()
