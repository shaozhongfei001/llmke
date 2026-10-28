#!/usr/bin/env python3
"""取登录 token（走服务端既有 simpleLogin 接口，同一密码校验链，仅跳过图形验证码）。
登录交互本身归 AG-1，AG-4 只借它建立已登录会话。"""
import json
import os
import sys

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import login  # noqa: E402

s, token, body = login()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence", ".token.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
d = (body.get("data") or {})
with open(out, "w") as f:
    json.dump({"token": token, "userName": d.get("userName"), "userId": d.get("id"),
               "email": d.get("userEmail"), "realName": d.get("userRealname")}, f)
print(out)
