# MySQL 租约：跨机部署的选主（2026-10-31）

`graph_engine_adapter/lease_mysql.py`（6 项测试，含真实库），`scripts/v2_lease_drill.py`
新增 `--lease-backend mysql`，隔离库 `gienrag_v2_restore` 上双进程真跑。

## 为什么文件租约不够

文件租约只在**同一块盘**上成立（单机多进程 / 共享存储）。跨机部署时两台机器各有一份
租约文件，谁都能抢到——等于没有租约。所以补 MySQL 版，用共享库做互斥。

## 语义与文件租约一致，只有存储手段不同

| | `FileLease` | `MySqlLease` |
|---|---|---|
| 互斥 | `os.mkdir` 原子创建 | `SELECT ... FOR UPDATE` 行锁 + 事务 |
| fencing | 独立计数文件 | 同表 `fencing` 列，**接管时 +1，自己续租不变** |
| 释放 | 删锁目录，计数文件保留 | 行保留、`expires_at=0`（**不能删行**，否则 fencing 从 1 重来） |
| 适用 | 单机 / 共享盘 | 跨机、多副本 |

表结构（首次使用自动建）：

```sql
CREATE TABLE IF NOT EXISTS v2_rebuild_lease (
  lease_key VARCHAR(64) PRIMARY KEY, owner VARCHAR(191), fencing BIGINT,
  expires_at DOUBLE, taken_at DOUBLE) ENGINE=InnoDB
```

## 实测

单测（假连接 + 真库各一轮）：6 passed。真库那条覆盖"接管 fencing +1、自己续租不加、
释放后他人可接管、释放保留行"。

双进程演练（隔离库，B 先启动、A 6 秒后）：

```
B: builds=1, fencing=1, stale_write_blocked=True, not_leader=0
A: builds=0, skipped_fresh=1, fencing=2, stale_write_blocked=True, not_leader=146
合计构建次数 = 1
```

与文件租约版本结论一致：只有一个主真正重建；跟随者拿到租约时快照已新，跳过；
两者"旧主晚到写入"都被 fencing 拒掉。

## 两个真实缺口（本轮发现并处理）

**1. 交付 wheelhouse 缺 pymysql。**
演练第一次直接报 `MySQL 租约需要 pymysql（交付的 graph venv 未包含）`。
租约是 graph 服务的运行时依赖，离线机没有它会退化成"永远选不到主、永不重建"。
已把 `PyMySQL 1.2.3` wheel 补进 `delivery/wheels-r12-graph` 并更新 manifest
（wheel 100 / bytes 100,073,000），随后重跑 graph bundle 干净安装 → PASS。

**2. 我把版本号搞错了。**
`pymysql.__version__` 打印 `2.2.8`，我据此去 PyPI 找 `pymysql==2.2.8`，报"无此版本"。
实际 `2.2.8` 是**协议版本**，包版本是 `1.2.3`（`pip show PyMySQL` 才是准的）。
教训：装依赖看 `pip show`，不要看模块里的 `__version__`。

## 顺带修掉一处验收偶发失败

Q 的 `graph:写并发与多读者一致性` 在 36 项全跑时**偶发失败一次**（单独跑必过）。
根因是子进程结果走 `mp.Queue.get(timeout=10)`：Q 里前面已连跑多轮引擎构建，CPU 紧张时
子进程投递慢，主进程超时就把"子进程慢"记成"验收失败"。

改法：读者结果**落文件**，主进程轮询等待（最多 60s），并单独报告
`missing_reader_results`。改后连跑 3 次全过。

这类偶发不能靠"再跑一次就绿"糊过去——它会把真实回归淹掉。

## 还没做

- **断网 / 主从切换下的租约行为**：未测。MySQL 不可用时 `acquire` 抛错，
  调度器会走 FAILED + 退避，等于**fail-closed 不重建**，但没有告警出口；
- 表自动创建需要 DDL 权限，生产若要收紧权限需预建表（未提供迁移脚本）；
- 未做 `lease_key` 多租户隔离（当前一个 key 一把锁）；
- 未验证长事务/锁等待超时（`innodb_lock_wait_timeout` 默认 50s）对 acquire 的影响。
