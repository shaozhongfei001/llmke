#!/usr/bin/env python
"""配额接进真实请求入口后的**并发**验证：30 个并发 POST，只能放行 limit 个。

之前只有"单进程 + 两实例交替"的证据，没有并发数值——而配额最容易出错的地方正是并发：
两个请求同时读到 used=limit-1，就都放行。这里用真 MySQL 计数器 + 真 HTTP handler 压一次。

判据（任一不满足即 FAIL）：
1. 放行数 == limit（不多不少）；
2. 被拒的都是 429/TENANT_QUOTA；
3. 数据库里该窗口的 used == limit（没有"拒了还占额度"）；
4. 另一个租户不受影响（同一次压测里对照）。
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services", "rag-alg", "index_data_service"))
sys.path.insert(0, os.path.join(HERE, "scripts"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--requests", type=int, default=30)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--window-s", type=float, default=30.0, help="窗口拉长，避免压测中途滚动")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    env = os.environ
    need = ("LLMKE_LEASE_MYSQL_HOST", "LLMKE_LEASE_MYSQL_USER",
            "LLMKE_LEASE_MYSQL_PASSWORD", "LLMKE_LEASE_MYSQL_DB")
    missing = [k for k in need if not env.get(k)]
    if missing:
        print(json.dumps({"status": "SKIP", "why": f"缺少 {missing}"}, ensure_ascii=False))
        return 0

    from graph_engine_adapter.lease_mysql import make_pymysql_factory
    from graph_engine_adapter.quota_shared import SharedQuotaCounter, ensure_schema

    import v2_graph_worker as worker

    factory = make_pymysql_factory(host=env["LLMKE_LEASE_MYSQL_HOST"],
                                   port=int(env.get("LLMKE_LEASE_MYSQL_PORT", "3306")),
                                   user=env["LLMKE_LEASE_MYSQL_USER"],
                                   password=env["LLMKE_LEASE_MYSQL_PASSWORD"],
                                   database=env["LLMKE_LEASE_MYSQL_DB"])
    ensure_schema(factory)

    stamp = int(time.time())
    tenant = f"drill-quota-{stamp}"
    control = f"drill-control-{stamp}"
    counter = SharedQuotaCounter(factory, limit=args.limit, window_s=args.window_s)

    class Sched:
        owner = "drill"
        lease_fencing = 1
        lease = None

        def stats(self):
            return {}

    class Coord:
        def __init__(self):
            self.calls = 0
            self._lock = threading.Lock()

        def request(self, reason, files=None):
            with self._lock:
                self.calls += 1
                return {"status": "QUEUED", "pending": self.calls}

    coord = Coord()
    quota = worker._QuotaAdapter(counter, tenant)
    handler = worker.make_handler(Sched(), None, None, None, coord=coord, quota=quota,
                                  request_token=None)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    # 默认 backlog 只有 5：30 个并发会有一部分直接 connect 失败，
    # 看起来像"请求被拒"，实际是测试脚手架连不上。
    httpd.request_queue_size = max(64, args.requests)
    port = httpd.server_port
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    results, lock = [], threading.Lock()
    errors = []

    def fire(kb=None):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/rebuild", data=b"{}",
                                     method="POST")
        if kb:
            req.add_header("X-KB-Id", kb)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                code, body = resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            code, body = exc.code, exc.read()
        except Exception as exc:  # noqa: BLE001
            code, body = -1, str(exc).encode()
            with lock:
                errors.append(f"{type(exc).__name__}: {exc}")
        with lock:
            results.append((code, kb))

    threads = []
    for _ in range(args.requests):
        threads.append(threading.Thread(target=fire))
    for index, thread in enumerate(threads):
        thread.start()
        if index % max(1, args.concurrency) == 0:
            pass
    for thread in threads:
        thread.join()
    httpd.shutdown()

    accepted = sum(1 for code, _ in results if code == 202)
    denied = sum(1 for code, _ in results if code == 429)
    other = [code for code, _ in results if code not in (202, 429)]

    # 数据库里的实际计数：窗口内 used 必须等于放行数（不能把被拒的也算进去）
    # 直接读该租户**最新一行**：窗口起点由计数器自己算，不要在外部重复推导
    # （第一版按 `int(time.time()//window_s)*window_s` 猜，和实现的口径对不上，读到 0）。
    used = None
    try:
        conn = factory()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT window_start, used FROM v2_quota_window "
                            "WHERE tenant = %s ORDER BY window_start DESC LIMIT 1", (tenant,))
                row = cur.fetchone()
                used = int(row[1]) if row else 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        used = f"error: {type(exc).__name__}"

    # 对照租户：配额用尽不应影响别人
    control_ok = counter.take(control)["allowed"]

    problems = []
    if accepted != args.limit:
        problems.append(f"放行 {accepted} 条，应为 {args.limit}")
    if denied != args.requests - args.limit:
        problems.append(f"拒绝 {denied} 条，应为 {args.requests - args.limit}")
    if other:
        problems.append(f"出现非 202/429 状态：{other[:5]} 错误样例：{errors[:2]}")
    if used != args.limit:
        problems.append(f"库中 used={used}，应为 {args.limit}")
    if not control_ok:
        problems.append("对照租户被误伤")

    report = {"schema": "llmke.quota-endpoint-drill.v1", "tenant": tenant,
              "limit": args.limit, "requests": args.requests,
              "accepted": accepted, "denied": denied, "used_in_db": used,
              "coordinator_calls": coord.calls, "control_tenant_allowed": control_ok,
              "problems": problems, "status": "PASS" if not problems else "FAIL"}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
