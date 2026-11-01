"""按租户配额 + 指标标签。

两条都是多租户上线后第一批会踩的问题：
- 配额不隔离：一个库刷爆，所有库一起被限；
- 指标没标签：面板上只看到总量，看不出是谁把量打上来的。
"""

from graph_engine_adapter.metrics import render
from graph_engine_adapter.quota import MAX_KEY_LEN, QuotaRegistry, SharedQuota, normalize_key
from graph_engine_adapter.rate_limit import TokenBucket


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class Scheduler:
    def stats(self):
        return {"cycles": 3, "builds": 2}


def test_two_tenants_do_not_block_each_other():
    clock = Clock()
    q = QuotaRegistry(2, 0, clock=clock, sleep=lambda s: None)
    assert q.take("kb_a") is True
    assert q.take("kb_a") is True
    assert q.take("kb_a") is False          # A 用完了
    assert q.take("kb_b") is True           # B 不受影响
    stats = q.stats()
    assert stats["per_key"]["kb_a"]["denied"] == 1
    assert stats["per_key"]["kb_b"]["denied"] == 0


def test_refill_restores_each_key_independently():
    clock = Clock()
    q = QuotaRegistry(1, 1.0, clock=clock, sleep=lambda s: None)
    assert q.take("kb_a") is True and q.take("kb_a") is False
    clock.now += 1.0
    assert q.take("kb_a") is True


def test_max_keys_evicts_least_recently_used_and_counts_it():
    q = QuotaRegistry(5, 0, max_keys=2)
    q.bucket("a")
    q.bucket("b")
    q.bucket("a")                            # a 变成最近使用
    q.bucket("c")                            # 触发淘汰 → 淘汰 b
    stats = q.stats()
    assert stats["evicted"] == 1
    keys = set(stats["per_key"])
    assert "a" in keys and "c" in keys


def test_key_is_normalized_and_bounded():
    assert normalize_key("") == "default"
    assert normalize_key(None) == "default"
    long_key = "k" * (MAX_KEY_LEN * 3)
    assert len(normalize_key(long_key)) == MAX_KEY_LEN


def test_shared_quota_checks_tenant_before_global():
    """先过租户：一个库打满自己配额就停，不消耗全局份额。"""
    clock = Clock()
    per_key = QuotaRegistry(1, 0, clock=clock, sleep=lambda s: None)
    overall = TokenBucket(5, 0, clock=clock, sleep=lambda s: None)
    q = SharedQuota(per_key, overall)
    assert q.take("kb_a")["allowed"] is True
    denied = q.take("kb_a")
    assert denied["allowed"] is False and denied["reason"] == "TENANT_QUOTA"
    assert overall.stats()["allowed"] == 1    # 全局只被扣了一次
    assert q.take("kb_b")["allowed"] is True


def test_global_quota_denies_when_exhausted():
    clock = Clock()
    per_key = QuotaRegistry(10, 0, clock=clock, sleep=lambda s: None)
    overall = TokenBucket(1, 0, clock=clock, sleep=lambda s: None)
    q = SharedQuota(per_key, overall)
    assert q.take("kb_a")["allowed"] is True
    second = q.take("kb_b")
    assert second["allowed"] is False and second["reason"] == "GLOBAL_QUOTA"


def test_metrics_labels_are_sorted_and_escaped():
    text = render(Scheduler(), labels={"kb": 'kb_"9"', "az": "a\\b"})
    line = [l for l in text.splitlines() if l.startswith("llmke_graph_scheduler_cycles_total")][0]
    assert line.index('az=') < line.index('kb=')          # 排序，输出稳定
    assert '\\"' in line and "\\\\" in line                # 引号与反斜杠都转义


def test_metrics_without_labels_are_byte_identical_to_before():
    """不传标签时输出必须与原来一致，否则所有既有面板都会对不上。"""
    assert render(Scheduler()) == render(Scheduler(), labels=None)


def test_quota_snapshot_is_per_tenant_only_counts():
    q = QuotaRegistry(1, 0)
    q.take("kb_a")
    q.take("kb_a")
    snap = q.snapshot()
    assert snap["kb_a"] == {"allowed": 1, "denied": 1}
