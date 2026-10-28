#!/usr/bin/env python3
"""桥接：取服务端签发的 admin token（simpleLogin，同一密码校验链，仅跳过图形验证码）。
输出一行 JSON。登录正确性归 S1（AG-1），AG-6 只用它建立浏览器会话（注入式会话，报告中注明）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ag6_lib as L  # noqa: E402
import requests  # noqa: E402

s, token = L.login()
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
