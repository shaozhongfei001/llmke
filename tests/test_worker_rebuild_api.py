"""POST /rebuild：真实请求入口，配额在这里生效。

用真 HTTPServer + 真 urllib（不打桩 urllib），只把 coordinator/quota/clock 注入。
判据全是状态码与响应体——这条链路的价值就在"调用方拿到什么"。
"""

import importlib.util
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "worker_mod", os.path.join(REPO, "scripts", "v2_graph_worker.py"))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class Sched:
    owner = "test"
    lease_fencing = 1
    lease = None

    def stats(self):
        return {}


class Coord:
    def __init__(self, status="QUEUED", pending=1):
        self.status, self.pending = status, pending
        self.calls = []

    def request(self, reason, files=None):
        self.calls.append((reason, files))
        if self.status == "BACKPRESSURE":
            return {"status": "BACKPRESSURE", "pending": self.pending}
        return {"status": "QUEUED", "pending": self.pending}


class Quota:
    def __init__(self, allowed=True, retry=2.0):
        self.allowed, self.retry, self.tenants = allowed, retry, []

    def take(self, tenant=None):
        self.tenants.append(tenant)
        return {"allowed": self.allowed, "retry_after_s": None if self.allowed else self.retry}


class Server:
    def __init__(self, **kwargs):
        handler = worker.make_handler(Sched(), None, None, None, **kwargs)
        self.httpd = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_port
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def post(self, path="/rebuild", token=None, kb=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=b"{}", method="POST")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        if kb:
            req.add_header("X-KB-Id", kb)
        def _body(raw):
            try:
                return json.loads(raw or b"{}")
            except ValueError:
                return {}          # send_error 返回的是 HTML，不是我们的 JSON 契约

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, _body(resp.read()), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, _body(exc.read()), dict(exc.headers)

    def close(self):
        self.httpd.shutdown()


def test_rebuild_is_queued_with_202():
    srv = Server(coord=Coord())
    try:
        code, body, _ = srv.post()
        assert code == 202 and body["status"] == "QUEUED"
    finally:
        srv.close()


def test_quota_exhausted_returns_429_with_retry_after():
    srv = Server(coord=Coord(), quota=Quota(allowed=False, retry=3))
    try:
        code, body, headers = srv.post()
        assert code == 429 and body["status"] == "TENANT_QUOTA"
        assert headers.get("Retry-After") == "3"
    finally:
        srv.close()


def test_tenant_comes_from_header_then_query():
    q = Quota()
    srv = Server(coord=Coord(), quota=q)
    try:
        srv.post(kb="kb_7")
        srv.post(path="/rebuild?kb=kb_9")
        assert q.tenants == ["kb_7", "kb_9"]
    finally:
        srv.close()


def test_token_is_enforced_when_configured():
    srv = Server(coord=Coord(), request_token="t0ken")
    try:
        assert srv.post()[0] == 401
        assert srv.post(token="wrong")[0] == 401
        assert srv.post(token="t0ken")[0] == 202
    finally:
        srv.close()


def test_backpressure_maps_to_429():
    srv = Server(coord=Coord(status="BACKPRESSURE", pending=50))
    try:
        code, body, _ = srv.post()
        assert code == 429 and body["status"] == "BACKPRESSURE"
    finally:
        srv.close()


def test_quota_denied_does_not_touch_coordinator():
    """被配额拒掉的请求不能进重建队列——否则限流只是"晚一点被处理"。"""
    coord = Coord()
    srv = Server(coord=coord, quota=Quota(allowed=False))
    try:
        srv.post()
        assert coord.calls == []
    finally:
        srv.close()


def test_unknown_post_path_is_404():
    srv = Server(coord=Coord())
    try:
        assert srv.post(path="/nope")[0] == 404
    finally:
        srv.close()
