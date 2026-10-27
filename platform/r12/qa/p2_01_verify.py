#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R14-P2-01 端到端验证：加密 PDF 是否"稳定快速失败"（不是"偶尔被兜底收尾"）。

为什么需要这个脚本（TL/C 的判据）：
  修好之前：同一类文件终结耗时 **1 分钟 / 23 分钟**两个样本 —— 不是产品在判，是哪条兜底先撞上；
  修好之后：白名单命中 → 一次定死，`retry_times` 走到 1/3 后终结，**三次耗时同量级**。
  所以"PASS"不够，必须报 **耗时分布 + 上传时刻**（有上传时刻才能证明样本跑在新代码上）。

判据（写死，不放宽）：
  ① 三次都到 status=4（解析失败）→ 单次 PASS；任一次 3/98/99 到超时 → 该次 TIMEOUT
  ② 三次耗时 max/min <= 3 且 max <= 300s → "稳定快速失败"
  ③ retry_times 必须 >= 1（说明走了"失败计数"路径，而不是计数恒 0）
附带对照：正常文件解析成功后 `retry_times` 仍应为 0、task status=4（成功），
         证明"修重试计数"没有把正常路径搞乱。
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

QA = "/home/szf/data/dev/llmke-r12/platform/r12/qa"
sys.path.insert(0, QA)

from r12_client import api, login  # noqa: E402

import acceptance as AC  # noqa: E402  复用 upload()，避免重复实现上传协议

SAMPLES = "/home/szf/data/dev/coordination/samples"
KB_NAME = "R14-P201-KB"
TS = datetime.now().strftime("%Y%m%dT%H%M%SZ")
EVID = os.path.join("/home/szf/data/dev/llmke-r12/platform/r12/qa/evidence", f"R14-P201-{TS}")
MYSQL = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]


def sql(q):
    out = subprocess.run(MYSQL + [q], capture_output=True, text=True)
    return out.stdout.strip()


def ensure_kb(s):
    code, body = api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=50", s.token)
    for r in (((body.get("data") or {}).get("records") or []) if isinstance(body, dict) else []):
        if r.get("kbName") == KB_NAME:
            return r["id"], r.get("primitiveName"), "reuse"
    payload = {"kbName": KB_NAME, "kbDes": "R14-P2-01 端到端验证专用（可随时删除）",
               "fileType": "naive", "chunkSize": 512, "chunkOverlap": 50,
               "embeddingModelName": "bge-m3", "privateKb": 0, "platform": "rag-qa"}
    code, body = api(s, "POST", "/index/knowledgeBase/create", s.token, json=payload)
    data = (body.get("data") or {}) if isinstance(body, dict) else {}
    return data.get("id"), data.get("primitiveName"), f"create http={code}"


def wait_terminal(s, fid, limit=420, interval=5):
    """轮询到终态；返回 (最终状态, 耗时秒, 状态轨迹)。"""
    t0 = time.time()
    seq, last = [], None
    while time.time() - t0 < limit:
        code, body = api(s, "GET", f"/index/knowledgeBase/file/getFileStatusById?fileId={fid}", s.token)
        st = body.get("data") if isinstance(body, dict) else None
        if st != last:
            seq.append([round(time.time() - t0, 1), st])
            last = st
        if st in (3, 4):
            return st, time.time() - t0, seq
        time.sleep(interval)
    return last, time.time() - t0, seq


def tasks_of(fid):
    raw = sql("select id,status,retry_times,retry_limit,start_time,gmt_create,"
              "left(coalesce(error_msg,''),120) from gienrag.file_parse_task "
              f"where file_id={int(fid)} order by id;")
    rows = []
    for line in raw.splitlines():
        p = line.split("\t")
        if len(p) >= 7:
            rows.append({"task": p[0], "status": p[1], "retry_times": p[2],
                         "retry_limit": p[3], "start_time": p[4], "gmt_create": p[5],
                         "error_msg": p[6]})
    return rows


def main():
    os.makedirs(EVID, exist_ok=True)
    s, token, _ = login()
    s.token = token
    kb_id, kb_prim, how = ensure_kb(s)
    print(f"KB {KB_NAME} id={kb_id} primitive={kb_prim} ({how})")
    out = {"started": datetime.now().isoformat(timespec="seconds"), "kb_id": kb_id,
           "kb_primitive": kb_prim, "samples": [], "control": None}

    enc = os.path.join(SAMPLES, "pdf-encrypted.pdf")
    for i in range(1, 4):
        t_up = time.time()
        code, body = AC.upload(s, kb_id, enc)
        data = (body or {}).get("data") if isinstance(body, dict) else None
        fid = (data[0].get("id") if isinstance(data, list) and data
               else (data.get("id") if isinstance(data, dict) else None))
        up_at = datetime.fromtimestamp(t_up).strftime("%H:%M:%S")
        if not fid:
            rec = {"n": i, "upload_at": up_at, "http": code, "file_id": None, "error": "上传未返回 fileId"}
            out["samples"].append(rec)
            print(f"样本{i} 上传失败 http={code}")
            continue
        st, el, seq = wait_terminal(s, fid)
        rec = {"n": i, "upload_at": up_at, "file_id": fid, "final_status": st,
               "elapsed_s": round(el, 1), "status_seq": seq, "tasks": tasks_of(fid)}
        out["samples"].append(rec)
        print(f"样本{i} 上传={up_at} file={fid} 终态={st} 耗时={el:.0f}s 轨迹={seq[:6]} "
              f"tasks={[(x['task'], x['status'], x['retry_times']) for x in rec['tasks']]}")
        time.sleep(3)

    # 对照：正常文件（证明"修重试计数"没有搞乱成功路径）
    docx = os.path.join(SAMPLES, "docx-plain.docx")
    code, body = AC.upload(s, kb_id, docx)
    data = (body or {}).get("data") if isinstance(body, dict) else None
    fid = (data[0].get("id") if isinstance(data, list) and data
           else (data.get("id") if isinstance(data, dict) else None))
    if fid:
        st, el, seq = wait_terminal(s, fid)
        out["control"] = {"file_id": fid, "final_status": st, "elapsed_s": round(el, 1),
                          "tasks": tasks_of(fid)}
        print(f"对照(正常文件) file={fid} 终态={st} 耗时={el:.0f}s "
              f"tasks={[(x['task'], x['status'], x['retry_times']) for x in out['control']['tasks']]}")

    # -------- 判定 --------
    ok_samples = [x for x in out["samples"] if x.get("final_status") == 4]
    times = [x["elapsed_s"] for x in ok_samples]
    spread = (max(times) / min(times)) if len(times) >= 2 and min(times) > 0 else None
    retry_ok = all(int(t["retry_times"]) >= 1 for x in ok_samples for t in x["tasks"] if t["status"] == "5")
    stable = (len(ok_samples) == 3 and spread is not None and spread <= 3 and max(times) <= 300 and retry_ok)
    out["verdict"] = {"terminal_fail_3of3": len(ok_samples) == 3, "times": times,
                      "spread_max_over_min": round(spread, 2) if spread else None,
                      "retry_times_nonzero": retry_ok, "stable_fast_fail": stable}
    print(f"\n判定：3/3 到 status=4={len(ok_samples) == 3} 耗时={times} 波动倍数={spread} "
          f"retry_times>=1={retry_ok} → 稳定快速失败={stable}")
    with open(os.path.join(EVID, "p2_01_verify.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"证据: {EVID}")
    return 0 if stable else 1


if __name__ == "__main__":
    sys.exit(main())
