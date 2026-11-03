# 告警通道接线（worker → 企微/钉钉）（2026-11-01）

上一步只做了报文与签名（`alert_channels.py`），**没有调用方**——通道写好却没接上，
等于告警仍然发不出去。本步把它接进 worker，并真跑了一次"数据库不可用"的告警。

## 接线

`v2_graph_worker.py` 新增：

- `--alert-channel wecom|dingtalk` + `--alert-url`：群机器人通道；
- `--alert-secret-env`（默认 `LLMKE_ALERT_SECRET`）：**只存环境变量名**。
  密钥写在命令行上会进 `ps` 与 shell history，等于把告警通道的钥匙贴出去；
- 群机器人通道优先于旧的 `--alert-webhook`：两个都给会同时往两处发，事后说不清哪条到了；
- 缺 `--alert-url`、或钉钉缺 secret → **启动期 fail-fast**，而不是上线后每 60s 静默失败。

`build_lease()` 另改一处：MySQL 建表失败**不再启动即退出**。
原来的行为是"数据库不可用 → 进程直接不启动"，而这正是最该发告警的时刻。
现在改为打印 `[warn]` 后继续，由 `acquire` 走 `LEASE_ERROR` 路径计数并告警。

## 真跑（MySQL 指向 127.0.0.1:1，必然连不上）

```
worker --lease-backend mysql --enqueue-on-start --alert-channel wecom --alert-url http://127.0.0.1:18111/...
[warn] 租约建表失败，继续以失败态运行：OperationalError: (2003, "Can't connect to MySQL server ...")
stop: cycles=5, lease_errors=5, alerts_sent=1, builds=0
本地模拟网关收到 1 条：
  msgtype=markdown
  ### LLMKE 图引擎告警: LEASE_UNAVAILABLE
  > 级别: ALERT
  > 时间: 2026-11-01 16:03:50 UTC
  > 错误: OperationalError: (2003, "Can't connect to MySQL server on '127.0.0.1' ([Errno 111] ...)")
  > 影响: 重建已暂停（fail-closed），读路径继续读旧快照
```

5 个周期只发 1 条，说明边沿触发+节流生效（否则挂一天会刷上万条）。

## 端到端跑出来的一个真 bug

第一次真跑，群消息里的时间是 **`1970-01-01 04:01:38 UTC`**。
原因：调度器事件里的 `at` 用的是注入时钟（多为 `time.monotonic()`，起点是开机时刻），
通道却按 epoch 秒格式化。**单元测试发现不了**——测试用假时钟且不校验时间字段的语义。

修法：调度器事件补 `wall_time = time.time()`；通道优先取 `wall_time`/`ts`，最后才退回 `at`。
复跑后时间正确。

## 测试

`tests/test_worker_alert_wiring.py` 7 项：无配置返回 None、企微通道可构造、
钉钉缺 secret fail-fast、按环境变量名取 secret、缺 url fail-fast、
旧 webhook 仍可用、两者都给时优先通道。
另有既有 `test_alert_channels`(16) + `test_scheduler_lease_faults` 回归，共 32 项通过。

## 边界

- **没有真实企业微信/钉钉账号**：只验证到"本地模拟网关收到正确报文"，`errcode:0` 是桩返回的；
- 通道自身不做去重（去重在 `WebhookAlertSink`），装配时若不经过 scheduler 的节流会放大成刷屏；
- 未做钉钉 20 条/分钟频控、access_token 轮换、NTP 漂移检测（漂移表现为 310000）；
- 未接共享配额/多副本告警聚合。
