#!/usr/bin/env python
"""多副本并发配额：3 个**独立进程**各起一个 /rebuild 入口，共用同一个 MySQL 计数器。

单进程并发只能证明"进程内没并发问题"；多副本时每个进程有自己的内存与连接，
唯一共享的是数据库。要证明"3 副本总量不是 3×limit"，必须在多个进程里同时压。

判据：
1. 三个进程里放行总数 == limit（不是 3×limit）；
2. 每个进程都至少被命中一次（否则等于只压了一个进程）；
3. 库里该窗口 used == limit；
4. 被拒的都是 429，没有连接错误（连接错误会让结论不可信）。
"""

import argparse
import json
import multiprocessing as mp
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


def _node(port_queue, stop_event, tenant, limit, window_s, conn_kwargs):
    """子进程：独立连接 + 独立计数器 + 独立 HTTP server。"""
    from graph_engine_adapter.lease_mysql import make_pymysql_factory
    from graph_engine_adapter.quota_shared import SharedQuotaCounter

    import v2_graph_worker as worker

    factory = make_pymysql_factory(**conn_kwargs)
    counter = SharedQuotaCounter(factory, limit=limit, window_s=window_s)

    class Sched:
        owner = "node"
        lease_fencing = 1
        lease = None

        def stats(self):
            return {}

    class Coord:
        def request(self, reason, files=None):
            return {"status": "QUEUED", "pending": 1}

    handler = worker.make_handler(Sched(), None, None, None, coord=Coord(),
                                  quota=worker._QuotaAdapter(counter, tenant),
                                  request_token=None)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.request_queue_size = 64
    port_queue.put(httpd.server_port)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    stop_event.wait()
    httpd.shutdown()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", type=int, default=3)
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--requests", type=int, default=30)
    ap.add_argument("--window-s", type=float, default=60.0)
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
    from graph_engine_adapter.quota_shared import ensure_schema

    conn_kwargs = {"host": env["LLMKE_LEASE_MYSQL_HOST"],
                   "port": int(env.get("LLMKE_LEASE_MYSQL_PORT", "3306")),
                   "user": env["LLMKE_LEASE_MYSQL_USER"],
                   "password": env["LLMKE_LEASE_MYSQL_PASSWORD"],
                   "database": env["LLMKE_LEASE_MYSQL_DB"]}
    factory = make_pymysql_factory(**conn_kwargs)
    ensure_schema(factory)

    # 租户名必须**每次唯一**：用秒级时间戳时，同一秒内跑两次会共用窗口，
    # 第二次一开始就 used=limit，全部被拒——看起来像"配额没共享"，其实是自己在打自己。
    tenant = f"drill-multi-{int(time.time() * 1000)}-{os.getpid()}"
    ctx = mp.get_context("fork")
    ports, procs, stop = [], [], ctx.Event()
    for _ in range(args.nodes):
        queue = ctx.Queue()
        proc = ctx.Process(target=_node,
                           args=(queue, stop, tenant, args.limit, args.window_s, conn_kwargs),
                           daemon=True)
        proc.start()
        ports.append(queue.get(timeout=30))
        procs.append(proc)

    results, errors, lock = [], [], threading.Lock()

    def fire(port):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/rebuild", data=b"{}",
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception as exc:  # noqa: BLE001
            code = -1
            with lock:
                errors.append(f"{type(exc).__name__}: {exc}")
        with lock:
            results.append((code, port))

    threads = [threading.Thread(target=fire, args=(ports[i % len(ports)],))
               for i in range(args.requests)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stop.set()
    for proc in procs:
        proc.join(timeout=10)
        if proc.is_alive():
            proc.terminate()

    accepted = [port for code, port in results if code == 202]
    denied = sum(1 for code, _ in results if code == 429)
    other = [code for code, _ in results if code not in (202, 429)]
    # 每个进程**收到**多少请求（含被拒）：证明流量确实分到了三个进程。
    # 不能要求"每个进程都拿到放行"，limit 很小时可能一个进程抢到全部放行——
    # 那是调度巧合，不是配额失效。
    per_node_requests = {str(port): sum(1 for _, p in results if p == port) for port in ports}
    per_node_accepted = {str(port): sum(1 for code, p in results if p == port and code == 202)
                         for port in ports}

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

    problems = []
    if len(accepted) != args.limit:
        problems.append(f"三进程合计放行 {len(accepted)}，应为 {args.limit}"
                        f"（若为 {args.limit * args.nodes} 说明配额没有共享）")
    if denied != args.requests - args.limit:
        problems.append(f"拒绝 {denied} 条，应为 {args.requests - args.limit}")
    if other:
        problems.append(f"出现非 202/429 状态 {other[:5]}，错误样例 {errors[:2]}")
    if used != args.limit:
        problems.append(f"库中 used={used}，应为 {args.limit}")
    if any(count == 0 for count in per_node_requests.values()):
        problems.append(f"有进程一次请求都没收到，压测没覆盖到它：{per_node_requests}")

    report = {"schema": "llmke.quota-multinode-drill.v1", "tenant": tenant,
              "nodes": args.nodes, "limit": args.limit, "requests": args.requests,
              "accepted": len(accepted), "denied": denied, "used_in_db": used,
              "per_node_accepted": per_node_accepted,
              "per_node_requests": per_node_requests, "problems": problems,
              "status": "PASS" if not problems else "FAIL"}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
