# W03 整库图重建：运维脚本 `graph-rebuild.sh` 与原子发布方案

版本：V1.0（2026-10-29）
范围：`platform/r12/bin/graph-rebuild.sh`（本文件是它的设计与实测记录）
对应任务：W03「同代、按权限的整库构建与原子发布」→ F03/F05 的运维侧切片
本文件只描述**运维脚本**与**发布方案的代码改动清单**；`services/` 下任何代码本轮未改。

---

## 0. 一页结论

| 项 | 状态 |
|---|---|
| 脚本 | `platform/r12/bin/graph-rebuild.sh`，`bash -n` 通过；默认 dry-run，`--apply` 才写 |
| 对 kb 9 的实测 | `relationship` 边 **93 条**（22:23:07 那一刻），**全部**来自 `status=3` 有效文件（329/333/343）；**0 条陈旧边** |
| 本机 `--apply` 结果 | 0 删除、0 写入（ES `community_summary_kb_9` 前后都是 11 条，边数 97→97，见 §4.2） |
| **端到端（隔离 KB 1000）** | 造 6+2 条边 → 把 6 条来源文件标记已删 → `--apply` 删掉 6 条、有效 2 条不变、边数守恒 8-6=2、社区 1 个摘要 1 条、`RESULT` 可解析、rc=0；kb 9 全程 93 条未动（§9） |
| **与派工背景的差异** | 派工单给的「204 条边中 94 条只来自已删文件」**当前环境不能复现**（详见 §1.2）。不是脚本没实现，是这份数据现在不带陈旧边 |
| 并发写入（持续） | 同一份图的实测读数：94 → 97 → 93，全部来自有效文件。**这不是一次性抖动，是持续在变**（§1.3） |
| 版本绑定（已按裁决实现） | `content_fingerprint` = 9 py + rag-index-service **jar** + 部署态 yml（整文件 hash）的内容哈希；硬判据 `runtime_matches_content = 进程启动 > 内容最大 mtime`。实测同一天出现过 `false`（22:28，改了没重启）与 `true`（22:33）；`false` 时结论行直接写"本次结果不作为代次对比依据"（§1.4） |
| 原子发布 | 现在只能做到「重建前后一致性校验」；真正的 alias 原子切换**需要改 7 处代码**（C1–C7），本轮未改（§6） |

---

## 1. 事实基线（全部实测，带时间）

测量方式：MySQL 走 `docker exec r12-mysql`；Nebula 走 `platform/r12/venvs/graph/bin/python` + `nebula3` 直连 `127.0.0.1:19669`（**没有**用 nebula-console）；ES 走 `127.0.0.1:19200`。

### 1.1 数据面

| 事实 | 值 | 时间 |
|---|---|---|
| `knowledge_base.id=9` | `primitive_name=kb_9` | 2026-10-29T22:13 |
| `knowledge_base_list`（kb 9）行数 | 274 | 同上 |
| 按 status | `0=262`（已删）、`3=11`（解析成功）、`4=1`（解析失败） | 同上 |
| valid 集合（status=3） | `127,290,328,329,330,331,332,333,334,343,999002` | 同上 |
| Nebula 空间 | `g_kb_9`（`DESCRIBE SPACE`：`vid_type=FIXED_STRING(500)`，partition=10） | 同上 |
| `entity` 顶点 | 133 | 同上 |
| `relationship` 边 | **94**（22:13–22:14）→ **97**（22:15:32–22:17）→ **93**（22:22 起） | 见 §1.2/§1.3 |
| `relationship_similar` 边 | 432（`SHOW STATS` 快照记 438，统计任务本身有时滞） | 22:13 |
| 边的 `file_id` 分布 | 343=68/71、329=18、333=8（随写入变化） | — |
| ES `community_summary_kb_9` | 11 条 | 22:15 |

两条容易踩错的点，脚本按实测处理：

1. **`knowledge_base_list.file_id` 列在 kb 9 全是 `NULL`**；图边上的 `file_id` 属性存的是 `knowledge_base_list.id`（主键）。
   证据：边属性出现 `343`/`329`/`333`，对应表行 `343=R12FIX-product-intro(1).pptx`、`329=R12FIX-credit-ledger.xlsx`、`333=docx-table.docx`，都是 status=3。
   所以"有效文件集合"必须取 `id`，不是 `file_id` 列；脚本取 `id`。
2. **`status` 语义**（源码 `KnowledgeBaseListDO.java:53`）：`0:删除 1:正常 2:解析中 3:解析成功 4:解析失败`。
   派工单只说"status=3"，但把 `4:解析失败` 当已删会误删仍然可见资料的事实；脚本把 0 与"行不存在"判为已删，1/2/4 单列为「待确认」不删（§3）。

### 1.2 与派工背景数字的差异（必须记录）

派工单背景：「kb_9：status=0（已删）262 个文件、status=3（有效）11 个；图里 204 条边中 94 条只来自已删文件」。

- 262 / 11 **完全复现**（实测 262 / 11，另有 1 条 status=4 派工单未提）。
- 「204 条边中 94 条只来自已删文件」**不可复现**：当前 `relationship` 边 94→97 条，`file_id` 只有 329/333/343，**全部**是 status=3 有效文件，**陈旧边 = 0**。

多次独立测量（同一语句 `MATCH (a)-[e:relationship]->(b) RETURN e.file_id`）：

| 时刻 | 行数 | `file_id` 分布 | 备注 |
|---|---|---|---|
| 22:12:5x（首次探测，仅取 `e.file_id` 一列） | **170** | `""=70`、`343=68`、`329=18`、`333=8`、`226=6` | `226` 在 kb 9 表中**不存在**（更早已整行删除） |
| 22:13:0x（同一语句，数秒后） | 94 | 343/329/333 | `SUBMIT JOB STATS` + `SHOW STATS` 同刻也报 94 |
| 22:14:21（dry-run） | 94 | 343/329/333 | 脚本第 [2/5] 步 |
| 22:15:32（--apply） | 97 | 343=71/329/333 | 边数在增加 |
| 22:17:25（复核） | 97 | 343=71/329/333 | 暂稳 |
| 22:22:31 / 22:23:07 | 93 | 343/329/333 | 又降了 4 条 |

判读（事实与推断分开）：

- **事实**：首次探测到 170 行，其中 `file_id` 为空 70 条 + 指向已不存在行 6 条 = **76 条**；这个 76 恰好等于 R14 记录过的旧代残留数（`platform/r12/graph/rebuild_kb9_full.py` 头注释："55 个旧代顶点、76/126 条旧代边全部留存"）。
- **事实**：同一语句在数秒后稳定返回 94，且 `SHOW STATS`、`LOOKUP ON entity | GO`、`MATCH` 三种口径一致。
- **推断（未定论）**：76 条旧代边在两次探测之间被并发进程清掉了（22:15 那次还观察到边从 94 涨到 97）；也不排除首次查询命中了未完全收敛的读路径。**没有证据支持"脚本读错了"**——三口径一致 + `SHOW STATS` 都对得上 94。
- **结论**：派工单的「94 条只来自已删文件」与「全图 204 条」都不成立（204 = 94+110 或 170+34 都对不上任何实测口径）。**不要用这两个数字做验收基线**；以脚本每次现算的 `RESULT {...}` 为准。

### 1.3 并发写入未受控

22:14:21（94 条）→ 22:15:32（97 条），增量全部来自 `file_id=343`，说明**有其它进程在往 `g_kb_9` 写三元组**（本轮其它工作包）。同一时间段图服务 `19529` 还出现过一次"进程存活但不监听"：

```
[2026-10-29T22:12:30+08:00] [graphsvc] 启动宽限期内（启动于 161s 前，宽限 180s，缺 19529），本轮不判死
```
（`platform/r12/logs/watchdog.log`；22:13 起恢复可达，dry-run 第 [3/5] 步实测 `openapi.json` 返回 200。）

同一时间点 `git status` 里另有三处未提交改动：`graph_extract.py`、`graph_service.py`、`graph_summary.py`（其它工作包）。之后这三个文件被提交进 HEAD `5f1df93`，工作树只剩下 `graph_fun_tool.py`——**工作树自身的状态也在变**。

**关于 94→97 那 3 条边的归因，抽取侧给了比"同期改动"更强的证据**（`extract-w01` 提供，我已复核日志原文）：

```
2026-10-29T22:14:48.388641+0800 INFO R15-W01 EXTRACT_STATS passage=1 passage_chars=123
  llm_calls=4 rounds=1 retries=0 candidate_lines=73 parse_failed_lines=0
  field_anomalies=0 valid_entities=25 valid_triples=29 elapsed_ms=30568 | PID:1278581
```

- **事实**：该窗口内只有 1 个 passage 完成抽取（全日志仅 1 条 stats 行）；`retries=0`、`parse_failed_lines=0`、`field_anomalies=0`；`grep -c "单块重试：最终失败"` = 0，即重试路径一次都没进。
- **判读**：抽取在旧代码与新代码下的执行路径等价，`valid_triples=29` → 去重后净增 3 条边属正常增量抽取。这是**推断**，但依据是"路径未触发"而不是时间相邻。
- **对 W03 的影响**：边数变化不必归因于 W03 的替换逻辑；反过来，**"重建后边数应稳定"这类断言从现在起多了一个变量**，所以脚本把抽取侧统计做成提示项（§5.2），并在 `RESULT` 里落 `extract_stats`。

因此脚本的三条设计是必需而不是洁癖：**每步现算**（不复用 dry-run 结果）、**apply 前并发守卫**、**删后重新枚举比对**。22:22–22:23 再测已经变成 93 条，说明"读一次然后据此删除"的做法本身就不可靠。

### 1.4 版本绑定（已按 TL 2026-10-29 裁决落地：方案 c = 内容哈希）

#### 1.4.1 为什么不用 commit

实测（只读）：`worktree == HEAD` 这个判定在 **95 秒内翻过面**——22:23:07 是 `false`（`graph_fun_tool.py` 脏），22:24:42 变 `true`（该文件被提交），而**进程一次都没重启**。HEAD 在我工作期间也被推进两次（`3469699` → `5f1df93` → `68fcfb1` → …）。

结论：commit 只代表"仓库某一刻的样子"，不代表"进程加载的字节"。因此 **HEAD 降为参考字段**（`RESULT.fingerprint.head` / `dirty` / `script_dirty`），**不作判据**。

#### 1.4.2 content_fingerprint（判据本体）

文件集合由 TL 指定，**不自行扩**（扩了历史 fingerprint 就不可比）：

| 类别 | 文件 |
|---|---|
| Python（`services/rag-alg/index_data_service/index_graph_service/`） | `graph_extract.py` `graph_service.py` `graph_summary.py` `graph_types.py` `graph_fun_tool.py` `graph_community.py` `base.py` `prompt_config.py` `utils.py` |
| Java | `services/rag-java/rag-parent/rag-index-service/target/rag-index-service-*.jar` 的 sha256（**取 jar 不取源码**：源码改了没重编，源码 hash 代表不了运行版本） |
| 配置 | `platform/r12/conf/rag-index-service/application-r12.yml`，**整文件 hash**（不是只 hash `remote.*` 段，已在字段上标注） |

算法（照裁决实现）：

```
items = [ sha256( 相对路径 + "|" + 文件字节 ) for 文件 in sorted(集合) ]
content_fingerprint = sha256( "\n".join(items) )
```

实测值（2026-10-29T22:33，11 项）：

```
content_fingerprint=ca93e3c025cfa3649734d92d4ae3bbb7152908e8a681d99712599cc19d789859
逐项: application-r12.yml=242d3762062c, base.py=28b63696c42a, graph_community.py=1517e0dd9199,
     graph_extract.py=3438a51ac201, graph_fun_tool.py=7dd6d563c783, graph_service.py=19bc69512cff,
     graph_summary.py=0e471007664d, graph_types.py=19daa6acd86d, prompt_config.py=76c8a5090939,
     rag-index-service-0.0.1-SNAPSHOT.jar=d055e62e8d9f, utils.py=5a93d9a2b94c
```

#### 1.4.3 硬判据 `runtime_matches_content`

```
runtime_matches_content = 进程启动时间  >  max(上述文件 mtime)
```

- 用 **`>` 不用 `>=`**：同一秒内重启可能读到半写文件，相等必须判 false。
- `true` → 该次 `RESULT` **可用于代次对比**；结论行打印 `[ok] 本次结果可作为代次对比依据`。
- `false` → `RESULT.fingerprint.comparable=false`，结论行打印
  `[!!] 本次结果不作为代次对比依据（runtime_matches_content=false）`。
- 缺文件（jar 不在、yml 不在、某个 py 被改名）→ 逐项 `[!!]` 报出来并**跳过该项**，不静默缩小口径；同时 `comparable` 仍按实际算出的集合判定，读的人能看到"这次指纹少了几项"。

实测两个方向都出现过，都在同一天：

| 时刻 | 进程 | 内容文件最大 mtime | runtime_matches_content | 说明 |
|---|---|---|---|---|
| 22:28:37 | `PID 1333986` @22:21:25 | `graph_extract.py` @22:28:07 | **false** | 源码改了没重启 → 该次抽取跑的不是 22:28 那份实现（第一轮 E2E 因此标为不可比） |
| 22:33:25 | `PID 1404435` @22:32:44 | `graph_extract.py` @22:28:07 | **true** | 重启后内容一致 → §9.6 第二轮 E2E 就在这个窗口 |
| 22:36:37 | `PID 1404435` @22:32:44 | `graph_extract.py` @22:35:22 | **false** | 22:35:22 源码又被改（未重启）→ 判据再次翻面 |
| 22:38:33 | `PID 1439817` @22:38:07 | `graph_extract.py` @22:35:22 | **true** | 又重启了一次 → 判据翻回 true |

四个读数在 10 分钟内 **true/false/true…** 来回翻，这本身就是要"每次现算"、不能缓存判定结果的最直接理由。

> **2026-10-29 22:31 那次重启是 TL 做的**（TL 报告 `PID 1404211` @22:31:38；我实测该 PID 的 `etimes` 起点是 22:32:43，另有 `PID 1404435` @22:32:45——两个进程同时在跑，脚本取最新的那个判定）。TL 重启消除了 22:28 那处不一致；但 22:35:22 又有新改动进来，所以**"运行版本 == 工作树"只在某个窗口内成立，不是长期状态**。
>
> 本脚本全程不重启、不停服，只负责把"这一刻跑的是哪份字节"钉住；重启策略不在它职责内。

---

## 2. 用法

```bash
# 1) 只看（默认，只读，不写任何数据）
platform/r12/bin/graph-rebuild.sh 9

# 2) 真删 + 重建社区摘要
platform/r12/bin/graph-rebuild.sh 9 --apply

# 3) 0 条陈旧边也想强制重建社区（默认会跳过，省 LLM 且不动索引）
platform/r12/bin/graph-rebuild.sh 9 --apply --force-community

# 4) 抽取侧严格模式：`单块重试：最终失败 > 0` 也算失败（默认关）
platform/r12/bin/graph-rebuild.sh 9 --apply --strict-extract
```

退出码：`0` 全通；`1` 有步骤失败（此时已发生的写入**不回滚**，见 §5）；`2` 前置/用法错误（**未产生任何写入**）。

环境变量（都可选，默认值即本机实测值）：

| 变量 | 默认 | 用途 |
|---|---|---|
| `R12_ENV_FILE` | `platform/r12/.env` | 口令来源文件 |
| `MYSQL_CONTAINER` | `r12-mysql` | MySQL 容器名 |
| `W03_MYSQL_DB` | `gienrag` | 库名 |
| `GRAPH` / `ES` | `http://127.0.0.1:19529` / `:19200` | 图服务 / ES |
| `NEBULA_HOST`/`NEBULA_PORT` | `127.0.0.1`/`19669` | Nebula |
| `GRAPH_LLM_MODEL`/`_URL`/`_KEY` | 与 `probe_community_twice.py` 同值 | 社区摘要用的模型（换模型必须同步那份证据脚本，否则两边社区数不可比） |
| `GRAPH_LOG_DIR` | `<repo>/services/rag-alg/index_data_service/index_graph_service/logs/graph_service` | 抽取侧 stats 提示读哪里的日志（只读当天 `graph_info_<date>.log`） |
| `REPO` | 由脚本位置推出（`platform/r12/../..`） | 构建指纹取 `git` 的仓库根 |
| `GRAPH_REBUILD_FORCE=1` | 未设 | 越过 `--apply` 的并发守卫（后果自负，会打印 `[!!]`） |

口令处理：只从 `.env` 的 `R12_MYSQL_ROOT_PASSWORD`（或环境变量）读，**脚本内不写死任何口令**；传入 MySQL 用 `docker exec -e MYSQL_PWD`（不带 `=值`，从宿主环境转发），**口令不出现在 argv**，`ps` 看不到。读不到就 `[FAIL]` 退出 2，不静默回退默认值。

---

## 3. 判定规则（改这里必须同步本节）

`relationship` 边按 `file_id`（逗号分隔，可多来源）分 5 桶：

| 桶 | 判定 | 动作 | 理由 |
|---|---|---|---|
| **仅有效** | 所有来源都在 `status=3` | 保留 | 来源仍然有效 |
| **仅已删** | 所有来源都是 `status=0` **或该行已不存在** | `--apply` 时逐条 `DELETE EDGE` | 唯一真正该收回的"幽灵事实" |
| **混合** | 同时含有效来源与已删来源 | **不删**，报 `[!!]` | 另一个来源仍然支持这条事实；删了会丢有效结论（A05「仍有合法支持的事实不误删」） |
| **待确认** | 来源是 `status 1/2/4`，或 `file_id` 非数字 | **不删**，报 `[!!]` 并给示例 | `4=解析失败` 的文件行还在、页面仍可见；把"解析失败"当"已删"是误删高发点。需要人判定 |
| **来源未知** | `file_id` 为空 | **不删**，报 `[!!]` | 删了无据可依、无法回滚 |

补充规则：

- 只处理 `relationship`。`relationship_similar` 没有 `file_id` 属性（`DESCRIBE EDGE` 实测只有 `name, show_flag`），是遍历辅助边，不参与（W02-4 要求"社区与问答排除辅助边"）。
- **计数口径 = 全部 `relationship` 边，不按 `show_flag` / `generation` 过滤**。所以本脚本报的边数与"页面/查询侧过滤后看到的边数"可能不同。实测（22:34）：`g_kb_9` 93 条**全部** `show_flag='1'`（`generation` 分布 V1=71 / V0=22），`g_kb_1000` 2 条也全是 `'1'`——即当前不存在"过滤前 97 / 过滤后 93"的口径差，97→93 是**真的删了 4 条**（TL 已确认：他删的 4 条 `show_flag=0` 残留伪反向边）。这个口径差异在别的 KB 上仍可能出现，届时先量 `show_flag` 分布再对比数字。
- **三个口径必须分开记，不能用一个数当全部**（TL 与 W01 一致要求；本脚本只负责第一个数，另两个记在证据里）：

  | 口径 | 定义 | 用途 | 实测（`g_kb_9` 22:40） |
  |---|---|---|---|
  | `total_edges` | 全部 `relationship` 边（本脚本报的就是这个） | 报数、趋势、可复现 | **94** |
  | `per_generation_edges` | 按 `generation` 分组 | **A09（一请求固定同代、不混代）只能用这个** | V1=**71** / V0=**23** |
  | `effective_edges` | 叠加 `show_flag='1'` | W01 的 A09 双口径 | **94**（当前全部为 `'1'`） |

  为什么 A09 不能用 `total_edges`：拿总数做代次前后对比时，"代次变化"和"真实增删"会混成一个数字，正是 A09 要避免的。

- **待办（W03 阻塞项候选，交 TL 判）**：`g_kb_9` 里 **V0 代次仍有 23 条边**，而 V1 已经存在（71 条）。若按"V1 为现行代"的口径，这 23 条属**陈旧边非 0**，与 R14「重建只抽有效版本」的结论不一致——需要确认它们是"V0 输入本应排除但没排掉"还是"generation 属性写入口径不同"。**本脚本按 §3 判定规则不会删它们**（它们的 `file_id` 都是 status=3 的文件，属"仅来自有效文件"桶），所以这是一个必须由 A09/F05 侧解决的语义问题，不是删除策略问题。
- 顶点一律不动：脚本不 `DROP SPACE`、不删顶点、不碰 Milvus 图集合。`--apply` 只发 `DELETE EDGE` 单语句。
- `--apply` 且陈旧边为 0 时**跳过** `/generate_community`（图没变，重建只会白烧 LLM 并制造一次索引窗口）；需要强制用 `--force-community`。

### 3.1 `DELETE EDGE ... @rank` 语法已单独验证

rank 是本空间真实的主键之一（实测现存边 rank 是 313735900797098165 这类随机 i64，不是 0），语句不能省 `@rank`。在**临时空间** `zz_w03_probe`（建了立刻 `DROP SPACE`，不触碰任何既有数据）实测：

```
INSERT EDGE relationship(name,file_id) VALUES 'a'->'b'@0:('r0','1'),
   'a'->'b'@123456789:('rbig','1'), 'a'->'b':('rdefault','1')
MATCH 结果:            [[0,"rdefault"], [123456789,"rbig"]]      <- 默认 rank == 0，@0 那条被覆盖
DELETE EDGE ...@123456789 后: [[0,"rdefault"]]                   <- 只删该 rank
DELETE EDGE ...（不带 @rank）后: []                              <- 不带 rank 删的是 rank 0
```

结论：`DELETE EDGE relationship "src"->"dst"@rank` 语义正确；**不带 `@rank` 会删错边**（删成 rank 0），所以脚本强制带 rank。vid 用 `ngql_str()` 转义（`"`、`\`、换行、中文），有单测（§4.3）。

---

## 4. 实测输出

### 4.1 dry-run（kb 9，原始输出，未删改；抓取时刻 22:35:27）

```
$ platform/r12/bin/graph-rebuild.sh 9   # 抓取时刻 22:35:27
== W03 graph-rebuild ==
  [..] kb=9  mode=DRY-RUN  script=./platform/r12/bin/graph-rebuild.sh
== [0/5] 环境前置 ==
  [ok] python: /home/szf/data/dev/llmke-r12/platform/r12/venvs/graph/bin/python
  [ok] MySQL 口令已从 /home/szf/data/dev/llmke-r12/platform/r12/.env 读取（值不打印）
  [ok] MySQL 容器 r12-mysql 运行中
  [ok] dry-run：并发守卫不生效（本模式只读）
  [ok] primitive_name=kb_9  Nebula space=g_kb_9
  -- 内容指纹（版本绑定硬判据：进程加载的字节）--
  [ok] content_fingerprint=3d8dce3218b2bf5c…（11 项：9 py + jar + yml(整文件 hash)）
      逐项: application-r12.yml=242d3762062c, base.py=28b63696c42a, graph_community.py=1517e0dd9199, graph_extract.py=f1a63001a042, graph_fun_tool.py=7dd6d563c783, graph_service.py=19bc69512cff, graph_summary.py=0e471007664d, graph_types.py=19daa6acd86d, prompt_config.py=76c8a5090939, rag-index-service-0.0.1-SNAPSHOT.jar=d055e62e8d9f, utils.py=5a93d9a2b94c
  [!!] runtime_matches_content=false：进程(PID 1404435) 启动于 2026-10-29T22:32:45，不晚于 graph_extract.py 的 mtime 2026-10-29T22:35:22 -> 进程加载的不是当前内容；本次结果不作为代次对比依据
      [参考] HEAD=509d41d feat(r15-w01/w03/f12): description_overflow 标记、W03 端到端证据、验收脚；服务源码脏=1 项：graph_extract.py（仅供参考，不作判据）
== [1/5] 有效文件集合（MySQL knowledge_base_list.status=3）==
  [ok] 文件行 274 条，按 status 分布 0=262, 3=11, 4=1
  [ok] 有效文件 11 个: 127,290,328,329,330,331,332,333,334,343,999002
  [!!] 非有效状态: 0=已删 262 条, 4=解析失败 1 条 —— 其中只有 0 与'行不存在'算已删，1/2/4 不会被删除
  [ok] Nebula 127.0.0.1:19669 空间 g_kb_9 已选中
== [2/5] 边来源统计 ==
  全图 relationship 边合计 93 条
  [ok] 仅来自有效文件(status=3)             : 93  保留
  [ok] 仅来自已删文件(0/行不存在)               : 0  无陈旧边
  [ok] 混合来源(有效+已删)                   : 0  不删：另一来源仍支持该事实
  [ok] 待确认(status 1/2/4 或 file_id 非法): 0  不删：文件行还在，需人工判定
  [ok] 来源未知(file_id 为空)              : 0  不删：删了无据可依
== [3/5] 删除陈旧边：dry-run 跳过（加 --apply 才执行）==
  [ok] 图服务可达（http 200）：--apply 时会调 /generate_community 重建社区摘要
== [4/5] 重建社区摘要：dry-run 跳过 ==
== [5/5] 一致性校验 ==
  当前 relationship 边合计 93 条（进场时 93）
  [!!] dry-run：跳过'边数守恒/陈旧边归零/摘要条数'三项校验（需 --apply 才有写入）
  将校验: 边数守恒(93 条) / 陈旧边归零 / ES 摘要条数 == 本次摘要数
  -- 抽取侧可复现性（R15-W01 EXTRACT_STATS，仅提示）--
  [ok] passage 4 个：llm_calls=24 retries=0 parse_failed_lines=0 field_anomalies=0 valid_triples=44，平均 2.9s/次调用
RESULT {"edge_mixed": 0, "edge_pending": 0, "edge_stale": 0, "edge_stale_after": 0, "edge_unknown": 0, "edge_valid": 93, "edges_after": 93, "edges_total": 93, "extract_stats": {"field_anomalies": 0, "llm_calls": 24, "log": "graph_info_2026-10-29.log", "parse_failed_lines": 0, "passages": 4, "retries": 0, "retry_final_fail": 0, "secs_per_call": 2.9, "valid_triples": 44}, "fingerprint": {"comparable": false, "config": "platform/r12/conf/rag-index-service/application-r12.yml", "content_files": 11, "content_fingerprint": "3d8dce3218b2bf5cd7c35f4cb5605d06ea13520960c174f5af5361a9633784f3", "content_max_file": "graph_extract.py", "content_max_mtime": "2026-10-29T22:35:22", "dirty": ["services/rag-alg/index_data_service/index_graph_service/graph_extract.py"], "head": "509d41de9c9565da01a728e0cecdf51a9dcdd0a7", "jar": "services/rag-java/rag-parent/rag-index-service/target/rag-index-service-0.0.1-SNAPSHOT.jar", "per_file": {"application-r12.yml": "242d3762062c", "base.py": "28b63696c42a", "graph_community.py": "1517e0dd9199", "graph_extract.py": "f1a63001a042", "graph_fun_tool.py": "7dd6d563c783", "graph_service.py": "19bc69512cff", "graph_summary.py": "0e471007664d", "graph_types.py": "19daa6acd86d", "prompt_config.py": "76c8a5090939", "rag-index-service-0.0.1-SNAPSHOT.jar": "d055e62e8d9f", "utils.py": "5a93d9a2b94c"}, "runtime_matches_content": false, "script_dirty": ["platform/r12/bin/graph-rebuild.sh"], "service_pid": 1404435, "service_start": "2026-10-29T22:32:45"}, "kb": "9", "mode": "DRY-RUN", "primitive": "kb_9", "space": "g_kb_9", "ts": "2026-10-29T22:35:27+0800", "verdict": "PASS"}
== 结论 ==
  [ok] graph-rebuild 通过（mode=DRY-RUN kb=9）
  [!!] 本次结果不作为代次对比依据（runtime_matches_content=false）
  [!!] 本次是 dry-run，未写任何数据；确认上面的数字后再加 --apply
```

> 边数是某一时刻的快照，不是基线：同一份图在 40 分钟内测到过 94 / 97 / 93（§1.2）。验收请以当次 `RESULT` 为准，不要复制这里的数字。

末尾 `RESULT {...}` 是给上层聚合用的机器行（`acceptance.sh` / 证据归档直接 grep `^RESULT `）。

### 4.2 `--apply` 的 0 写入验证（22:15:32，当时 97 条）

在 kb 9 上跑了 `--apply`（陈旧边 0，因此不进第 3/4 步的写分支），用于验证 apply 分支的**守恒校验**数学与跳过逻辑：

```
ES_before={"count":11,...}                    # curl /community_summary_kb_9/_count
  [ok] 0 条陈旧边，无需删除
  [!!] 0 条陈旧边且未加 --force-community：图没变，跳过 /generate_community（省 LLM 且不动索引）
  删后 relationship 边合计 97 条（删前 97）
  [ok] 边数守恒：97 - 0 = 97
  [ok] 陈旧边已归零
  [ok] 有效来源边数不变：97
RESULT {"deleted": 0, ..., "mode": "APPLY", "verdict": "PASS"}      rc=0
ES_after={"count":11,...}                     # 前后一致，确认零写入
```

**这不是"验证了删除能跑通"**：kb 9 现在没有陈旧边，真删除路径只能靠 §3.1 的临时空间语法验证 + §4.3 的分桶逻辑单测覆盖。要端到端验证删除，需要先造一条"仅来自已删文件"的边（见 §7 建议）。

### 4.3 负例与单测（证明断言不空转）

分桶是"删什么"的唯一判据，所以对它做了 11 条正反例（`classify()` 抽出来单独喂合成数据，`st_map={100:3,101:3,200:0,300:4,301:1,302:2}`）：

| 用例 | 期望 | 结果 |
|---|---|---|
| `file_id=100` | valid | PASS |
| `file_id=200`（status 0） | stale | PASS |
| `file_id=999`（行不存在） | stale | PASS |
| `file_id=100,200`（混合） | mixed | PASS |
| `file_id=200,999`（逗号全已删） | stale | PASS |
| `file_id=300`（status 4 解析失败） | pending | PASS |
| `file_id=301`（status 1 正常） | pending | PASS |
| `file_id=302`（status 2 解析中） | pending | PASS |
| `file_id=""` | unknown | PASS |
| `file_id=abc` | pending | PASS |
| `file_id=100,300`（有效+待确认） | pending | PASS |

转义单测：`ngql_str('智造贷"引号"') == '"智造贷\"引号\""'`、`a\b → "a\\b"`、`含\n换行 → "含\n换行"`。

前置失败路径（全部非零退出、不写入）：

```
$ graph-rebuild.sh abc            -> [FAIL] kbId 必须是数字，收到: abc            rc=2
$ graph-rebuild.sh 999            -> [FAIL] knowledge_base 里找不到 kb 999 ...     rc=1
$ R12_ENV_FILE=/tmp/empty.env ... -> [FAIL] 里没有 R12_MYSQL_ROOT_PASSWORD ...     rc=2
$ 有并发 acceptance.py 时 --apply -> [FAIL] 检测到可能的并发重建/验收进程 ...        rc=2
```

并发守卫用 `pgrep -af 'rebuild_kb9|generate_triple|acceptance\.py'`（`pgrep` 不自匹配；用 `ps|grep` 会被自己的命令替换子 shell 命中，实测过，已换掉）。

`--strict-extract` 也做了"闸门会不会响"的验证（把 `GRAPH_LOG_DIR` 指向 `/tmp` 里一份构造日志，不碰真实日志）：

```
构造: R15-W01 EXTRACT_STATS ... retries=2 parse_failed_lines=3 valid_triples=0
      单块重试：最终失败 passage=1
默认模式   -> [ok] passage 1 个 …／[!!] '单块重试：最终失败' 1 次 -> 边数不可复现      verdict=PASS rc=0
--strict   -> [FAIL] --strict-extract：'单块重试：最终失败' 1 次 …                  verdict=FAIL rc=1
```

证明两条：① 严格模式确实会翻成失败（不是只在文档里写着）；② 默认模式不会因为别人的日志文本变红（W01 承诺的契约之外的情况也不误伤）。

---

## 5. 一致性校验与失败语义

### 5.1 三项硬校验（参与退出码）

`--apply` 的第 [5/5] 步做三项硬校验，任一不成立即 `[FAIL]` 退出 1：

1. **边数守恒**：`进场边数 - 实际删除数 == 删后边数`。不等说明有并发写入或 `DELETE` 没落地。
2. **陈旧边归零**：删后重枚举，`stale` 桶必须为 0（`DELETE` 返回 `SUCCEEDED` 不等于边没了，必须回读）。
3. **有效来源边数不变** + **ES 摘要条数 == 本次摘要数**。后者是防"新旧代摘要混在一起"：ES 侧写入是派生 `_id` 覆盖，社区变少时旧摘要不会被自动清掉（§6.2），所以第 4 步按本次响应的 `community_detail[].community_id` 反向清理，清完再对数。

### 5.2 构建指纹与抽取侧提示（不参与退出码，只落证据）

| 块 | 内容 | 是否参与退出码 |
|---|---|---|
| **内容指纹（第 [0/5] 步）** | `content_fingerprint`（§1.4.2）+ 硬判据 `runtime_matches_content`（§1.4.3）+ HEAD/脏文件作**参考** | 不改退出码，但**决定 `RESULT.fingerprint.comparable` 与结论行**：`false` 时明确写"本次结果不作为代次对比依据"。这是 TL 定的硬判据——它管的是"这份结果能不能用"，不是"这次跑成功没有" |
| 抽取侧可复现性（第 [5/5] 步末） | 从 `graph_info_<date>.log` 聚合 `R15-W01 EXTRACT_STATS`：`llm_calls` / `retries` / `parse_failed_lines` / `field_anomalies` / `valid_triples` / 单次调用耗时；并数 `单块重试：最终失败` | 默认**不参与**（假红风险，见下）；仅 `--strict-extract` 时把 `单块重试：最终失败 > 0` 升格为失败 |

`--strict-extract` 按 W01 承诺的格式契约实现（对方保证：前缀 `R15-W01 EXTRACT_STATS` 不改名、字段只允许行尾追加）：

1. 只断言一条：`单块重试：最终失败` 计数 == 0；
2. `parse_failed_lines` / `field_anomalies` 非 0 **只提示**（实测 343 块常见"超出"型异常但关系仍落地，非 0 不等于坏）；
3. **找不到 STATS 行 = SKIP，不是 FAIL**（老日志/换机器/该行未上线都属此列）。

工时估算的单位成本（W01 提供，我采纳）：同一天三个真实样本 `27.4s→20 条`、`234.59s→22 条`、`30.6s→14 条`，**单 passage 上界按 235s 算，不是 30s**——耗时与输出行数相关、波动接近一个数量级。按"passage 数 × 30s"估整库重建会严重低估；本次夹具实测 `2.9s/次调用 × 24 次` 是小文本的下限，不能当通则。

两个实现细节（都踩过）：

- **只读当天的 loguru 文件**（`logs/graph_service/graph_info_<date>.log`），**不要**同时扫 `platform/r12/logs/index_graph_service.log`——同一条 stats 行会被两个 sink 各写一次，扫两处会把 `llm_calls`/`valid_triples` 翻倍。脚本内部再按 `(passage, elapsed_ms)` 去重兜底。
- 脏文件解析**不能用 `ln[3:]`**：命令输出的整体 `strip()` 会把首行的 `" M "` 前缀吃掉一格，截出 `latform/r12/...`（实测踩到）。改用 `ln.split(None, 1)[-1]`。另外脏文件现在**只是参考字段**（`dirty` / `script_dirty`），不再参与 `runtime_matches_content` 判定——判定看的是内容哈希 + 进程启动时间（§1.4.3）。

### 5.3 失败语义

失败语义：

- 第 3 步部分失败 → 打印失败明细（最多 5 条）并 `[FAIL]`，**不回滚**（已删的边是删对了的，回滚反而制造二次不一致），需人工复核。
- 第 4 步失败但边已删 → 额外打 `[!!]` 提示"图与社区摘要现在不同代，需要重跑脚本（重跑幂等）"。这条是本轮**唯一**需要人看的中间态。
- `generate_community` 返回 `code != 200`（ES/Milvus 写入异常时服务返回 500）→ 不当成功（W06-3「社区摘要全部失败不得标已就绪」）。
- `summaries == 0` → 保留旧摘要不动，但本次重建判失败（避免把可用摘要删空）。

---

## 6. 原子发布

### 6.1 现在能做到什么（不改代码）

- **重建前后一致性校验**（可执行、已实现）：`边数守恒` / `陈旧边归零` / `有效边不变` / `ES 摘要条数 == 本次摘要数`，外加打印社区数、失败数、Milvus 双写状态（`es_ok`/`milvus_ok`）。
- **回滚靠数据事实而不是切换**：脚本不 DROP SPACE、不整体替换图；删边是逐条可枚举的（`RESULT` 里有条数，`[3/5]` 打印语句示例；批量场景建议先 `dump` 一遍要删的边再执行）。
- **重建是幂等的**：`generate_community` 的 `community_id = L<level>-sha1(kb|level|sorted(members))[:8]`，主键由它派生，重复调用不累积（R14-A 证据 `community_twice_after.json`：两次调用 ES 7 条 / Milvus 7 行，`community_ids` 与 `pks` 逐项相同）。

**做不到的**：重建期间没有原子切换点。窗口有三段，都是真实存在的：

| 窗口 | 现状 | 后果 |
|---|---|---|
| 删边 → 重建社区之间 | 图已经变了，摘要还是上一代的 | global 会引用已不存在的边/实体（引用点不开） |
| `generate_community` 内部 | Milvus 侧对社区集合是**先删旧代再写新代**（`milvus_kb_service.py:669-683`：`_visible_count` → `coll.delete(expr="pk >= 0")` → `_wait_until_deleted` → 插入） | 该集合在这段时间**为空**（删除是最终一致的，代码要等到不可见才写），global 可能读到"没有摘要" |
| ES 侧 | 没有整代替换，只按派生 `_id` 覆盖（`es.py:536-538` 明确把 `community_summary_` 排除在"写后按 source 剪枝"之外） | 社区数变少时旧摘要残留，global 读到上一代的社区 |

即：**现在的一致性靠"脚本前后对数"，不靠"发布切换"**。对验收口径（A09/A10）够用于工程验证，对"构建失败不破坏仍安全有效的旧代"不够。

### 6.2 要做真正的原子发布：改哪些代码（最小方案，本轮不改）

前提是 W03-2 的**不可变构建清单**：物理索引/集合名带代次 `g<generation>`（不是时间戳，时间戳无法与构建记录绑定）。读侧只认别名，别名名保持现在的 `community_summary_<kb>`（这样读侧零改动）。

> 行号按 2026-10-29 22:1x 的工作树状态记录。此时 `graph_summary.py` 已有其它工作包的**未提交改动**，行号可能漂移——**定位请以函数名为准**（`write_summary_indexes` / `_load_summaries` / `del_community` / `generate_community` / `community_doc_id` / `insert_vector_documents_custom`）。

| # | 文件 / 函数 | 现在 | 最小改法 |
|---|---|---|---|
| C1 | `services/rag-alg/index_data_service/index_graph_service/graph_summary.py` `write_summary_indexes()`（L73-84） | `es_index = f"community_summary_{_idx(kb)}"`、`mv_collection = f"community_summary_{kb}"` 固定名 | 增加参数 `generation`：写 `community_summary_<kb>_g<gen>`；写完不切别名，交给 C5 统一切 |
| C2 | 同上 `_load_summaries()`（L446-449） | 读固定名 | **不改**：继续读 `community_summary_<kb>`，由 C5 把它做成 alias |
| C3 | 同上 `del_community()`（L956-978） | 删固定名 | 改为"解析 alias → 删其指向的物理索引/集合"，并保留"只允许删非 active 代"的守卫 |
| C4 | `index_data_service/index_fulltext_service/src/index_fulltext_service_pactera/controller/es.py` `community_doc_id()`（L48-55）/ `derive_doc_id()`（L38-45） | 主键种子含**物理**索引名 → 物理名一换代，所有 `_id` 就变 | 种子改用**逻辑基名** `community_summary_<kb>`（不含 `_g<gen>`）。**这条是原子切换的前提**：否则每次切代 `_id` 全变，历史引用/`chunk_doc_id` 全失效 |
| C5 | `index_fulltext_service` 新增 `/alias_switch`（`es.py` 同级，仿 `del_index` 路由） | 无 | `POST _aliases`：`{"actions":[{"remove":{"index":"<old>","alias":"community_summary_<kb>"}},{"add":{"index":"<new>","alias":"community_summary_<kb>"}}]}`，**一次请求原子生效**；同名 alias 已存在时先移除再加 |
| C6 | `index_data_service/index_vector_service/src/index_vector_service_pactera/milvus_kb_service.py` `insert_vector_documents_custom()`（L471 前缀判定、L669-683 整代替换）+ 新增 `/create_alias` | 社区集合"先删后写"、无别名 | ①`_g<gen>` 集合写新代，**不删旧代**；②`utility.create_alias(collection=<new>, alias=community_summary_<kb>)` 切别名；③主键种子同样改用逻辑基名（与 C4 同一算法，两处必须同步，注释已写明"改一处必须同步另一侧"） |
| C7 | `index_graph_service/graph_summary.py::generate_community()`（L374-443） | 检测→摘要→双写→返回 | 末尾插入"校验 → 切别名 → 标记 active 代 → 释放上一代"四步；任一步失败则不切别名（旧代继续服务），并把失败按 W06-3 语义返回 |

配套但不是本次范围：`generation` 生命周期合同（`contracts/` 已登记）里要加"社区摘要物理产物的代次绑定"，以及 A10 的"撤权立即围栏"要在别名层面按可见集判定。

顺序建议：C4（主键种子）→ C5（ES alias 路由）→ C1/C2/C3 → C6（Milvus alias）→ C7（编排）。**C4 必须先做**，否则后面所有切换都会制造一次全量 `_id` 变更。

### 6.3 C4 是本轮的**阻塞项**，不是待办（TL 2026-10-29 裁决）

TL 认了 C4 的问题，但**本轮不实施**，理由与处置已确认：

- 理由：C4 改主键种子会让已有 `community_summary_kb_9` 的**全部 `_id` / `pk` 整体换一代**，必须配套"旧摘要清理 + 引用重写"，本质是一次数据迁移。在"代次还没闭环"的时候先做迁移，等于把一个可回滚的窗口变成不可回滚的窗口。
- 影响：**C1–C7（即 §6.2 全部原子发布改造）在本轮都不交付**，`community_summary_<kb>` 继续是真实索引名、无法原子切换。W03 的"同代发布"仍只能靠 §5 的前后一致性校验。
- 登记：C4 记为 **W03 阻塞项**与 **F05 的前置**。F05 要动，必须先完成 C4 的数据迁移方案（含回滚点与旧摘要清理脚本），且该方案要单独评审。
- 本轮只交付设计（§6.2），**未改 `services/` 任何代码**。

也就是说：读这份文档的人不要以为 §6.2 是"下一步就能开工"。**下一步是 C4 的迁移方案评审，不是写 alias 代码。**

---

## 7. 已知限制与后续动作

1. **`status=3` ≠ "有效版本"**。`290`（V0 loan）与 `330`（V0 intro）在表里仍是 `status=3`，但按 R14 口径（同 `parent_file_name` 取最大 `version`）它们是旧稿。本脚本按派工单用 `status=3`，所以"V0 旧稿抽出的边"会算作"保留"。当前 `g_kb_9` 没有 290/330 的边（只有 329/333/343），所以今天无影响；要按版本口径清理需新增判定，脚本未做（避免自创口径）。
2. **ES `community_summary_<kb>` 目前是"真实索引名"而非 alias**，无法原子切换（§6）。另外 ES 名 lower、Milvus 集合名保持原大小写、Nebula 空间名 `g_<primitive>` 原样——三处归一规则不同（`graph_summary._idx()` 注释里有原因），排查时不要想当然。
3. **并发写入未受控**：`pgrep` 守卫只认 `rebuild_kb9|generate_triple|acceptance.py` 三类驱动，认不出别的写入方（§1.3 实测就有一个）。真正解决要靠 W03-5 的任务/事件屏障，不是靠 `ps`。
4. **删除不可撤销**：脚本只打印语句示例与条数，没有内置 dump。批量前建议先跑 `platform/r12/graph/backup_graph.py` 或把 `[2/5]` 输出的 `stale` 明细 `--apply` 前导成 JSON 存档。
5. **端到端删除已在隔离 KB 验证**（§9），kb 9 本身仍是 0 条陈旧边、不宜拿来做破坏性验证。
   **未验证的分支**：`communities == 0` 的"合法空"分支本次没触发（实测 1 条边 / 3 个顶点仍产出 1 个社区，见 §9.5），代码按服务返回契约实现但**没有跑通证据**。
6. **计数随时在变**：本文所有边数都带时间戳（94 / 97 / 93 三个读数），因为环境里有其它写入方在跑。任何把"边数 = N"写成验收基线的做法都会第二天就红。
7. **运行代码 ≠ HEAD 是当前常态**：服务加载工作树内容、HEAD 在 22:19:45 还被推进了一次。本脚本已经把指纹落进 `RESULT.fingerprint`，但**"构建清单该绑到哪个版本"需要 TL 决定**（绑工作树 content hash？绑进程启动时的源码指纹？），这不是运维脚本能自己定的。
8. **重启不是本脚本做的**：22:09 之后图服务至少重启过 3 次（有实测启动时间的两次：`PID 1278581` @22:12:47、`PID 1333986` @22:21:25；更早一次在 22:09 前后，`watchdog.log` 里有"启动宽限期内…缺 19529"的记录）。`graph-rebuild.sh` 全程不重启、不停服。

---

## 8. 复现命令

```bash
cd /home/szf/data/dev/llmke-r12

bash -n platform/r12/bin/graph-rebuild.sh          # 语法
platform/r12/bin/graph-rebuild.sh 9                # dry-run（只读）
platform/r12/bin/graph-rebuild.sh 9 --apply        # 真删+重建（本机当前是 0 写入）

# 图侧计数（不用 console）
platform/r12/venvs/graph/bin/python - <<'PY'
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool
p=ConnectionPool(); p.init([('127.0.0.1',19669)],Config()); s=p.get_session('root','nebula')
s.execute('USE g_kb_9')
print(s.execute('MATCH (a)-[e:relationship]->(b) RETURN e.file_id AS f').row_size())
s.release(); p.close()
PY

# 摘要条数
curl -s http://127.0.0.1:19200/community_summary_kb_9/_count

# 抽取侧统计（脚本第 [5/5] 步读的就是这里；注意不要再扫 platform/r12/logs/ 那份，会双计）
SVC=services/rag-alg/index_data_service/index_graph_service/logs/graph_service
grep -h "R15-W01 EXTRACT_STATS" "$SVC/graph_info_$(date +%F).log" | tail -5
grep -c "单块重试：最终失败" "$SVC"/graph_info_*.log

# 运行版本指纹（脚本第 [0/5] 步做的同一件事）
git -C . rev-parse HEAD; git -C . status --porcelain -- services/rag-alg/index_data_service/index_graph_service
ls -l --time-style=+%FT%T services/rag-alg/index_data_service/index_graph_service/graph_extract.py
pgrep -af graph_api_start
```

---

## 9. 端到端验证（隔离 KB，2026-10-29 22:27–22:34，两轮）

目的：证明 `--apply` 的删除路径在**真实图数据**上成立——kb 9 现在陈旧边为 0，拿它验证不了删除。全过程不碰 kb 9、不重启服务。

### 9.1 夹具怎么造出来的（可复现）

走真实产品入口（登录 → 建库 → 上传 → 解析），再走真实抽取入口（`POST /generate_triple_data`）：

| 步骤 | 实际结果 |
|---|---|
| 登录 `POST /auth/user/simpleLogin` | 200 |
| 建库 `POST /index/knowledgeBase/create`，`kbName=r15-w03-probe` | 200，`kbId=1000`，`primitiveName=kb_1000`（Nebula 空间 `g_kb_1000`） |
| 上传 2 个夹具 docx（`R14FIX-graph-01-project.docx` / `R14FIX-graph-02-dept.docx`） | 均 200，`kb_list.id` = `999003` / `999004`，解析后 `status=3`，ES `kb_1000` 2 条 |
| 图抽取 `POST 19529/generate_triple_data`（`col_name=file_id`, `col_values=[999003,999004]`） | 200，74s，`edges_written=8` |
| 边分布 | `999003 → 6 条`、`999004 → 2 条`（合计 8） |
| **造"已删"** | `update knowledge_base_list set status=0 where kb_id=1000 and id=999003` → 该文件 6 条边变成"仅来自已删文件"，另 2 条仍有效 |

> 关于造数据方式：只把 `status` 改成 0，**没有**同时删 ES 文档/向量。理由是脚本的唯一判据就是 `status`（§3）；真删 ES 会让这个夹具失去"另一文件仍有效"的对照，反而削弱断言。这一点如实写明，不冒充"完整删除链路"。

### 9.2 dry-run（真实输出，节选）

```
== [1/5] 有效文件集合（MySQL knowledge_base_list.status=3）==
  [ok] 文件行 2 条，按 status 分布 0=1, 3=1
  [ok] 有效文件 1 个: 999004
  [!!] 非有效状态: 0=已删 1 条 —— 其中只有 0 与'行不存在'算已删，1/2/4 不会被删除
== [2/5] 边来源统计 ==
  全图 relationship 边合计 8 条
  [ok] 仅来自有效文件(status=3)             : 2  保留
  [!!] 仅来自已删文件(0/行不存在)               : 6  --apply 时逐条 DELETE EDGE
  [ok] 混合来源(有效+已删)                   : 0  不删：另一来源仍支持该事实
  [ok] 待确认(status 1/2/4 或 file_id 非法): 0  不删：文件行还在，需人工判定
  [ok] 来源未知(file_id 为空)              : 0  不删：删了无据可依
== [3/5] 删除陈旧边：dry-run 跳过（加 --apply 才执行）==
  将删除 6 条；示例语句：
    DELETE EDGE relationship "启明计划"->"恒星项目一期"@607488791311432274
    DELETE EDGE relationship "启明计划"->"恒星项目一期"@788103995677433323
    DELETE EDGE relationship "恒星项目一期"->"2026年9月"@284590625794598767
    DELETE EDGE relationship "恒星项目一期"->"2026年9月"@1000820877368422334
    DELETE EDGE relationship "装备制造板块"->"三家配套企业"@393601861127176005
```

dry-run 的 `RESULT`：`edge_stale=6`、`edge_valid=2`、`verdict=PASS`（dry-run 不改数据，`edges_after` 仍是 8）。

### 9.3 `--apply`（真实输出，节选）

```
== [3/5] 删除陈旧边（逐条 DELETE EDGE，无批量、无 DROP SPACE）==
  [ok] 已删除 6 条陈旧边
== [4/5] 重建社区摘要（POST /generate_community）==
  重建前 ES community_summary_kb_1000 摘要 0 条
  http=200 用时 5.8s  msg=社区 1 个，摘要 1 条，失败 0 条
  [ok] 社区数 1 / 摘要数 1 / 失败数 0（es_ok=True milvus_ok=True）
  [ok] ES 按新代 community_id 清理：命中新代 1 条，删除旧代 0 条
  重建后 ES community_summary_kb_1000 摘要 1 条（重建前 0）
== [5/5] 一致性校验 ==
  删后 relationship 边合计 2 条（进场时 8）
  [ok] 边数守恒：8 - 6 = 2
  [ok] 陈旧边已归零
  [ok] 有效来源边数不变：2
  [ok] ES 摘要条数 == 本次摘要数 == 1；社区数 1；失败 0
== 结论 ==
  [ok] graph-rebuild 通过（mode=APPLY kb=1000）
```
`rc=0`。`RESULT` 行可 `json.loads`；下面是为便于阅读删掉了 `extract_stats` / `fingerprint` 两段后的样子（原行是单行 JSON，两段都在）：

```json
{"community": {"communities": 1, "es_after": 1, "es_before": 0, "es_index": "community_summary_kb_1000",
  "es_removed": 0, "failures": 0, "secs": 5.8, "summaries": 1},
 "deleted": 6, "edge_mixed": 0, "edge_pending": 0, "edge_stale": 6, "edge_stale_after": 0,
 "edge_unknown": 0, "edge_valid": 2, "edges_after": 2, "edges_total": 8,
 "kb": "1000", "mode": "APPLY", "primitive": "kb_1000", "space": "g_kb_1000",
 "ts": "2026-10-29T22:28:43+0800", "verdict": "PASS"}
```

### 9.4 断言逐条对账

| # | 断言 | 期望 | 实际 | 结果 |
|---|---|---|---|---|
| 1 | dry-run 报告陈旧边 | 派工单写"1 条" | **6 条**（该文件产出 6 条边，全部仅来自它） | PASS（数量以数据为准，见下） |
| 2 | `--apply` 后陈旧边消失 | 0 | `edge_stale_after=0`，回读 `g_kb_1000` 只剩 2 条 | PASS |
| 3 | 有效边不变 | 2 | 2（`edge_valid=2` 前后一致） | PASS |
| 4 | 边数守恒 | 8-6=2 | 8-6=2 | PASS |
| 5 | `RESULT` 行可解析 | JSON | `json.loads` 成功，字段齐全 | PASS |
| 6 | 重复执行幂等（额外） | 0 陈旧边、0 写入 | `22:29:14` 复跑 dry-run：`edge_stale=0`、`edges_total=2`，跳过 `/generate_community` | PASS |
| 7 | kb 9 未被触碰（额外） | 93 条边 / 11 条摘要不变 | 前：`g_kb_9 edges=93`；后：`93`；`community_summary_kb_9` 仍 11 条 | PASS |
| 8 | 未重启服务（额外） | PID 不变 | 全程 `PID 1333986` | PASS |

关于断言 1 的期望值：派工单预期"1 条陈旧边"，实际是 6 条——因为一次抽取对该文件产出 6 条边，脚本删的是**全部 6 条**（按设计逐条删，不做"删一条示意"）。这不是偏差，是把期望值写细了。

### 9.5 这轮 E2E 暴露/确认的三件事

1. **`community_summary_kb_1000` 与真实索引名一致**：脚本用 `community_summary_` + `primitive.strip().lower()` 计算（与 `graph_summary._idx()` 同规则），`es_before=0 / es_after=1` 与写入条数对得上，说明这个拼法对 `kb_*` 形态的 primitive 是正确的。
   但顺带观察到一处**既有的命名不一致**（与本脚本无关）：对 `rag_graph` 调 `generate_community` 后，ES 里真实索引名是 `community_summary_ragraph`（下划线被去掉），而不是 `community_summary_rag_graph`。原因未定位。**结论：本脚本只对 `kb_*` 形态实测过；primitive 里带额外下划线的 KB 需要先核对真实索引名。**
2. **"合法空"分支没被触发 → 记为 UNVERIFIED（有明确验证条件，本轮不造）**：删完 6 条边后空间只剩 2 条边 / 3 个顶点，`generate_community` 仍返回 `communities=1`（`size=3, edge_count=2`）。所以 `communities == 0` 的"合法空"分支本次**没有跑通证据**，只能按服务返回契约（`graph_summary.py::generate_community` 里 `if not communities: return code=200, msg="未检测到满足条件的社区（图可能过小）"`）实现。
   **判据（TL 2026-10-29 明确）：该分支要验证，必须造一个顶点数 < 3 的空间**——例如只上传 1 个极短文件、使其抽不出 ≥3 个实体。本轮不造，状态记 **UNVERIFIED**；**不得为了让分支"有证据"而临时改判据**（例如把 `min_community_size` 调大后拿正常图冒充"合法空"，那是改被测条件，不是验证）。
3. **服务进程没加载最新改动（新指纹块当场抓到）**：第一轮 `--apply` 那一步的指纹是
   `service_start=2026-10-29T22:21:25` / `content_max_mtime=2026-10-29T22:28:07`（`graph_extract.py`）→ `runtime_matches_content=false`。
   即：**那一轮抽取用的不是 22:28:07 那份实现**，所以第一轮 RESULT 标记为"不可作代次对比"（第二轮在重启后复跑，见 §9.6，那次 `comparable=true`）。
   这不是本脚本能修的（需要重启服务，而重启不在本任务授权内），但它说明"跑过一次就代表当前代码"在本环境不成立——这条已作为 `[!!]` 打印，可作为 A14「运行版本正确」的证据入口。同一现象在 22:35:27 又出现一次（`graph_extract.py` 被再次修改，mtime 22:35:22 > 进程启动 22:32:45）——**这个环境里源码改动比服务重启频繁得多**，所以判据必须是"每次现算"，不能缓存。

### 9.6 第二轮：在 `runtime_matches_content=true` 窗口复跑（结果可用于代次对比）

第一轮（§9.2–9.3）跑在 22:28，当时指纹是 `runtime_matches_content=false`（进程 22:21:25 早于 `graph_extract.py` 的 mtime 22:28:07）——按 §1.4.3 的硬判据，**那一轮的 RESULT 不能用于代次对比**。所以服务重启后（`PID 1404435` @22:32:44）又做了一遍完整流程：

1. `status` 999003 恢复为 3 → 重新 `generate_triple_data`（`edges_written=8`，6+2 与第一轮一致，说明同一输入可复现）
2. 再次置 `status=0`（造陈旧边）
3. dry-run → `--apply`

```
-- 内容指纹（版本绑定硬判据：进程加载的字节）--
  [ok] content_fingerprint=ca93e3c025cfa364…（11 项：9 py + jar + yml(整文件 hash)）
  [ok] runtime_matches_content=true：进程(PID 1404435, 2026-10-29T22:32:44) 晚于 graph_extract.py 的 mtime
       2026-10-29T22:28:07 -> 本次结果可用于代次对比
      [参考] HEAD=509d41d …；服务源码脏=0 项（仅供参考，不作判据）
```

dry-run：`edge_stale=6 / edge_valid=2 / edges_total=8`，`fingerprint.comparable=true`。

`--apply`（rc=0）：

```
  [ok] 已删除 6 条陈旧边
  重建前 ES community_summary_kb_1000 摘要 1 条
  http=200 用时 9.5s  msg=社区 1 个，摘要 1 条，失败 0 条
  [ok] ES 按新代 community_id 清理：命中新代 1 条，删除旧代 0 条
  删后 relationship 边合计 2 条（进场时 8）
  [ok] 边数守恒：8 - 6 = 2
  [ok] 陈旧边已归零
  [ok] 有效来源边数不变：2
  [ok] ES 摘要条数 == 本次摘要数 == 1；社区数 1；失败 0
== 结论 ==
  [ok] graph-rebuild 通过（mode=APPLY kb=1000）
  [ok] 本次结果可作为代次对比依据（runtime_matches_content=true）
```

两轮的差别只有指纹与"是否可比"，删除/守恒/对账三项断言结果完全一致。**第二轮这次才是可以拿去和别的代次对比的记录**（`content_fingerprint=ca93e3c025cfa3649734d92d4ae3bbb7152908e8a681d99712599cc19d789859`）。

### 9.7 遗留夹具清单与清理单（已于 2026-10-29 22:39–22:41 授权执行，回读见 9.7.1）

**现状（2026-10-29 22:36 实测）**

| # | 对象 | 位置/名字 | 规模 | 来源 |
|---|---|---|---|---|
| 1 | 夹具 KB | MySQL `gienrag.knowledge_base` `id=1000`，`kbName=r15-w03-probe`，`primitive_name=kb_1000` | 1 个库 + 2 个文件行（`999003` status=0、`999004` status=3） | §9.1 建的 |
| 2 | 图空间 | Nebula `g_kb_1000` | 3 个 `entity` 顶点 / 2 条 `relationship` 边 | `generate_triple_data` 建的 |
| 3 | 主索引 chunk | ES `kb_1000` | 2 条 | 上传解析写的 |
| 4 | 社区摘要（ES） | ES `community_summary_kb_1000` | 1 条 | §9.3/§9.6 `generate_community` 写的 |
| 5 | 社区摘要（Milvus） | `graph_base._community_summary_kb_1000` | 1 行 | 同上（双写） |
| 6 | **副作用**：R13 测试空间摘要 | ES `community_summary_ragraph`（注意：真实名字里下划线被吞，见 §10） | 1 条 | 我为验证"图太小"的返回形状，对 `rag_graph` 调了一次 `generate_community` |

**保留原因（TL 2026-10-29 裁决）**：① 复跑幂等还要用（22:29:14 dry-run `edge_stale=0` 已验证）；② 删除不可逆，由 TL 在收尾时统一执行。

### 9.7.1 清理记录（TL 已授权的执行）

**清理前盘点（2026-10-29T22:39:17+0800，只读）**

| 对象 | 清理前 |
|---|---|
| MySQL `knowledge_base` id=1000 | 存在：`r15-w03-probe` / `primitive_name=kb_1000` |
| MySQL `knowledge_base_list` where kb_id=1000 | 2 行 |
| Nebula `g_kb_1000` | 存在；`relationship` 边 2 条（`generation=''` 2 条、`show_flag='1'` 2 条） |
| ES `kb_1000` | 存在，2 条 |
| ES `community_summary_kb_1000` | 存在，1 条 |
| Milvus `graph_base._community_summary_kb_1000` | 存在，可见行 1 行（`num_entities` 报 2 —— 删除最终一致，**盘存以 `query` 可见行为准，不能看 `num_entities`**） |
| ES `community_summary_ragraph`（副作用） | 存在，1 条 |
| **kb_9 基线（要求不动）** | 边 **94** 条（`generation` V1=71 / V0=23，`show_flag='1'` 94）；ES `community_summary_kb_9` **11** 条；Milvus `_community_summary_kb_9` 存在 |

> kb_9 的边数从本文前面记录的 93 变成 94（又多 1 条 V0 边），是别人在写，不是本次清理造成的——清理前后各取一次快照就是为了把这件事分清。

**清理执行（2026-10-29T22:39:5x–22:40:5x）**

| 步 | 动作 | 结果 |
|---|---|---|
| ① | 产品接口 `DELETE /index/knowledgeBase/delete?id=1000` | http=200 `data=true`；ES `kb_1000` 已被删（前后各查一次确认） |
| ② | Nebula `DROP SPACE g_kb_1000`（先 `SHOW SPACES` 确认存在） | `is_succeeded=true`；5 秒后 `SHOW SPACES` 里已消失 |
| ③ | 删社区摘要（ES 索引 + Milvus 集合），对 `kb_1000` 与 `rag_graph` 各一次 | ES 两个索引 `{"acknowledged":true}`；Milvus 两个集合 `dropped=true` |

③ 有一处**必须记录的执行偏差**：原计划走 `POST 19529/del_community`（服务侧双写删除），但当时图服务**进程在跑、19529 不监听**（`del_community:000`；`watchdog.log` 同时刻写"启动宽限期内（启动于 144s 前，缺 19529）"），所以改为**等价直连**：ES 侧 `DELETE /community_summary_<kb>`（即 `del_index` 的效果）+ Milvus 侧 `POST 19526/del_collection`（名字不带前导下划线，服务端自己加）。**没有重启服务**。

**清理后回读（2026-10-29T22:40:53，只读）**

| 对象 | 期望 | 回读 | 结论 |
|---|---|---|---|
| Nebula `g_kb_1000` | 不存在 | `ABSENT`（`SHOW SPACES`: `g_kb_22 g_kb_26 g_kb_9 g_rag_graph rag_graph`） | ✅ |
| ES `community_summary_kb_1000` | 不存在 | `_cat/indices` 无该名，`_count` 404 | ✅ |
| ES `kb_1000` | 不存在 | 同上 | ✅ |
| ES `community_summary_ragraph`（副作用） | 不存在 | 同上 | ✅ |
| Milvus `_community_summary_kb_1000` | 不存在 | `utility.has_collection=false` | ✅ |
| Milvus `_community_summary_ragraph` | 不存在 | `has_collection=false`；`list_collections` 里 community 相关只剩 `_community_summary_kb_9` | ✅ |
| MySQL `knowledge_base` id=1000 | 不存在 | **仍存在，`status=0`**（软删） | ⚠️ 见 §9.7.2 |
| MySQL `knowledge_base_list` where kb_id=1000 | 不存在 | **仍有 2 行，且 `999004` 仍是 `status=3`** | ⚠️ 见 §9.7.2 |
| **kb_9（要求不动）** | 94 边 / 11 摘要 | 边 **94**（V1=71 / V0=23，`show_flag='1'` 94，与清理前**逐项相同**）；ES `community_summary_kb_9` **11** 条；Milvus `_community_summary_kb_9` 存在 | ✅ 未被动到 |

### 9.7.2 清理时发现的两件事（都不是本脚本能修的）

1. **产品侧"删 KB"是软删，且不联动下层**：`DELETE /index/knowledgeBase/delete` 返回成功、用户列表里确实消失、ES 主索引也删了，但：
   - `knowledge_base` 行还在（`status=0`）；
   - **`knowledge_base_list` 的文件行完全没动**——`999004` 仍然 `status=3`（"解析成功"）。

   这意味着：**图空间、社区摘要、kb_list 的 status 都不会因为"删了知识库"而自动收回。** 这正是 `graph-rebuild.sh` 存在的理由；同时也说明 A10「删除/撤权」若只看产品接口返回会误判"已清理干净"。
   本轮**没有**直接 SQL 硬删这两张表的行——那是绕开产品的写操作，不属于"清理夹具"的授权范围。若 TL 要彻底抹掉，需要单独授权并确认是否影响软删审计链。

**清理后再跑一次脚本（22:41:24）**：对已删的 kb 1000 执行 dry-run，脚本 **fail-closed**：
```
[FAIL] graph-rebuild 未通过（mode=DRY-RUN kb=1000）：
       Nebula 空间 g_kb_1000 不存在或不可用: SpaceNotFound: SpaceName `g_kb_1000`
```
即"KB 已经没了"不会让脚本静默跑成 PASS——这条顺带验证了第 [0/5] 步的空间存在性检查。

2. **`del_community` 端点在服务未监听时静默不可用**：`curl` 直接 `000`（连接拒绝），不会有业务错误码。所以**不能只凭"调用过 del_community"就认为摘要删了**，必须回读 ES `_cat/indices` 与 Milvus `has_collection`。本次就是靠回读才发现要走等价直连。

**清理单（逐条；每条都标影响面与不可逆性；执行前逐条确认对象仍是表里的那个）**

```bash
# 前置：确认不是 kb_9、不是业务库。三条只读确认，先跑
docker exec -e MYSQL_PWD -i r12-mysql mysql -uroot -N -e \
  "select id,kb_name,primitive_name from gienrag.knowledge_base where id=1000;"
curl -s 'http://127.0.0.1:19200/_cat/indices/community_summary_*?h=index,docs.count&format=json'

# ① 删夹具 KB（走产品接口；连带 kb_list 行、索引与任务）
#    影响面：该 KB 的文件记录/解析产物/检索数据；不可逆（无回收站）。
#    先用 /index/knowledgeBase/list 确认 kbName=r15-w03-probe 且 id=1000，再执行。
curl -s -X DELETE -H "Authorization: <token>" 'http://127.0.0.1:8088/index/knowledgeBase/delete?id=1000'

# ② DROP 图空间 g_kb_1000（Nebula）
#    影响面：3 顶点 / 2 边；不可逆。⚠ 必须带 g_ 前缀，且**只删 g_kb_1000**——
#    传错名字不会报错（DROP SPACE IF EXISTS 幂等），所以先 SHOW SPACES 确认存在再删。
platform/r12/venvs/graph/bin/python - <<'PY2'
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool
p=ConnectionPool(); p.init([('127.0.0.1',19669)],Config()); s=p.get_session('root','nebula')
print("exists:", "g_kb_1000" in [s.execute("SHOW SPACES").row_values(i)[0].as_string()
                                  for i in range(s.execute("SHOW SPACES").row_size())])
# 确认上面是 True 再放开下一行
# print(s.execute("DROP SPACE g_kb_1000").is_succeeded())
s.release(); p.close()
PY2

# ③ 删社区摘要索引 + Milvus 集合（走服务接口，双写一起删）
#    影响面：ES 1 条 + Milvus 1 行；不可逆。
#    注意 del_collection 会自己加前导下划线，所以 collection_name 传不带下划线的名字。
curl -s -X POST http://127.0.0.1:19529/del_community -H 'Content-Type: application/json' \
  -d '{"space_name":"kb_1000"}'
#    副作用那条（rag_graph）同样用这个接口，但 space_name 传 "rag_graph"：
#    ⚠ 它会被服务端 replace("g_","") 改成 "ragraph" —— 恰好对上真实索引名，
#      所以这条**能删对**；但如果你把它当"正常"用，就会误以为接口没问题（见 §10）。
```

**不建议**用 `curl -X DELETE $ES/community_summary_kb_1000` 直接删索引：那样 Milvus 侧会留孤儿行（双写只删一半），下次重建时 `_visible_count` 还会把它当旧代。要么走 `/del_community`，要么 ES/Milvus 两边都删。

---

## 10. 边界缺陷记录：primitive 里含 `g_` 时 ES 社区摘要索引名会被改写（本轮不修）

**状态**：已定位根因，**本轮不修**（属 `services/`，且不影响 kb_/现有业务 KB）；脚本已加只读核对与告警。

**现象**（实测）：对 `rag_graph` 调 `generate_community` 后，ES 里真实索引名是 `community_summary_ragraph`，而不是按 `graph_summary._idx()`（只做 `strip().lower()`）推算的 `community_summary_rag_graph`。

**根因**（2026-10-29 22:38 定位到具体语句）：

```python
# services/rag-alg/index_data_service/index_graph_service/graph_summary.py
#   generate_community() 约 L377、del_community() 约 L958
space_name = str(payload.get("space_name", "")).replace("g_", "")
```

`.replace("g_", "")` 是**全局替换**，本意是去掉图空间前缀 `g_`，但它会吃掉字符串里**任意位置**的 `g_`：

```
'rag_graph'.replace('g_','')      -> 'ragraph'        # 应为 rag_graph
'rag_graph'.removeprefix('g_')    -> 'rag_graph'      # 正确写法
```

于是 `write_summary_indexes("ragraph")` 写出 `community_summary_ragraph`；`_load_summaries` 又用**原样 primitive** 去读（`f"community_summary_{_idx(kb)}"`），**写读两侧名字不一致**——这类 KB 的 global 会"写入成功但读不到摘要"。

**影响面**：`primitive_name` 里含字面量 `g_` 的 KB（例如 `rag_graph`、`log_group`、`cfg_xx`）。`kb_9` / `kb_1000` 这类 `kb_<数字>` **不受影响**，因此不阻塞本轮。

**本轮已做的（脚本侧，只读）**：`graph-rebuild.sh` 新增 `precheck_index_name()`——primitive 不是 `kb_<数字>` 时，去 `_cat/indices/community_summary_*` 核对真实名，并按服务端同一套 `replace("g_","")` 算出"服务端形态"：

```
正例 kb_9          -> 直接返回 community_summary_kb_9（不查 ES）
反例 rag_graph     -> [!!] 按 _idx() 规则应写 community_summary_rag_graph，但服务端 replace("g_","")
                      把 primitive 改成了 ragraph，真实索引是 community_summary_ragraph …
```

**临时规避（给运维/验收用）**：对非 `kb_<数字>` 形态的 primitive，**先** `GET /_cat/indices/community_summary_*?h=index&format=json` 核对真实索引名，再对照脚本第 [4/5] 步的"ES 摘要条数 == 本次摘要数"断言；对不上就说明命中了本缺陷，不要把它当成"重建失败"。

**修复建议（留档，不在本轮）**：`graph_summary.py` 两处 `.replace("g_", "")` 改成 `.removeprefix("g_")`，并补一条回归：`primitive=rag_graph` 时写入与读取的索引名必须相同。改完需要清理一次已错名的 `community_summary_ragraph`（1 条），否则那批摘要会永久读不到。
