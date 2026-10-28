#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 UI 用例用：上传一个带唯一文件名的小文件，输出一行 JSON（供 node 侧观测页面是否自动出现）。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import FIXTURES, login, upload

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
s, token = login()
fname = f"AG5-LIVE-{time.strftime('%H%M%S')}.docx"
code, body, meta = upload(s, token, KB_ID, FIXTURES["docx_plain"], fname=fname)
data = (body.get("data") or []) if isinstance(body, dict) else []
fid = data[0].get("id") if data and isinstance(data[0], dict) else None
print(json.dumps({"fname": fname, "http": code, "file_id": fid, "req_time": meta["req_time"]},
                 ensure_ascii=False))
