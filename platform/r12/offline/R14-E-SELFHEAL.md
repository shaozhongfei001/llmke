# R14-F07 服务自愈改造与实测证据（E-deliver）

## 0. 看门狗设计约束（后来人先读这一页，别重踩）

R14 里这个看门狗在 3 小时内**自己犯了 3 次致命错误**，每次都是真实运维里的高发坑。以下六条是硬约束，
代码里逐条实现，改这个脚本前先确认不会破坏任何一条。

| # | 约束 | 违反后的真实后果（本机实测） |
|---|---|---|
| 1 | **告警不得用退出码表达**。巡检脚本恒 `exit 0`，"不健康"通过日志 `ALERT` 行 + `run/watchdog-status.txt` 暴露 | 第一版用 `exit 1` 表示"发现问题" → unit `failed` → systemd 连带停掉 `OnUnitActiveSec` 的 timer → **看门狗停摆 11 分钟**（10:44:34 起） |
| 2 | **自愈动作必须非阻塞**。`systemctl --user restart --no-block`，只排队不等待 | 阻塞式 restart 遇上 index 冷启动 120s，一拍巡检跑 3 分钟，节拍被打乱、timer 被拖停 |
| 3 | **自愈拉起的进程不得落在看门狗自己的 cgroup**。用 `systemd-run --user --scope --collect` 执行 launcher，并配 `KillMode=process` | 子进程落进自身 cgroup → 停看门狗时被 `SIGKILL` 连坐，**把自己刚救活的服务杀了**（10:45:21） |
| 4 | **排程必须时间驱动**。`OnCalendar=*-*-* *:*:00,30`，不要用 `OnUnitActiveSec` | 依赖"单元上次激活"排程，一旦有残留进程/单元停在 activating → `NextElapse=infinity`，**空窗 1 小时** |
| 5 | **启动宽限期 180s**。`STARTUP_GRACE`，期间只记账不判死 | Java 冷启动 60–120s，宽限不足会"启动 9 秒就判死并 restart"，反复重启把健康服务打成不可用 |
| 6 | **事件必须可归因**。每次动作打：服务名、缺失端口、持续时长、unit、动作、**修复前/后 listener pid**、用时 | 只有 "Finished" 的日志无法区分"没重启"和"重启了但没起来" |

**探针选型规则**（C 指出后再收紧，务必遵守）：
- 只用**不依赖用户主体、不依赖对象存在性**的端点：`/index/knowledgeBase/list`(200)、`/auth/user/kaptcha`(200)。
- **不要**用 `/folder/list`、`/presign`、`/stream` 这类端点：它们的失败本来就是"该失败"（无主体→403/404），
  拿来当探针会让看门狗杀健康服务（12:29:04 就是这么误重启 index 的）。
- 想要"业务可用"而不是"进程活着"，优先在**依赖层**做只读检查（MySQL ping / Redis PING / Nacos readiness /
  ES `_cluster/health` / Nebula health），`up.sh verify` 已按此实现；不要在业务端点里硬造健康语义。
- 附：直连服务出现 500 + `Cannot parse null string`，根因是 `getUserInfo()` 依赖网关注入的 `X-UserName`、
  直连时主体为空（C 已修：改为 30016→403）。这类 500 是"直连没有主体"，不代表服务坏。

配套参数（都是事故后定的，不要为了"更快"随意调小）：
`FAIL_CONFIRM=3`（连续 3 拍判失，30s×3）、`COOLDOWN=300`（同一服务 5 分钟内最多动作一次）、
`MAX_BACKOFF=900`、`TIER_BYPASS=3`（≥3 组同时不健康视为整层故障，可跳过冷却，但仍有 120s 最小间隔）。

自验证方法：
```bash
platform/r12/bin/r12-watchdog.sh --status          # 各组端口/业务探针/失败计数
systemctl --user list-timers r12-watchdog.timer    # NEXT 必须有值（n/a 且 LAST 很久 = 停摆）
systemctl --user show -p Result -p ActiveState r12-watchdog.service   # 必须是 inactive/success
grep -E 'ALERT|触发自愈|自愈成功' platform/r12/logs/watchdog.log
```

日期：2026-10-27　范围：`platform/r12/{bin,systemd}/**`
触发事故：`r12-alg` 因 Nacos 抖动整单元 failed、`Restart=no`，子进程全灭后 7 小时无人拉起。

## 1. 根因（实际机制，不是推测）

| 事实 | 证据 |
|---|---|
| `r12-alg` / `r12-models` 是 `Type=oneshot + RemainAfterExit=yes + Restart=no`：启动器退出后子进程无守护，unit 仍显示 `active (exited)` | 改造前 `systemctl --user status r12-alg`：`Active: active (exited)`，`Main PID: 93234 (code=exited, status=0/SUCCESS)`，cgroup 下 10 个 python 子进程 |
| 启动阶段失败无人重试 | `journalctl --user -u r12-alg` 10:00:55/10:01:01/10:01:05 连续 3 个服务 `FAILED to start`，10:01:05 `Main process exited, status=1/FAILURE` 后再无动作 |
| stop 阶段卡死：父进程被 SIGTERM，worker 子进程不退出，unit 长期停在 `deactivating(final-sigterm)`，期间端口已经不监听 | `journalctl --user -u r12-graphsvc` 2026-10-26 23:31:56、23:38:52 两次 `State 'final-sigterm' timed out. Killing.`（默认 90s）；2026-10-27 10:23:38 再次 `Stopping...` 后 19529 消失 90s |
| 看门狗自身曾因 `flock` fd 被自愈拉起的子进程继承而永久持锁空转 | `logs/watchdog.log` 10:29:44 / 10:30:29 / 10:31:15 / 10:32:00 连续 4 轮 `上一轮巡检仍在进行，跳过本轮`，期间已停止的 docparse 未被拉起 |

## 2. 改动清单

| 文件 | 改动 | 目的 |
|---|---|---|
| `bin/r12-watchdog.sh`（新增） | 按真实监听口 + 模型 HTTP 探针判定服务组存活；连续 2 次判失才动作；修复按组最小化（算法只重启缺失的那一个服务）；成功后又失败不套冷却；失败才退避（300s→1800s）；`mkdir` 原子锁（不向子进程继承 fd） | 补上"进程死了没人知道/没人拉起" |
| `bin/r12-wait-ready.sh`（新增） | `nacos`（`/nacos/v1/console/health/readiness` 200）、`tcp <ports>`、`docker` 三类就绪闸门，超时返回非零 | 冷启动先等依赖就绪 |
| `systemd/r12-alg.service` | `ExecStartPre` 等 Nacos readiness；`Restart=on-failure`/`RestartSec=30`；`StartLimitIntervalSec=300`/`Burst=15` | 启动即失败可被 systemd 重试，超限交看门狗 |
| `systemd/r12-models.service` | `ExecStartPre` 等 docker；`Restart=on-failure`；StartLimit | 同上 |
| `systemd/r12-docparse.service` | `ExecStartPre` 等 Nacos；`KillMode=control-group`；`TimeoutStopSec=30` | 修"停不下来" |
| `systemd/r12-graphsvc.service` | `ExecStartPre` 等 Nacos + Nebula 19669；`KillMode=control-group`；`TimeoutStopSec=30` | 修"停不下来" |
| `systemd/r12-java@.service` | `ExecStartPre` 等 Nacos + `tcp 13306 16379`；`Restart=on-failure`；StartLimit | 业务服务不再因 Nacos/DB 未就绪直接失败 |
| `systemd/r12-watchdog.service` + `.timer`（新增） | 45s 巡检一次（`OnBootSec=120`、`OnUnitActiveSec=45`） | 45s×2=90s 确认窗口，使恢复落在 60–120s |
| 看门狗"卡死单元"升级动作 | 过渡态（activating/deactivating/reloading）滞留 >150s 且端口已失 → `systemctl --user kill -s KILL` 后 `restart` | 覆盖 `final-sigterm` 卡死这一真实形态 |

运维约定：需要保持停机（例如临时排查）时 `touch platform/r12/run/.maintenance`，看门狗不再介入；`r12-watchdog.sh --reset` 清状态。

## 3. 实测（真实 kill，非同进程模拟）

### 3.1 算法组 19995 被 kill（timer 驱动，FAIL_CONFIRM=2）

```
=== 2026-10-27T10:39:00+08:00 kill 前 ===
LISTEN 0 2048 127.0.0.1:19995 0.0.0.0:* users:(("python",pid=180188,fd=20),("python",pid=185729,fd=20))
=== 10:39:00 kill -9 持有者(180188,185729) ===
--- kill 后：19995 无监听 ---
=== 2026-10-27T10:40:21+08:00 19995 恢复，用时 79s
```
看门狗日志：
```
[10:39:34] [alg] FAIL(1/2) 缺失=19995 ustate=active
[10:40:19] [alg] FAIL(2/2) 缺失=19995 ustate=active
[10:40:19] [alg] 触发自愈：缺失=19995（已持续 45s）
[10:40:19] [alg] 修复动作: .../run/algctl.sh restart alg_retrieval_service（端口 19995 不在监听）
alg_retrieval_service stopped (freed :19995)
alg_retrieval_service started pid=249442 port=19995
[10:40:26] [alg] 自愈成功，端口/探针已恢复
```

### 3.2 模型组 18090 被 kill（同一轮）

```
=== 2026-10-27T10:40:36+08:00 18090 恢复，用时 94s ===
```
```
[10:39:34] [models] FAIL(1/2) 缺失=18090,http:18090/healthz
[10:40:27] [models] 触发自愈：缺失=18090,http:18090/healthz（已持续 45s）
[10:40:27] [models] 修复动作: systemctl --user restart r12-models
```
恢复后真实推理（不是只看端口）：
```
$ curl -sS -m 30 http://127.0.0.1:18092/v1/chat/completions -d '{"model":"qwen2.5-7b-instruct",...}'
{"choices":[{"finish_reason":"stop","message":{"role":"assistant","content":"服务已恢复"}}],...}
$ curl -sS http://127.0.0.1:18090/v1/embeddings -d '{"model":"bge-m3","input":"自愈验证"}'
{"object":"list","data":[{"object":"embedding","embedding":[-0.01140712,...]}]}
$ curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18090/healthz   -> 200
$ curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18092/health    -> 200
```

### 3.3 解析服务"unit 已死、无人拉起"（R14 事故形态）

```
=== 2026-10-27T10:37:21+08:00 执行 systemctl --user stop r12-docparse
--- stop 后 ss：无监听；ActiveState=inactive
=== 2026-10-27T10:38:51+08:00 12340 恢复，距 stop 90s
--- 恢复后：LISTEN 0 2048 127.0.0.1:12340 users:(("python",pid=240396,fd=65))；ActiveState=active
[10:38:03] [docparse] FAIL(1/2) 缺失=12340 ustate=inactive
[10:38:48] [docparse] FAIL(2/2) 缺失=12340 ustate=inactive
[10:38:48] [docparse] 触发自愈 ... → [10:38:52] [docparse] 自愈成功
```

### 3.4 就地启动闸门实测

```
$ r12-wait-ready.sh nacos 20      -> [wait-ready] nacos readiness=200（用时 0s） rc=0
$ r12-wait-ready.sh tcp 13306 16379 -- 10 -> tcp 13306 16379 全部可连（用时 0s） rc=0
$ r12-wait-ready.sh tcp 13306 9 -- 3      -> FAIL tcp 9 3s 内未就绪 rc=1
```

## 4. 未覆盖/限制（如实列出）

1. **同机其它角色在并发重启服务**：10:25–10:29 观测到 `retrieval_api_start.py` 在 10:25:21/10:25:44/10:25:54、`vector_milvus_api_start.py` 在 10:26:40/10:27:43 被反复重启（非本看门狗所为，日志无对应动作），因此单次 kill 测试存在被外部重启掩盖的可能；本文件 3.1/3.2/3.3 均在看门狗日志中有完整动作链，可排除外部因素。
2. 算法服务（19526/19527/19995/19996）**没有 HTTP 健康端点**（`/healthz`、`/health`、`/actuator/health` 均 404），因此看门狗对它们只能判"监听 + 可连 + 监听进程未挂起/僵尸"，无法判"业务可用"。业务级判据仍靠 `bin/up.sh verify`。要补真实健康端点需改算法源码（A/B 角色）。
3. `r12-java@` 系列仍为 `Type=forking` + pidfile，看门狗按端口判活；JVM 存活但 Spring 上下文未就绪时不重启，只在端口消失时介入。
4. 看门狗对"人为 stop 的 enabled 单元"会重新拉起（这是本轮事故要求的语义）；需要保持停机时必须用 `.maintenance` 锁，否则与看门狗互相打架。

---

## 5. 补充（2026-10-27 11:00）：看门狗自身两个致命缺陷，已修并复测

第一版看门狗上线 20 分钟后，自己犯了和 r12-alg 一样的错——**它把自己关掉了，而且会杀掉它刚救活的服务**。两条都已修复并复测。

### 5.1 缺陷 A：发现问题时 `exit 1` → unit failed → systemd 停掉 timer → 看门狗彻底停摆

证据（journal）：
```
10:42:12 r12-watchdog.service: Consumed 1.538s CPU time.
10:42:58 r12-watchdog.service: Main process exited, code=exited, status=1/FAILURE
10:42:58 r12-watchdog.service: Failed with result 'exit-code'.  Failed to start ...
10:43:42 Starting R14 r12 service watchdog (one tick)...
10:44:34 systemd[1285]: Stopped R14 r12 service watchdog timer (45s).     <- timer 被停
```
后果：`list-timers` 显示 `NEXT n/a`，从 10:44:34 到 10:56:01 **11 分钟没有任何巡检**。
修法：巡检脚本**恒 exit 0**；问题通过 `logs/watchdog.log` 的 `ALERT` 行 + `run/watchdog-status.txt` 暴露（不再靠退出码），并在 `[Unit]` 保留 `StartLimitIntervalSec=0`。

### 5.2 缺陷 B：自愈动作的子进程落在看门狗自己的 cgroup 里，stop 时被连带 SIGKILL

证据（journal）：`10:45:21 r12-watchdog.service: Killing process 270324 (python) with signal SIGKILL` —— 这两个 python 正是 10:43:42 自愈拉起的 retrieval，**被看门狗自己杀掉了**（team-lead 担心的"watchdog 杀掉健康服务"就是这么发生的）。
修法（双保险）：
1. `r12-watchdog.service` 加 `KillMode=process` + `TimeoutStopSec=15`（只杀巡检脚本本身，不等子进程）；
2. 自愈动作改为 `systemd-run --user --scope --collect --quiet bash algctl.sh restart <svc>`，让常驻进程落到独立 scope。

复测（11:59 前）：
```
$ kill -9 $(cat run/alg_retrieval_service.pid)      # 10:58:16，端口真的消失
[10:59:03] [alg] FAIL(2/2) 缺失=19995 ustate=active listener_pids=[无]
[10:59:03] [alg] 触发自愈：缺失=19995 已持续 45s unit=r12-alg 动作=alg-granular 修复前 listener_pids=[19995:]
[10:59:03] [alg] 修复动作: .../algctl.sh restart alg_retrieval_service
[10:59:11] [alg] 自愈成功 用时=8s 修复后 listener_pids=[19526:186040 19527:173458 19995:360263 19996:103860,94269]
$ systemctl --user show -p ActiveState -p Result r12-watchdog.service
ActiveState=inactive  Result=success          <- 不再 failed，timer 继续排程
```
之后 100s 采样，`19995` 的 pid `350390` 保持不变（未被再次杀掉）。

### 5.3 顺带发现：算法服务 restart 会遗留 worker 孤儿
`pgrep -f "venvs/alg/bin/python -u retrieval_api_start.py"` 曾出现 7 个进程，其中 6 个既不监听端口也不知 pidfile（最老 44 分钟）。这是"父进程被 SIGKILL、worker 被 systemd 收养"的典型形态，反复 restart 会累积内存/连接池占用。
- 已修：`run/algctl.sh` 的 `stop_one` 增加同入口脚本清理（`pgrep -f "^$PY -u <entry>$"`），stop/restart 时一并回收并打印"清理遗留进程 N 个"。
- 已手工清理 6 个旧孤儿（按 age > 主进程 age 判定，保留与主进程同龄的 worker），清理后 retrieval 从 7 → 2 个进程，端口正常。
- **未强杀** vector(5)/fulltext(4)/llm(3) 的疑似孤儿：无法在不停服务的前提下安全区分"合法 worker"与"孤儿"，留给下次 `algctl restart` 自动收敛。

### 5.4 另外：容器级守护
`r12-fe` 是 14 个 `r12-*` 容器里唯一 `RestartPolicy=no`（`ExitCode=0` 说明是 `docker stop` 正常停止，非崩溃）。已 `docker update --restart unless-stopped r12-fe`，并在看门狗里加容器级守护（存在但非 running → `docker start`，带冷却/退避）。

---

## 6. 事故记录 E-2026-10-27-02：**我**把业务层打下线 16 分钟（11:01–11:17），并连带 auth 再停 30 分钟

如实记录，避免把"环境不稳"当成别人的问题。

### 6.1 时间线（全部有日志）
| 时间 | 事件 |
|---|---|
| 10:42–10:44 | 我为暴露面收口给 5 个业务服务加 `-Djava.net.preferIPv4Stack=true` 并滚动重启；index 冷启动约 120s，期间 18082 不可用（D 报的"整条不在线"就是这段） |
| 11:00:33 | 我想把"进程在跑但 unit 显示 inactive"的状态对齐，执行 `systemctl --user start r12-java@...` |
| 11:00:16 起 | `Type=forking` 与 `r12ctl start`（sleep 3 后才写 pidfile）竞态 → `Result: protocol` → `Restart=on-failure` 每 30s 重试一次，**每轮 ExecStop 都真的杀 JVM**；4 个 pidfile 被 `r12ctl stop` 删除 |
| 11:00:5x | 我把 `Type=forking` 改成 `oneshot + RemainAfterExit=yes`——但**同一 [Service] 段后面原有的一行 `RemainAfterExit=no` 覆盖了它**（后写者生效）→ oneshot 退出后立即 deactivate → 又跑 ExecStop → 继续杀 JVM |
| 11:01:42–11:17 | 业务层（18081/18082/18083/18085 + 网关 8088）全部不可用；看门狗虽在报警，但被上一轮退避卡住：`[11:12:10] [java-qa] 冷却中，剩余 130s`、`[11:13:40] 剩余 40s`（连续 4 轮） |
| 11:16:49 | 我用 `r12ctl.sh start` 全量拉起（此时 unit 已 inactive、无挂起 job，不再被 ExecStop 抢杀）→ 5 个端口恢复 |
| 11:47 | 我在 auth 上做"单点同步试验"→ 再次被杀（同一条 `RemainAfterExit=no`），18081 再停 |
| 12:17 | 删掉重复的 `RemainAfterExit=no`，`systemctl --user start` 变成真 no-op（pid 前后一致、unit `active(exited)`）；4 个单元逐个对齐，22 项 verify 全 ok / exit 0 |

### 6.2 根因（两个，都在我这边）
1. **unit 类型与 `r12ctl` 不匹配**：`Type=forking` + `PIDFile` 要求 pidfile 在 ExecStart 退出瞬间就存在，而 r12ctl 是 `sleep 3` 后 `pgrep` 再写 → 必然 `protocol` 失败。
2. **同一 unit 里 `RemainAfterExit=yes` 与 `RemainAfterExit=no` 并存**（后者生效）→ oneshot 退出即 deactivate → 触发 ExecStop → 杀服务。这是我的疏漏：改 unit 时只加了新行、没删旧行。

### 6.3 已修
- `systemd/r12-java@.service`：`Type=oneshot` + **唯一一条** `RemainAfterExit=yes`，去掉 `PIDFile=`；注释写清竞态原因。
- 验证：`systemctl --user start r12-java@x` 现在 pid 不变、unit `active(exited)`、端口不掉。
- 看门狗冷却策略修正（本次事故暴露）：`COOLDOWN` 300→**120s**、`MAX_BACKOFF` 1800→**600s**，并新增**整层故障旁路**——同时不健康组数 ≥3 时跳过冷却立即修复（每轮仍只尝试一次）。不再出现"整层挂了还在等 130s 冷却"。

### 6.4 给使用者的影响
- 11:01–11:17：业务层全不可用（含网关 8088）。
- 11:47–12:17：rag-auth-service（18081）不可用，其余 4 个正常。
- 12:17 起全线恢复：`up.sh verify` 22 项 ok / exit 0；Nacos 5 个服务实例 `healthy=true`。
- 教训写在这里，不写"环境抖动"。

---

## 7. 第三次自愈缺陷：timer 用 OnUnitActiveSec 会停摆（已改 OnCalendar 30s）

事故 E-2026-10-27-02 期间又暴露一条：**看门狗在 11:13:41 之后再没跑过（1h 空窗）**。
```
$ systemctl --user list-timers --all
NEXT n/a   LAST Tue 2026-10-27 11:13:40 CST   PASSED 1h 4min   r12-watchdog.timer
$ systemctl --user show -p NextElapseUSecMonotonic r12-watchdog.timer
NextElapseUSecMonotonic=infinity
```
journal 显示该轮单元是正常结束的（`Finished ... Consumed 1.358s`），但同一轮里留了两个进程在单元 cgroup
（`Unit process 402767 (bash) / 402769 (java) remains running after unit stopped`，其中 java 是 **rag-graph-service**，由 `r12ctl start` 拉起）。
`OnUnitActiveSec` 的下一次排程依赖"单元上次激活 → 变回 inactive"，一旦有残留进程/单元长时间停在 activating，就不再有下一次。

修法（三处，一起）：
1. timer 改 **`OnCalendar=*-*-* *:*:00,30`**（时间驱动，与单元结果无关）+ `AccuracySec=1s`；
2. `systemctl --user restart` 一律加 **`--no-block`**：只排队、立即返回，避免 index 这种 120s 冷启动把一拍巡检拖到 3 分钟（11:13 就是这样拖停的）；
3. `r12ctl start`（图服务）也放进 `systemd-run --user --scope`，长驻进程不再落在看门狗 cgroup 里。

改后节拍实测（`list-timers` + 日志）：
```
NEXT Tue 2026-10-27 12:22:30 CST   LAST 12:22:00   r12-watchdog.timer
巡检结束  12:20:50 / 12:21:08 / 12:21:32 / 12:22:13   （约 30s 一拍，连续无空窗）
```
30s × 2 次判失 = 30–60s 确认窗口，加拉起约 8s，恢复落在 30–70s（优于 60–120s 目标）。

补充记录：`rag-graph-service` 的 java 进程当前仍留在 `r12-watchdog.service` 的 cgroup 里（历史上由看门狗的 r12ctl 调用拉起）。`KillMode=process` 下停看门狗不会波及它；下次图服务被看门狗重启时会落到独立 scope，自然迁出。**不要**用 `systemctl --user stop r12-watchdog.service` 之外的方式去清这个 cgroup。
