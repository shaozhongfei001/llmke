# 租约故障可见性：存储挂了不能"安静地停摆"（2026-10-31）

`rebuild_scheduler.py` 加 `on_alert` 接缝 + `LEASE_ERROR` 决策；6 项单测、1 项真库故障恢复、
1 个演练（连接拒绝）和 1 条 Q 检查。

## 修的是什么

上一版的 `run_cycle()` 直接 `acquired = self.lease.acquire()`，**没有 try**。
MySQL 版租约一抛异常（连接拒绝、超时、server gone away），异常会穿过 `run()` 打死整个循环：

- 服务进程还活着（线程死了但不退出进程）；
- 重建**永远停摆**，读路径一直读旧快照；
- 除了日志里一条栈，**没人知道**。

这正是"fail-closed 但无声"最坏的一种：看起来在跑，其实什么都不做。

## 现在的行为

| 场景 | 决策 | 是否构建 | 可见性 |
|---|---|---|---|
| 租约存储抛异常（acquire） | `LEASE_ERROR` | 否 | `lease_errors += 1`，边沿触发 `LEASE_UNAVAILABLE` |
| 续租抛异常 | `LOST_LEASE` | 否 | 同上 + `lost_lease += 1`（无法确认是主就不能写） |
| 租约被他人持有 | `NOT_LEADER` | 否 | `not_leader += 1`（正常跟随，不告警） |
| 恢复后成功拿到 | 正常 | 是 | 一次 `LEASE_RECOVERED` |

告警是**边沿触发 + 节流**：首次失败立即报，持续失败每 `alert_every_s`（默认 60s）报一次，
恢复报一次。不是"每轮都报"——5s 一轮的故障挂一天会刷 1.7 万条，等于没有告警。

`on_alert` 自己抛异常只记 `alert_sink_errors`，主循环照跑：**发不出告警不能变成服务停摆**。

## 实测

单测 `tests/test_scheduler_lease_faults.py`（6 项，假时钟）：
`run(max_cycles=3)` 在 acquire 全抛时不向外抛、`lease_errors=3`、`builds=0`；
节流（10s 内不重报、60s 后重报）；恢复只报一次；告警通道抛错不拖死循环；renew 抛错不构建。

真库 `tests/test_lease_mysql.py::test_real_mysql_outage_then_recovery_builds_once`：
先连不上 → `LEASE_ERROR` + `LEASE_UNAVAILABLE` + 未构建；恢复后 → `BUILT` + `LEASE_RECOVERED`。
（隔离库 `gienrag_v2_restore`，7 passed）

演练 `v2_lease_drill.py --lease-backend mysql`（端口指向 127.0.0.1:1，必然拒绝）：

```
builds=0, lease_errors=5~6, thread_stopped=True
alert_kinds=[LEASE_UNAVAILABLE × N], alerts_sent=5, sink_errors=0
schema_error=OperationalError (2003, "Can't connect ...")
```

建表也失败（`ensure_schema` 在启动时就撞上数据库不可用），演练不再直接 `SystemExit`，
而是继续跑——这正是需要观察的场景。

## 一处自己踩的坑

`test_alert_sink_failure...` 第一版断言 `alert_sink_errors == 2`，跑红得到 1。
原因不是 bug：两轮之间时钟没走，第二次落在节流窗口内、根本没发起投递。
按真实语义改成"推进 61s 再看第二次投递"。

## 还没做

- **没有接真实告警通道**：只留 `on_alert` 接缝，Webhook/短信/企业微信均未接，
  所以"告警能发出去"这件事在部署侧仍是空白；
- 未测**连上但查询超时**（`read_timeout` / `innodb_lock_wait_timeout` 50s）——
  这类故障表现为"卡住"而非"抛错"，会让一轮 cycle 长时间不返回，当前没有超时保护；
- 未做故障期间的**指标导出**（Prometheus 等），`stats()` 只能被本地读；
- 未做"长时间故障后的自动降级"（例如超过 N 分钟退回单实例文件租约），刻意不做：
  静默改变选主语义比停摆更危险。
