# 按租户配额 + 指标标签（2026-11-01）

多租户上线后最先遇到的两个问题，都是"总量看不出来是谁"：

1. 一个库把配额吃光 → 所有库一起被限流；
2. 面板只有总量 → 看不出哪个库把量打上来的。

## 配额（`quota.py`）

- `QuotaRegistry`：每个键一个令牌桶，**按键隔离**；
- `max_keys` + LRU 淘汰：键来自外部（kb_id/租户名），无上限就是内存泄漏，
  淘汰次数记进 `stats()["evicted"]`，不悄悄发生；
- `normalize_key`：空键归 `default`，超长截断到 128 字符（超长 kb_id 会撑爆内存与日志）；
- `SharedQuota`：**先过租户桶，再过全局桶**。顺序不能反——先扣全局的话，
  一个库打满自己配额时已经把全局份额吃掉了，租户隔离等于没有。

真实演示（capacity=2，无补充）：

```
takes    [('kb_a', True), ('kb_a', True), ('kb_a', False), ('kb_b', True)]
snapshot {'kb_a': {'allowed': 2, 'denied': 1}, 'kb_b': {'allowed': 1, 'denied': 0}}
```

kb_a 被拒时 kb_b 照常放行——这就是租户隔离的可观测形态。

## 指标标签（`metrics.render(labels=...)`）

- 标签**按 key 排序**输出，保证同一组标签每次渲染一致（面板与快照可比）；
- 值按 Prometheus 文本格式转义（反斜杠、双引号、换行）；
- 不传标签时输出与原来**逐字节一致**（有测试钉住，否则所有既有面板都会对不上）；
- worker 新增 `--metrics-label-kb`：一个 worker 服务一个库时导出自带 `kb="..."`。

真实输出：

```
llmke_graph_rebuild_pending{kb="kb_a"} 0
llmke_graph_rebuild_pending{kb="kb_b"} 0
```

## 测试

`tests/test_quota_labels.py` 9 项：两租户互不阻塞、按 key 独立补充、LRU 淘汰并计数、
键规范化与截断、先租户后全局、全局耗尽拒绝、标签排序与转义、无标签输出不变、
`snapshot()` 只输出计数不含请求内容。

## 边界

- **单进程内生效**：多副本部署时每个实例各自计数，总量 = 副本数 × 配额。
  这条必须写进部署文档，否则"配额 100 QPS"在 3 副本下就是 300；
- 没做跨实例共享配额（需要 Redis/MySQL 原子计数器，是另一套机制）；
- 淘汰是近似 LRU（dict 插入序），并发极高时可能淘汰刚用过的键；
- 配额只覆盖"重建请求"这一层，未覆盖单次构建内部的 LLM 调用（那由 `llm_budget` 管）。
