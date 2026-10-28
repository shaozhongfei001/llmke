#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 重试：入口可用 + 重试后产生新任务（记录两个 task id）+ 状态流转采样。

判据：
  R1 POST /index/knowledgeBase/file/filesParse 返回 success=true（数据面）
  R2 重试后 file_parse_task 新增一行、task_id 与重试前不同（两个 task id 都要落证据）
  R3 重试后的任务是新代次：start_time 晚于重试时刻
  R4 状态流转采样里能观察到"非终态"（排队/解析中）再到终态；若一次都没采到中间态，
     如实记录（页面/轮询可能根本看不到中间态），不得用"终态=成功"冒充"流转可见"
  R5 重试失败文件仍失败（可重复失败，不是一次成功后静默变成功）
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, TASK_STATUS, api, file_rows,
                     file_status, fstatus_name, login, now, parse_tasks, tstatus_name)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
KB_NAME = "kb_36"
FAIL_FID = int(os.environ.get("AG5_FAIL_FID", "503"))     # truncated.docx
OK_FID = int(os.environ.get("AG5_OK_FID", "493"))         # docx-plain.docx


def tasks_of(fid):
    return (parse_tasks([fid]).get("tasks") or [])


def sample_states(s, token, fid, max_wait=180, interval=0.5):
    t0 = time.time()
    seen = []
    while time.time() - t0 < max_wait:
        c, b = file_status(s, token, fid)
        v = b.get("data") if isinstance(b, dict) else b
        if not seen or seen[-1]["status"] != v:
            seen.append({"t": round(time.time() - t0, 2), "status": v,
                         "name": FILE_STATUS.get(v, "?")})
        if v in (FILE_OK, FILE_FAIL):
            break
        time.sleep(interval)
    return {"samples": seen, "elapsed": round(time.time() - t0, 2),
            "intermediate_seen": any(x["status"] not in (FILE_OK, FILE_FAIL) for x in seen),
            "final": seen[-1]["status"] if seen else None}


def do_retry(s, token, fid, label):
    before_tasks = tasks_of(fid)
    before_row = (file_rows([fid]).get("rows") or [{}])[0]
    t_req = time.time()
    code, body = api(s, "POST", "/index/knowledgeBase/file/filesParse", token,
                     json={"file_ids": [str(fid)], "knowledge_base_name": KB_NAME,
                           "knowledge_base_id": KB_ID})
    rec = {"label": label, "file_id": fid, "retry_http": code, "retry_body": body,
           "req_time": now(), "before_tasks": before_tasks, "before_row": before_row}
    # 立刻密集采样状态（0.5s），尽量抓到中间态
    rec["state_sampling"] = sample_states(s, token, fid)
    after_tasks = tasks_of(fid)
    rec["after_tasks"] = after_tasks
    rec["after_row"] = (file_rows([fid]).get("rows") or [{}])[0]
    new = [t for t in after_tasks if t["task_id"] not in [b["task_id"] for b in before_tasks]]
    rec["new_tasks"] = new
    rec["two_task_ids"] = ([before_tasks[-1]["task_id"]] if before_tasks else []) + \
                          ([new[-1]["task_id"]] if new else [])
    # 新任务确实是新代次（start_time 不早于重试请求时刻）
    ok_start = True
    for t in new:
        st = t.get("start_time") or ""
        if st and st < time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_req - 1)):
            ok_start = False
    rec["new_task_starttime_ok"] = ok_start
    return rec


def main():
    s, token = login()
    out = {"ts": now(), "kb_id": KB_ID, "fail_file": FAIL_FID, "ok_file": OK_FID}
    out["fail_retry"] = do_retry(s, token, FAIL_FID, "对解析失败文件点重试（truncated.docx）")
    out["ok_retry"] = do_retry(s, token, OK_FID, "对解析成功文件重新解析（docx-plain.docx）")

    for k, title in (("fail_retry", "失败文件重试"), ("ok_retry", "成功文件重解析")):
        r = out[k]
        r["verdict"] = "PASS" if (
            r["retry_http"] == 200 and isinstance(r["retry_body"], dict)
            and r["retry_body"].get("success") and r["new_tasks"]
            and r["new_task_starttime_ok"]
        ) else "FAIL"
        print(f"[{k}] http={r['retry_http']} success={r['retry_body'].get('success') if isinstance(r['retry_body'], dict) else r['retry_body']} "
              f"task_ids={r['two_task_ids']} final={fstatus_name(r['state_sampling']['final'])} "
              f"intermediate={r['state_sampling']['intermediate_seen']} -> {r['verdict']}")

    p = os.path.join(EVID, "S4", f"S4-retry-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence]", p)


if __name__ == "__main__":
    main()
