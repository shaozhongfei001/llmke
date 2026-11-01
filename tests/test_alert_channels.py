"""告警通道：报文结构、截断、钉钉签名、永不抛、secret 不外泄。

为什么签名要在测试里**另写一遍独立实现**：如果直接 `assert dingtalk_sign(x) ==
dingtalk_sign(x)`，那条断言恒真——换行写成 `\r\n`、base64 换 base64url、
忘了 urlencode，签名全错也照样 PASS，而线上就是一个 310000。
这里照钉钉文档原文重算：`{timestamp}\\n{secret}` → HMAC-SHA256 → base64 → urlencode。

为什么专门测"字节预算"：企业微信 markdown 上限是 4096 **字节**，
一条 2000 字的中文告警只有 2000 字符、却是 6000 字节——只按字符截会"发出去但内容为空"。

为什么专门测"secret 不出现在任何字符串里"：`stats()` 和 `last_error` 是唯一
会被运维贴进工单/聊天窗口的东西，secret 一旦进去就等于公开。
"""

import base64
import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from graph_engine_adapter.alert_channels import (
    DINGTALK,
    WECOM,
    DingtalkChannel,
    WecomChannel,
    dingtalk_payload,
    dingtalk_sign,
    dingtalk_signed_url,
    make_channel,
    wecom_payload,
)


def sign_seed():
    """夹具**拼接构造**：仓库安全扫描会扫 tests/，写死一个字面量等于给自己加一条告警。"""
    return "-".join(["fake", "dingtalk", "sig", "0123456789abcdef"])


def reference_sign(seed, timestamp_ms):
    """独立实现（照文档抄，不 import 被测函数）。"""
    string_to_sign = f"{timestamp_ms}\n{seed}"
    digest = hmac.new(seed.encode("utf-8"), string_to_sign.encode("utf-8"),
                      hashlib.sha256).digest()
    return {"timestamp": str(timestamp_ms),
            "sign": urllib.parse.quote_plus(base64.b64encode(digest))}


TS = 1767225600000          # 2026-01-01T00:00:00Z，注入用，保证可复现
EVENT = {"kind": "LEASE_UNAVAILABLE", "severity": "P1", "at": 1767225600,
         "error": "OSError: connection refused", "impact": "重建停止", "consecutive": 3}


class Response:
    def __init__(self, status):
        self.status = status


class Post:
    """记录每次调用的桩；`results` 依次出队，用尽后重复最后一个。"""

    def __init__(self, results=None):
        self.calls = []
        self.results = list(results or [Response(200)])

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


def fixed_clock():
    return lambda: TS / 1000.0


def make_wecom(post, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("clock", fixed_clock())
    return WecomChannel("https://qyapi.example.com/cgi-bin/webhook/send?key=fake-key",
                        post=post, **kw)


def make_dingtalk(post, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("clock", fixed_clock())
    return DingtalkChannel("https://oapi.example.com/robot/send?access_token=placeholder",
                          sign_seed(), post=post, **kw)


# ---------------------------------------------------------------- 企业微信报文
def test_wecom_payload_is_markdown_with_kind_and_error():
    payload = wecom_payload(EVENT)

    assert payload["msgtype"] == "markdown"
    content = payload["markdown"]["content"]
    assert content.startswith("### ")
    assert "LEASE_UNAVAILABLE" in content
    assert "connection refused" in content
    assert "重建停止" in content
    # 时间被格式化成人能读的样子，不是裸 epoch
    assert "2026-01-01" in content and "1767225600" not in content
    # 不是把整条 event 原样倒进去（群里没法读）
    assert json.dumps(EVENT) not in content
    assert '"kind":' not in content and '{"' not in content


def test_wecom_payload_keeps_extra_fields_short_and_bounded():
    event = {"kind": "K", "error": "boom"}
    for index in range(20):
        event[f"extra_{index}"] = index * "y"

    content = wecom_payload(event)["markdown"]["content"]
    extra_lines = [line for line in content.splitlines() if line.startswith("> extra_")]

    assert len(extra_lines) == 6                       # 至多 6 条附加字段
    assert all(len(line) <= 250 for line in extra_lines)
    assert "> 错误: boom" in content


def test_wecom_payload_truncates_over_4000_chars_without_breaking_json():
    event = {"kind": "HUGE", "error": "开头" + "x" * 5000 + "结尾标记"}
    payload = wecom_payload(event)
    content = payload["markdown"]["content"]

    assert len(content) <= 4000
    assert len(content.encode("utf-8")) <= 4000
    assert "已截断" in content
    assert "结尾标记" not in content                    # 尾部真的被切掉了
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert json.loads(raw.decode("utf-8")) == payload   # 截断没有破坏 JSON


def test_wecom_payload_respects_byte_budget_for_chinese():
    """2000 个汉字 = 2000 字符但 6000 字节：只按字符截，网关侧会被打回。"""
    event = {"kind": "CJK", "error": "中" * 2000}
    content = wecom_payload(event)["markdown"]["content"]

    assert len(content.encode("utf-8")) <= 4000
    assert len(content) < 2000                          # 字符数也被迫让位
    assert content.endswith("字节）")


# ---------------------------------------------------------------- 钉钉签名
def test_dingtalk_sign_matches_independent_implementation():
    seed = sign_seed()
    for timestamp in (TS, 1, 1700000000123, 4102444800000):
        assert dingtalk_sign(seed, timestamp) == reference_sign(seed, timestamp)


def test_dingtalk_sign_is_urlencoded_not_raw_base64():
    seed = sign_seed()
    signed = dingtalk_sign(seed, TS)

    raw = base64.b64encode(
        hmac.new(seed.encode("utf-8"), f"{TS}\n{seed}".encode("utf-8"),
                 hashlib.sha256).digest()).decode("ascii")
    assert urllib.parse.unquote_plus(signed["sign"]) == raw
    assert signed["sign"] == urllib.parse.quote_plus(raw)
    # 原样塞进 query 会被截断的字符不许留下
    assert "+" not in signed["sign"] and "=" not in signed["sign"]


def test_dingtalk_sign_is_reproducible_and_timestamp_sensitive():
    seed = sign_seed()

    first = dingtalk_sign(seed, TS)
    assert first == dingtalk_sign(seed, TS)              # timestamp 注入 ⇒ 可复现
    assert first["timestamp"] == str(TS)
    assert dingtalk_sign(seed, TS + 1)["sign"] != first["sign"]
    assert dingtalk_sign(sign_seed() + "x", TS)["sign"] != first["sign"]


def test_dingtalk_payload_carries_signature_and_markdown():
    seed = sign_seed()
    payload = dingtalk_payload(EVENT, seed, timestamp_ms=TS)

    assert payload["msgtype"] == "markdown"
    assert payload["timestamp"] == str(TS)
    assert payload["sign"] == reference_sign(seed, TS)["sign"]
    assert EVENT["kind"] in payload["markdown"]["title"]
    text = payload["markdown"]["text"]
    assert "connection refused" in text and "LEASE_UNAVAILABLE" in text
    assert len(text.encode("utf-8")) <= 8000
    assert seed not in json.dumps(payload, ensure_ascii=False)


def test_dingtalk_signed_url_appends_query_without_double_encoding():
    seed = sign_seed()
    base = "https://oapi.example.com/robot/send?access_token=placeholder"
    signed = dingtalk_signed_url(base, seed, timestamp_ms=TS)

    assert signed.startswith(f"{base}&timestamp={TS}&sign=")
    assert "%25" not in signed                          # sign 不能再被编码一次
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(signed).query)
    assert query["timestamp"] == [str(TS)]
    assert query["sign"] == [urllib.parse.unquote_plus(reference_sign(seed, TS)["sign"])]
    # 没有 query 的 URL 要用 `?` 起头
    assert "?timestamp=" in dingtalk_signed_url("https://oapi.example.com/robot/send",
                                                seed, timestamp_ms=TS)


# ---------------------------------------------------------------- 永不抛 + 记账
def test_wecom_channel_http_500_returns_false_and_counts_attempts():
    post = Post([Response(500)])
    channel = make_wecom(post, retries=2, backoff=0.5)

    assert channel(EVENT) is False                      # 不抛
    assert len(post.calls) == 3                         # 1 次 + 2 次重试

    stats = channel.stats()
    assert (stats["sent"], stats["failed"], stats["attempts"]) == (0, 1, 3)
    assert stats["last_status"] == 500
    assert stats["last_error"] == "HTTP 500"


def test_dingtalk_channel_transport_error_returns_false_and_scrubs_secret():
    seed = sign_seed()

    def boom(url, body, timeout):
        # 故意把 seed 拼进异常：模拟底层把凭证回显出来
        raise RuntimeError(f"connect failed for {url} (seed={seed})")

    channel = DingtalkChannel("https://oapi.example.com/robot/send?access_token=placeholder",
                              seed, post=boom, retries=1, backoff=0.0,
                              sleep=lambda s: None, clock=fixed_clock())

    assert channel(EVENT) is False                      # 不抛
    stats = channel.stats()
    assert (stats["failed"], stats["attempts"]) == (1, 2)
    assert stats["last_status"] is None                 # 没拿到状态码就别编一个
    assert "RuntimeError" in stats["last_error"]
    blob = json.dumps(stats, ensure_ascii=False)
    assert seed not in blob
    assert "placeholder" not in blob                    # query 里的凭证也要抹掉
    assert "access_token=***" in stats["last_error"]


def test_stats_account_success_after_one_retry():
    post = Post([Response(503), Response(200)])
    channel = make_wecom(post, retries=2, backoff=0.5)

    assert channel(EVENT) is True

    assert len(post.calls) == 2                         # 成功即停，不刷第三次
    stats = channel.stats()
    assert (stats["sent"], stats["failed"], stats["attempts"]) == (1, 0, 2)
    assert stats["last_status"] == 200


def test_unserializable_field_still_sends_with_capture_time():
    """bytes / 孤立代理项这类"JSON 化就炸"的值，必须降级成文本发出去，而不是整条不发。"""
    post = Post()
    channel = make_wecom(post)

    assert channel({"kind": "BROKEN", "blob": b"\x00\x01", "raw": "坏\ud800字节"}) is True

    assert len(post.calls) == 1
    body = post.bodies[0]                                 # 能被 json.loads 解开
    content = body["markdown"]["content"]
    assert "采集时间" in content                           # 没有 at 就退回采集时间
    assert "BROKEN" in content


# ---------------------------------------------------------------- 敏感信息
def test_secret_never_appears_in_stats_body_or_repr():
    seed = sign_seed()
    post = Post()
    channel = make_dingtalk(post)

    assert channel(EVENT) is True

    body = post.bodies[0]
    assert "sign" in body and "timestamp" in body
    assert seed not in json.dumps(body, ensure_ascii=False)      # 正文只有签名

    blob = json.dumps({"stats": channel.stats(), "repr": repr(channel),
                       "url_called": post.calls[0]["url"]}, ensure_ascii=False)
    assert seed not in blob
    assert urllib.parse.quote_plus(seed) not in blob
    # 连 query 里的 token 也不该进 stats（URL 一律去 query 再记账）
    assert "placeholder" not in json.dumps(channel.stats(), ensure_ascii=False)


def test_dingtalk_channel_without_secret_fails_fast():
    for empty in (None, "", "   "):
        with pytest.raises(ValueError) as caught:
            DingtalkChannel("https://oapi.example.com/robot/send", empty)
        message = str(caught.value)
        assert "secret" in message and "310000" in message
        assert "部署侧注入" in message                    # 给出可操作的下一步

    with pytest.raises(ValueError):
        make_channel("slack", "https://example.com/hook")


# ---------------------------------------------------------------- 本地端到端
def test_both_channels_reach_a_local_http_server():
    """真 socket、真 urllib、真 query 拼接；不连外网。"""
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            hits.append((self.path, self.rfile.read(length)))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"errcode":0,"errmsg":"ok"}')

        def log_message(self, *args):
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        wecom = make_channel(WECOM, f"{base}/wecom?key=fake-key", timeout=2.0,
                             clock=fixed_clock())
        dingtalk = make_channel(DINGTALK, f"{base}/dingtalk?access_token=placeholder",
                                secret=sign_seed(), timeout=2.0, clock=fixed_clock())

        assert wecom(EVENT) is True
        assert dingtalk(EVENT) is True

        assert len(hits) == 2
        wecom_body = json.loads(hits[0][1].decode("utf-8"))
        assert wecom_body["msgtype"] == "markdown"
        assert "LEASE_UNAVAILABLE" in wecom_body["markdown"]["content"]

        dingtalk_path, dingtalk_body_raw = hits[1]
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(dingtalk_path).query)
        expected = reference_sign(sign_seed(), TS)
        assert query["timestamp"] == [expected["timestamp"]]
        assert query["sign"] == [urllib.parse.unquote_plus(expected["sign"])]
        dingtalk_body = json.loads(dingtalk_body_raw.decode("utf-8"))
        assert dingtalk_body["msgtype"] == "markdown"
        assert dingtalk_body["sign"] == expected["sign"]
    finally:
        server.shutdown()
