#!/usr/bin/env python3
"""桥接：取一个服务端签发的 admin token（simpleLogin，同一密码校验链，仅跳过图形验证码）。
输出一行 JSON：{"token":..., "user":{...}} —— 不含密码明文。
登录正确性属 S1（AG-1）；AG-5 只用它建立浏览器会话（口径与 AG-3 一致，报告中注明"注入式会话"）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ag5_lib import login  # noqa: E402

s, token = login()
c, b = None, None
import requests  # noqa: E402
r = requests.get("http://127.0.0.1:8088/auth/user/getUserInfo",
                 headers={"Authorization": token, "X-Platform": "rag-qa"}, timeout=30)
d = (r.json().get("data") or {}) if r.ok else {}
print(json.dumps({
    "token": token,
    "user": {
        "userName": d.get("userName"),
        "userEmail": d.get("userEmail"),
        "url": d.get("url"),
        "userPhone": d.get("userPhone"),
        "userRealname": d.get("userRealname"),
        "id": d.get("id"),
        "hasSetSecurityQuestion": d.get("hasSetSecurityQuestion"),
        "hasAdminResetPassword": d.get("hasAdminResetPassword"),
    },
}, ensure_ascii=False))
