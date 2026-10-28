#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S0 前置：版本自证 / 端口代次 / 库归属确认 / 建自建库（id 从响应取）。"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, dump, es_count, kb_create, kb_list, login, now, pids, api)

RUN = "/home/szf/data/dev/llmke-r12"
KB_NAME = sys.argv[1] if len(sys.argv) > 1 else None
if not KB_NAME:
    from datetime import datetime
    KB_NAME = "R14-E2E-AG5-" + datetime.now().strftime("%H%M")

out = {"ts": now(), "kb_name_planned": KB_NAME}

# 1) 前端版本自证（§1.4）
A = subprocess.run(["bash", "-lc",
                    f"cd {RUN} && grep -oE 'assets/index-[A-Za-z0-9_-]+\\.js' frontend/plateform/dist/index.html | head -1"],
                   capture_output=True, text=True).stdout.strip()
served = "/tmp/served-ag5.js"
curl = subprocess.run(["bash", "-lc",
                       f"curl -sS 'http://127.0.0.1:18088/{A}' -o {served} -w '%{{http_code}} %{{size_download}}'"],
                      capture_output=True, text=True).stdout.strip()
m = subprocess.run(["bash", "-lc", f"md5sum {served} {RUN}/frontend/plateform/dist/{A}"],
                   capture_output=True, text=True).stdout
lines = [l.split()[0] for l in m.strip().splitlines() if l.strip()]
out["frontend"] = {"entry": A, "curl": curl, "md5_served": lines[0] if lines else None,
                   "md5_dist": lines[1] if len(lines) > 1 else None,
                   "match": len(lines) > 1 and lines[0] == lines[1]}

# 2) 端口代次
out["pids_open"] = pids()

# 3) 库归属确认
s, token = login()
code, body = kb_list(s, token)
recs = ((body.get("data") or {}).get("records") or []) if isinstance(body, dict) else []
out["kb_list"] = {"http": code, "total": (body.get("data") or {}).get("total") if isinstance(body, dict) else None,
                  "records_n": len(recs),
                  "names": sorted([r.get("kbName") for r in recs if isinstance(r, dict)])}
kb9 = [r for r in recs if isinstance(r, dict) and r.get("kbName") == "kb_9"]
out["kb_9"] = kb9[0] if kb9 else None
existing = [r for r in recs if isinstance(r, dict) and r.get("kbName") == KB_NAME]

# 4) 建库（id 从响应取）
if existing:
    out["kb_create"] = {"reused": True, "kb": existing[0]}
    kb_id = existing[0]["id"]
else:
    code, body = kb_create(s, token, KB_NAME)
    data = (body.get("data") or {}) if isinstance(body, dict) else {}
    out["kb_create"] = {"http": code, "body": body}
    kb_id = data.get("id")
out["kb_id"] = kb_id
out["kb_primitive"] = (out["kb_create"].get("body", {}) or {}).get("data", {}).get("primitiveName") \
    if isinstance(out["kb_create"].get("body"), dict) else None

# 5) 建库后 ES 条数基线
if kb_id:
    out["es_after_create"] = [es_count(f"kb_{kb_id}"), es_count(f"table_chunks_kb_{kb_id}"),
                              es_count(f"table_summary_kb_{kb_id}")]

p = dump(f"preflight-{now().replace(' ', 'T').replace(':', '')}.json", out, sub="S0")
print(json.dumps(out, ensure_ascii=False, indent=1))
print("[evidence]", p)
print(f"[kb] name={KB_NAME} id={kb_id}")
