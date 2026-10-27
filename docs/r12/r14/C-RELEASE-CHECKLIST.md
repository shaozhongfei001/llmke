# R14 上线清单与行为判据（C-business）

> 目的：每条改动都配一条**可在运行态观测**的判据。判据不写"应该会"，只写"看到什么算什么"。
> 原则：**判据要挂在必然被执行的地方，并带时间窗**——否则判据自己会产生假阴（今天发生过两次）。

## 0. 当前运行态（2026-10-27 15:26 批次）

```
rag-index-service  pid 2052541  start 15:26:48   端口 18082
rag-qa-service     pid 1647331  start 14:22:00   端口 18083
alg_retrieval_service（19995）含 FIX-14/17/18（16:16 前最后一次重启）
配置：kb.file-parse.task-timeout = 60（分钟）；search_config.depend_on_kb：id=1/12 为 1
```

## 1. 上线清单（按服务分层）

**每条改动的模板（TL 定的检查项）**：

```
改动 + 行为判据 + **它依赖哪个未写下来的前提**（若无写"无"）
```

第三格是硬要求：今天五次事故全中在这一格——`task-timeout=3600` 依赖"单位是分钟"、`RETRY_ING` 双计依赖"一个状态一种语义"、`start_time` 依赖"只表示开始时间"、`depend_on_kb` 依赖"代码读列"、`retry_times+1` 依赖"回调时状态仍是 RETRY_ING"。**五条里没有一条被写下来过。**

### 1.1 rag-index-service（jar）

| 编号 | 改动 | 行为判据（运行态可观测） | 依赖的隐含前提 |
|---|---|---|---|
| FIX-23 | 路径 `URLDecoder` 只解一次 | 含 `%` 的文件名可回取；无 `IllegalArgumentException: URLDecoder` | 路径**只被编码一次**（未写下） |
| FIX-29 | `start_time` 缺失时用 `gmt_modified/gmt_create` 兜底（防御，非本次病因） | 日志 `R14-C-FIX-29 任务 N 缺 start_time …` 仅历史脏数据出现 | 存在缺 `start_time` 的历史行 |
| FIX-30 | 在飞只算 `DEAL_ING(2)` | 调度日志 `正在处理的任务数` 与 `本次执行的任务id` 非空 | `RETRY_ING` 语义 = 等待重试，**不是在飞** |
| FIX-30b | `RETRY_ING` 且 `retry_times >= retry_limit` → `DEAL_FAIL(5)` | 任务不再永久停在 3 | `retry_limit` 语义是"尝试次数上限" |
| FIX-31 | `task-timeout` 3600 → **60（分钟）** | 见 FIX-31b 行内 `taskTimeout=60分钟` | **单位是分钟**（注释曾写"一个小时"） |
| FIX-31b/c/d | 启动参数播报（字符串拼接，挂首次调度） | 启动后 **15–30 秒**出现 `R14-C-FIX-31b 解析任务参数：… taskTimeout=60分钟（折合1.0小时）retryLimit=3`；`found 4 argument placeholders` = 0 | ~~`@PostConstruct` 保证启动执行~~（**已推翻**：`@RefreshScope` 懒代理） |
| FIX-32 | 派发前 CAS 抢占（`where id=? and status in (1,3)`） | 并发时出现 `R14-C-FIX-32 抢占失败…跳过重复派发`（**保护生效，非错误**） | ~~回调时状态仍是 `RETRY_ING`~~（**本改动打破，见 P2-01①**） |
| FIX-32b | 调度锁 `leaseTime 5s → -1`（watchdog） | 长解析期间不再重复派发同一任务 | 锁需覆盖**整个**解析窗口 |
| FIX-33 | 未超时但已跑 ≥ 阈值 1/3 → warn | `R14-C-FIX-33 解析任务 N 已运行 Xs…`；正常任务（p99 189s）不触发 | 慢任务会跨多次调度被观测到 |
| FIX-16 | group 变更审计（只记日志） | `[AUDIT-GROUP] action=JOIN/REJECT … oldGroupId/oldParent → newGroupId/newParent` | 无 |
| FIX-03c | `presign` 前 `statObject`，不存在即 404 | 不存在的键：`404`（此前可签发 200） | 调用方以"能否取回"为判据 |
| P2-01① | `retry_times` 在 `doFail` 里 +1（不依赖状态） | `retry_times` 1→2→3，第 3 次后 `status=5`、文件 `status=4` | `retry_times` 只由回调路径推进 |
| P2-01② | `claimTask` 用 `COALESCE(start_time, NOW())`（**语义修正**） | 多次重试时 `start_time` 不变（重试时刻看 `gmt_modified`） | `start_time` **单语义** = 开始时间 |
| P2-01③ | 永久性错误白名单（加密/unsupported/损坏/不存在）一次定死 | `R14-C-P2-01 终结解析任务 … permanent=true`；秒级到终态 4 | `error_msg` 含可识别关键词 |

### 1.2 rag-qa-service（jar）+ rag-common

| 编号 | 改动 | 行为判据 | 依赖的隐含前提 |
|---|---|---|---|
| FIX-13 | `metadata.source` 下发**桶内相对对象键** | `/qa` 的 `source` 形如 `r12-rag/kb_9/...`，无 `http://`、无双 host | 前端拼法是 `/minio/${source}` |
| FIX-05 | global `global_answer` 被消费（reduce 原文回显） | globalMode=true 答案含 `[L0-xxxxxxxx]` | `global_answer` 由 reduce 产生 |
| FIX-06 | SSE 拒绝体 403 + `errorCode` | 无权限 → `403 {"errorCode":"30016"}`，不再 500 空体 | 客户端按 `errorCode` 分流 |
| FIX-15 | 未选助手：个人默认 → 系统默认 → 都没有则 400+4014 | 无默认配置时 `http=400 errorCode=4014` | 默认助手存在且未被删 |
| FIX-15b | 系统默认助手不按 `create_by` 过滤 | 非 admin 走默认助手可作答 | DB 层至多一行默认（函数唯一索引保证） |
| P1-01（数据侧） | `search_config.depend_on_kb=1`（id=1、12） | 0 命中 + 无上传文件 → `answer="抱歉未能找到您要的答案"`、`resultType=4`、`refs=0` | **`depend_on_kb` 是列，不在 `config_json`** |

### 1.3 alg_retrieval_service（python）

| 编号 | 改动 | 行为判据 | 依赖的隐含前提 |
|---|---|---|---|
| FIX-14 | metadata 白名单补 `title` + 表格 7 键 + `file_ids` | 引用 metadata 含 `title`；不含 `base64/image_url` | 本处白名单是唯一裁剪点 |
| FIX-17 | 版本判定：逐行优先 `metadata.version`，缺失才 source 反推 + 两数打点 | `document_version: blocks=N 其中靠 source 路径兜底=X 无版本行=Y`；**步1 判据：兜底=0 且 无版本行=0** | `source` 路径含 `/V\d+/`（兜底路径） |
| FIX-18 | 删 `documents.setdefault(query, [])` 空键 + rerank 跳过空集合 | 大写问句开图 `refs ≥ 2`、某块 `search_type` 含 `graph`；无 `documents must be a non-empty list` | rerank 服务对空列表返回 400 |
| FIX-11b | 多版本分支 `documents.get(query) or .get(lower) or []` | 多版本/多 KB 检索不 500 | 字典键可能被小写归一化 |

### 1.4 数据与配置（不进 jar）

```
search_config.depend_on_kb = 1  where id in (1,12)          （每轮读库，无缓存，立即生效）
search_config 唯一索引 uk_search_config_default（函数索引）   （至多一行默认助手；负例 1062）
kb.file-parse.task-timeout = 60                              （@Value 静态注入，需重启 index）
```

## 2. "这批是否已加载"的唯一一眼判据

```
① 正常行（重启后 15–30 秒内，首次调度触发）
   R14-C-FIX-31b 解析任务参数：maxTaskNums=5 taskTimeout=60分钟（折合1.0小时）retryLimit=3
   出现且 taskTimeout=60      -> 代码 + 配置同时到位
   出现但 taskTimeout=3600    -> 代码新、yml 未加载（--spring.config.additional-location 指错）
   30 秒后仍无                -> 仍是旧代次（jar 未替换或进程未重启）
② 异常行必须为 0
   grep -c "found 4 argument placeholders"  == 0
```
**不要用 `strings|grep` 单独充当"已加载"的证据**：它只证明字节码里有字符串，证明不了它被执行。
纯逻辑改动（无日志文案）只能用 `javap -p -c …|grep claimTask` 或行为判据。

## 3. 未经充分验证的项（如实标注，不写"逻辑上不受影响"）

```
· P2-01 加密 PDF 端到端 3 次（耗时分布 + retry_times 轨迹）—— 待 F
· P1-01③ 带 files 的上传问答 —— 未构造场景
· FIX-17 步1（metadata.version 落库）—— 需 index 重启 + 重新解析后才可判
· 存储级重复写（同 source 并发写 ES 3 条 / Milvus 1 条）—— 未修，属独立缺陷
```

**★ 一个"差点被用错的数"（必须写进来，否则会被当成修复证据）**：

```
file 459 (pdf-encrypted)：gmt_create 15:17:11 -> gmt_modified 15:27:16（约 10 分钟）

这个 10 分钟**不是**"修复后耗时"：
  文件 15:17 上传时跑的是**旧代码**，它在旧代码下已经重试了 9 分钟；
  新代码 15:26:48 才启动，重启后首次调度（15:27:15 左右）才把它判死。
```

结论：**"数字是真的"和"数字属于哪一代"是两件事**。取"修复后耗时"必须满足：上传时间 **晚于** 新进程 `lstart`，且该任务的 `start_time >= lstart`。否则一律记为"跨代数据"，不得引用。

## 4. 已知口径（避免误判）

```
· /minio/<key> 是前端 vite 代理（→ MinIO 19000，去前缀），**不是网关路由**；直连网关 404 属正常
· MinIO 匿名已关：直连 19000 = 403 属正常；取文件走 presign(300s) 或 previewStream
· /retrieval_documents 的 knowledge_base_name 是 List[str]；返回体是 data.documents_list
· rerank 后 metadata.score 被 rerank 分覆盖，**不可**跨"开/关 rerank"比较；比块请用 source+offset+内容前缀
· /retrieval_documents 未显式传 score_threshold 时用服务端默认 0.05；/qa 用助手 config_json（多数 0.001）
· "图增量"在本环境不可观测（3 个文本块 / top_k=10，召回已满）；判"图是否命中"看 search_type 含 graph，别判块数增加
· 多 worker ≠ 多实例：判单实例只看"持端口的 pid 是否唯一"
```

## 5. 教训（每一条都对应本轮一个真实缺陷）

```
① 判据要挂在"必然被执行"的路径上，并写明时间窗
   —— @RefreshScope 懒代理使 @PostConstruct 不保证启动执行 → 播报挪到每 15 秒必跑的 execTask
② 兜底必须是"构造上不可能失败"，不是"出错了再捕获"
   —— 占位符不匹配的异常发生在 appender 层，调用点 try/catch 兜不住（这条日志坏过两次）
③ 修一个缺陷时，要检查它是否碰到了别的保护机制
   —— CAS 抢占改变了状态，打断了 `retry_times+1 依赖 RETRY_ING`；两个缺陷是同一状态机上的两个依赖
④ 一个字段只承担一个语义
   —— start_time 是"开始"，不是"最近重试"；复用会让超时永远算不出来
⑤ 改了 ≠ 生效
   —— 判定依据是"代码读哪里 / 进程加载哪份字节码 / 行为是否变化"，不是"我改了哪里"
⑥ 判据要挂在"必然被执行"的地方，而不是"应该被执行"的地方
   —— 与 ② 是一对：一个管"在哪执行"，一个管"怎么不失败"
```

> ①②⑥ 三条共同指向一件事：**验证手段本身必须先被验证一次**。
> 我们用了一条"看日志即可判"的判据，却没人确认过这行日志真的会打出来——它少一个实参而被静默丢弃，
> 导致判据指向错误结论（"没打包"），并诱发重复打包、重复重启。
> **凡是"用来判断别人对不对"的东西，自己必须先被验证一次。**

## 6. 待决策（需产品/TL，不由实现方定）

```
· depend_on_kb 默认值该不该改成 1（现在默认 0 = 允许无依据作答，新建助手天然有这个洞）
· 代码侧根治（"有检索配置 + 0 命中 → 拒答"）需先答三问：
  ① 闲聊/寒暄是否也走检索（会一律拒答）
  ② FAQ 命中但 0 文档算不算"有依据"
  ③ files 非空必须不受影响
· score_threshold 默认值（0.05 vs 0.001）是否统一 —— 会整体改变 refs 数量，牵动多条断言
· 存储级重复写是否要按 (source, version) 做幂等键
```
