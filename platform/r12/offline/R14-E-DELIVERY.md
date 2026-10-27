# R14 E（交付与运行）交付清单

日期：2026-10-27　角色：E-deliver　所有权：`platform/r12/{bin,docker,conf,nacos,systemd,offline,preview}/**`、`platform/r12/run/{algctl.sh}`

> 口径：只列**有实测命令与输出**的项。状态 `DONE` / `DONE(部分)` / `BLOCKED(外部)` / `NOT DONE`。
> 证据文件都在 `platform/r12/offline/`。

## 0. 一屏结论

| 能力 | 状态 | 关键证据 |
|---|---|---|
| C20 离线安装（顺序/校验/健康判据） | DONE(部分：完整包未重打、干净主机未实装) | `R14-E-INSTALL-F06-F07.md` |
| C20 完整源码与离线构建材料 | DONE | 同上（src-build 108M、清单 409 行、7 项点名 ok） |
| F02 暴露面收口 | DONE(部分：剩 3 个非本项目端口) | `R14-E-EXPOSURE-ES.md §1` |
| 服务自愈（F07 事故项） | DONE | `R14-E-SELFHEAL.md` |
| ES 单节点 yellow | DONE | `R14-E-EXPOSURE-ES.md §2` |
| Nebula unhealthy 根因 | DONE | `R14-E-EXPOSURE-ES.md §3` |

## 1. 新增/修改文件

| 文件 | 类型 | 作用 |
|---|---|---|
| `bin/r12-watchdog.sh` | 新增 | 服务自愈看门狗（10 个服务组 + 14 个容器） |
| `bin/r12-wait-ready.sh` | 新增 | 启动依赖闸门（nacos readiness / tcp / docker） |
| `bin/es-single-node.sh` | 新增 | 单节点 ES 副本治理（幂等，含 green 断言） |
| `bin/offline-build-manifest.py` | 新增 | 离线构建清单生成（Java 运行时坐标 + sha256） |
| `systemd/r12-watchdog.{service,timer}` | 新增 | 30s OnCalendar 巡检 |
| `systemd/r12-{alg,models,docparse,graphsvc}.service` | 修改 | 依赖就绪闸门 + Restart/StartLimit/KillMode |
| `systemd/r12-java@.service` | 修改 | `Type=oneshot` + `RemainAfterExit=yes`（修 forking 竞态）+ 依赖闸门 |
| `bin/up.sh` | 修改 | 顺序修、就绪判据、verify must/warn 非零退出、去 npm dev 默认、ES 治理接入 |
| `bin/offline-kit.sh` | 修改 | 安装文档重写、src-build 打包、`PACK_SCOPE`、自愈脚本入包 |
| `bin/r12ctl.sh` | 修改 | IPv4 单栈绑定（网关除外）、`[STALE_JAR]` 检测、`.out` 启动前截断 |
| `run/algctl.sh` | 修改 | `stop` 时清理同入口脚本孤儿进程 |
| `offline/templates/{BUILD-OFFLINE.md,settings-r12.xml,resolve-*.sh}` | 新增 | 源码复建材料 |
| `offline/patches/check-exposure-attribution.diff` | 新增 | 暴露面门禁口径补丁（待 TL adopt） |

## 2. 运行态基线（2026-10-27 12:26）

```
18 个端口全在监听；pids 3 分钟内不变
up.sh verify -> 22 项 [ok]，exit 0
Nacos 5 个业务实例 healthy=true
ES: status=green, unassigned_shards=0
Nebula: 3 容器 healthy；nebula3 SHOW SPACES=3 / LOOKUP ON entity=3 行
看门狗：30s 节拍，连续 8 轮"不健康组=0"
```

## 3. 本轮我造成的两次中断（必须记住）

| 时间 | 影响 | 根因 |
|---|---|---|
| 10:42–10:47 | 18082 index 不可用 | 加 IPv4 绑定参数后滚动重启，index 冷启动 120s |
| 11:01–11:17 | **业务层全断（含 8088）16 分钟** | `r12-java@` 改 `Type=oneshot` 时同一段里 `RemainAfterExit=yes/no` 并存（后者生效）→ 退出即 deactivate → `ExecStop` 杀 JVM |
| 11:47–12:17 | 18081 auth 不可用 30 分钟 | 同上（单点验证时复现） |

处置：删重复项 + 唯一 `RemainAfterExit=yes`；`systemctl --user start` 已验证为 no-op（pid 不变）。
纪律：**涉及 systemd/端口的改动先报时间窗，改完立刻 `up.sh verify` 并@受影响角色**；`10:42–12:17` 的验收结果全部作废。

## 4. 外部阻塞（我无法自主关闭）

1. **`check-exposure.sh --expect-closed` 归零**：剩 `3306/33060`（宿主 `/usr/sbin/mysqld`，需 root）与 `2379@172.17.0.1`（k8s 控制面 etcd，不该动）。补丁已备、已在 /tmp 实测 exit 0，待 TL adopt。
2. **MinIO 引用原文**：`r12-rag` 无匿名策略，前端 `/minio/...` 403。是否开匿名属于安全口径，需 TL 裁决（我建议走后端 presigned URL，不动桶策略）。
3. **完整包重打与干净主机实装**：完整包需 ~20G 镜像导出 + 24G 运行时拷贝（30–40 分钟）；干净主机/VM 不在当前资源内，只能做到"独立目录 + 独立库"。

## 5. 运维速查

```bash
# 看门狗
systemctl --user list-timers r12-watchdog.timer
platform/r12/bin/r12-watchdog.sh --status          # 各组健康/失败计数
platform/r12/bin/r12-watchdog.sh --reset           # 清失败计数与退避
touch platform/r12/run/.maintenance                # 维护窗口：看门狗不介入（记得删）
tail -f platform/r12/logs/watchdog.log

# 全栈
platform/r12/bin/up.sh up|status|verify
platform/r12/bin/es-single-node.sh                 # ES 副本治理（幂等）
platform/r12/bin/check-exposure.sh --expect-closed
platform/r12/bin/r12ctl.sh status                  # 带 [STALE_JAR] 提示

# 离线包
PACK_SCOPE=src OUT=/tmp/out platform/r12/bin/offline-kit.sh pack   # 只出源码/构建材料
platform/r12/bin/offline-kit.sh manifest|verify|smoke
```

---

## 6. 第二轮（TL 四项硬要求 + 后续裁决）落地记录

| # | 要求 | 落地物 | 实测 |
|---|---|---|---|
| 1 | unit 缺 EnvironmentFile / `.env` 变量名不一致打挂 5 个 Java 服务 | repo `systemd/r12-java@.service` 加 `EnvironmentFile=-…/.env`；`offline/templates/env.template` 补 `R12_MYSQL_PASSWORD`；`up.sh verify` 增 must「conf 占位符都能在 .env 找到」 | `[ok] conf 占位符全部能在 .env 找到（3 个）` |
| 2 | `RemainAfterExit` 重复定义这类"改了没生效" | 新增 `bin/check-units.sh`：重复单值指令 / `forking` 缺 PIDFile / `oneshot+ExecStop` 需 `RemainAfterExit=yes` / repo vs 已装副本 diff / `systemctl show` 生效值比对 | 首跑即抓出 repo 与已装副本不一致；现 `EXIT=0` |
| 3 | 看门狗误杀健康服务 | 宽限 180s、连续 3 拍、同服务 5 分钟最多一次、整层故障旁路（≥3 组，120s 最小间隔）、**业务端点探针**（index `/index/knowledgeBase/list`=200、gateway `/auth/user/kaptcha`=200、qa `/qa/ai/question`）、事件含修复前后 listener pid | 见 `R14-E-SELFHEAL.md §0` 六条约束 |
| 4 | presign 网关注册靠人工 SQL | 新增 `bin/init-endpoints.sh`（幂等，含回读校验）；`init-db.sh` **在"已有表则跳过导入"之前**调用（升级库也补） | 删注册→脚本补回→网关 401/30022（不再 30021） |
| 5 | 前端 bind mount 旧 inode | `up.sh` 比对入口 chunk 名，不一致自动 `docker restart r12-fe`；`verify` 增 must | `[ok] 入口 chunk 一致：index-_Z7TjdPH.js` |
| 6 | 离线包 SQL 被覆盖 | pack 默认**沿用**已有 `payload/db/gienrag.sql`（校验 `uk_search_config_default`），仅 `FORCE_DB_DUMP=1` 重导；`sql/*.sql` 随包不执行 | `[ok] 沿用已有 db/gienrag.sql（含 uk_search_config_default 补丁）` |
| 7 | 跨模块构建陷阱 | `BUILD-OFFLINE.md §1.5`：共享模块先 `mvn install -pl <m> -am`，并给 fat jar `BOOT-INF/lib` 版本 + `strings` 特征串校验命令 | 文档 |
| 8 | check-exposure 口径 | **已 adopt**：宿主类单列 + 打印"需 root 处置"；`::ffff:127.0.0.1` 与 `::ffff:7f00:1` 均识别为回环；补丁工件 `offline/patches/check-exposure-attribution.diff`（`patch -p1 --dry-run` 干净） | `EXIT=0`，`数据面非回环=0` |

| 9 | 默认助手"唯一索引 + 数据归零"必须成对（C 报） | `init-db.sh` 增 `check_default_helper_invariant`：**生效默认行数 ≤1** 且**唯一索引存在**，任一不成立非零退出；新库导入后与已有库跳过时都校验 | 现库 `[ok] 生效默认=1 行，唯一索引存在`；临时库负例（2 行默认/缺索引）分别命中 die/warn |
| 10 | 不借业务端点当健康检查（C 建议） | `up.sh verify` 增 must：MySQL ping、Redis PING、Nacos readiness=200、Nebula graphd healthy | `[ok] MySQL ping alive / Redis PONG / Nacos 200 / Nebula healthy` |

### 6.1 本轮又踩的一次（自曝）
12:29:04 看门狗**误重启了 rag-index-service**：我给探针选的第一版端点是
`/index/knowledgeBase/file/folder/list?...&kbId=9`，该接口返回 **500**（body `{"errorCode":"10001","知识库不存在"}`），
探针判死 → `restart --no-block`。已换 `/index/knowledgeBase/list`（200）。
新约束：**探针所选端点必须先手工 curl 确认基线非 5xx**，并写进 `R14-E-SELFHEAL.md §0`。

### 6.2 当前基线（12:36）
```
up.sh verify            exit=0（23 ok / 0 fail）
check-units.sh          exit=0
check-exposure.sh       exit=0（数据面非回环=0；宿主 3 个单列）
watchdog                不健康组=0；timer 30s（Next 有值）
ES green / unassigned=0；Nebula 3 容器 healthy；14 个 r12-* 容器 running
6 个 Java 服务 jar mtime 均早于进程启动时间（无 STALE_JAR）
```

### 6.3 "grace 期不误杀"的现场实证（非构造测试）

B-graph 在 12:31 与 12:34:57 两次部署 global 修复，`systemctl --user restart r12-graphsvc`（单服务，未整栈）。
看门狗在这两个窗口里的行为正好证明宽限期生效——**只记账，不动作**：

```
[12:32:41] [graphsvc] 启动宽限期内（启动于 93s 前，宽限 180s，缺 19529），本轮不判死
[12:33:31] [graphsvc] 启动宽限期内（启动于 42s 前，宽限 180s，缺 19529），本轮不判死
[12:34:30] [graphsvc] 启动宽限期内（启动于 37s 前，宽限 180s，缺 19529），本轮不判死
（同期无一条 [graphsvc] 触发自愈 / 修复动作）
```
对照：`r12-graphsvc` 的 `ActiveEnterTimestamp=12:34:57`、`19529` 单 listener pid=927375，`verify=0`、不健康组=0。
这条比我自己 kill 的构造测试更有说服力：**别人正常重启服务时，看门狗没有插手**。

归属备忘（避免当幽灵进程排查）：
| 时间 | 事件 | 归属 |
|---|---|---|
| 12:31 左右 / 12:34:57 | `r12-graphsvc` 重启（部署"概念归一"与"确定性连接+引用纠正"） | **B-graph**，已报备，非异常 |
| 12:29:04 | `rag-index-service` 重启 | **我**（探针选错端点致误判），已修 |
| 11:01–11:17 / 11:47–12:17 | 业务层/ auth 中断 | **我**（unit `RemainAfterExit` 重复定义），已修 |
| 10:26–10:27 | 19527/19995/19526 反复重启 | 外部角色（看门狗日志无对应动作） |

### 6.4 `[STALE_JAR]` 门禁本身是假阴性（C 报 + 我查出第二处），已修

这是"门禁自己坏了却显示绿色"的又一例，且**同一门禁里有两个独立 bug 互相掩盖**：

| # | 位置 | 错误 | 后果 |
|---|---|---|---|
| 1 | `r12ctl.sh` `proc_ts="$(ps -o lstart= -p $pid \| xargs -r date -d '+%s')"` | `date -d` 的入参是"日期字符串"，`+%s` 是输出格式却被当成 `-d` 的入参 → `date` 失败 → `proc_ts` 为空 → `return 1` | 永远判"不 stale" |
| 2 | `jar="$JAVA_PARENT/$name/${JARS[$name]}"` | `JARS[]` 里已含 `rag-qa-service/target/x.jar`，再拼 `$name` 变成 `.../rag-qa-service/rag-qa-service/target/x.jar` | `[[ -f ]]` 失败 → 同样 `return 1` |

只有 1 修了仍不告警（会被 2 继续掩盖），两处都修后才生效。C 描述的复现（jar 比进程新 968s 却不告警）与实测一致。

修法：
```bash
proc_ts="$(ps -o lstart= -p "$pid" 2>/dev/null | xargs -r -I{} date -d '{}' +%s 2>/dev/null)" || return 1
jar="$JAVA_PARENT/${JARS[$name]:-}"
```
新增 `r12ctl.sh diag`：打印每个服务的 `JAR_TS / PROC_TS / DELTA`，并在 `[STALE_JAR]` 行带上差值——下次再写错，`diag` 里会出现 `-`，一眼可见而不是继续绿灯。

修后实测（C 已把两个新 jar 放进 target）：
```
$ bash bin/r12ctl.sh status
rag-index-service RUNNING pid=883601 [STALE_JAR] jar 比进程新 336s（重启才生效）
rag-qa-service    RUNNING pid=802208 [STALE_JAR] jar 比进程新 968s（重启才生效）
$ bash bin/r12ctl.sh diag
rag-index-service  883601  1793075680  1793075344   336s
rag-qa-service     802208  1793075563  1793074595   968s
```

### 6.5 默认助手索引校验按 C 的边界收紧
原判据"索引名存在"会放过语义错误的结构（普通人把唯一索引建在 `is_default` 列上：只允许 1 个 0 + 1 个 1，多用户永远标不了默认）。
现判据：`non_unique=0` **且** `expression is not null` **且** `expression like '%is_default%'`（即函数索引）。
负例验证（临时库，已删）：普通列唯一索引 → 按名字计数=1、按新判据=0 → 正确判为不通过。

### 6.6 门禁自检：证明"这些门禁会失败"（`bin/gates-selftest.sh`）

本轮教训：门禁自身坏了会显示绿色（`[STALE_JAR]` 假阴性、看门狗 exit 1 停摆）。因此每个门禁都配一个**注入已知缺陷**的用例：

| 用例 | 注入 | 期望 |
|---|---|---|
| A | 假 `ss` 输出 `0.0.0.0:19200`（本项目数据面非回环） | `check-exposure --expect-closed` **FAIL** 且输出含 19200 |
| B | 假 `ss` 只输出 `[::ffff:127.0.0.1]` / `[::ffff:7f00:1]` | **PASS**（IPv4-mapped 回环不能被误判） |
| C | 临时单元里 `RemainAfterExit=yes` + `RemainAfterExit=no` | `check-units --repo-only` **FAIL** 且指出该指令；删掉重复后必须 PASS（证明不是恒定失败） |
| D | 读取 `r12ctl diag` | 所有 RUNNING 服务的 `JAR_TS/PROC_TS` 不得为 `-`（即 C 报的假阴性形态不能复现） |

实测：
```
$ bash bin/gates-selftest.sh
  [ok] 非回环数据面被判 FAIL（退出非零，且列出 19200）
  [ok] [::ffff:127.0.0.1] 与 [::ffff:7f00:1] 正确识别为回环（退出 0）
  [ok] 重复 RemainAfterExit 被判 FAIL（正是 11:00 事故的形态）
  [ok] 去掉重复后检查通过（不是恒定失败）
  [ok] diag 对所有 RUNNING 服务都取到了 JAR_TS/PROC_TS（无 '-'）
  [ok] 门禁自检全部通过：5 项
EXIT=0
```
交付/安装说明建议把它作为"候选冻结前必跑"，与 `check-units` / `check-exposure` / `up.sh verify` 一起。

### 6.7 ES 判据从"只报 yellow"升级为"点名到索引 + 给处置"（端到端验证）
风险场景（B-graph 提的）：新建 KB/索引若索引名**不匹配**模板 pattern，会按 ES 默认 `number_of_replicas=1` 建出来
→ 单节点必然 1 个 unassigned → 集群 yellow → `up.sh verify` 的 `ES 必须 green` FAIL，但原来只打印 "yellow"，
排查要人去 `_cat/indices`。现在 verify 直接点名：

端到端实测（造一个不匹配 pattern 的索引 `r14_repcheck`）：
```
$ PUT /r14_repcheck                     -> {"acknowledged":true}
$ /_cluster/health                      -> {"status":"yellow","unassigned_shards":1}
$ up.sh verify
  [FAIL] ES 集群非 green（status:yellow）
       诊断：以下索引 number_of_replicas>0，单节点无法分配副本：r14_repcheck(rep=1)
       处置：bash …/bin/es-single-node.sh（既有索引置 0 + 模板默认 0）；若是新前缀，把 pattern 加进该脚本
  [FAIL] 验收失败：must 项 1 个未通过
$ DELETE /r14_repcheck ; /_cluster/health -> {"status":"green","unassigned_shards":0} ; verify=0
```
运维口径：**新增索引前缀先加进 `bin/es-single-node.sh` 的 `index_patterns`**（幂等脚本，可重复跑），
不要等集群变黄再查。

### 6.8 `[STALE_JAR]` 的口径（C 建议后明确，避免告警脱敏）

`[STALE_JAR]` 在 `up.sh verify` 里是 **warn 级**、不是 must，原因：它是"有人在改构建产物"的正常中间态。

| 状态 | 含义 | 判读 |
|---|---|---|
| STALE = 0 | 运行中的 jar 不旧于进程启动 | **无人改动时应恒为 0**；=0 才算"跑的是最新构建" |
| STALE > 0 | 有人 stage 了新 jar 但没重启 | 不是误报；`r12ctl status` 会列服务名 + 落后秒数，`diag` 给 `JAR_TS/PROC_TS/DELTA` |
| `diag` 出现 `-` | 时间取值失败 | **门禁坏了**（12:40 的真实 bug 就是这个形态），不是"没问题" |

要求：候选冻结与最终验收时 STALE 必须为 0（此时不许有人 stage）；开发迭代期出现 >0 属正常，但**不能长期挂着不看**。

### 6.9 引用原文链路端到端验证（方案 a：后端签名，桶匿名保持关闭）

用 QA 客户端 `platform/r12/qa/r12_client.py`（只读导入，未改 F 目录）取 token 后实测（**运行态为 12:42:50 加载的 12:39 构建**）：

| # | 断言 | 期望 | 实测 |
|---|---|---|---|
| 1 | `PUT {GW}/index/faq/changeStatus {"kbId":9,"status":1}` | 200 success=true | **200** `{"success":true}` |
| 2 | `GET …/file/presign?key=…/__not_exist__.docx` | 404 / 10002 | **404** `{"errorCode":"10002","知识库文件不存在"}` |
| 3 | `GET …/file/presign?key=…/V0/R12FIX-product-loan.docx` | 200 + 带签名 url | **200**，url 形如 `http://127.0.0.1:19000/r12-rag/kb_9/…?response-content-type=…&X-Amz-Signature=…` |
| 4 | `POST …/file/previewStream` | 200 `%PDF-1.7` | **200** `application/pdf` `b'%PDF-1.7'` |
| 5 | **用签名 URL 直取对象**（我加的闭环） | 200 且字节正确 | **200, 37544 bytes, magic `PK\x03\x04`（docx zip）** |
| 6 | **去掉签名匿名直取**（我加的负例） | 403（桶匿名必须关闭） | **403** |

结论：`/minio/` 匿名读那条路已经不需要了——引用原文走"后端签名 300s 短链"，**用户可打开、匿名口不开**，与 `up.sh verify` 里 `MinIO 匿名 GET=403` 的 must 一致。

登录凭据口径（记录，避免重复踩）：`simpleLogin` 的 `password` **不是明文**，需 `r12_client.aes_zero_pad()`；直接用明文 curl 会得到 `errorCode 999 用户名或密码错误`。

### 6.10 12:46 批次加载（E 执行单服务重启）与就绪快照

| 时间 | 动作 | 结果 |
|---|---|---|
| 12:49:59 | `r12ctl.sh restart rag-index-service` | pid=1033963；18082 就绪 **12:50:43**（44s） |
| 12:50:55 | `r12ctl.sh restart rag-qa-service` | pid=1038952；18083 就绪 **12:51:07**（12s） |
| 12:51:2x | `r12ctl status` / `diag` / `up.sh verify` | 无 `[STALE_JAR]`；index DELTA **-251s**、qa **-287s**；verify **exit 0 / 30 项 ok** |
| 12:51:39 | 带 admin token `POST {GW}/qa/ai/question`（configId=1） | **200 + `text/event-stream`**，data 行增量输出，含 `reference` |

口径：本次为**单服务粒度**重启（未整栈 stop/start），执行前已向 TL 报备、执行后向 F/C 同步"就绪时刻 + DELTA"，供其证据对齐。
图侧真值仍以 **12:41:17** 为准（19529 pid=927375 此后未重启）。

---

## 7. 运维手册增补（TL 指定，冻结期只写文档不动运行态）

### 7.1 发布窗口必须按"停机成本"算，不是按"启动耗时"算

`r12-graphsvc` 实测（2026-10-27，4 次部署各一次）：
```
Stopping 12:52:42 → State 'final-sigterm' timed out → Killing 12:53:12 → Stopped → Starting → 端口可用
                      └────────────── 30s ──────────────┘
不可用总时长 ≈ 30s（等待 SIGTERM 超时）+ 5s（启动） ≈ 35s
```
根因：uvicorn 多 worker 不响应 SIGTERM → 只能等 `TimeoutStopSec=30` 到期后 SIGKILL；**期间在途请求被硬杀**，表现为"随机 5xx"。
影响：这正是今天若干"假故障"的来源之一（部署动作本身产生 5xx），与数据/逻辑无关。

处置（**冻结后**执行，本轮未做）：
1. 低成本缓解：`systemd` 侧 `TimeoutStopSec=10` + `KillMode=mixed`（先把停机成本从 30s 压到 10s）；
2. 根治：应用侧处理 SIGTERM（uvicorn `--graceful-shutdown` 或 gunicorn `--graceful-timeout`），**属应用侧，本轮不做**，在交付文档里明确标注；
3. 发布纪律：每次 restart 按 **≥35s 不可用** 计窗口；客户端需重试；不要在验收/基线期间重启（见 7.4）。

### 7.2 判断"谁在重启"的硬判据（比读日志推断可靠）
```bash
systemctl --user show -p NRestarts -p Result <unit>
```
- `NRestarts=0` 且 journal 有 `Stopping → Stopped → Starting` 循环 ⇒ **外部手发 `systemctl restart`**，不是 systemd 自愈、不是服务自崩；
- 有 `Main process exited, code=…` ⇒ 才是崩溃（`Restart=` 触发）；
- 默认 systemd **不记录"谁发的 restart"**；需要时临时加 `SYSTEMD_LOG_LEVEL=debug` 或 `ExecStop` 记录时刻。

### 7.3 已登记的独立语义缺陷（不属于部署问题）
| 缺陷 | 现象 | 影响 | 处置 |
|---|---|---|---|
| 登录参数错误映射成 5xx | `POST /auth/user/simpleLogin` 密码错误 → `HTTP 500` + `{"errorCode":"999"}`；`GlobalHandler` 只把 30016→403、10001/10002→404、4014→400，其余一律 500 | 与 F 的"拒绝态不许 5xx"口径冲突：合法的鉴权失败会被判"验收失败" | **冻结后**与 C 一起排（改 `rag-common` 需 `mvn install` + 重编 index/qa，会把已就绪 jar 变 STALE，必须安排窗口） |

### 7.4 冻结期与冷启动证据采集
- 冻结期（如 12:52–13:17）规则：**不构建、不写 `target/`、不重启任何服务**；只写源码/文档/只读验证。
- 冷启动证明方式选定为 **(B) 干净安装时一次完成**（不在此刻做单服务冷启动），要求记录每个服务的
  "启动耗时 + 首次业务探针就绪时间"。工具：`bin/boot-timing.sh`
  ```bash
  bin/boot-timing.sh                    # 只对未运行的服务计时（幂等，不打断在跑的服务）
  bin/boot-timing.sh --restart <svc…>   # 冷启动全量计时（需窗口）
  bin/boot-timing.sh --stop-only <svc…>  # 只测停机成本（发布窗口估算）
  ```
  输出：`logs/boot-timing-<ts>.tsv`（service/mode/start/ready/duration_ms/probe_code/pid/jar_mtime）。
  判据：**端口可连 + 业务探针 <500** 双条件才算就绪（只看端口会把"起了但业务炸"算通过）。
- 候选冻结前必跑（缺一不可）：`check-units.sh`、`check-exposure.sh --expect-closed`、`up.sh verify`（STALE=0）、`gates-selftest.sh`。

---

## 8. 事故记录 E-2026-10-27-03：宽泛 pkill 误伤（13:22–13:44 业务层全断）

### 8.1 现象与判定
```
13:23:22  r12-docparse.service: Failed with result 'signal'
13:23:22  dkws-skill.service:    Failed with result 'signal'    ← 另一个项目的服务
13:39:43  同上两条同时
13:41:50  同上两条同时
13:20–13:23  6 个 Java 服务全部 STOPPED、算法四服务子进程消失、docparse auto-restart 循环
13:44–13:45  Java 层逐个恢复；14:14:51 verify=0（30 项）
```
判定依据：
- `Failed with result 'signal'` = **外部发信号**，不是应用异常退出（异常会是 `exit-code`/`Main process exited`）；
- **同一秒两个不相关项目（r12 + dkws）同时被信号杀死** ⇒ 不是定向 restart，而是宽泛匹配的 `pkill -f <串>`；
- 现场还留有 `r12ctl.sh restart rag-index-service`（pid 1227877）与其子 JVM（1227879）在 13:23:00 收到 SIGTERM 后关闭上下文但进程残留。

### 8.2 影响
- 业务层 13:22–13:44 不可用（约 22 分钟），F 的基线窗口作废；
- **误伤非本项目资产**（dkws-skill），这是比"我们自己的服务断了"更严重的问题；
- 19529 在 13:52:48 再次重启（pid→1461792），图侧真值需以 14:16:13 为新基线。

### 8.3 恢复过程（未使用通配 kill）
1. 13:23 立即报 TL 与 F，并声明"90 秒无指示则按现网优先恢复"；
2. 90 秒后仍 0/12 监听 → 逐服务 `r12ctl.sh start`（gateway → auth/sensitive/qa → index）；
3. 发现已有另一路在起（`already running` 显示新 pid）→ 为避免双实例**停止继续启停**，仅清理 1227879/1227877 两个已失效残留；
4. 13:44–13:45 业务层补齐；14:14 复核 `verify=0`、六服务各 1 实例、无 `[STALE_JAR]`。

### 8.4 团队硬规矩（建议写进所有角色的操作纪律）
> 禁止 `pkill -f python` / `pkill java` / 任何宽泛匹配。只允许：①`systemctl --user stop r12-*` 精确 unit；②pidfile 中的明确 pid；③按端口定位到的 pid。
> 任何"清理残留"动作，先 `ps -o pid,cmd` 列出待杀 pid 再执行；杀完立即 `up.sh verify`。

---

## 9. 控制面自洽性（"服务在跑"不等于"控制面说对了"）

今天连续出现三例"pidfile 指向的进程 ≠ 持端口的进程"，后果比端口冲突更隐蔽：
`status` 显示 RUNNING → `stop` 杀掉的是孤儿 → 真实例继续跑 → 再 `start` 又多一个，越滚越多；且
"整栈掉线后恢复"也被这种状态放大。**根治放在脚本层，不靠人比对。**

### 9.1 `r12ctl` 新增三条硬判据（不一致即 `exit 3`）
| 判据 | 触发条件 | 提示 |
|---|---|---|
| `[PIDFILE_MISMATCH]` | pidfile 的 pid ≠ 持端口 pid（含 pidfile 缺失但端口有人监听） | 给出"`echo <listen_pid> > pidfile`" |
| `[NO_LISTEN]` | 进程活着但端口未绑定（未就绪孤儿） | `r12ctl stop` 后 `start` |
| `[STALE_JAR]`（已有） | jar 比进程新 | 附"懒加载损坏态，勿继续压测" |

### 9.2 `start` 不再制造孤儿
原实现：spawn → `sleep 3` → `pgrep -f <jar>` 写 pidfile。
若端口被上一实例占着，新 JVM 绑不上也不退出 → 留下"不监听"的 JVM，而 pidfile 恰好指向它。
现实现：**轮询到端口真正绑定**（默认 180s，`R12CTL_WAIT` 可调）→ 把**持端口的 pid**写进 pidfile；
超时则杀掉未就绪进程并返回非零。
`run/algctl.sh` 同步改造：`ALG_START_WAIT=60` 轮询端口 + `/docs` 应答；`ALG_STOP_WAIT=20` + `ALG_RELEASE_WAIT=10`
等待端口释放，消除"`STOP FAILED(: still held)` 紧接 `already listening`"的矛盾输出。

### 9.3 变更留痕：`bin/r12-change.sh`
```bash
r12-change.sh <start|stop|restart|status> <服务|all> <原因…>   # 无原因直接拒绝(exit 2)，--force 记为 NO-REASON
r12-change.sh --tail                                          # 看最近 20 条
```
`r12ctl` 的 start/stop/restart 内部都会写 `logs/changes.log`：
`时间 | 用户 | 原因 | 动作 | 目标 | 调用方 4 层进程链 | 结果`
目的不是防外部，而是**下次"服务莫名停了"能在 1 分钟内定位是"我们干的"还是"外部批量 stop"**——
今天两次整栈中断就是因为没有这条记录，排查绕了 20 分钟。

### 9.4 解析任务僵尸兜底：`recover-stuck-tasks.sh` 重写
旧版 `update ... set status=2 where status=5` 与真实枚举相反（**2=处理中、5=失败**），等于把"失败"改成
"处理中"：既不重试、又永久占并发槽。新版语义与调用方式见脚本头部枚举表；要点：
- `2 处理中 超时 → 1 待处理`、`3 重试中 超时 → 5 失败`、`5 失败 不改`、`knowledge_base_list.status=99 → 4 解析失败`；
- **任何分支都不写 status=2**；每次改动写 `error_msg`（含时间与"recover 判为僵尸"）；
- 口令改走 `MYSQL_PWD`（旧版 `-p明文` 在 `ps` 可见）；
- `--check` / `--dry-run` 两种只读模式；
- **已挂看门狗每 5 分钟兜底**（`recoverStaleTasksOnStartup` 只在重启时跑一次，今天 13:45 那批僵尸就是这样漏掉的）。

### 9.5 包与代码同步的可执行检查：`bin/pack-verify.sh`
把本轮三个交付阻断（F1 清单过期 / F2 文档顺序 / F3 脚本缺修复）变成断言：
```
① sha256sum -c（禁止 --ignore-missing）
② INSTALL 步骤**顺序断言**（"起基础设施"必须早于"初始化数据库"）+ 关键步骤必须存在
③ 必备 bin 清单 + 必备 unit 清单存在、且与仓库逐字节一致；.env.template 逐字节一致
```
实测（对盘上 24G 旧包）：`exit=1`，报 8 项阻断 —— **现在就能报红，说明断言有效**；重打后应转绿。

### 9.6 当前门禁快照（2026-10-27 14:29）
```
check-units=0  check-exposure=0  up.sh verify=0（30 项 must）  gates-selftest=0
recover-stuck-tasks --check=0（无僵尸）  watchdog 不健康组=0
pack-verify dist/offline=1（旧包，按要求待重打）
```

---

## 10. 禁止宽泛 kill（今天最贵的一课）+ 唯一清理入口

### 10.1 证据
```
13:23:22  r12-docparse.service: Failed with result 'signal'
13:23:22  dkws-skill.service:    Failed with result 'signal'    <- 另一个项目
13:39:43 / 13:41:50  同样两项目同秒 'signal'
```
两个**不相关项目**的服务在同一秒被信号杀死 ⇒ 不是定向 restart，是 `pkill -f python` / `pkill java` /
`killall` 这类**宽泛匹配 kill**。`~/.bash_history` 最后修改 09:59 之后无记录 ⇒ 不是人在终端敲的。

### 10.2 硬规矩
```
禁止：pkill -f python / pkill java / pkill -f <宽泛串> / killall
只允许 ①systemctl --user stop r12-java@<svc>  ②kill -TERM $(cat run/<svc>.pid)  ③按端口定位 pid 后杀
任何"清理残留"动作：先把 ps -o pid,cmd 贴出来，再杀。
```

### 10.3 落地：`bin/r12-kill-port.sh`（方式③的唯一入口）
```bash
r12-kill-port.sh 18082                     # 默认 dry-run：只显示"要杀谁"
r12-kill-port.sh 18082 --yes               # TERM，10s 未释放端口才升 KILL
r12-kill-port.sh 12340 --yes --with-children   # 多 worker 服务
```
内置约束：只按 `ss -ltnp` 取**该端口监听者**（不做进程名匹配）；默认 dry-run；`--yes` 才执行；
`--with-children` 才动 worker；全过程写 `logs/changes.log`。

### 10.4 落地：`r12-change.sh` 拦截宽泛目标
```
$ r12-change.sh restart python "清残留"
[FAIL] 目标 'python' 不是明确的 r12 服务名。允许: rag-auth-service … all
       按进程名/宽泛串清理被禁止（pkill/killall 会波及其它项目）。
       要清理某端口的残留进程，用: bin/r12-kill-port.sh <端口> [--yes]
```

### 10.5 处置纪律（TL 修正后）
**全栈不可用 → 只读确认 + 报 TL；90s 未恢复再问一次；超过 5 分钟 TL 不在才自行恢复。**
今天的实际情形是"多路并发 + 外部 kill"，第三人自动恢复只会让"谁起的/谁停的"更难追。

### 10.6 打包清单同步
`offline-kit.sh` 的 bin 拷贝清单已加入 `recover-stuck-tasks.sh / r12-change.sh / r12-kill-port.sh /
pack-verify.sh`（否则重打后这些"今天的修复"仍然进不了包，正是 F3 的复发路径）。
