# 多副本共享配额 + 租户维度指标（2026-11-02）

上一步证明了"单进程 30 并发只放行 limit 个"，但**多副本**时每个进程有自己的内存与连接，
唯一共享的是数据库。要证明"3 副本总量不是 3×limit"，必须在多个进程里同时压。

## 多进程压测（`v2_quota_multinode_drill.py`）

3 个**独立进程**各起一个 `POST /rebuild` 入口（各自连接 + 各自计数器），
父进程把 30 个请求轮询打到三个端口。

```
nodes=3 limit=6 requests=30
accepted=6  denied=24  used_in_db=6
per_node_accepted={43399:4, 34445:1, 34995:1}
per_node_requests={43399:10, 34445:10, 34995:10}
status=PASS
```

关键数字是 **accepted=6 而不是 18**：三个进程共用同一行计数，SQL 原子自增保证总量不被放大。

## 压出来的三个真问题

### 1. 死锁 1213（会让一部分请求 503）

并发 UPSERT 同一行时 InnoDB 判死锁：

```
[warn] 配额查询失败：SharedQuotaError ... OperationalError: (1213, 'Deadlock found when trying to get lock')
```

修：`_consume_with_retry` 对 **1213/1205** 重试最多 3 次（带抖动退避），其它错误立即抛出。
死锁会回滚整个事务，所以重试不会重复计数。加完连跑 5 次全部 PASS。

### 2. 租户名用秒级时间戳 → 自己打自己

压测连跑时第二次 `accepted=0 denied=12`，看起来像"配额没共享"，实际是两次跑在同一秒、
共用同一个租户窗口，第二次一开始 `used=limit`。改为毫秒 + pid。

### 3. 配额库异常时连接被直接断开

原来 handler 里 `quota.take()` 没有兜异常，DB 一抖客户端只看到 `RemoteDisconnected`，
无从判断。改为明确 `503 {"status":"QUOTA_UNAVAILABLE"}` 并打日志。

## 租户维度指标

`metrics.render_quota(quota_stats)` 渲染：

```
# TYPE llmke_graph_quota_used gauge
llmke_graph_quota_used{tenant="demo"} 2
# TYPE llmke_graph_quota_limit gauge
llmke_graph_quota_limit{tenant="demo"} 2
```

worker 的 `/metrics` 在配置了配额时自动追加；**配额查询失败只掉这一段**
（追加 `# quota_stats_unavailable <类型>`），不会让整页 500。

真跑：worker 起在 18903、`--quota-limit 2`，连发 3 次 `POST /rebuild`：

```
202 202 429
llmke_graph_quota_used{tenant="demo"} 2
llmke_graph_quota_limit{tenant="demo"} 2
```

## 测试

- `tests/test_worker_rebuild_api.py` 10 项：新增配额指标渲染、配额统计失败降级、
  **配额查询异常 → 503 而不是连接重置**；
- `tests/test_quota_shared.py` 19 项：新增死锁重试（3 次后成功、只计一次）与不可重试错误 fail-fast。

## 边界

- 压测在同一台机器上的 3 个进程（loopback），不是真的跨机；跨机差异主要在 RTT 与断连，
  计数器语义不受影响；
- 固定窗口在边界仍有最多 2×limit 的瞬时突发（未做滑动窗口/GCRA）；
- `per_node_requests` 只证明流量分到了三个进程，**不保证公平**——limit 小时一个进程可能抢到全部放行；
- 租户指标只导出当前窗口，不保留历史（要看趋势需外部 TSDB 抓取）。
