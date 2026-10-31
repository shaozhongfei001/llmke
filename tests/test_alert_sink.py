"""告警通道：投递成功/重试/非 2xx/去重/扇出，全部用注入桩，不碰网络、不真等。

关键的不是"不抛异常"这一条（那只要 `except: pass` 就过了），而是：
抛出失败**必须**变成返回值 False + `failed`/`last_error`/`last_status` 的可见记账，
否则运维只会看到"调度器说 alerts_sent=6"，然后什么都没收到。
"""

import json

import pytest

from graph_engine_adapter.alert_sink import SCHEMA, CompositeSink, WebhookAlertSink


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Response:
    def __init__(self, status):
        self.status = status


class Post:
    """记录每次调用的桩；`results` 依次出队，用尽后重复最后一个。"""

    def __init__(self, results=None):
        self.calls = []
        self.results = list(results or [Response(202)])

    def __call__(self, url, body, timeout):
        self.calls.append({"url": url, "body": body, "timeout": timeout})
        index = min(len(self.calls) - 1, len(self.results) - 1)
        result = self.results[index]
        if isinstance(result, Exception):
            raise result
        return result

    @property
    def bodies(self):
        return [json.loads(call["body"].decode("utf-8")) for call in self.calls]


def make(post, clock=None, **kw):
    sleeps = []
    kw.setdefault("sleep", sleeps.append)
    kw.setdefault("clock", clock or Clock())
    sink = WebhookAlertSink("https://hooks.example/alert", post=post, **kw)
    return sink, sleeps


EVENT = {"schema": "llmke.graph-engine.alert.v1", "kind": "LEASE_UNAVAILABLE",
         "at": 1000.0, "error": "OSError: refused", "consecutive": 3}


# ---------------------------------------------------------------- 成功路径
def test_success_posts_once_and_reports_true():
    post = Post([Response(204)])
    sink, sleeps = make(post)

    assert sink(EVENT) is True

    assert len(post.calls) == 1
    assert sleeps == []
    stats = sink.stats()
    assert (stats["sent"], stats["failed"], stats["attempts"]) == (1, 0, 1)
    assert stats["last_status"] == 204
    assert stats["last_error"] is None


def test_body_is_the_event_verbatim_and_event_is_not_mutated():
    post = Post([Response(200)])
    sink, _ = make(post)
    event = {"kind": "LEASE_SLOW", "elapsed_s": 4.2}

    sink(event)

    body = post.bodies[0]
    assert body["kind"] == "LEASE_SLOW" and body["elapsed_s"] == 4.2
    assert body["schema"] == SCHEMA          # 缺 schema 时补上
    assert "schema" not in event             # 但绝不改动调用方的 dict
    assert post.calls[0]["timeout"] == 3.0


def test_event_schema_wins_over_sink_schema():
    post = Post()
    sink, _ = make(post)
    sink(dict(EVENT))
    assert post.bodies[0]["schema"] == "llmke.graph-engine.alert.v1"


# ---------------------------------------------------------------- 失败与重试
def test_failure_retries_with_exponential_backoff():
    post = Post([Response(500)])
    sink, sleeps = make(post, retries=2, backoff=0.5)

    assert sink(EVENT) is False

    assert len(post.calls) == 3               # 1 次 + 2 次重试
    assert sleeps == [0.5, 1.0]               # 指数退避
    stats = sink.stats()
    assert (stats["sent"], stats["failed"], stats["attempts"]) == (0, 1, 3)
    assert stats["last_status"] == 500
    assert stats["last_error"] == "HTTP 500"


def test_retry_stops_as_soon_as_one_attempt_succeeds():
    post = Post([Response(503), Response(200)])
    sink, sleeps = make(post, retries=3, backoff=0.5)

    assert sink(EVENT) is True

    assert len(post.calls) == 2
    assert sleeps == [0.5]
    stats = sink.stats()
    assert (stats["sent"], stats["failed"], stats["attempts"]) == (1, 0, 2)
    assert stats["last_status"] == 200


def test_retries_zero_means_single_attempt():
    post = Post([Response(500)])
    sink, sleeps = make(post, retries=0)
    assert sink(EVENT) is False
    assert len(post.calls) == 1 and sleeps == []
    assert sink.stats()["attempts"] == 1


def test_transport_exception_is_swallowed_but_recorded():
    post = Post([OSError("connection refused")])
    sink, _ = make(post, retries=1)

    assert sink(EVENT) is False               # 不抛
    assert len(post.calls) == 2
    stats = sink.stats()
    assert stats["failed"] == 1
    assert "connection refused" in stats["last_error"]
    assert stats["last_status"] is None       # 没拿到状态码就别编一个


def test_unserializable_event_fails_without_raising_and_without_posting():
    post = Post()
    sink, _ = make(post)

    assert sink({"kind": "BROKEN", "blob": b"\x00\x01"}) is False

    assert post.calls == []
    stats = sink.stats()
    assert stats["failed"] == 1 and stats["attempts"] == 0
    assert stats["last_error"].startswith("serialize: TypeError")


def test_unverifiable_response_is_treated_as_failure():
    class Opaque:
        pass

    post = Post([Opaque()])
    sink, _ = make(post, retries=0)
    assert sink(EVENT) is False
    assert "unverified" in sink.stats()["last_error"]


# ---------------------------------------------------------------- 去重
def test_same_kind_is_deduped_within_window():
    clock = Clock()
    post = Post()
    sink, _ = make(post, clock=clock, dedupe_window_s=30.0)

    assert sink(EVENT) is True
    clock.advance(10)
    assert sink(EVENT) is True                # 窗口内重复：算已处理，不算失败

    assert len(post.calls) == 1
    stats = sink.stats()
    assert stats["deduped"] == 1
    assert stats["failed"] == 0 and stats["sent"] == 1


def test_dedupe_expires_after_window_and_different_kind_is_independent():
    clock = Clock()
    post = Post()
    sink, _ = make(post, clock=clock, dedupe_window_s=30.0)

    sink(EVENT)
    clock.advance(31)
    sink(EVENT)                                          # 过期 → 再发
    sink({**EVENT, "kind": "LEASE_SLOW"})                # 不同 kind → 不受影响

    assert len(post.calls) == 3
    assert sink.stats()["deduped"] == 0


def test_dedupe_window_disabled_sends_every_time():
    post = Post()
    sink, _ = make(post, dedupe_window_s=0)
    sink(EVENT)
    sink(EVENT)
    assert len(post.calls) == 2
    assert sink.stats()["deduped"] == 0


def test_failed_delivery_also_arms_the_dedupe_window():
    """webhook 挂掉时不能在窗口内反复重投：失败也打点，失败靠 failed/last_error 暴露。"""
    clock = Clock()
    post = Post([Response(500)])
    sink, _ = make(post, clock=clock, retries=1, backoff=0.5)

    sink(EVENT)                       # 2 次尝试，全失败
    clock.advance(5)
    sink(EVENT)                       # 窗口内：不再打网络

    assert len(post.calls) == 2
    assert sink.stats()["deduped"] == 1
    assert sink.stats()["failed"] == 1


# ---------------------------------------------------------------- 扇出
def test_composite_calls_every_sink_even_when_one_fails():
    ok_post = Post([Response(200)])
    bad_post = Post([Response(500)])
    ok_sink, _ = make(ok_post, dedupe_window_s=0)
    bad_sink, _ = make(bad_post, dedupe_window_s=0, retries=0)

    composite = CompositeSink([bad_sink, ok_sink])
    assert composite(EVENT) is False            # 不是全部成功

    assert len(bad_post.calls) == 1
    assert len(ok_post.calls) == 1              # 失败通道没有拦住成功通道
    stats = composite.stats()
    assert stats["calls"] == 1 and stats["any_failed"] == 1
    assert [r["ok"] for r in stats["results"]] == [False, True]
    assert stats["results"][1]["stats"]["sent"] == 1


def test_composite_returns_true_when_all_succeed_and_counts_deduped():
    a, _ = make(Post(), dedupe_window_s=0)
    b, _ = make(Post(), dedupe_window_s=0)
    composite = CompositeSink([a, b])

    assert composite(EVENT) is True
    assert [r["ok"] for r in composite.stats()["results"]] == [True, True]
    assert composite.stats()["all_ok"] == 1


def test_composite_swallows_sink_exceptions_and_marks_that_branch_failed():
    class Boom:
        def __call__(self, event):
            raise RuntimeError("sink 坏了")

    ok_post = Post()
    ok_sink, _ = make(ok_post, dedupe_window_s=0)
    composite = CompositeSink([Boom(), ok_sink])

    assert composite(EVENT) is False
    assert len(ok_post.calls) == 1
    results = composite.stats()["results"]
    assert results[0]["ok"] is False and "sink 坏了" in results[0]["error"]


def test_composite_with_no_sinks_fails_closed():
    assert CompositeSink([])(EVENT) is False


# ---------------------------------------------------------------- 构造校验
def test_constructor_rejects_invalid_arguments():
    with pytest.raises(ValueError):
        WebhookAlertSink("")
    with pytest.raises(ValueError):
        WebhookAlertSink("https://x", retries=-1)


def test_real_http_post_is_counted_as_success(monkeypatch):
    """真实 HTTP 200 必须记 sent，而不是"未确认响应"重试到 failed。

    这条是补漏：之前所有用例都注入 post 桩（返回 int/None），而从没有人跑过
    `_default_post` 与 `_status_of` 的真实组合——结果每次 200 都被判失败、
    重试 3 次、`failed=1`，明明投递成功却在监控上显示失败。
    """
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            hits.append(self.rfile.read(length))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, *args):
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        from graph_engine_adapter.alert_sink import WebhookAlertSink

        sink = WebhookAlertSink(f"http://127.0.0.1:{server.server_port}/hook",
                                timeout=2.0, retries=2, sleep=lambda s: None)
        assert sink({"kind": "LEASE_UNAVAILABLE"}) is True
        stats = sink.stats()
        assert stats["sent"] == 1
        assert stats["failed"] == 0
        assert stats["attempts"] == 1          # 成功就不该重试
        assert len(hits) == 1
    finally:
        server.shutdown()
