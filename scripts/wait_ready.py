#!/usr/bin/env python
"""systemd `ExecStartPre` 用的依赖就绪探针：依赖没起来就让 unit 启动失败，而不是反复崩溃重启。

为什么需要它：服务自己连不上 Nacos/MySQL 时会**启动即崩**，`Restart=always` 于是变成
"每 5 秒崩一次"的循环，日志被刷满、真正的原因埋在栈里、StartLimit 还会把 unit 打成 failed。

三种探针（都只做"能不能用"，不做业务校验）：
- `tcp HOST PORT`：三次握手成功即就绪（连不上会明确报 ECONNREFUSED/timeout）；
- `http URL`：返回 2xx/3xx 视为就绪；
- `nacos`：拉一次配置（能拉到说明注册中心可用，比只看端口更接近真实依赖）。

退出码：0 就绪、2 超时（systemd 会据此判定 unit 启动失败，不进入 Restart 循环）。
"""

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.request


def probe_tcp(host, port, timeout):
    with socket.create_connection((host, port), timeout=timeout):
        return True, f"tcp {host}:{port} 可连接"


def probe_http(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        code = getattr(response, "status", 200)
        return 200 <= code < 400, f"http {url} -> {code}"


def probe_nacos(timeout):
    base = (f"http://{__import__('os').environ.get('NACOS_SERVER_ADDRESS', '127.0.0.1:18848')}"
            .replace("http://http://", "http://"))
    data_id = __import__('os').environ.get("NACOS_DATA_ID", "alg_doc_config_py")
    url = f"{base}/nacos/v1/cs/configs?dataId={data_id}&group=DEFAULT_GROUP&tenant="
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8", "replace")
    ok = bool(body.strip())
    return ok, f"nacos {data_id} -> {len(body)} 字节" if ok else f"nacos {data_id} 返回空配置"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["tcp", "http", "nacos"])
    ap.add_argument("target", nargs="*", help="tcp: HOST PORT；http: URL")
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--per-try", type=float, default=3.0, help="单次探测超时")
    args = ap.parse_args(argv)

    if args.kind == "tcp" and len(args.target) != 2:
        raise SystemExit("tcp 需要 HOST PORT")
    if args.kind == "http" and len(args.target) != 1:
        raise SystemExit("http 需要 URL")

    deadline = time.time() + args.timeout
    attempt, last = 0, ""
    while time.time() < deadline:
        attempt += 1
        try:
            if args.kind == "tcp":
                ok, last = probe_tcp(args.target[0], int(args.target[1]), args.per_try)
            elif args.kind == "http":
                ok, last = probe_http(args.target[0], args.per_try)
            else:
                ok, last = probe_nacos(args.per_try)
        except urllib.error.HTTPError as exc:
            ok, last = False, f"http 错误码 {exc.code}"
        except Exception as exc:  # noqa: BLE001
            ok, last = False, f"{type(exc).__name__}: {exc}"
        if ok:
            print(json.dumps({"status": "READY", "attempt": attempt, "detail": last},
                             ensure_ascii=False), flush=True)
            return 0
        print(json.dumps({"status": "WAITING", "attempt": attempt, "detail": last},
                         ensure_ascii=False), flush=True)
        time.sleep(args.interval)

    print(json.dumps({"status": "TIMEOUT", "attempts": attempt, "detail": last,
                      "hint": "依赖未就绪，unit 不应进入 Restart 循环；先查依赖自身日志"},
                     ensure_ascii=False), flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
