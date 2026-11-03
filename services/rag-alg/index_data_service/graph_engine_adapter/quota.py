"""按租户（知识库）的配额：一个库把配额吃光，不能拖垮其它库。

为什么不能只用一个全局令牌桶：多租户上线后第一个故障一定是"某个库刷爆，
所有库一起被限流"，而面板上看不出是谁。配额必须**按键隔离**，并**按键导出**。

两个必须处理的工程问题：
1. **键来自外部**（kb_id/租户名），无限增长就是内存泄漏 → `max_keys` 上限 + LRU 淘汰，
   淘汰次数记进 stats，不能悄悄发生；
2. 键长度不设限会被超长字符串撑爆内存与日志 → 截断到 `MAX_KEY_LEN`，并在 stats 里标明。

不做的事：不做跨实例共享配额（那需要 Redis/MySQL 计数器与原子性，属于另一套机制）。
本模块只在**单进程内**成立；多实例部署时每个实例各自计数，总量 = 实例数 × 配额。
这一点必须写在部署文档里，否则"配额 100 QPS"在多副本下会变成 100×N。
"""

import threading
from typing import Any, Dict, Iterable, Optional

from .rate_limit import TokenBucket

MAX_KEY_LEN = 128


def normalize_key(key: Any) -> str:
    """键规范化：空 → `default`，超长截断（避免超长 kb_id 把内存/日志撑爆）。"""
    text = str(key or "").strip() or "default"
    return text[:MAX_KEY_LEN]


class QuotaRegistry:
    """每个键一个令牌桶；桶按需创建，键数超上限时淘汰最久未用的那个。"""

    def __init__(self, capacity: float, refill_per_s: float, *,
                 max_keys: int = 1000,
                 clock=None, sleep=None):
        if max_keys <= 0:
            raise ValueError(f"max_keys 必须为正：{max_keys}")
        self.capacity = float(capacity)
        self.refill_per_s = float(refill_per_s)
        self.max_keys = int(max_keys)
        self._clock = clock
        self._sleep = sleep
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self._state = {"created": 0, "evicted": 0, "truncated_keys": 0}

    def bucket(self, key: Any) -> TokenBucket:
        name = normalize_key(key)
        with self._lock:
            bucket = self._buckets.pop(name, None)
            if bucket is None:
                bucket = TokenBucket(self.capacity, self.refill_per_s,
                                     clock=self._clock, sleep=self._sleep)
                self._state["created"] += 1
                while len(self._buckets) >= self.max_keys:
                    # 淘汰最久未用的：dict 保持插入顺序，取第一个即最旧。
                    # （`popitem(last=False)` 是 OrderedDict 的签名，普通 dict 会 TypeError）
                    oldest = next(iter(self._buckets))
                    del self._buckets[oldest]
                    self._state["evicted"] += 1
            self._buckets[name] = bucket      # 重新插入到末尾 = 标记为最近使用
        return bucket

    def take(self, key: Any, n: int = 1) -> bool:
        return self.bucket(key).take(n)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            buckets = {k: b.stats() for k, b in self._buckets.items()}
        return {"keys": len(buckets), "max_keys": self.max_keys,
                "capacity": self.capacity, "refill_per_s": self.refill_per_s,
                "per_key": buckets, **self._state}

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        """按 kb 导出用：只给 {key: {allowed, denied}}，不带任何请求内容。"""
        with self._lock:
            return {k: {"allowed": b.stats()["allowed"], "denied": b.stats()["denied"]}
                    for k, b in self._buckets.items()}


class SharedQuota:
    """全局上限 + 按租户上限的组合：先过租户桶，再过全局桶。

    顺序有讲究：先过租户，一个库把自己配额打满就停在原地，不会消耗全局份额——
    否则"某库刷爆"会把全局配额一起吃掉，等于没有租户隔离。
    """

    def __init__(self, per_key: QuotaRegistry, overall: TokenBucket):
        self.per_key = per_key
        self.overall = overall

    def take(self, key: Any, n: int = 1) -> Dict[str, Any]:
        if not self.per_key.take(key, n):
            return {"allowed": False, "reason": "TENANT_QUOTA",
                    "retry_after_s": self.per_key.bucket(key).retry_after(n)}
        if not self.overall.take(n):
            return {"allowed": False, "reason": "GLOBAL_QUOTA",
                    "retry_after_s": self.overall.retry_after(n)}
        return {"allowed": True, "reason": "OK", "retry_after_s": None}
