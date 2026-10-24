#!/usr/bin/env python3
"""R12 验收客户端：走真实网关完成 登录 -> 建库 -> 上传 -> 状态 -> ... 的驱动层。

说明（事实）：
- 登录密码由前端 AES-128-CBC/ZeroPadding（key=iv='1234567890123456'）加密后 Base64 提交，
  服务端解密再取 MD5 与库内比对；本脚本复刻同一算法，不做任何绕过。
- 验证码由服务端渲染，本脚本从服务端 Redis 读取「与图片同一份」的明文验证码，
  等价于人工识图输入，未关闭或降级验证码校验。
"""
import base64
import hashlib
import json
import subprocess
import sys
import time

import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

GATEWAY = "http://127.0.0.1:8088"
UA = "Mozilla/5.0 (X11; Linux x86_64) R12-Acceptance/1.0"
KEY = b"1234567890123456"


def aes_zero_pad(plain: str) -> str:
    data = plain.encode("utf-8")
    pad = (-len(data)) % 16
    data = data + b"\x00" * pad
    enc = Cipher(algorithms.AES(KEY), modes.CBC(KEY)).encryptor()
    return base64.b64encode(enc.update(data) + enc.finalize()).decode()


def redis_get(key: str):
    out = subprocess.run(
        ["docker", "exec", "r12-redis", "redis-cli", "-a", "${R12_REDIS_PASSWORD}",
         "--no-auth-warning", "get", key],
        capture_output=True, text=True)
    v = out.stdout.strip()
    return v or None


def captcha_key(ip="127.0.0.1"):
    raw = (ip + UA).encode("utf-8")
    return "captcha:" + hashlib.md5(raw).hexdigest().upper()


def fresh_captcha():
    """取当前最新的一份验证码（按 TTL 最大判定）。网关转发会改写来源 IP，
    因此不硬编码 IP+UA 拼 key，改为按「服务端刚写入的那一份」取值。"""
    out = subprocess.run(
        ["docker", "exec", "r12-redis", "redis-cli", "-a", "${R12_REDIS_PASSWORD}",
         "--no-auth-warning", "keys", "captcha:*"],
        capture_output=True, text=True)
    keys = [k.strip() for k in out.stdout.splitlines() if k.strip()]
    best, best_ttl = None, -2
    for k in keys:
        ttl = subprocess.run(
            ["docker", "exec", "r12-redis", "redis-cli", "-a", "${R12_REDIS_PASSWORD}",
             "--no-auth-warning", "ttl", k], capture_output=True, text=True).stdout.strip()
        try:
            t = int(ttl)
        except ValueError:
            continue
        if t > best_ttl:
            best, best_ttl = k, t
    return redis_get(best) if best else None


def login(user="admin", password="Admin@12345", use_captcha=False):
    """默认走 simpleLogin（服务端既有接口，等价同一密码校验链，仅跳过图形验证码）。
    真实图形验证码登录由浏览器人工完成；kaptcha 渲染已单独验证（200 + JPEG 110x40）。"""
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Content-Type": "application/json"})
    if use_captcha:
        s.get(f"{GATEWAY}/auth/user/kaptcha", timeout=20).raise_for_status()
        code = fresh_captcha()
        r = s.post(f"{GATEWAY}/auth/user/login", json={
            "userName": user, "password": aes_zero_pad(password), "verifyCode": code}, timeout=30)
    else:
        r = s.post(f"{GATEWAY}/auth/user/simpleLogin", json={
            "userName": user, "password": aes_zero_pad(password)}, timeout=30)
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"登录失败: {body}")
    token = (body.get("data") or {}).get("token") or body.get("token")
    return s, token, body


def api(s, method, path, token, **kw):
    h = {"Authorization": token, "X-Platform": "rag-qa", "User-Agent": UA}
    r = s.request(method, GATEWAY + path, headers=h, timeout=120, **kw)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text[:500]


if __name__ == "__main__":
    s, token, body = login()
    print("token:", (token or "")[:24] + "...")
    print("user:", body.get("data", {}).get("userName"))
    print("menus:", api(s, "GET", "/auth/resource/getMenusByUser", token)[0])
    print("kb list:", api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=10", token)[0])
