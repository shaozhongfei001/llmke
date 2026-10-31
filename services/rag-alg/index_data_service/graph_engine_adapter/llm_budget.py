"""调用预算：把"回答段还能打几次外部 LLM"从散落的 if 判断收成一个可注入对象。

为什么要有这一层，而不是直接在调用点写 `if count > 6: return ""`：
- 限流必须**可配置且可解释**：配置写成 `6/60`（每 60 秒 6 次）人能看懂，
  换算成"容量 + 补充速率"这种实现细节由本模块消化；
- 限流必须**可测试**：时钟与 sleep 可注入，测试断言"补多少、什么时候能继续打"，
  不真等、不 flaky。这套能力已经由 `rate_limit.TokenBucket` 提供，这里**复用**
  而不是重写一份令牌桶——两份实现必然在边界上给出不同答案；
- 限流必须**可观测**：`stats()` 是给 metrics/健康检查消费的稳定形状，
  `describe()` 是给人看的、可安全进日志的摘要（不含密钥、端点、请求内容）。

设计取舍：
- 默认**关闭**。`from_env()` 在 `LLMKE_ANSWER_RATE` 未设置或为空时返回 `None`，
  调用方用 `guard(budget)` 无脑包一层即可，`None` 时什么都不做。限流是运维开关，
  不是默认行为——加限流不该悄悄改变既有部署的吞吐。
- 拒绝时抛 `RateLimitedError`（**复用** `rate_limit` 的异常类型），消息带建议等待秒数。
  调用方据此决定降级还是重试，本模块不做等待、不做排队。
- `n > capacity` 是永久不可满足的请求，直接拒绝且**不扣减**余量：扣了也补不回来，
  只会让后续 `retry_after` 的建议值凭空变大、账目失真。
"""

import contextlib
import math
import os
from typing import Any, Callable, Dict, Optional, Tuple

from .rate_limit import RateLimitedError, TokenBucket

SCHEMA = "llmke.answer-llm-budget.v1"

# 环境变量名：与 llm_config 的 `LLMKE_ANSWER_*` 家族保持一致，运维只需记一套前缀。
ENV_VAR = "LLMKE_ANSWER_RATE"

# 报错时把"该怎么写"直接摆出来，省得人翻文档猜格式。
FORMAT_HINT = ('期望格式为 "N/PERIOD"，例如 "6/60" 表示每 60 秒最多 6 次；'
               "N 为非负数（0 表示不允许任何调用），PERIOD 必须为正数")

__all__ = ["SCHEMA", "ENV_VAR", "CallBudget", "RateLimitedError", "from_env", "guard",
           "parse_limit"]


def parse_limit(text: Any) -> Tuple[float, float]:
    """把 `"6/60"` 解析成 `(capacity, refill_per_s)`，即 `(6.0, 0.1)`。

    只接受"恰好一个斜杠 + 两个有限数字"的形状。所有失败分支都抛 `ValueError`，
    消息里带上原值与期望格式——配置错误应该一眼能改，而不是报个裸 `ZeroDivisionError`。
    """
    raw = "" if text is None else str(text)
    shown = raw.strip()
    if not shown:
        raise ValueError(f"限流配置为空；{FORMAT_HINT}")

    parts = shown.split("/")
    if len(parts) != 2:
        raise ValueError(f"限流配置 {shown!r} 应当恰好包含一个斜杠；{FORMAT_HINT}")

    head, tail = parts[0].strip(), parts[1].strip()
    try:
        capacity = float(head)
        period = float(tail)
    except (TypeError, ValueError):
        raise ValueError(
            f"限流配置 {shown!r} 含非数字部分；{FORMAT_HINT}") from None

    if not math.isfinite(capacity) or not math.isfinite(period):
        raise ValueError(f"限流配置 {shown!r} 含非有限数值；{FORMAT_HINT}")
    if capacity < 0:
        raise ValueError(f"限流配置 {shown!r} 的次数不能为负（收到 {head}）；{FORMAT_HINT}")
    if period <= 0:
        raise ValueError(
            f"限流配置 {shown!r} 的分母必须为正数（收到 {tail}）；{FORMAT_HINT}")

    # capacity == 0 时补充速率必须也是 0：0 次/60 秒意味着"永不允许"，
    # 若写成 0/0.1 会让 retry_after 算出 0 而误报"马上可以重试"。
    refill_per_s = 0.0 if capacity == 0 else capacity / period
    return capacity, refill_per_s


class CallBudget:
    """调用预算。内部就是一个令牌桶，对外只暴露"打之前问一句"的语义。"""

    def __init__(self, capacity: float, refill_per_s: float,
                 clock: Optional[Callable[[], float]] = None,
                 sleep: Optional[Callable[[float], None]] = None):
        try:
            self._bucket = TokenBucket(capacity, refill_per_s, clock=clock, sleep=sleep)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"调用预算参数非法：{exc}") from exc

    # ---------- 调用前 ----------
    def before_call(self, n: int = 1) -> None:
        """有额度则扣减并返回 `None`；没有则抛 `RateLimitedError`（带 `retry_after`）。"""
        if self._bucket.take(n):
            return None

        capacity = self._bucket.capacity
        if n > capacity:
            # 永久不可满足：等多久都不会有 n 个令牌，别给一个会误导人的正数。
            retry: Optional[float] = None
            reason = f"请求数 {n} 超过容量 {capacity:g}，等待不会恢复"
        else:
            retry = self._bucket.retry_after(n)
            reason = ("补充速率为 0，等待不会恢复，请检查限流配置" if retry is None
                      else f"建议 {retry:.3f}s 后重试")
        raise RateLimitedError(
            f"调用预算不足：本次需要 {n}，当前余量 {self._bucket.available():.3f}，"
            f"容量 {capacity:g}；{reason}", retry)

    # ---------- 观测 ----------
    def stats(self) -> Dict[str, Any]:
        """给 metrics / 健康检查消费的稳定形状（键集合即契约，不要随手加字段）。"""
        raw = self._bucket.stats()
        tokens = raw["tokens"]
        return {"schema": SCHEMA,
                "capacity": raw["capacity"],
                "refill_per_s": raw["refill_per_s"],
                "allowed": raw["allowed"],
                "denied": raw["denied"],
                "tokens": tokens,
                # 容差 1e-9：0.1/s 地累积补充会让"刚好补满"落在 0.9999999999 上。
                "exhausted": tokens + 1e-9 < 1.0}

    def describe(self) -> Dict[str, Any]:
        """可安全打印的摘要：只有数量与计数，没有密钥、端点、请求内容。

        注意字段名刻意用 `remaining` 而不是令牌桶里的 `tokens`：这份摘要会进日志，
        留着 `token` 字样迟早有人把它当凭据字段去脱敏/误读。
        """
        stats = self.stats()
        return {"schema": SCHEMA,
                "capacity": stats["capacity"],
                "refill_per_s": stats["refill_per_s"],
                "remaining": stats["tokens"],
                "allowed": stats["allowed"],
                "denied": stats["denied"],
                "exhausted": stats["exhausted"]}

    def __repr__(self) -> str:
        stats = self.describe()
        return (f"CallBudget(capacity={stats['capacity']:g}, "
                f"refill_per_s={stats['refill_per_s']:.6g}, "
                f"remaining={stats['remaining']:.3f}, "
                f"exhausted={stats['exhausted']})")


def from_env(env: Optional[Dict[str, str]] = None) -> Optional[CallBudget]:
    """按 `LLMKE_ANSWER_RATE` 造预算；未设置/空串返回 `None`（= 不限流，保持现状）。

    解析失败抛 `ValueError`（由 `parse_limit` 抛出，这里补上环境变量名与原值）：
    配置写错应该在启动时就炸，而不是等到第一次调用才发现限流没生效。
    """
    env = os.environ if env is None else env
    raw = env.get(ENV_VAR)
    if raw is None or not str(raw).strip():
        return None
    try:
        capacity, refill_per_s = parse_limit(raw)
    except ValueError as exc:
        raise ValueError(f"{ENV_VAR}={raw!r} 无法解析：{exc}") from exc
    return CallBudget(capacity, refill_per_s)


@contextlib.contextmanager
def guard(budget: Optional[CallBudget], n: int = 1):
    """`budget` 为 `None` 时什么都不做；否则进块前先扣一次额度，不足即抛。

    有了它，调用方只写 `with guard(budget): call()`，无需在业务代码里判空——
    关闭限流就是"配置不写"，不是"改业务代码"。
    """
    if budget is None:
        yield None
        return
    budget.before_call(n)
    yield budget
