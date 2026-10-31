"""令牌桶限流：把"每秒最多打几次外部接口"做成可注入、可断言的实现。

为什么需要：重建/回答链路会打外部 LLM 与图引擎接口，突发请求既会被对端 429，
也会让失败重试把一次故障放大成雪崩。限流器要能**不阻塞**地回答"现在能不能打"，
也要能"等到能打为止"——这两种语义在调用侧完全不同，所以分成两个入口：

- `take(n)`：够则扣减返回 True，不够返回 False，**绝不等待**，调用方自己决定降级；
- `wait_take(n, timeout)`：最多等到 timeout，返回**实际等待秒数**；超时返回 None。

`guard(bucket)` 给"拿不到就别打"的写法用：直接抛 `RateLimitedError`，消息里带建议
等待秒数，免得每个调用侧自己算 `缺的令牌数 / 补充速率`。

时钟与 sleep 都可注入：测试用假时钟断言"什么时候补、补多少"，不真等、不 flaky。

刻意不做的事：
- 不做分布式限流（跨进程/跨机共享状态要引入 Redis 或 DB，本仓离线交付不为此加依赖）；
- 不做等待队列（FIFO 排队会让超时语义变含糊：排到了才发现超时，线程白占）；
- 不记录每次调用明细（只累计 allowed/denied/waited_s，明细归 metrics.py 的导出层）。

两个必须显式挡住的边界（否则线上是"偶发 ZeroDivisionError / 卡死"这种最难查的形状）：
1. `capacity == 0` 或 `refill_per_s == 0` 时**不能除零**；补充速率为 0 还意味着
   `wait_take` 等多久都不会有令牌，必须立即判失败，而不是无限等下去。
2. `n > capacity` 永远取不到，直接拒绝且**不扣减**——扣了也补不回来，只会让余量失真、
   让后续 `retry_after` 的建议值凭空变大。
"""

import contextlib
import threading
import time
from typing import Any, Callable, Dict, Optional

SCHEMA = "llmke.graph-engine.rate-limit.v1"

# 浮点比较容差：0.1s 一次地累积补充，tokens 可能与 n 差个 1e-16，
# 不放容差会出现"明明等够了却被拒"的偶发失败。1e-9 个令牌的偏差不可能被观测到。
_EPS = 1e-9


class RateLimitedError(RuntimeError):
    """令牌不足。

    `retry_after` = 建议等待秒数；`None` 表示"等也不会恢复"（补充速率为 0）。
    消息里只有数量与秒数，不含任何凭据或请求内容。
    """

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TokenBucket:
    """线程安全的令牌桶。`clock` 与 `sleep` 可注入（假时钟测试用）。"""

    def __init__(self, capacity: float, refill_per_s: float, *,
                 clock: Optional[Callable[[], float]] = None,
                 sleep: Optional[Callable[[float], None]] = None):
        capacity = float(capacity)
        refill_per_s = float(refill_per_s)
        if capacity < 0:
            raise ValueError(f"capacity 不能为负：{capacity}")
        if refill_per_s < 0:
            raise ValueError(f"refill_per_s 不能为负：{refill_per_s}")
        self.capacity = capacity
        self.refill_per_s = refill_per_s
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._balance = capacity          # 初始满桶：冷启动不该先罚一次等待
        self._last = self._clock()
        self._state: Dict[str, Any] = {"allowed": 0, "denied": 0, "waited_s": 0.0}

    # ---------- 内部 ----------
    @staticmethod
    def _check_n(n: Any) -> int:
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError(f"n 必须是整数，收到 {type(n).__name__}")
        if n <= 0:
            raise ValueError(f"n 必须为正整数，收到 {n}")
        return n

    def _refill_locked(self) -> None:
        """按经过的时间补令牌（调用方必须已持锁）。

        `_last` 无条件推进到 now：时钟倒退（NTP 回拨/注入的时钟抖动）时宁可少补，
        也不能把倒退的时间当成"负经过时间"去倒扣。
        """
        now = self._clock()
        elapsed = now - self._last
        self._last = now
        if elapsed > 0 and self.refill_per_s > 0.0 and self._balance < self.capacity:
            self._balance = min(self.capacity, self._balance + elapsed * self.refill_per_s)

    # ---------- 观测 ----------
    def available(self) -> float:
        """当前余量（会先按时间补充）。"""
        with self._lock:
            self._refill_locked()
            return self._balance

    def retry_after(self, n: int = 1) -> Optional[float]:
        """离"凑够 n 个令牌"还要多少秒；`None` = 等也不会恢复。"""
        n = self._check_n(n)
        with self._lock:
            self._refill_locked()
            deficit = n - self._balance
            if deficit <= _EPS:
                return 0.0
            if self.refill_per_s <= 0.0:
                return None
            return deficit / self.refill_per_s

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            self._refill_locked()
            return {"schema": SCHEMA, "capacity": self.capacity,
                    "refill_per_s": self.refill_per_s, "tokens": self._balance,
                    "allowed": self._state["allowed"], "denied": self._state["denied"],
                    "waited_s": self._state["waited_s"]}

    # ---------- 取令牌 ----------
    def take(self, n: int = 1) -> bool:
        """够就扣减并返回 True；不够返回 False，**不等待、不扣减**。"""
        n = self._check_n(n)
        with self._lock:
            self._refill_locked()
            if n > self.capacity or self._balance + _EPS < n:
                self._state["denied"] += 1
                return False
            self._balance = max(0.0, self._balance - n)
            self._state["allowed"] += 1
            return True

    def wait_take(self, n: int = 1, timeout: Optional[float] = None) -> Optional[float]:
        """最多等到 timeout 秒；返回**实际等待秒数**（立即可取返回 0.0），超时返回 None。

        超时/不可能满足时**不扣减**：没拿到令牌却把余量减掉，会让后面的调用
        替这次失败买单，账就对不上了。
        """
        n = self._check_n(n)
        with self._lock:
            self._refill_locked()
            if n > self.capacity:
                self._state["denied"] += 1
                return None
            deficit = n - self._balance
            if deficit <= _EPS:
                self._balance = max(0.0, self._balance - n)
                self._state["allowed"] += 1
                return 0.0
            if self.refill_per_s <= 0.0:
                # 补充速率为 0：等一分钟和等一年结果一样，别把线程挂死在这里。
                self._state["denied"] += 1
                return None
            need = deficit / self.refill_per_s
            if timeout is not None and need > timeout:
                self._state["denied"] += 1
                return None
        # 睡眠必须在锁外：等待期间别的线程还得能取令牌，否则"等"本身就变成全局串行。
        self._sleep(need)
        with self._lock:
            self._refill_locked()
            self._balance = max(0.0, self._balance - n)
            self._state["allowed"] += 1
            self._state["waited_s"] += need
        return need


def _limit_message(bucket: TokenBucket, n: int, retry: Optional[float]) -> str:
    head = (f"限流：令牌不足（本次需要 {n}，当前余量 {bucket.available():.3f}，"
            f"容量 {bucket.capacity:.0f}）")
    if retry is None:
        return head + "；补充速率为 0，等待不会恢复，请检查限流配置"
    return head + f"；建议 {retry:.3f}s 后重试"


@contextlib.contextmanager
def guard(bucket: TokenBucket, n: int = 1):
    """拿不到令牌就抛 `RateLimitedError`（消息含建议等待秒数），拿到则原样让过。"""
    if not bucket.take(n):
        retry = bucket.retry_after(n)
        raise RateLimitedError(_limit_message(bucket, n, retry), retry)
    yield bucket
