#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S4 重试（第二轮，用前端真实 payload）+ 状态流转密集采样。

背景（第一轮结论，已入证据 S4-retry-*.json）：
  只传 `file_ids` 时 filesParse 返回 success=true 但**零任务、零状态变化**——
  源码事实：getFilePathByFolder() 只从 folder_ids 装配 files，从不读 fileIds
  （KnowledgeBaseListAppServiceImpl.java:689-709），所以 file_ids 分支恒空。
  前端真实调用见 S4/ui3.json 的 postData：传的是 files[]（含 file_id/file_path）。

本轮判据：
  P1 用前端同款 payload → 必须新增一条 file_parse_task（新 task_id ≠ 旧）
  P2 状态采样必须能看见"排队/解析中"中间态（否则"流转可见"不成立，只能记"只看得到终态"）
  P3 终态与语义一致（对失败文件仍是失败）
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, TASK_STATUS, api, file_rows,
                     file_status, login, now, parse_tasks)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
KB_NAME = "R14-E2E-AG5-1111"
OK_FID = int(os.environ.get("AG5_OK_FID", "493"))
FAIL_FID = int(os.environ.get("AG5_FAIL_FID", "503"))


def tasks_of(fid):
    return (parse_tasks([fid]).get("tasks") or [])


def row_of(fid):
    return (file_rows([fid]).get("rows") or [{}])[0]


def payload_for(fid):
    r = row_of(fid)
    return {"files": [{"folder_id": None,
                       "file_path": f"r12-rag/kb_{KB_ID}/{r.get('file_name')}/{r.get('version')}/{r.get('file_name')}",
                       "file_id": str(fid),
                       "parent_file_name": r.get("file_name")}],
            "folder_ids": [], "knowledge_base_name": KB_NAME,
            "knowledge_base_id": str(KB_ID), "override": True, "is_all": False}


def sample(s, token, fid, max_wait=240, interval=0.3):
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


def run(s, token, fid, label):
    before = tasks_of(fid)
    rec = {"label": label, "file_id": fid, "payload": payload_for(fid),
           "before_tasks": before, "before_row": row_of(fid), "req_time": now()}
    code, body = api(s, "POST", "/index/knowledgeBase/file/filesParse", token,
                     json=rec["payload"])
    rec["http"], rec["body"] = code, body
    rec["sampling"] = sample(s, token, fid)
    after = tasks_of(fid)
    rec["after_tasks"] = after
    rec["after_row"] = row_of(fid)
    old = {t["task_id"] for t in before}
    new = [t for t in after if t["task_id"] not in old]
    rec["new_tasks"] = new
    rec["task_ids_before_after"] = [sorted(old), [t["task_id"] for t in new]]
    rec["verdict"] = "PASS" if (code == 200 and isinstance(body, dict) and body.get("success")
                                and new) else "FAIL"
    return rec


def main():
    s, token = login()
    out = {"ts": now(), "kb_id": KB_ID}
    out["ok_file_retry"] = run(s, token, OK_FID, "API：成功文件重解析（前端同款 payload）")
    out["fail_file_retry"] = run(s, token, FAIL_FID, "API：失败文件重试（前端同款 payload）")
    for k in ("ok_file_retry", "fail_file_retry"):
        r = out[k]
        print(f"[{k}] http={r['http']} success={r['body'].get('success') if isinstance(r['body'], dict) else r['body']} "
              f"new_task={[t['task_id'] for t in r['new_tasks']]} "
              f"states={'->'.join(x['name'] for x in r['sampling']['samples'])} "
              f"intermediate={r['sampling']['intermediate_seen']} -> {r['verdict']}")
    p = os.path.join(EVID, "S4", f"S4-retry2-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence]", p)


if __name__ == "__main__":
    main()
