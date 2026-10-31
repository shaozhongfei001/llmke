"""调用预算：配置解析、耗尽/恢复语义、环境变量开关的确定性测试。

假时钟 + 假 sleep：所有"补多少令牌、什么时候能继续打"都靠推进虚拟时间断言，
不真等、不 flaky。断言的是**具体数值与计数**，不是"没抛异常"。
"""

import pytest

from graph_engine_adapter.llm_budget import (
    ENV_VAR,
    SCHEMA,
    CallBudget,
    RateLimitedError,
    from_env,
    guard,
    parse_limit,
)

STAT_BUDGET_KEYS = {"schema", "capacity", "refill_per_s", "allowed", "denied",
                    "tokens", "exhausted"}
DESCRIBE_KEYS = {"schema", "capacity", "refill_per_s", "remaining", "allowed",
                 "denied", "exhausted"}


class FakeClock:
    """假时钟 + 假 sleep：sleep 只推进虚拟时间并记录被要求等多久。"""

    def __init__(self, start=1000.0):
        self.now_s = start
        self.sleeps = []

    def clock(self):
        return self.now_s

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now_s += seconds

    def advance(self, seconds):
        self.now_s += seconds


def make_budget(capacity=6.0, refill=0.1):
    fake = FakeClock()
    return CallBudget(capacity, refill, clock=fake.clock, sleep=fake.sleep), fake


# ------------------------------------------------------------------ parse_limit


def test_parse_six_per_minute_is_six_capacity_and_one_tenth_per_second():
    capacity, refill = parse_limit("6/60")
    assert capacity == pytest.approx(6.0)
    assert refill == pytest.approx(0.1)


def test_parse_ten_per_second():
    assert parse_limit("10/1") == (pytest.approx(10.0), pytest.approx(10.0))


def test_parse_zero_capacity_means_no_calls_allowed():
    capacity, refill = parse_limit("0/60")
    assert capacity == 0.0
    # 0 次/60 秒 = 永不允许；补充速率必须是 0，否则 retry_after 会误报"马上可重试"
    assert refill == 0.0


def test_parse_tolerates_surrounding_whitespace():
    assert parse_limit("  12 / 30  ") == (pytest.approx(12.0), pytest.approx(0.4))


def test_parse_fractional_allowance_is_supported():
    capacity, refill = parse_limit("0.5/10")
    assert capacity == pytest.approx(0.5)
    assert refill == pytest.approx(0.05)


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_parse_rejects_empty(bad):
    with pytest.raises(ValueError) as exc:
        parse_limit(bad)
    assert "N/PERIOD" in str(exc.value)


@pytest.mark.parametrize("bad", ["6", "60", "/60", "6/"])
def test_parse_rejects_missing_slash(bad):
    with pytest.raises(ValueError) as exc:
        parse_limit(bad)
    assert "N/PERIOD" in str(exc.value)


@pytest.mark.parametrize("bad", ["6/0", "6/-1", "-6/60"])
def test_parse_rejects_zero_or_negative_denominator_and_negative_capacity(bad):
    with pytest.raises(ValueError) as exc:
        parse_limit(bad)
    message = str(exc.value)
    assert bad in message or "正数" in message


@pytest.mark.parametrize("bad", ["abc", "6/abc", "six/60", "6/60/1", "1e/9"])
def test_parse_rejects_non_numeric_and_extra_slash(bad):
    with pytest.raises(ValueError) as exc:
        parse_limit(bad)
    message = str(exc.value)
    assert bad in message and ("斜杠" in message or "非数字" in message)


@pytest.mark.parametrize("bad", ["nan/60", "6/inf"])
def test_parse_rejects_non_finite(bad):
    with pytest.raises(ValueError) as exc:
        parse_limit(bad)
    assert "有限" in str(exc.value)


# ------------------------------------------------------------ 耗尽与恢复语义


def test_before_call_returns_none_while_quota_remains():
    budget, _fake = make_budget(capacity=3.0, refill=1.0)
    assert budget.before_call() is None
    assert budget.before_call() is None
    assert budget.stats()["allowed"] == 2


def test_drain_then_deny_and_counts_are_exact():
    budget, _fake = make_budget(capacity=2.0, refill=1.0)
    assert budget.before_call() is None
    assert budget.before_call() is None
    with pytest.raises(RateLimitedError):
        budget.before_call()
    stats = budget.stats()
    assert stats["allowed"] == 2
    assert stats["denied"] == 1
    assert stats["tokens"] == pytest.approx(0.0)
    assert stats["exhausted"] is True


def test_error_carries_positive_retry_after():
    """6/60 打空后，补 1 个令牌需要 1/0.1 = 10 秒。"""
    budget, _fake = make_budget(capacity=6.0, refill=0.1)
    for _ in range(6):
        budget.before_call()
    with pytest.raises(RateLimitedError) as exc:
        budget.before_call()
    assert exc.value.retry_after == pytest.approx(10.0)
    assert exc.value.retry_after > 0


def test_zero_budget_denies_everything_without_reachable_retry():
    budget, _fake = make_budget(capacity=0.0, refill=0.0)
    with pytest.raises(RateLimitedError) as exc:
        budget.before_call()
    # 0/60：等多久都不会有额度，必须明确说"不可恢复"而不是给个正数
    assert exc.value.retry_after is None
    stats = budget.stats()
    assert stats["allowed"] == 0 and stats["denied"] == 1
    assert stats["capacity"] == 0.0 and stats["exhausted"] is True


def test_advancing_clock_restores_quota():
    budget, fake = make_budget(capacity=2.0, refill=1.0)
    budget.before_call()
    budget.before_call()
    with pytest.raises(RateLimitedError):
        budget.before_call()

    fake.advance(0.4)          # 补 0.4 个，仍不足 1
    assert budget.stats()["tokens"] == pytest.approx(0.4)
    with pytest.raises(RateLimitedError) as exc:
        budget.before_call()
    assert exc.value.retry_after == pytest.approx(0.6)

    fake.advance(1.0)          # 累计 1.4，够 1 个
    assert budget.before_call() is None
    stats = budget.stats()
    assert stats["allowed"] == 3
    assert stats["tokens"] == pytest.approx(0.4, abs=1e-6)


def test_refill_never_exceeds_capacity():
    budget, fake = make_budget(capacity=2.0, refill=1.0)
    budget.before_call()
    fake.advance(1000)
    assert budget.stats()["tokens"] == pytest.approx(2.0)
    assert budget.stats()["exhausted"] is False


def test_n_greater_than_capacity_is_rejected_without_deduction():
    budget, _fake = make_budget(capacity=2.0, refill=1.0)
    with pytest.raises(RateLimitedError) as exc:
        budget.before_call(3)
    assert exc.value.retry_after is None       # 永久不可满足，别给误导性的正数
    stats = budget.stats()
    assert stats["tokens"] == pytest.approx(2.0)   # 未扣减
    assert stats["allowed"] == 0 and stats["denied"] == 1


def test_before_call_with_n_deducts_n_tokens():
    budget, _fake = make_budget(capacity=5.0, refill=1.0)
    assert budget.before_call(3) is None
    assert budget.stats()["tokens"] == pytest.approx(2.0)
    assert budget.stats()["allowed"] == 1


# ------------------------------------------------------------------ from_env


def test_from_env_unset_returns_none():
    assert from_env({}) is None


@pytest.mark.parametrize("blank", ["", "   "])
def test_from_env_blank_returns_none(blank):
    assert from_env({ENV_VAR: blank}) is None


def test_from_env_configured_returns_working_budget():
    budget = from_env({ENV_VAR: "6/60"})
    assert isinstance(budget, CallBudget)
    stats = budget.stats()
    assert stats["capacity"] == pytest.approx(6.0)
    assert stats["refill_per_s"] == pytest.approx(0.1)
    for _ in range(6):
        budget.before_call()
    with pytest.raises(RateLimitedError):
        budget.before_call()


def test_from_env_invalid_value_raises_with_original_value():
    with pytest.raises(ValueError) as exc:
        from_env({ENV_VAR: "abc"})
    message = str(exc.value)
    assert ENV_VAR in message and "abc" in message


# --------------------------------------------------------------------- guard


def test_guard_none_is_a_noop():
    reached = False
    with guard(None) as entered:
        reached = True
    assert reached is True
    assert entered is None


def test_guard_allows_while_quota_remains():
    budget, _fake = make_budget(capacity=2.0, refill=1.0)
    with guard(budget) as entered:
        assert entered is budget
    assert budget.stats()["allowed"] == 1


def test_guard_raises_when_exhausted_and_body_never_runs():
    budget, _fake = make_budget(capacity=0.0, refill=0.0)
    body_ran = False
    with pytest.raises(RateLimitedError):
        with guard(budget):
            body_ran = True
    assert body_ran is False


# --------------------------------------------------------------- 可观测性


def test_stats_shape_is_fixed():
    budget, _fake = make_budget()
    stats = budget.stats()
    assert set(stats) == STAT_BUDGET_KEYS
    assert stats["schema"] == SCHEMA
    assert stats["exhausted"] is False
    assert stats["allowed"] == 0 and stats["denied"] == 0


def test_describe_is_safe_to_log():
    budget, _fake = make_budget(capacity=6.0, refill=0.1)
    described = budget.describe()
    assert set(described) == DESCRIBE_KEYS
    rendered = repr(described).lower() + " " + repr(budget).lower()
    for banned in ("key", "token", "secret", "password", "bearer", "http"):
        assert banned not in rendered


def test_describe_reflects_usage():
    budget, _fake = make_budget(capacity=2.0, refill=1.0)
    budget.before_call()
    with pytest.raises(RateLimitedError):
        budget.before_call(2)          # n > 剩余额度：拒绝并计数
    described = budget.describe()
    assert described["allowed"] == 1 and described["denied"] == 1
    assert described["remaining"] == pytest.approx(1.0)
    assert described["exhausted"] is False
