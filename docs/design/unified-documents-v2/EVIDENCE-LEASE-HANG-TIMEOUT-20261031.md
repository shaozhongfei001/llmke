# 卡住型租约故障：超时兜底与可复现反例（2026-10-31）

上一轮补的是"连不上会抛"；这一轮补"连上但不回包会卡"。两者故障形态完全不同，
后者更危险：不抛异常、不记失败、整轮调度停在那里，看起来一切正常。

## 两种形态的差别

| | 连接拒绝 | 连上不回包 |
|---|---|---|
| 表现 | 立刻抛 `OperationalError(2003)` | **阻塞**在 `recv`，默认可到 50s（`innodb_lock_wait_timeout`）或更久 |
| 上一版行为 | 已处理（LEASE_ERROR） | **未处理**：`run_cycle()` 卡住，`lease_errors` 一直是 0 |
| 可观测性 | 有告警 | 无任何记录 —— 最坏的一种 |

## 修法：超时写进驱动默认值，不靠调用方记得传

`make_pymysql_factory()` 现在自带：

```
connect_timeout=3, read_timeout=8, write_timeout=8
```

调用方显式传值优先（演练/测试会压短）。为什么不依赖机器上的 `my.cnf`：
交付机上那份配置不归我们管，且 `read_timeout` 属于客户端参数，服务端配置改不动它。

**不做线程级强制中断**：Python 无法安全打断卡在 C 层 `recv` 的调用。
写一个"看门狗"线程去 `kill` 只会让连接状态不可预测。所以这里的选择是：
让驱动自己按时返回错误，上层把错误变成 LEASE_ERROR + 告警。假装能中断就是骗人。

## 慢也是有信息的：`op_budget_s` + `LEASE_SLOW`

`MySqlLease` 记录 `last_op_s`（最近一次 acquire/renew 耗时）与 `slow_ops`。
调度器在成功路径上检查：超过 `op_budget_s`（默认 5s）就记 `slow_lease_ops` 并发一次
`LEASE_SLOW`（同 `alert_every_s` 节流）。

为什么慢也要报：**每轮卡 4s 不抛错**会让调度节拍从 0.5s 掉到 4.5s，积压会越滚越大，
但任何"失败计数"都是 0。这类退化只有耗时指标能抓到。

## 可复现反例（不再是"理论上会卡"）

**单测 `test_blackhole_peer_fails_fast_instead_of_hanging`**：起一个只 `accept()` 不回包的
TCP 对端（模拟"TCP 通、MySQL 不应答"），`read_timeout=1`，断言：

- `0.8 <= elapsed < 10` —— 下界同样重要：小于 0.8s 说明是"连不上就抛"，根本没走到等回包；
- 对端确实 `accepted`（证明是"连上但不回包"，不是连接被拒）；
- `last_op_s` 有记录。

**演练（Q 里 `graph:租约卡住型故障超时`）**：同样的黑洞对端，drill 跑 20s：

```
builds=0, lease_errors=3, alert_kinds=[LEASE_UNAVAILABLE ×3],
connections_accepted=5, read_timeout_s=2, elapsed=39.2s
schema_error=OperationalError (2013, 'Lost connection ... (timed out)')
```

含义：连接真的建立了 5 次、每次都按时超时、一次都没构建、告警都出来了、线程干净退出。

## 自己踩的坑

`_slow_state = {"last_at": 0.0}` 用来节流，结果**首次慢告警被吞**：
判据是 `now - last_at >= alert_every_s`，测试里假时钟从 0 起，`0 - 0 = 0 < 60`，判"没到窗口"。
改成 `None` 表示"还没报过"。生产上 monotonic 起点不为 0 大概率不触发，但这是逻辑错，改了。

## 还没做

- 真实 MySQL 的**锁等待**场景（`SELECT ... FOR UPDATE` 撞长事务等 50s）未构造：
  需要另一个连接持锁不放，能测但会占一个连接 50s，暂未做；
- 无**指标导出**：`slow_ops` / `lease_errors` 只在 `stats()` 里，Prometheus 未接；
- 超时值没有按部署环境自适应（跨机房 RTT 大时 8s 可能偏紧），当前只能调环境变量；
- Q 的卡住型检查依赖 `/tmp/ingest-*.json` 载荷，换机器要先跑 ingest（同其他图检查）。
