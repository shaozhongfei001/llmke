"""告警通道：把 `event` 变成企业微信 / 钉钉群机器人**认得**的报文并与签名。

`alert_sink.py` 解决的是"怎么可靠地送"（重试、去重、永不抛），但它把 `event` 原样
JSON 化就发出去了。真实群机器人不吃这一套：企业微信要
`{"msgtype": "markdown", "markdown": {"content": ...}}`，钉钉还要额外带
`timestamp` + `sign`（HMAC-SHA256 → base64 → urlencode）。缺这一层，接生产网关只能
现场改代码并试错——而试错的场景恰好是"告警发不出去"的故障时刻。

分工（刻意不重叠）：
- **报文构造**：`wecom_payload()` / `dingtalk_payload()`，纯函数，可离线比对；
- **签名**：`dingtalk_sign()` / `dingtalk_signed_url()`，timestamp 可注入 ⇒ 结果可复现；
- **投递**：`WecomChannel` / `DingtalkChannel`，`__call__(event) -> bool`，**永不抛异常**，
  与 `WebhookAlertSink` 同一契约；重试与状态码判定直接复用 `alert_sink` 的实现，
  不复制一份"看起来一样"的循环（两份迟早会漂移）。

四条刻意的取舍，写下来是为了别被后来人顺手优化掉：

1. **群里要能读**：正文是 markdown（标题 + 级别 + 时间 + 错误 + 影响 + 至多 6 个附加字段），
   不是 `json.dumps(event)`。把整条 JSON 倒进群消息，告警就退化成噪声，没人会看。
2. **按字节截断，不只按字符**：企业微信 markdown 上限是 4096 **字节**，而中文 3 字节/字，
   只按"4000 字符"截会让一条中文长告警在网关侧被整体拒绝（发出去、但内容是空的或被丢弃）。
   所以字符预算与字节预算取先到者，尾部留一行"已截断"说明，不静默丢内容。
3. **secret 只进签名，不进任何可观测面**：不进日志、不进异常消息、不进 `stats()`，
   连"前 4 位"也不给——前 4 位对机器人 secret 来说就是可爆破的锚点；
   sha256 指纹同样不给（虽然不可逆，它确实是 secret 的函数，而这里没有"确认轮换"的需求）。
   底层传输异常可能把完整 URL（内含 access_token）带进 `last_error`，因此失败记账
   统一过一遍 `_scrub()`；URL 进 `stats()` 时一律去掉 query。
4. **没有 secret 就拒绝构造（fail-fast）**：空 secret 发出去只会拿到
   `errcode=310000 sign not match`，把"配置错"伪装成"网络抽风"，排查方向全错。
   构造时就报错，并说明从哪注入（不打印值）。

不做的事：
- **不做去重**：去重语义留在 `WebhookAlertSink`（"窗口在决定发送时打点而不是发送成功后"
  的道理见该模块文档）。本通道若直连调度器，装配侧必须自己保留去重，否则 webhook 抖动时
  每轮告警都会各打一遍网络。这是**已知限制**，不是忘了。
- 不做密钥托管/加密、不落盘重试队列（进程死了告警就丢，本仓没有可靠本地队列）、不导出指标。
"""

import base64
import datetime
import hashlib
import hmac
import json
import re
import threading
import time
import urllib.error
import urllib.parse
from typing import Any, Dict, List, Optional

from .alert_sink import _default_post, _status_of

WECOM = "wecom"
DINGTALK = "dingtalk"

TITLE_PREFIX = "LLMKE 图引擎告警"

# 网关上限（官网文档）：企业微信 markdown 4096 字节；钉钉 markdown 20000 字节。
# 这里都取保守值，字符/字节两个预算同时生效。
WECOM_MAX_CHARS = 4000
WECOM_MAX_BYTES = 4000
DINGTALK_MAX_CHARS = 4000
DINGTALK_MAX_BYTES = 8000

# 正文里"值得排在前面"的字段：出故障时人第一眼看的就是这些。
_NAMED_FIELDS = ("error", "impact", "reason", "detail")
_LABELS = {"error": "错误", "impact": "影响", "reason": "原因", "detail": "详情"}
# 已经渲染过、或属于内部元数据、不必再当附加字段重复一遍的键。
_CONSUMED = frozenset(
    {"kind", "alert", "type", "severity", "level", "at", "schema"}
    | set(_NAMED_FIELDS)
)
# 长字段的渲染上限：**故意大于报文预算**，让"整条报文截断"成为唯一的收口点；
# 附加字段则各自压到 200 字（它们只是补充信息，不该把正文挤出去）。
_LONG_FIELD_CHARS = 6000
_SHORT_FIELD_CHARS = 200
_MAX_EXTRA_FIELDS = 6

# 传输层异常文本里可能带完整 URL：把 query 里的凭证值抹掉。
# `sign` 故意**不抹**——排查 310000 时要靠它比对，而且它不是长期凭证。
_CRED_QUERY_RE = re.compile(
    r"(?i)\b(access_token|api[_-]?key|token|key|secret)=([^&\s'\"><]+)")


# ------------------------------------------------------------------ 文本工具
def _utf8_safe(text: str) -> str:
    """去掉孤立代理项（lone surrogate）。

    事件里的字符串可能来自 `surrogateescape` 解码；`ensure_ascii=False` 后
    `.encode("utf-8")` 会直接抛 `UnicodeEncodeError`——告警因此变成"发不出去"。
    这里提前把不可编码的码位丢掉，代价是一个乱码字符，换来整条告警发得出去。
    """
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", "ignore").decode("utf-8")


def _text(value: Any, limit: Optional[int] = None) -> str:
    """把任意字段值渲染成**一行可读文本**；空值返回空串（调用方据此跳过）。"""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, bool) or isinstance(value, (int, float)):
        text = str(value)
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        except (TypeError, ValueError):
            text = repr(value)
    text = _utf8_safe(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if limit is not None and len(text) > limit:
        text = text[:limit] + "…"
    return text


def _format_epoch(value: Any) -> Optional[str]:
    """把 epoch（秒或毫秒）格式化成 UTC 时间；认不出来的原样留着。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds >= 1e11:            # 毫秒时间戳（1e11 秒 ≈ 公元 5138 年，不会误判）
            seconds /= 1000.0
        try:
            moment = datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return moment.strftime("%Y-%m-%d %H:%M:%S UTC")
    if isinstance(value, str) and value.strip():
        return _text(value, 64)
    return None


def _kind_of(event: Any) -> str:
    fields = event if isinstance(event, dict) else {}
    for name in ("kind", "alert", "type"):
        text = _text(fields.get(name), 80)
        if text:
            return text
    return "UNKNOWN"


def _truncate(text: str, *, max_chars: int, max_bytes: int,
              marker: Optional[str] = None) -> str:
    """字符/字节双预算截断，尾部留痕。

    两个预算都要守：中文按字符数没超、按字节数早就超了，这是企业微信侧
    "消息发出去但内容被丢"的常见成因。
    """
    if max_chars <= 0 or max_bytes <= 0:
        raise ValueError("max_chars / max_bytes 必须为正：0 预算等于什么都不发")
    text = _utf8_safe(text)
    raw = text.encode("utf-8")
    if len(text) <= max_chars and len(raw) <= max_bytes:
        return text

    if marker is None:
        marker = f"\n\n…（已截断：原文 {len(text)} 字符 / {len(raw)} 字节）"
    char_budget = max_chars - len(marker)
    byte_budget = max_bytes - len(marker.encode("utf-8"))
    if char_budget <= 0 or byte_budget <= 0:
        # 预算小到连提示都放不下：硬截，绝不返回超预算的正文。
        return _utf8_safe(raw[:max_bytes].decode("utf-8", "ignore"))[:max_chars]
    cut = text[:char_budget]
    encoded = cut.encode("utf-8")
    if len(encoded) > byte_budget:
        cut = encoded[:byte_budget].decode("utf-8", "ignore")   # 丢掉尾部半个多字节字符
    return cut + marker


def _render_markdown(event: Any, *, title_prefix: str, max_chars: int, max_bytes: int,
                     now_ms: Optional[int]) -> str:
    """事件 → 群消息正文（markdown）。**不是** JSON 转储。"""
    fields: Dict[str, Any] = event if isinstance(event, dict) else {"error": event}
    kind = _kind_of(event)
    severity = _text(fields.get("severity") or fields.get("level") or "ALERT", 32) or "ALERT"

    lines: List[str] = [f"### {_text(title_prefix, 40)}: {kind}",
                        f"> 级别: {severity}"]

    stamp = _format_epoch(fields.get("at"))
    if stamp:
        lines.append(f"> 时间: {stamp}")
    else:
        fallback = now_ms if now_ms is not None else int(time.time() * 1000)
        lines.append(f"> 时间: {_format_epoch(fallback)}（采集时间；事件未带 at）")

    for key in _NAMED_FIELDS:
        text = _text(fields.get(key), _LONG_FIELD_CHARS)
        if text:
            lines.append(f"> {_LABELS[key]}: {text}")

    extras = 0
    for key in sorted(fields):
        if key in _CONSUMED or extras >= _MAX_EXTRA_FIELDS:
            continue
        text = _text(fields.get(key), _SHORT_FIELD_CHARS)
        if not text:
            continue
        lines.append(f"> {_text(key, 40)}: {text}")
        extras += 1

    return _truncate("\n".join(lines), max_chars=max_chars, max_bytes=max_bytes)


# ------------------------------------------------------------------ 报文构造
def wecom_payload(event: Any, *, max_chars: int = WECOM_MAX_CHARS,
                  max_bytes: int = WECOM_MAX_BYTES,
                  now_ms: Optional[int] = None,
                  title_prefix: str = TITLE_PREFIX) -> Dict[str, Any]:
    """企业微信群机器人报文：`msgtype=markdown` + 一段人可读的 `content`。"""
    content = _render_markdown(event, title_prefix=title_prefix, max_chars=max_chars,
                               max_bytes=max_bytes, now_ms=now_ms)
    return {"msgtype": "markdown", "markdown": {"content": content}}


def dingtalk_sign(secret: Optional[str], timestamp_ms: Optional[int] = None) -> Dict[str, str]:
    """按钉钉文档算签名：`f"{timestamp}\\n{secret}"` → HMAC-SHA256 → base64 → urlencode。

    参数里必须能注入 timestamp：否则签名不可复现，测试只能"跑一次看像不像"，
    没法逐字符比对（而签名错一位就是一个 310000）。
    """
    if not isinstance(secret, str) or not secret.strip():
        raise ValueError(
            "dingtalk 签名需要非空 secret——空 secret 发出去只会被网关拒绝"
            "（errcode=310000 sign not match），在线上表现为“告警收不到”。"
            "请由部署侧注入（环境变量或密钥文件）后再传入，不要写进代码或配置文件。")

    timestamp = str(int(timestamp_ms) if timestamp_ms is not None else int(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"),
                      hashlib.sha256).digest()
    # quote_plus 是官方示例的写法：`+` `/` `=` 必须转义，原样塞进 query 会被截断。
    return {"timestamp": timestamp,
            "sign": urllib.parse.quote_plus(base64.b64encode(digest))}


def dingtalk_signed_url(url: str, secret: Optional[str], *,
                        timestamp_ms: Optional[int] = None) -> str:
    """把 `timestamp` / `sign` 拼进 URL 的 query。

    真实网关**从 query 读签名**（不是从 body 读），所以通道实际投递用的是本函数。
    `sign` 已经 urlencode 过，这里不能再编码一次，否则 `%` 会被翻成 `%25`，签名必然不匹配。
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("webhook url 不能为空")
    signed = dingtalk_sign(secret, timestamp_ms)
    joiner = "&" if "?" in url else "?"
    return (f"{url}{joiner}timestamp={signed['timestamp']}"
            f"&sign={signed['sign']}")


def dingtalk_payload(event: Any, secret: Optional[str], *,
                     timestamp_ms: Optional[int] = None,
                     max_chars: int = DINGTALK_MAX_CHARS,
                     max_bytes: int = DINGTALK_MAX_BYTES,
                     title_prefix: str = TITLE_PREFIX) -> Dict[str, Any]:
    """钉钉群机器人报文：markdown（title + text），并带上 `timestamp` / `sign`。

    body 里同时附 timestamp/sign 是为了"抓包能看到自己发了什么"（排查 310000 时
    必须能对上哪一次请求、哪个时间戳）；网关真正校验的是 query 里的那一对，
    两者由同一个 timestamp 算出，必然一致。
    """
    signed = dingtalk_sign(secret, timestamp_ms)
    kind = _kind_of(event)
    title = _text(f"{title_prefix}: {kind}", 64)
    text = _render_markdown(event, title_prefix=title_prefix, max_chars=max_chars,
                            max_bytes=max_bytes, now_ms=int(signed["timestamp"]))
    return {"msgtype": "markdown",
            "markdown": {"title": title, "text": text},
            "timestamp": signed["timestamp"],
            "sign": signed["sign"]}


# ------------------------------------------------------------------ 通道
def _redact_url(url: str) -> str:
    """去掉 query / fragment：webhook 的 key / access_token 就藏在那里。"""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "<unparsable-url>"
    if not parts.query and not parts.fragment:
        return url
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class AlertChannel:
    """群机器人通道基类：`__call__` **永不抛异常**，与 `WebhookAlertSink` 同一契约。

    失败只体现在两处：返回 `False`、以及 `stats()` 里的 `failed` / `last_error` /
    `last_status`。调度器按"是否抛异常"记 `alert_sink_errors`，**不看返回值**——
    所以"告警到底送到没送到"要看 `stats()`，不要看调度器的计数。
    """

    kind = "alert"
    default_max_chars = WECOM_MAX_CHARS
    default_max_bytes = WECOM_MAX_BYTES

    def __init__(self, url: str, *,
                 timeout: float = 3.0,
                 retries: int = 2,
                 backoff: float = 0.5,
                 max_chars: Optional[int] = None,
                 max_bytes: Optional[int] = None,
                 post: Optional[Any] = None,
                 clock: Optional[Any] = None,
                 sleep: Optional[Any] = None,
                 title_prefix: str = TITLE_PREFIX):
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"{self.kind} 通道需要非空 webhook url")
        if retries < 0:
            raise ValueError("retries 不能为负")
        self.url = url
        self.timeout = timeout
        self.retries = retries            # 总尝试次数 = retries + 1
        self.backoff = backoff
        self.max_chars = self.default_max_chars if max_chars is None else max_chars
        self.max_bytes = self.default_max_bytes if max_bytes is None else max_bytes
        if self.max_chars <= 0 or self.max_bytes <= 0:
            raise ValueError("max_chars / max_bytes 必须为正")
        self.title_prefix = title_prefix
        self._post = post or _default_post
        self._clock = clock or time.time          # 返回 epoch **秒**
        self._sleep = sleep or time.sleep
        self._secret = ""                          # 子类签名用，绝不出现在可观测面
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "sent": 0,           # 成功投递的告警数
            "failed": 0,         # 最终失败（已含重试）
            "attempts": 0,       # HTTP 尝试次数（含重试）
            "last_error": None,
            "last_status": None,
        }

    # ---------- 记账 ----------
    def _scrub(self, message: Any) -> str:
        """把 secret 从任何要落进 `stats()` / 异常消息的文本里抹掉。

        防的是"底层报错顺手把凭证回显出来"（例如把完整 URL 或请求头拼进异常文本）。
        两层：先把 query 里的凭证值抹成 `***`，再把 secret 的三种编码形态
        （原文 / 严格 urlencode / quote_plus）抹掉——底层若对 secret 做过编码，
        只抹原文会漏。
        """
        text = _CRED_QUERY_RE.sub(r"\1=***", "" if message is None else str(message))
        plain = self._secret
        if not plain:
            return text
        for form in {plain,
                     urllib.parse.quote(plain, safe=""),
                     urllib.parse.quote_plus(plain)}:
            if form:
                text = text.replace(form, "***")
        return text

    def _record_failure(self, error: Any, status: Optional[int]) -> None:
        with self._lock:
            self._state["failed"] += 1
            self._state["last_error"] = self._scrub(error)
            if status is not None:
                self._state["last_status"] = status

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            state = dict(self._state)
        return {**state,
                "channel": self.kind,
                "url": _redact_url(self.url),      # 去 query：key/token 就在里面
                "retries": self.retries,
                "max_chars": self.max_chars,
                "max_bytes": self.max_bytes}

    def __repr__(self) -> str:
        state = self.stats()
        return (f"<{type(self).__name__} {self.kind} sent={state['sent']} "
                f"failed={state['failed']} url={state['url']}>")

    # ---------- 子类接口 ----------
    def build_payload(self, event: Any, *, now_ms: int) -> Dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} 必须实现 build_payload")

    def target_url(self, *, now_ms: int) -> str:
        return self.url

    # ---------- 入口：永不抛 ----------
    def __call__(self, event: Any) -> bool:
        try:
            return self._deliver(event)
        except Exception as exc:  # noqa: BLE001
            # 兜底：连记账这一层都出错，也不能把调度主循环带走。
            self._record_failure(f"{type(exc).__name__}: {exc}", None)
            return False

    def _deliver(self, event: Any) -> bool:
        now_ms = int(self._clock() * 1000)
        try:
            payload = self.build_payload(event, now_ms=now_ms)
            url = self.target_url(now_ms=now_ms)
        except Exception as exc:  # noqa: BLE001
            # 报文构造失败（含 secret 缺失）属于配置问题，同样不许抛给调度器。
            self._record_failure(f"payload: {type(exc).__name__}: {exc}", None)
            return False

        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            self._record_failure(f"serialize: {type(exc).__name__}: {exc}", None)
            return False

        attempt = 0
        while True:
            attempt += 1
            ok = False
            status: Optional[int] = None
            error: Optional[str] = None
            try:
                status = _status_of(self._post(url, body, self.timeout))
                if status is None:
                    error = "unverified response (no status code)"
                elif 200 <= status < 300:
                    ok = True
                else:
                    error = f"HTTP {status}"
            except urllib.error.HTTPError as exc:
                status = getattr(exc, "code", None)
                error = f"HTTP {status}: {exc}"
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"

            with self._lock:
                self._state["attempts"] += 1
                if status is not None:
                    self._state["last_status"] = status
                if error:
                    self._state["last_error"] = self._scrub(error)

            if ok:
                with self._lock:
                    self._state["sent"] += 1
                return True
            if attempt > self.retries:
                with self._lock:
                    self._state["failed"] += 1
                return False

            delay = self.backoff * (2 ** (attempt - 1))    # 指数退避：0.5, 1.0, 2.0 ...
            if delay > 0:
                self._sleep(delay)


class WecomChannel(AlertChannel):
    """企业微信群机器人：URL 里自带 `key`，报文不带签名。"""

    kind = WECOM
    default_max_chars = WECOM_MAX_CHARS
    default_max_bytes = WECOM_MAX_BYTES

    def build_payload(self, event: Any, *, now_ms: int) -> Dict[str, Any]:
        return wecom_payload(event, max_chars=self.max_chars, max_bytes=self.max_bytes,
                             now_ms=now_ms, title_prefix=self.title_prefix)


class DingtalkChannel(AlertChannel):
    """钉钉群机器人：URL 带 `access_token`，另需 `timestamp` + `sign`。

    没给 secret 就在构造期失败——理由见模块文档第 4 条（空 secret = 线上 310000，
    排查方向会被带到网络上，而真实原因是配置）。
    """

    kind = DINGTALK
    default_max_chars = DINGTALK_MAX_CHARS
    default_max_bytes = DINGTALK_MAX_BYTES

    def __init__(self, url: str, secret: Optional[str] = None, **kwargs: Any):
        if not isinstance(secret, str) or not secret.strip():
            raise ValueError(
                "dingtalk 通道缺少 secret（fail-fast）：空 secret 会被网关拒绝"
                "（errcode=310000 sign not match），在线上只表现为“告警收不到”。"
                "请由部署侧注入（环境变量或密钥文件）后通过本参数传入。")
        super().__init__(url, **kwargs)
        self._secret = secret             # 只用于签名；不进日志/异常/stats

    def build_payload(self, event: Any, *, now_ms: int) -> Dict[str, Any]:
        return dingtalk_payload(event, self._secret, timestamp_ms=now_ms,
                                max_chars=self.max_chars, max_bytes=self.max_bytes,
                                title_prefix=self.title_prefix)

    def target_url(self, *, now_ms: int) -> str:
        return dingtalk_signed_url(self.url, self._secret, timestamp_ms=now_ms)


CHANNELS = {WECOM: WecomChannel, DINGTALK: DingtalkChannel}


def make_channel(kind: str, url: str, *, secret: Optional[str] = None,
                 **kwargs: Any) -> AlertChannel:
    """按配置里的通道名建通道（部署侧按 `alerts.channel=wecom|dingtalk` 装配）。"""
    if kind == DINGTALK:
        return DingtalkChannel(url, secret, **kwargs)
    if kind == WECOM:
        return WecomChannel(url, **kwargs)
    raise ValueError(f"未知告警通道 {kind!r}，可选 {sorted(CHANNELS)}")
