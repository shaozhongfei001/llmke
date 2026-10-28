#!/usr/bin/env python3
"""桥接：取一个服务端签发的 admin token（simpleLogin，同一密码校验链，仅跳过图形验证码）。

输出一行 JSON：{"token":..., "user":{...}}   —— 不含密码明文。
登录正确性属 S1（AG-1）；本角色只用它建立浏览器会话。
"""
import json
import os
import sys

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import login  # noqa: E402

s, token, body = login()
d = body.get("data") or {}
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
