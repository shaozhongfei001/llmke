"""令牌桶与密钥来源链：确定性测试（假时钟、临时文件、无真实等待）。"""

import hashlib
import os
import threading

import pytest

from graph_engine_adapter.rate_limit import RateLimitedError, TokenBucket, guard
from graph_engine_adapter.secret_source import (
    MissingSecret,
    SecretSource,
    fingerprint,
    warn_if_world_readable,
)

ENV_NAME = "LLMKE_TEST_KEY_ENV_WINS"


class FakeClock:
    """假时钟 + 假 sleep：sleep 只推进虚拟时间并记录被要求等多久。"""

    def __init__(self, start=100.0):
        self.now_s = start
        self.sleeps = []

    def clock(self):
        return self.now_s

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now_s += seconds

    def advance(self, seconds):
        self.now_s += seconds


def make_bucket(capacity=2.0, refill=1.0, fake=None):
    fake = fake or FakeClock()
    bucket = TokenBucket(capacity, refill, clock=fake.clock, sleep=fake.sleep)
    return bucket, fake


# ---------------------------------------------------------------- 令牌桶基本语义


def test_bucket_starts_full():
    bucket, _fake = make_bucket(capacity=3.0)
    stats = bucket.stats()
    assert stats["tokens"] == pytest.approx(3.0)
    assert stats["allowed"] == 0 and stats["denied"] == 0
    assert stats["capacity"] == pytest.approx(3.0)


def test_take_drains_then_denies():
    bucket, fake = make_bucket(capacity=3.0)
    assert [bucket.take() for _ in range(3)] == [True, True, True]
    assert bucket.take() is False
    stats = bucket.stats()
    assert stats["allowed"] == 3 and stats["denied"] == 1
    assert stats["tokens"] == pytest.approx(0.0)
    # 拒绝不推进时钟、也不补令牌：假时钟没被动过
    assert fake.sleeps == []


def test_refill_by_elapsed_time():
    bucket, fake = make_bucket(capacity=2.0, refill=1.0)
    bucket.take(2)
    assert bucket.take() is False
    fake.advance(2.0)
    assert bucket.stats()["tokens"] == pytest.approx(2.0)
    assert bucket.take() is True


def test_refill_never_exceeds_capacity():
    bucket, fake = make_bucket(capacity=2.0, refill=1.0)
    bucket.take(2)
    fake.advance(10_000.0)
    assert bucket.available() == pytest.approx(2.0)


def test_zero_refill_rate_never_divides_by_zero():
    bucket, fake = make_bucket(capacity=2.0, refill=0.0)
    bucket.take(2)
    fake.advance(60.0)
    assert bucket.take() is False
    assert bucket.wait_take(1) is None          # 等也不会恢复，立刻判失败
    assert bucket.wait_take(1, timeout=5.0) is None
    assert bucket.retry_after(1) is None
    assert fake.sleeps == []
    assert bucket.available() == pytest.approx(0.0)


def test_zero_capacity_never_divides_by_zero():
    bucket, fake = make_bucket(capacity=0.0, refill=5.0)
    assert bucket.available() == pytest.approx(0.0)
    assert bucket.take(1) is False
    assert bucket.wait_take(1, timeout=1.0) is None
    fake.advance(30.0)
    assert bucket.take(1) is False
    assert fake.sleeps == []


def test_n_larger_than_capacity_is_rejected_without_deduction():
    bucket, _fake = make_bucket(capacity=2.0, refill=1.0)
    assert bucket.take(3) is False
    assert bucket.available() == pytest.approx(2.0)      # 没被扣成负数
    assert bucket.stats()["denied"] == 1
    assert bucket.wait_take(3, timeout=100.0) is None
    assert bucket.available() == pytest.approx(2.0)


def test_non_positive_n_is_rejected():
    bucket, _fake = make_bucket()
    with pytest.raises(ValueError):
        bucket.take(0)
    with pytest.raises(ValueError):
        bucket.take(-1)
    with pytest.raises(ValueError):
        bucket.wait_take(0)
    with pytest.raises(TypeError):
        bucket.take(1.5)


def test_fractional_refill_accumulates():
    bucket, fake = make_bucket(capacity=2.0, refill=1.0)
    bucket.take(2)
    fake.advance(0.4)
    assert bucket.take(1) is False                       # 0.4 个令牌不够
    fake.advance(0.6)
    assert bucket.take(1) is True                        # 0.4 + 0.6 够，说明没丢小数


def test_negative_config_is_rejected():
    with pytest.raises(ValueError):
        TokenBucket(-1.0, 1.0)
    with pytest.raises(ValueError):
        TokenBucket(1.0, -0.5)


# ---------------------------------------------------------------- wait_take


def test_wait_take_returns_zero_when_immediately_available():
    bucket, fake = make_bucket(capacity=2.0, refill=1.0)
    assert bucket.wait_take(1) == 0.0
    assert bucket.wait_take(1) == 0.0
    assert bucket.wait_take(1, timeout=0.0) is None        # 第三个才真的没有
    assert fake.sleeps == []
    assert bucket.stats()["allowed"] == 2


def test_wait_take_sleeps_and_reports_waited_time():
    bucket, fake = make_bucket(capacity=2.0, refill=1.0)
    bucket.take(2)
    waited = bucket.wait_take(1)
    assert waited == pytest.approx(1.0)
    assert fake.sleeps == [pytest.approx(1.0)]
    assert bucket.stats()["waited_s"] == pytest.approx(1.0)
    assert bucket.available() == pytest.approx(0.0)


def test_wait_take_timeout_too_short_returns_none_without_deduction():
    bucket, fake = make_bucket(capacity=2.0, refill=0.5)
    bucket.take(2)
    assert bucket.wait_take(1, timeout=1.0) is None       # 需要 2.0s，只给 1.0s
    assert fake.sleeps == []                               # 根本没睡
    assert bucket.available() == pytest.approx(0.0)        # 也没扣成负数
    assert bucket.stats()["waited_s"] == pytest.approx(0.0)


def test_wait_take_with_zero_timeout_only_takes_instant_tokens():
    bucket, _fake = make_bucket(capacity=2.0, refill=1.0)
    assert bucket.wait_take(1, timeout=0.0) == 0.0
    assert bucket.take(1) is True                          # 把剩下的取光
    assert bucket.wait_take(1, timeout=0.0) is None


def test_wait_take_does_not_hold_the_lock_while_sleeping():
    """睡眠期间别的线程必须还能进桶；抱着锁睡会让所有调用方一起排队。"""
    fake = FakeClock()
    outcome = {}

    def probing_sleep(seconds):
        def probe():
            outcome["granted"] = bucket.take(1)

        thread = threading.Thread(target=probe)
        thread.start()
        thread.join(timeout=2.0)
        outcome["released"] = not thread.is_alive()   # 卡住就说明锁没放开
        fake.advance(seconds)

    bucket = TokenBucket(2.0, 1.0, clock=fake.clock, sleep=probing_sleep)
    bucket.take(2)
    assert bucket.wait_take(1) == pytest.approx(1.0)
    assert outcome["released"] is True
    assert outcome["granted"] is False                 # 那一刻确实还没令牌


# ---------------------------------------------------------------- guard


def test_guard_raises_with_retry_suggestion():
    bucket, _fake = make_bucket(capacity=1.0, refill=1.0)
    bucket.take(1)
    with pytest.raises(RateLimitedError) as info:
        with guard(bucket):
            raise AssertionError("不该进入上下文体")
    message = str(info.value)
    assert "1.0" in message and "重试" in message
    assert info.value.retry_after == pytest.approx(1.0)


def test_guard_passes_when_token_available():
    bucket, _fake = make_bucket(capacity=2.0, refill=1.0)
    with guard(bucket, 2) as entered:
        assert entered is bucket
    assert bucket.available() == pytest.approx(0.0)


def test_guard_on_unrecoverable_bucket_says_wait_is_useless():
    bucket, _fake = make_bucket(capacity=1.0, refill=0.0)
    bucket.take(1)
    with pytest.raises(RateLimitedError) as info:
        with guard(bucket):
            pass
    assert "补充速率为 0" in str(info.value)
    assert info.value.retry_after is None


# ---------------------------------------------------------------- 并发


def test_threads_cannot_overdraw():
    capacity = 5
    bucket = TokenBucket(capacity, 0.0)                    # 不补充 → 结果完全确定
    workers = 8
    barrier = threading.Barrier(workers)
    results = []
    lock = threading.Lock()

    def worker():
        barrier.wait()
        granted = bucket.take(1)
        with lock:
            results.append(granted)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == workers
    assert sum(results) == capacity                        # 既没超发，也没漏发
    stats = bucket.stats()
    assert stats["allowed"] == capacity and stats["denied"] == workers - capacity
    assert stats["tokens"] == pytest.approx(0.0)


# ---------------------------------------------------------------- 密钥来源链


def test_env_wins_over_file(tmp_path, monkeypatch):
    path = tmp_path / "key.txt"
    path.write_text("value-from-file\n", encoding="utf-8")
    monkeypatch.setenv(ENV_NAME, "value-from-env\n")

    source = SecretSource([("env", ENV_NAME), ("file", str(path))])
    assert source.get() == "value-from-env"                # 换行被去掉

    described = source.describe()
    assert described["resolved"]["kind"] == "env"
    assert described["sources"][1]["state"] == "present"    # 文件也在，只是没被选中


def test_injected_environ_is_honoured():
    source = SecretSource([("env", ENV_NAME)], environ={ENV_NAME: "  injected-value  "})
    assert source.get() == "injected-value"


def test_file_used_when_env_absent_and_stripped(tmp_path):
    path = tmp_path / "key.txt"
    path.write_text("   file-based-value \n\n", encoding="utf-8")
    source = SecretSource([("env", "LLMKE_TEST_ABSENT_XYZ"), ("file", str(path))],
                          environ={})
    assert source.get() == "file-based-value"
    assert source.describe()["resolved"]["kind"] == "file"


def test_absent_source_returns_none_and_describe_says_absent(tmp_path):
    missing = tmp_path / "nope.txt"
    source = SecretSource([("env", "LLMKE_TEST_ABSENT_XYZ"), ("file", str(missing))],
                          environ={ENV_NAME: "   "})     # 只有空白 = 没有
    assert source.get() is None
    described = source.describe()
    assert described["present"] is False
    assert described["resolved"] == {"state": "absent"}
    assert [row["state"] for row in described["sources"]] == ["absent", "absent"]
    assert [row["fingerprint"] for row in described["sources"]] == [None, None]


def test_require_raises_listing_sources_without_value(tmp_path):
    missing = tmp_path / "nope.txt"
    source = SecretSource([("env", "LLMKE_TEST_ABSENT_XYZ"), ("file", str(missing))],
                          environ={})
    with pytest.raises(MissingSecret) as info:
        source.require()
    message = str(info.value)
    assert "LLMKE_TEST_ABSENT_XYZ" in message
    assert str(missing) in message
    assert "env" in message and "file" in message
    assert "值不入日志" in message


def test_require_returns_value_when_present(tmp_path):
    path = tmp_path / "key.txt"
    path.write_text("value-from-file\n", encoding="utf-8")
    source = SecretSource.from_env("LLMKE_TEST_ABSENT_XYZ", str(path), environ={})
    assert source.require() == "value-from-file"


def test_describe_exposes_only_fingerprint_not_value():
    plain = "zs-distinct-abc123"
    source = SecretSource([("env", "LLMKE_TEST_ABSENT_XYZ"), ("value", plain)],
                          environ={})
    described = source.describe()
    assert described["present"] is True
    assert described["resolved"]["kind"] == "value"
    assert described["resolved"]["fingerprint"] == hashlib.sha256(
        plain.encode("utf-8")).hexdigest()[:8]
    assert plain not in str(described)
    assert len(described["resolved"]["fingerprint"]) == 8   # 指纹定长 8 位


def test_fingerprint_is_sha256_prefix_and_none_for_empty():
    assert fingerprint(None) is None
    assert fingerprint("") is None
    expected = hashlib.sha256(b"value-from-env").hexdigest()[:8]
    assert fingerprint("value-from-env") == expected
    assert len(fingerprint("value-from-env")) == 8


def test_from_env_helper_builds_chain(tmp_path):
    path = tmp_path / "key.txt"
    path.write_text("fallback-value\n", encoding="utf-8")

    only_env = SecretSource.from_env("LLMKE_TEST_ABSENT_XYZ", environ={})
    assert [row["kind"] for row in only_env.describe()["sources"]] == ["env"]
    assert only_env.get() is None

    both = SecretSource.from_env("LLMKE_TEST_ABSENT_XYZ", str(path), environ={})
    assert [row["kind"] for row in both.describe()["sources"]] == ["env", "file"]
    assert both.get() == "fallback-value"


def test_literal_source_is_used_last():
    source = SecretSource([("env", "LLMKE_TEST_ABSENT_XYZ"), ("literal", "inline-value")],
                          environ={})
    assert source.get() == "inline-value"
    rows = source.describe()["sources"]
    assert [row["state"] for row in rows] == ["absent", "present"]


def test_unknown_source_kind_raises():
    with pytest.raises(ValueError):
        SecretSource([("kms", "arn:whatever")])


@pytest.mark.parametrize("mode,expected", [(0o644, True), (0o640, True), (0o600, False)])
def test_world_readable_detection(tmp_path, mode, expected):
    path = tmp_path / "key.txt"
    path.write_text("x\n", encoding="utf-8")
    os.chmod(path, mode)
    assert warn_if_world_readable(str(path)) is expected


def test_world_readable_missing_file_is_false(tmp_path):
    assert warn_if_world_readable(str(tmp_path / "absent.txt")) is False


def test_permission_probe_does_not_change_mode(tmp_path):
    path = tmp_path / "key.txt"
    path.write_text("x\n", encoding="utf-8")
    os.chmod(path, 0o644)
    before = os.stat(path).st_mode
    assert warn_if_world_readable(str(path)) is True
    assert os.stat(path).st_mode == before                 # 只提示，不改权限
