#!/usr/bin/env python
"""图重建常驻进程：把调度器 + 租约 + 指标 + 告警接成一个能交给 systemd 的服务。

之前这些能力都只存在于演练脚本里：演练跑完进程就退出，没人守护、没有端点、没有优雅停机。
这个入口把它们装成一个**长驻**进程：

- 循环：`RebuildScheduler.run(stop_event)`，收到 SIGTERM/SIGINT 在下一个检查点退出；
- 多实例：`--lease-backend file|mysql`，拿不到租约就只跟随、不构建；
- 观测：`/healthz`（进程活着）与 `/metrics`（Prometheus 文本，标准库实现，不引依赖）；
- 告警：`--alert-webhook` 时走 `WebhookAlertSink`（永不抛，失败只记账）。

刻意不做的事：不从数据库拉待重建队列、不做灰度、不做鉴权。
这个进程只做"把已有快照按当前文档集重建并原子切换"，数据来源由 `--payloads` 显式给出。
"""

import argparse
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services/rag-alg/index_data_service"))


def load_docs(payloads):
    docs = []
    for path in payloads:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")),
                         "text": chunk["page_content"],
                         # 可见范围必须一路带下来：丢掉它，--scope 就会把所有人都当 public
                         "visibility": meta.get("visibility")})
    return docs


def resolve_lease_key(args) -> str:
    """租约键的粒度：global（默认，全库一个键）或 kb（每个知识库一个键）。

    kb 粒度下两个不同知识库可以**并行重建**，互不阻塞；代价是它们会同时写盘，
    所以 `--root` 必须按 kb 分开（用 `{kb}` 占位），否则两个进程会抢同一份快照目录。
    """
    if getattr(args, "lease_scope", "global") != "kb":
        return args.lease_key
    if "{kb}" not in (args.root or ""):
        raise SystemExit("--lease-scope kb 要求 --root 含 {kb} 占位（不同库必须写到不同快照目录）")
    return f"{args.lease_key}:{args.kb_id}"


def build_lease(args):
    if args.lease_backend == "mysql":
        from graph_engine_adapter.lease_mysql import MySqlLease, make_pymysql_factory

        env = os.environ
        factory = make_pymysql_factory(
            host=env["LLMKE_LEASE_MYSQL_HOST"],
            port=int(env.get("LLMKE_LEASE_MYSQL_PORT", "3306")),
            user=env["LLMKE_LEASE_MYSQL_USER"], password=env["LLMKE_LEASE_MYSQL_PASSWORD"],
            database=env["LLMKE_LEASE_MYSQL_DB"])
        lease = MySqlLease(factory, owner=args.owner, ttl=args.lease_ttl,
                           lease_key=resolve_lease_key(args))
        # 建表失败不在启动期退出：数据库不可用正是"要发出告警"的场景，
        # 在这里 SystemExit 等于"故障时最该报警的时候进程直接不启动"。
        # 后续 acquire 会走 LEASE_ERROR 路径，由调度器计数并告警。
        try:
            lease.ensure_schema()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] 租约建表失败，继续以失败态运行：{type(exc).__name__}: {exc}",
                  file=sys.stderr)
        return lease
    from graph_engine_adapter.lease import FileLease

    if not args.lease:
        raise SystemExit("--lease-backend file 需要 --lease <path>")
    # 文件租约的 kb 粒度落在**不同文件**上：同一个文件里换 key 等于没隔离（mkdir 互斥）。
    path = args.lease
    if getattr(args, "lease_scope", "global") == "kb":
        resolve_lease_key(args)          # 复用占位校验，避免两库写同一目录
        path = f"{args.lease}-{args.kb_id}"
    return FileLease(path, owner=args.owner, ttl=args.lease_ttl)


def build_alert_sink(args):
    """按参数装配告警出口：群机器人通道优先，其次通用 webhook，都没有返回 None。

    secret 只从**环境变量**读（`--alert-secret-env` 指定变量名）：把密钥写在命令行上，
    `ps` 与 shell history 都会留底，等于把告警通道的钥匙贴出去。
    """
    if getattr(args, "alert_channel", None):
        from graph_engine_adapter.alert_channels import make_channel

        if not getattr(args, "alert_url", None):
            raise SystemExit("--alert-channel 需要 --alert-url")
        secret = None
        if args.alert_channel == "dingtalk":
            secret = os.environ.get(args.alert_secret_env or "")
            if not secret:
                raise SystemExit(
                    f"钉钉通道需要签名密钥：请设置环境变量 {args.alert_secret_env}")
        return make_channel(args.alert_channel, args.alert_url, secret=secret)
    if getattr(args, "alert_webhook", None):
        from graph_engine_adapter.alert_sink import WebhookAlertSink
        return WebhookAlertSink(args.alert_webhook)
    return None


def build_quota(args):
    """按需构造跨实例配额（MySQL 原子计数）。

    **失败时 fail-open 并大声告警**：配额是保护措施，不是正确性前提。
    数据库不可用时若一律拒绝，会把"配额库抖动"升级成"所有重建被拒"——
    比没有配额更糟。这里返回 None 等于"本实例不限额"，必须在日志里说清楚。
    """
    limit = float(getattr(args, "quota_limit", 0) or 0)
    if limit <= 0:
        return None
    env = os.environ
    need = ("LLMKE_LEASE_MYSQL_HOST", "LLMKE_LEASE_MYSQL_USER",
            "LLMKE_LEASE_MYSQL_PASSWORD", "LLMKE_LEASE_MYSQL_DB")
    missing = [k for k in need if not env.get(k)]
    if missing:
        print(f"[warn] 配额已配置但缺少环境变量 {missing}，本实例不限额", file=sys.stderr)
        return None
    from graph_engine_adapter.lease_mysql import make_pymysql_factory
    from graph_engine_adapter.quota_shared import SharedQuotaCounter, ensure_schema

    factory = make_pymysql_factory(host=env["LLMKE_LEASE_MYSQL_HOST"],
                                   port=int(env.get("LLMKE_LEASE_MYSQL_PORT", "3306")),
                                   user=env["LLMKE_LEASE_MYSQL_USER"],
                                   password=env["LLMKE_LEASE_MYSQL_PASSWORD"],
                                   database=env["LLMKE_LEASE_MYSQL_DB"])
    try:
        ensure_schema(factory)
        counter = SharedQuotaCounter(factory, limit=limit,
                                     window_s=float(getattr(args, "quota_window_s", 1.0)))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 配额库不可用（{type(exc).__name__}: {exc}），本实例不限额", file=sys.stderr)
        return None
    return _QuotaAdapter(counter, getattr(args, "kb_id", "default"))


class _QuotaAdapter:
    """把 SharedQuotaCounter 包成 `take(tenant) -> {allowed, retry_after_s}`，
    并允许请求自带 kb（多库共用一个 worker 时按请求里的 kb 计费）。"""

    def __init__(self, counter, default_tenant):
        self.counter = counter
        self.default_tenant = default_tenant

    def take(self, tenant=None):
        return self.counter.take(tenant or self.default_tenant)


def make_handler(sched, lease, guard=None, metric_labels=None,
                 coord=None, quota=None, request_token=None):
    """`metric_labels` 必须由调用方传进来：handler 在工厂里定义，
    它**看不到** main() 的局部变量（这里曾直接引用 `args`，一请求 /metrics 就 NameError）。"""
    from graph_engine_adapter.metrics import render_with_lease

    class Handler(BaseHTTPRequestHandler):
        def _deny(self, reason):
            body = json.dumps({"status": "denied", "reason": reason}).encode()
            self.send_response(401 if "TOKEN" in reason else 403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            # /healthz 不鉴权（探活用），/metrics 可鉴权
            if self.path.startswith("/metrics") and guard is not None:
                allowed, reason = guard(dict(self.headers), self.client_address[0])
                if not allowed:
                    self._deny(reason)
                    return
            if self.path in ("/healthz", "/health"):
                body = json.dumps({"status": "ok", "owner": getattr(sched, "owner", None),
                                   "fencing": sched.lease_fencing}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path.startswith("/metrics"):
                text = render_with_lease(sched, lease, metric_labels).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Content-Length", str(len(text)))
                self.end_headers()
                self.wfile.write(text)
                return
            self.send_error(404)

        # ---------- POST /rebuild：真实请求入口（配额在这里生效） ----------
        def _json(self, code, payload, extra_headers=None):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            if not self.path.startswith("/rebuild"):
                self.send_error(404)
                return
            if request_token:
                if self.headers.get("Authorization", "") != f"Bearer {request_token}":
                    self._json(401, {"status": "UNAUTHORIZED"})
                    return
            tenant = self.headers.get("X-KB-Id")
            if not tenant:
                from urllib.parse import parse_qs, urlparse
                tenant = (parse_qs(urlparse(self.path).query).get("kb") or [None])[0]
            if quota is not None:
                decision = quota.take(tenant)
                if not decision.get("allowed"):
                    retry = decision.get("retry_after_s")
                    headers = {"Retry-After": str(max(1, int(retry or 1)))} if retry else {}
                    self._json(429, {"status": "TENANT_QUOTA", "tenant": tenant,
                                     "retry_after_s": retry,
                                     "hint": "该知识库的配额已用尽，稍后重试"}, headers)
                    return
            if coord is None:
                self._json(503, {"status": "NOT_READY"})
                return
            got = coord.request("api", [])
            if got.get("status") == "BACKPRESSURE":
                self._json(429, {"status": "BACKPRESSURE", "pending": got.get("pending"),
                                 "hint": "重建积压已满，先排空再上传"})
                return
            self._json(202, {"status": "QUEUED", "pending": got.get("pending"),
                             "tenant": tenant or "default"})

        def log_message(self, *args):
            return None

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="快照根目录（含 pointer.json）")
    ap.add_argument("--payloads", nargs="+", required=True, help="当前文档投影（json）")
    ap.add_argument("--lease-backend", choices=["file", "mysql"], default="file")
    ap.add_argument("--lease", default=None)
    ap.add_argument("--lease-key", default="rebuild")
    ap.add_argument("--scope", default=None,
                    help="按可见范围建索引：只收 visibility 含该范围（或 public）的文档；"
                         "root 必须含 {scope}，否则多个范围会写同一目录")
    ap.add_argument("--lease-scope", choices=["global", "kb"], default="global",
                    help="global=全库单租约；kb=每知识库一个租约（可并行重建，需 --root 含 {kb}）")
    ap.add_argument("--kb-id", default="default", help="知识库标识，用于灰度策略判定")
    ap.add_argument("--canary-file", default=None,
                    help="灰度策略文件（JSON）；每次重建前重读，改文件即回退，不用重启")
    ap.add_argument("--lease-ttl", type=float, default=120.0)
    ap.add_argument("--owner", default=f"{os.uname().nodename}:{os.getpid()}")
    ap.add_argument("--metrics-port", type=int, default=0, help="0 = 不监听（只写文件）")
    ap.add_argument("--metrics-out", default=None)
    ap.add_argument("--request-token", default=None,
                    help="POST /rebuild 的 Bearer token（不配则仅本机可用）")
    ap.add_argument("--quota-limit", type=float, default=0,
                    help="每个知识库每窗口允许的重建请求数；0=不限额")
    ap.add_argument("--quota-window-s", type=float, default=1.0)
    ap.add_argument("--metrics-label-kb", action="store_true",
                    help="指标带 kb=<kb-id> 标签：一个 worker 服务一个库时，面板上才能按库切片")
    ap.add_argument("--metrics-token", default=None,
                    help="/metrics 的 Bearer token（不配则不鉴权，仅建议内网）")
    ap.add_argument("--metrics-allow-ip", action="append", default=[],
                    help="/metrics 允许的客户端 IP，可重复；配了就先判 IP")
    ap.add_argument("--alert-webhook", default=None,
                    help="通用 JSON webhook（旧方式，保留兼容）")
    ap.add_argument("--alert-channel", choices=["wecom", "dingtalk"], default=None,
                    help="群机器人通道；与 --alert-webhook 二选一")
    ap.add_argument("--alert-url", default=None,
                    help="通道地址（wecom 带 key，dingtalk 带 access_token）")
    ap.add_argument("--alert-secret-env", default="LLMKE_ALERT_SECRET",
                    help="钉钉签名密钥所在的**环境变量名**（不把密钥写进命令行，避免进 ps/历史）")
    ap.add_argument("--debounce", type=float, default=0.5)
    ap.add_argument("--idle-poll", type=float, default=1.0)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--enqueue-on-start", action="store_true",
                    help="启动时立刻请求一次重建（默认不请求，只等外部触发）")
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    from graph_engine_adapter.alert_sink import WebhookAlertSink
    from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    from graph_engine_adapter.fence import FenceState
    from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator
    from graph_engine_adapter.rebuild_scheduler import RebuildScheduler

    if "{kb}" in args.root:
        args.root = args.root.replace("{kb}", args.kb_id)
    if args.scope:
        if "{scope}" not in args.root:
            raise SystemExit("--scope 要求 --root 含 {scope}（不同范围必须写不同快照目录）")
        args.root = args.root.replace("{scope}", args.scope)

    docs = load_docs(args.payloads)
    if args.scope:
        # 构建期隔离：不可见的文档**不进这个索引**，而不是建完再过滤。
        from graph_engine_adapter.partition import build_plan
        docs = build_plan(docs, [args.scope])[args.scope]
    fence = FenceState()
    lease = build_lease(args)

    def engine_at(target):
        return HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                              embedding_base_url=args.embed)

    def full_build(items, target):
        return engine_at(target).build([d["text"] for d in items])

    def delta_apply(target, texts):
        return engine_at(target).apply_delta(texts)

    def build_once(batch):
        # 每次重建前重读灰度策略：改文件即回退，不需要重启进程。
        from graph_engine_adapter.canary import load as load_policy
        from graph_engine_adapter.rebuild import rebuild_by_policy
        policy = load_policy(args.canary_file or os.environ.get("LLMKE_CANARY_FILE"))
        result = rebuild_by_policy(args.root, fence, docs, args.kb_id, policy,
                                   full_build, delta_apply,
                                   fencing=sched.lease_fencing)
        return {"status": result["status"], "mode": result.get("effective_mode"),
                "documents": (result.get("current") or {}).get("documents")}

    coord = RebuildCoordinator(build_once)
    sink = build_alert_sink(args)
    on_alert = (lambda event: sink(event)) if sink else None
    sched = RebuildScheduler(coord, debounce=args.debounce, idle_poll=args.idle_poll,
                             lease=lease, on_alert=on_alert, alert_every_s=60.0)
    sched.owner = args.owner

    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_a: stop.set())

    guard = None
    if args.metrics_token or args.metrics_allow_ip:
        from graph_engine_adapter.metrics_auth import MetricGuard
        guard = MetricGuard(token=args.metrics_token, allow_ips=args.metrics_allow_ip)

    server = None
    if args.metrics_port:
        server = ThreadingHTTPServer(("127.0.0.1", args.metrics_port),
                                     make_handler(
                                         sched, lease, guard,
                                         {"kb": args.kb_id} if args.metrics_label_kb else None,
                                         coord=coord, quota=build_quota(args),
                                         request_token=args.request_token))
        threading.Thread(target=server.serve_forever, daemon=True).start()

    if args.enqueue_on_start:
        coord.request("startup", files=sorted({d["file_id"] for d in docs}))

    started = time.time()
    print(json.dumps({"event": "start", "owner": args.owner,
                      "pid": os.getpid(), "docs": len(docs),
                      "metrics_port": args.metrics_port,
                      "lease": args.lease_backend, "lease_key": args.lease_key,
                      "metrics_auth": bool(guard)},
                     ensure_ascii=False), flush=True)

    out = sched.run(stop)
    if server is not None:
        server.shutdown()
    if args.metrics_out:
        from graph_engine_adapter.metrics import render_with_lease
        with open(args.metrics_out, "w", encoding="utf-8") as fh:
            labels = {"kb": args.kb_id} if args.metrics_label_kb else None
            fh.write(render_with_lease(sched, lease, labels))
    try:
        lease.release()
    except Exception:  # noqa: BLE001
        pass

    print(json.dumps({"event": "stop", "uptime_s": round(time.time() - started, 1),
                      "cycles": out.get("cycles"), "stats": sched.stats()},
                     ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
