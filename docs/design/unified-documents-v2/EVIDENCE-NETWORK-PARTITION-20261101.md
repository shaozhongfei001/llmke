# 网络分区：建立 → 断开 → 恢复（2026-11-01）

租约故障已经测过"连接拒绝"和"连上不回包"。这一轮补的是第三种形态：**连接先建立并跑通过，
随后对端消失，最后网络恢复**。前两种都是"一上来就不通"，验证不了"故障前已存在的连接会怎样"
以及"恢复后实例能不能自己回来"。

## 三种形态的差别

| | 连接拒绝（已测） | 连上不回包（已测） | 网络分区（本轮） |
|---|---|---|---|
| 故障瞬间 | 对端没起，每次新建连接立刻 `ECONNREFUSED` | 连得上但收不到应答，靠驱动超时兜底 | **先在通路上跑成功**，随后对端消失 |
| 已建立的连接 | 不存在 | 存在，卡在 `recv` | 存在，被掐断（半开/被 RST） |
| 漏掉的风险 | — | — | 恢复后实例一直醒不过来；"分区没真生效"被当成 PASS |

## 手段：进程内 TCP 代理（不碰系统网络配置）

`scripts/v2_network_partition_drill.py` 起一个只在本进程内的代理：`listen 127.0.0.1:0`（随机端口）
→ 转发到真实的 `127.0.0.1:13306`。租约因此连**代理**，分区/恢复对同一条链路生效。

- `cut()`：`shutdown` + 关闭监听（新连接直接被拒）+ 逐条掐断已建立连接；
- `restore()`：在**同一端口**重新监听（`SO_REUSEADDR`），连接串不用改。

为什么不用 iptables / `docker stop`：那会改宿主机状态、影响别人的 MySQL（13306 是共享容器）。
代理只动自己的 socket，`13306` 只作为被连接的对端。租约只写自己那一行 `lease_key`
（`netpartition-test-<pid>`，库 `gienrag_v2_restore`），收尾 `release()`。

## 真实运行结果（不是构造的数字）

```
cd ~/data/dev/llmke-v2 && PW=$(grep -h '^R12_MYSQL_ROOT_PASSWORD=' \
  ~/data/dev/llmke-r12/platform/r12/.env | cut -d= -f2-) && \
PYTHONPATH=services/rag-alg/index_data_service LLMKE_TEST_MYSQL_HOST=127.0.0.1 \
LLMKE_TEST_MYSQL_PORT=13306 LLMKE_TEST_MYSQL_USER=root \
LLMKE_TEST_MYSQL_PASSWORD="$PW" LLMKE_TEST_MYSQL_DB=gienrag_v2_restore \
  ~/data/dev/llmke-v2-toolenv/bin/python scripts/v2_network_partition_drill.py --out /tmp/netpart.json
```

单测：

```
cd ~/data/dev/llmke-v2 && PYTHONPATH=services/rag-alg/index_data_service \
  ~/data/dev/llmke-v2-toolenv/bin/python -m pytest tests/test_network_partition_drill.py -q
```

| 阶段 | 关键数值 |
|---|---|
| `before` | `acquired=true`，`latency=0.057s`，`fencing=1`，调度器 `BUILT` |
| `cut` | `error_type=OperationalError`，`error_len=105`，`(2003, ... [Errno 111] Connection refused)`；`fail_latency=0.0026s`；调度器 `LEASE_ERROR`，`lease_errors=1`，`builds=0` |
| `cut`（已建立连接） | 分区前持有的一条 MySQL 连接被掐断：`(2013, 'Lost connection to MySQL server during query')`，`killed_conns=1` |
| `restored` | 同一个 lease 重新 `acquired=true`，`recovered_after_s=0.127s`，调度器 `BUILT` |
| 总体 | `status=PASS`，9 项检查全 true，`schema_error=null` |

`proxy` 计数：`accepted=9`、`cuts=1`、`restores=1`、`upstream_failures=0`、
`bytes_c2s=16127`/`bytes_s2c=30529`（流量确实穿过代理，不是"连上了但没转发"）。

三阶段的调度器动作连起来看：`BUILT → LEASE_ERROR(builds=0) → BUILT`，
说明 fail-closed（分区期间一次构建都没做）与自愈（恢复后立刻能重建）都成立。

## 单测：14 项，不连库

`PYTHONPATH=services/rag-alg/index_data_service python -m pytest tests/test_network_partition_drill.py -q`
→ **14 passed**（连跑 5 次稳定）。桩对端 + 真 TCP 代理 + 真 `RebuildScheduler`，
覆盖：转发正常、cut 后 acquire 抛可读错误、**已建立连接被掐断**、restore 后同一 lease 重新 acquire、
分区期间 `LEASE_ERROR`/`lease_errors>=1`/`builds==0`、恢复后不再是 `LEASE_ERROR`、
演练在"连不上"时 `status=FAIL` 且不抛栈、无 MySQL 时 `status=SKIP`。

## 两个"假绿"，都是反证用例抓出来的

1. **探测连接报 `TypeError` 被算成"连接被掐断"**。桩 `LineProbe.ping()` 不接受
   `ping(reconnect=False)`，抛 `TypeError`；而当时的判据只是"ping 有没有抛异常"，
   于是这一项永远为真。修法：桩对齐 pymysql 签名，且判据排除
   `TypeError/AttributeError/NameError`（自己代码写错 ≠ 连接断了）。
2. **`cut()` 漏掉"正在建立中"的连接**。反证用例（把 `cut()` 换成空操作、其余照跑）
   本应 FAIL，实测却是 `established_conn_broken=true` 之外还有 `cut_acquire_raised=false`；
   追下去发现：`accept()` 已返回、但登记到 `_relays` 之前的那条连接会漏过 `cut()`
   （probe 存活 → 演练假成功）。修法：登记与 `cut()` 用同一把锁，登记时若已在分区则自行掐断；
   `cut()` 末尾再等端口真的连不上才返回（否则"分区是否生效"取决于时序）。

第 2 条意味着：**如果只跑一次 PASS 就收工，会漏掉一个真实的实现缺陷**——这正是本团队此前的
"假绿"模式（断言空转）。因此本轮的 PASS 由"反证必须 FAIL"这条用例兜住。

## 没做的部分（别把这里当成已覆盖）

- **没有真实网络分区**：没有 `iptables`/`tc netem`、没有拔网线、没有 `docker stop`；
  是进程内代理模拟，故障点落在"代理端口"，不是真的链路丢包。真实分区的半开连接
  还可能表现为长时间静默（要等 TCP keepalive/驱动超时），本轮未覆盖该慢路径。
- **没有主从切换/故障转移**：MySQL 只有一个实例，没做 master 切换、没测 binlog/GTID 追平。
- **没有跨机**：全在 loopback（代理与 MySQL 同机）。跨机 RTT、丢包、MTU 影响未测。
- **构建体是桩**：`rebuild_runner` 只记账，不跑真实图重建（HippoRAG/LLM/embedding），
  因此"分区期间不构建"证明的是**调度决策**，不是"构建过程被打断后的状态一致性"。
- **租约是每操作一条连接**（`MySqlLease` 无连接池），所以分区期间 acquire 走的是
  "新连接被拒"路径；"长事务进行到一半被分区打断"只由上面那条持有连接（ping 失败）间接证明，
  没有构造"事务中途对端消失 → 重试 → 幂等"的完整链路。
- **告警通道未验证**：`LEASE_UNAVAILABLE`/`LEASE_RECOVERED` 的边沿触发在
  `tests/test_scheduler_lease_faults.py` 已覆盖，本轮没接真实 webhook。
- 分区时长的长尾（分钟级以上、跨越 TTL 与 `wait_timeout`）未测。
