"""告警投递通道：把 `on_alert(event)` 接到真实 webhook 上。

调度器只提供接缝（`on_alert`），并且**已经**假设"通道可能抛异常"——它自己会用
`alert_sink_errors` 记账后继续跑。这个模块把那个接缝落成一个可注入、可测的实现：

- `WebhookAlertSink`：POST JSON，失败按指数退避重试，`__call__` **永不抛异常**；
- `CompositeSink`：扇出到多个通道，任一失败不影响其他（一个通道配错了不该让另一个也不发）。

两个刻意的语义，写下来是为了别被后来人"顺手优化"掉：

1. **`__call__` 返回 bool，但不抛**。返回值只用于部署侧自检和 `CompositeSink` 汇总；
   调度器本身只按"是否抛异常"记 `alert_sink_errors`，**不看返回值**。也就是说投递失败
   时调度器仍算 `alerts_sent += 1`——所以"告警是否真的送达"要看本模块的 `stats()`
   （`sent` / `failed` / `last_status` / `last_error`），不要只看调度器计数。
2. **去重窗口在"决定发送"时打点，而不是"发送成功"之后**。webhook 挂掉时如果按成功打点，
   调度器每次重投都会再打一轮（`retries` 次 HTTP + 退避），等于把故障放大成雪崩。
   代价是：窗口内失败的那次会漏掉，只能从 `failed` / `last_error` 看出来。宁可漏一次
   也不刷屏——这是运维侧通话过的方向。

不做的事：不签名/不鉴权（部署侧在网关层做）、不落盘重试队列（进程死了告警就丢了，
本仓没有可靠的本地队列，假装有就是骗人）、不做指标导出（见 metrics.py）。
"""

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional

SCHEMA = "llmke.graph-engine.alert-sink.v1"

# 事件里就是这个键区分告警类型；去重按它做。
_KIND = "kind"


def _default_post(url: str, body: bytes, timeout: float) -> Dict[str, Any]:
    """默认投递：标准库 POST。非 2xx 会抛 `HTTPError`，由调用方按状态码记账。"""
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "llmke-graph-engine-alert-sink/1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # 直接返回状态码（int）：早先返回 {"status": 200} 这种 dict，_status_of 认不出来，
        # 于是**每次真实的 HTTP 200 都被当成"未确认的响应"重试 3 次并记 failed=1**。
        # 桩测试全用 int/None 返回值，永远碰不到这条路径——端到端演练才暴露出来。
        return int(getattr(response, "status", 200))


def _status_of(result: Any) -> Optional[int]:
    """从注入的 post 返回值里抠出 HTTP 状态码。

    容忍几种常见形状：int、`(status, body)`、带 `status`/`status_code` 的对象、
    带 `getcode()` 的对象（`http.client` 风格）。拿不到就返回 None → 调用方按失败处理
    （fail-closed：无法确认成功就不算成功）。

    例外：返回 None 视为 2xx。这是给"只关心被调用几次"的桩留的口子。
    """
    if result is None:
        return 200
    if isinstance(result, bool):
        return 200 if result else 500
    if isinstance(result, int):
        return result
    if isinstance(result, dict):
        value = result.get("status", result.get("status_code"))
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if isinstance(result, (tuple, list)) and result:
        first = result[0]
        return first if isinstance(first, int) and not isinstance(first, bool) else None
    for attr in ("status", "status_code"):
        value = getattr(result, attr, None)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    getcode = getattr(result, "getcode", None)
    if callable(getcode):
        try:
            value = getcode()
        except Exception:  # noqa: BLE001
            return None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _payload(event: Any) -> Dict[str, Any]:
    """请求体：event 原样铺开 + 补一个 schema。

    复制而不是就地改：调用方（调度器）可能还持有这个 dict 做后续判断，
    往别人的对象里塞键是隐形的耦合。已有 schema 时不覆盖（event 自带的更权威）。
    """
    if isinstance(event, dict):
        body = dict(event)
    else:
        body = {"event": event}
    body.setdefault("schema", SCHEMA)
    return body


class WebhookAlertSink:
    """单通道 webhook 投递。`post`/`clock`/`sleep` 可注入，测试里不碰网络、不真等。"""

    def __init__(self, url: str, *,
                 timeout: float = 3.0,
                 retries: int = 2,
                 backoff: float = 0.5,
                 post: Optional[Callable[[str, bytes, float], Any]] = None,
                 clock: Optional[Callable[[], float]] = None,
                 sleep: Optional[Callable[[float], None]] = None,
                 dedupe_window_s: float = 30.0):
        if not url:
            raise ValueError("webhook url 不能为空")
        if retries < 0:
            raise ValueError("retries 不能为负")
        self.url = url
        self.timeout = timeout
        self.retries = retries          # 重试次数（总尝试 = retries + 1）
        self.backoff = backoff
        self.dedupe_window_s = dedupe_window_s
        self._post = post or _default_post
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "sent": 0,          # 投递成功的告警数
            "failed": 0,        # 最终失败的告警数（已含重试）
            "attempts": 0,      # HTTP 尝试次数（含重试）
            "deduped": 0,       # 被去重窗口挡下的告警数
            "last_error": None,
            "last_status": None,
        }
        self._last_at: Dict[str, float] = {}

    # ---------- 记账 ----------
    def _count(self, **deltas: int) -> None:
        with self._lock:
            for key, delta in deltas.items():
                self._state[key] += delta

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {**self._state, "url": self.url, "retries": self.retries,
                    "dedupe_window_s": self.dedupe_window_s}

    # ---------- 入口：永不抛 ----------
    def __call__(self, event: Any) -> bool:
        try:
            return self._deliver(event)
        except Exception as exc:  # noqa: BLE001
            # 兜底：连记账/去重这一层都出错，也不能把调度主循环带走。
            self._record_failure(f"{type(exc).__name__}: {exc}", None)
            return False

    def _should_send(self, event: Any) -> bool:
        kind = event.get(_KIND) if isinstance(event, dict) else None
        if not isinstance(kind, str) or not kind or self.dedupe_window_s <= 0:
            return True                     # 没有 kind 就没法去重，宁可照发
        now = self._clock()
        with self._lock:
            last = self._last_at.get(kind)
            if last is not None and (now - last) < self.dedupe_window_s:
                self._state["deduped"] += 1
                return False
            self._last_at[kind] = now       # 先打点：失败也不许在窗口内反复重投
            return True

    def _record_failure(self, error: str, status: Optional[int]) -> None:
        with self._lock:
            self._state["failed"] += 1
            self._state["last_error"] = error
            if status is not None:
                self._state["last_status"] = status

    def _deliver(self, event: Any) -> bool:
        if not self._should_send(event):
            return True                     # 窗口内重复：算"已处理"，不算失败

        try:
            body = json.dumps(_payload(event), ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            # 告警事件里有不可序列化的东西本身就是 bug：记失败，但绝不抛给调度器。
            self._record_failure(f"serialize: {type(exc).__name__}: {exc}", None)
            return False

        attempt = 0
        while True:
            attempt += 1
            ok = False
            status: Optional[int] = None
            error: Optional[str] = None
            try:
                status = _status_of(self._post(self.url, body, self.timeout))
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
                    self._state["last_error"] = error

            if ok:
                self._count(sent=1)
                return True
            if attempt > self.retries:
                self._count(failed=1)
                return False

            delay = self.backoff * (2 ** (attempt - 1))   # 指数退避：0.5, 1.0, 2.0 ...
            if delay > 0:
                self._sleep(delay)


class CompositeSink:
    """扇出：一路配错不该让另一路也收不到告警。

    返回 True 仅当**所有**通道都成功（与 `WebhookAlertSink.__call__` 的"是否最终成功"对齐）；
    没有通道时返回 False —— "什么都没发"不能算成功（fail-closed）。
    某个通道自己抛异常也只在结果里记成失败，不向外传播。
    """

    def __init__(self, sinks: Any = ()):
        if sinks is None:
            self.sinks: List[Any] = []
        elif isinstance(sinks, (list, tuple)):
            self.sinks = list(sinks)
        else:
            self.sinks = [sinks]
        self._lock = threading.Lock()
        self._state = {"calls": 0, "all_ok": 0, "any_failed": 0}

    def __call__(self, event: Any) -> bool:
        results: List[Dict[str, Any]] = []
        for index, sink in enumerate(self.sinks):
            try:
                ok = bool(sink(event))
                error = None
            except Exception as exc:  # noqa: BLE001
                ok, error = False, f"{type(exc).__name__}: {exc}"
            entry: Dict[str, Any] = {"index": index, "ok": ok}
            if error:
                entry["error"] = error
            sink_stats = getattr(sink, "stats", None)
            if callable(sink_stats):
                try:
                    entry["stats"] = sink_stats()
                except Exception:  # noqa: BLE001
                    entry["stats"] = None
            results.append(entry)

        all_ok = bool(results) and all(item["ok"] for item in results)
        with self._lock:
            self._state["calls"] += 1
            self._state["all_ok"] += 1 if all_ok else 0
            self._state["any_failed"] += 0 if all_ok else 1
            self._last_results = results
        return all_ok

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            results = list(getattr(self, "_last_results", []))
            state = dict(self._state)
        return {**state, "sinks": len(self.sinks), "results": results}
