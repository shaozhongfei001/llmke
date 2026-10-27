# R14 严格断言基线（洁净轮 · 权威结论）

- 证据目录：`platform/r12/qa/evidence/R14-BASELINE-CLEAN-20261027T032432Z`
- 运行窗口：2026-10-27 11:24:32 – 11:35:30 CST（UTC+8）
- 脚本：`platform/r12/qa/{r13_full_check,acceptance,security_acceptance,revoke_acceptance,permission_domain_scope}.py`（R14 收紧版）
- 断言自检：**66/66 一致**（`assert_selftest.py`）；对 R13 旧断言同跑 **26/60 → 34 条不符**（`R14-SELFTEST-20261027T023154Z-r13qa`），证明自检非空转。

> 为什么有"洁净轮"：11:24 之前的环境经历 jar 热替换、整栈拆除重装（见 §5），且旧版 `acceptance.py` 会整批 OVERWRITE kb_9。本轮改为**独立验收库 + 每次先删后建**，并等到"连续两次 smoke 200"后才开跑。**产品结论只取本轮。**

## 0. 环境前置

| 时点 | date | `ss -lnt｜grep -c 1999` | 容器数 | 事件 |
|---|---|---|---|---|
| 11:24:32 | 2026-10-27T11:24:32+0800 | 2（127.0.0.1:19995/19996） | 14 | 6 个 Java 服务端口全在（8088/18081/18082/18083/18084/18085）；连续两次 smoke `智造贷最高额度` = 200（len 20185 / 21363）后才开跑 |
| 11:32:01 | 2026-10-27T11:32:01+0800 | 2 | 14 | 同上（ports6=6） |

ES `_cluster/health` 已 green（E 侧 `number_of_replicas=0`），本基线**不再以 yellow 为预期**。

## 1. 总账

| 套 | 严格通过 / 总数 | 耗时 | FAIL |
|---|---|---|---|
| `r13_full_check.py` | **5 / 7** | 29s | FAQ、GLOBAL |
| `acceptance.py`（独立库 kb_17，全场景） | **34 / 34** | 117s | — |
| `security_acceptance.py` | **16 / 16** | 3s | — |
| `revoke_acceptance.py` | **20 / 21** | 36s | R4（FAQ 直答） |
| `permission_domain_scope.py`（F05） | **8 / 8** | 8s | — |
| **合计** | **83 / 86** | 193s | 3 |

覆盖判定：`acceptance.py` 的 `COVERAGE` = **OK**（选中 8 个场景全部真实执行）。

## 2. FAIL 归类（3 条 → 2 个根因，全部产品缺陷，无环境 FAIL）

### A. FAQ 直答通道整体失效（2 条 FAIL 同源）→ 产品缺陷（检索层，A/B）
命中用例：`r13_full_check.FAQ`、`revoke_acceptance.R4`

事实链（可复核）：
1. 应用侧：`config_id=9`（enabled_faq=true）提问「客户访前准备是否是文档的主要内容？」，`http=200 status=2` 但 **`resultType=1`**（普通 LLM 回答，非 FAQ 直答的 2）。
2. 检索侧直连 19995（enabled_faq=true，rerank 开/关各一次）：`data.faq_result_list = 0`，`documents_list = 1`。
3. 数据侧：ES `faq_kb_9` 有 **20 条**，且第一条正是 `客户访前准备是否是文档的主要内容？@@不是，客户访前准备是文档的一部分内容，但不是主要部分。`（score 8.13）。
4. 断点：`alg_retrieval_service` 日志
   `multiple_retrieval:retrieval_milvus:214 - 解析 offset 失败: Expecting value: line 1 column 1 (char 0)`，
   而 FAQ 文档的 `metadata.offset` 实测为 **None（null）** → 解析异常 → 20 条命中被整批丢弃。

结论：不是"FAQ 没数据"，也不是阈值问题，是**检索层对 `offset=null` 不健壮**。修法建议：offset 缺失/非 JSON 时按"无定位信息"继续（或跳过该字段），而不是中断 FAQ 分支。归 A-data/B-graph 定位 `multiple_retrieval.py:214`。

### B. GLOBAL 跨文档归纳（1 条 FAIL）→ 产品缺陷（B/C 在改）
`r13_full_check.GLOBAL`：`http=200 status=2 refs=1`，断言要求 ≥2 条可解析来源且非拒答话术。
- 与首轮（10:18）相比，**引用 host 重复拼接已修**（C 侧 `toAbsoluteSource` 生效，本轮 source 已是可解析相对键 `r12-rag/kb_9/...`）。
- 仍不达标的原因按 C 的说法：`data.global_answer` 无人消费、reduce 结果被丢弃 → 退化。
- 归类依据：这不是环境（同窗口内其他 6 项能力均 200），也不是断言过严（≥2 来源是跨文档归纳的最低要求）。

## 3. 本轮由红转绿的项（不得写成"一直是对的"）

| 项 | 首轮 10:18 | 洁净轮 11:34 | 变化原因 |
|---|---|---|---|
| `GRAPH_LOCAL` | FAIL（`graph_docs=0`） | **PASS**（`docs=5 graph_docs=5 有正文=5`） | B 的图代次回取修复生效（`LOCAL-RETRIEVAL.md` L1） |
| `VERSION` | PASS（1 组多版本） | **PASS**（`groups=2 多版本组=2 版本=['V1','V0','V1','V0']`） | C 重建 V0/V1 夹具 |
| `GLOBAL` 引用可解析性 | FAIL（双 host） | 引用已归一（仍因 refs=1 FAIL） | C 的 `toAbsoluteSource` |
| SSE 拒绝态 | 10:35 `Accept: text/event-stream` → **500 空体** | 11:35 同 Accept → **403 + errorCode=30016** | C 修复生效（原缺陷单已可关闭） |

## 4. acceptance 改口径（team-lead 指令 1、2 的落实与自证）

1. **不再复用 kb_9**：`s2()` 改为独立库 `R14-BASELINE-KB`，且**每次运行先删后建**；`kb_9` 不再被任何 acceptance 运行写入（本轮实测新库 primitiveName=`kb_17`）。
2. **`--only` 假绿修复**：
   - `plan(only)`：选中的场景按固定顺序执行，未知场景单列；
   - `check_coverage(want, executed, unknown)`：**选中未执行 = FAIL**，未知场景 = FAIL；
   - 自证（本轮实测）：
     - `--only S99` → `plan=[] 未知场景=['S99']`，2 条 FAIL，**exit=1**；
     - `--only S6,S7` → 真实执行（含 S3/S4 前置），**27/27 PASS**，`覆盖判定=OK`；
     - 全量 → 34/34 PASS，`COVERAGE` 记录 8/8 执行。
3. **kb_9 被 10:22 批次污染的数据登记**：`kb9_pollution_20261027.md`（只读查询，未改任何行）。要点：`knowledge_base_list` 按 `parent_file_name` 累积 25–39 行（product-loan 39 行），绝大多数 `status=0`；`id=300`(credit-ledger) 落在 product-loan 的 `group_id=614524213` 内 → 证实 C 报的 parent_file_name/group_id 串组。

## 5. 环境事件（不计产品缺陷，但必须留痕）

| 时刻 | 事件 |
|---|---|
| 10:29:24/27 | rag-index/rag-qa 的 target jar 被重建，进程仍是 10:02:34 启动 → `ClassNotFoundException: ErrorAttributeOptions$Include` → 拒绝态 500 空体 |
| 10:31–10:44 | 服务重启；10:33 index-service 未注册 → qa `[503] Load balancer does not contain an instance` → 权限判定失败 |
| 10:35–11:05 | acceptance S4 三个解析任务各卡 600s（doc-parse 未就绪） |
| 11:06–11:23 | 整栈拆除重装；`rag-index-service` 曾报 `Failed to start bean 'webServerStartStop'`（端口被占/重复拉起） |
| 11:23:27 / 11:24:28 | 服务恢复，连续两次 smoke 200 → 本轮开跑 |

## 6. 覆盖与残余边界

- 已覆盖：主链 8 场景（34 条断言）、能力矩阵 7 项、对象授权 16 项、撤权全链 21 项、权限域对照 8 项（含"未指定助手不得 5xx"与"跨域提问 403"）。
- 已知但本轮未纳入断言（等外部口径/他人负责）：
  - 图块 `provenance_quality` / `identity_stability` / `identity_violations`：B 已上线字段，但 19995 的 metadata 白名单会丢掉它们（A 的 `UNVERIFIED_WHITELIST`）→ 目前**不可验**，不判 PASS 也不判 FAIL；
  - 图检索"业务空结果返 500"：等 TL 裁口径（`EMPTY_LEGIT`）；
  - "两次解析 id 相同"：解析服务 7 处随机 pk 未改，只可断言"计数不翻倍"。
- `S8 坏文件` 观察：上传返回 `http=200 success=true data=[]`（未生成 fileId），断言据"未入库"判 PASS；但响应语义矛盾（success=true 而 data 空），建议 C 侧核对契约，不作为本轮 FAIL。

## 7. 结论

本轮 **83/86**，3 条 FAIL 归为 2 个产品缺陷（FAQ 通道 offset=null 解析中断；GLOBAL reduce 结果未被消费），**无环境 FAIL、无我方夹具 FAIL**（S7 已修并收紧到"必须命中本轮 queryId"，本轮 PASS：`session=kb_17 问答对数=1 命中=True`）。

---

## 8. v2 增量（2026-10-27 11:43，能力矩阵 7→9 项）——**总账以此为准**

按 B-graph / A-data 提供的两条可断言事实，能力矩阵新增两项（不是放宽，是加严）：

| 新增项 | 判据 | 本轮实测 |
|---|---|---|
| `GRAPH_IDENTITY` | **直连 19529**；`code/data.code==200` 时 `identity_violations` 与 `identity_violations_count` **必须存在**（缺键不得当 0）、`count==0`；`>0` 时原始 violations 落证据 | **PASS** `http=200 code=200 键存在=True violations_count=0` |
| `GRAPH_UPPERCASE` | 成对用例：同一语义 `AAA` 与 `aaa` + enabled_graph=true，**两者都必须 200** | **FAIL** `大写(AAA)+开图 http=500 小写(aaa)+开图 http=200` |

字段位置纪律（B 明确纠正，已写入脚本注释）：
- `identity_violations*` 只在 **19529 响应 data 顶层**；19995 是自组合响应、**不转发**，所以只能直连 19529 断言；
- `provenance_quality` / `identity_stability` 才在每个块 `metadata` 里、且被 19995 白名单吃掉 → 现**不可验**（记 `UNVERIFIED_WHITELIST`，不计 PASS/FAIL）。

**v2 总账**

| 套 | 严格通过 / 总数 | 耗时 |
|---|---|---|
| `r13_full_check.py`（7→9 项） | **6 / 9** | 32s |
| `acceptance.py`（独立库，全场景） | **34 / 34** | 117s |
| `security_acceptance.py` | **16 / 16** | 3s |
| `revoke_acceptance.py` | **20 / 21** | 36s |
| `permission_domain_scope.py`（F05） | **8 / 8** | 8s |
| **合计** | **84 / 88** | 196s |

4 条 FAIL = 3 个产品缺陷根因：

| # | 用例 | 根因 | 归属 |
|---|---|---|---|
| 1-2 | `r13_full_check.FAQ`、`revoke.R4` | FAQ 记录 `metadata.offset` 为 `""`/None → `multiple_retrieval.py:215` 的 `break` 打断整批（A 复核：`retrieval_milvus` 同时服务 dense 召回，影响面不止 FAQ；图分支 `:459` 是 log-and-continue，属正确写法） | C（读侧改 `break→continue`）；A 侧写入层已规范化新数据 |
| 3 | `r13_full_check.GLOBAL` | `refs=1`（<2）+ 答案为拒答；host 重复已由 C 修复，剩余是 reduce 结果未被消费 | C/B |
| 4 | `r13_full_check.GRAPH_UPPERCASE` | 开图检索对含大写 ASCII 的查询 500（`retrieval_service.py:478` KeyError）；同句小写 200、关图 200 → 归检索层，不归图算法 | C |

**关于 `GRAPH_LOCAL` PASS 的收窄（B 的提醒，必须记住）**：该项证明的是「**算法侧图块进入了上下文**」（直连 19995：`docs=3 graph_docs=3`）。它**不证明**「用户入口的图引用可核验」——B 实测用户入口开图时 `refs=0`（答案对、零出处），成因大概率就是上表第 4 条的 500（由图分支失败导致引用被清空）。因此不能写成"local 图可用"，只能写"算法侧图块进上下文；用户入口引用可核验性仍被 GRAPH_UPPERCASE 缺陷阻塞"。

断言自检：**73/73**（新增 GID-1~4、GUP-1~2，覆盖"200 缺键不得当 0""count>0 判失败""500 不得当通过""成对大小写"）。

---

## 9. v3 判据边界修正（11:46，B 的补充；总账仍 84/88，但判据更严）

按 B 给的三条边界改了三处，**均为加严/去误判，不是放宽**：

1. **`GRAPH_LOCAL` 改判据**：图参与判定从"metadata JSON 里出现 graph 字符串"改为 **`metadata.search_type` 含 `graph`**（实测 shape `['milvus','es','es','graph']`）。理由（B 的实测）：纯中文查询时**开图/关图引用条数可能相同（各 3 条）**，差别只在 search_type → "引用数变多"不能当图有贡献的判据。
   新增自检 `GRAPH_LOCAL-4`：正文非空但 `search_type=['milvus','es']` → **判 FAIL**（证明判据不是被"有正文"蒙过）。
2. **`GRAPH_IDENTITY` 增加第三态 INFO/EMPTY_LEGIT**：图服务是 **HTTP 200 + body `code=500`**（FastAPI 外层不改状态码），业务空结果 = `http 200 + code 500 + data.reason ∈ {no_entity_extracted,no_vertex_matched,space_not_found}`。现在这类记 **INFO，不计 PASS 也不计 FAIL**（避免把"合法空结果"写成产品缺陷）；真正缺键/非 200 仍判 FAIL。自检 `GID-5` 覆盖。
3. **`GRAPH_UPPERCASE` 补强**：从"只看 HTTP 码"升级为"两边都 200 **且两边都有 docs 且都有 graph 块**"。理由（B）：否则"C 把 500 修掉、但图仍没并进来"会漏判。自检 `GUP-3`：两边 200 但无 graph 块 → 判 FAIL（证明新增条件非空转）。

**v3 实测（11:46:18，稳定态）**：`r13_full_check` **6/9**，FAIL = `FAQ`、`GLOBAL`、`GRAPH_UPPERCASE`；`GRAPH_LOCAL` PASS（`docs=4 含graph标记=4`）、`GRAPH_IDENTITY` PASS（`键存在=True count=0`）。合计仍 **84/88**。

**环境插曲（不计产品缺陷）**：11:45:xx 图服务 19529 被重启，那一轮出现 `GRAPH_LOCAL 含graph标记=0` 与 `GRAPH_IDENTITY ConnectionError（connection refused）`——**假 FAIL**。11:46:09 复核：19529 已 listening（两个 pid，重启期），直连 200；重跑两项均 PASS。教训：**图侧断言必须与"19529 存活"前置绑定**，否则一次重启就会写成"图能力退化"。

断言自检：**76/76**（新增 GRAPH_LOCAL-4、GID-5、GUP-3；GID/GUP/GRAPH_LOCAL 夹具全部改为按 `search_type` 列表构造）。

---

## 10. v4 最终（11:48–11:51，C 的两处修复加载后）——总账 **86/88**

**先记代码代次（A 的纪律，避免"旧代码当成没改"）**：
```
pid=641826 start=11:47:21 | pid=641889 start=11:47:22 | pid=643555 start=11:47:38   （retrieval_api_start.py）
mtime multiple_retrieval.py  = 2026-10-27 11:43:01
mtime retrieval_service.py   = 2026-10-27 11:46:36
19995 listen = 1
```
即两个修复（FAQ 的 `break`、大写查询的 KeyError）都**已被进程加载**，此前的失败确属"代码未加载"，不是"改了没用"。

| 套 | 通过 / 总数 | 变化 |
|---|---|---|
| `r13_full_check.py` | **8 / 9** | FAQ PASS（`resultType=2`）、GRAPH_UPPERCASE PASS（大写 `http=200 docs=3 graph块=2`）；仅 GLOBAL FAIL |
| `acceptance.py` | **34 / 34** | 不变 |
| `security_acceptance.py` | **16 / 16** | 不变 |
| `revoke_acceptance.py` | **20 / 21** | R4(FAQ) 已 PASS；FAIL 变为 **R3（global 问答，内容长度=19、引用=1、3 次尝试）** |
| `permission_domain_scope.py` | **8 / 8** | 不变 |
| **合计** | **86 / 88** | FAIL 从 4 条降到 2 条 |

**唯二 FAIL（同一根因）**：`r13_full_check.GLOBAL`（`refs=1`）与 `revoke.R3`（global 回答 19 字符、引用 1）。两者都是 **GLOBAL 全局问答链路**：引用可解析性（双 host）已由 C 修好，剩余是"reduce 结果未被消费/跨文档归纳不成立"。归属：C（`RetrievedData` 的 `global_answer` 消费）+ B（社区摘要召回质量）。

**已关闭的两条（每条都有复验证据，不得写成"一直是对的"）**：
| 原 FAIL | 关闭证据 |
|---|---|
| FAQ 直答（r13 FAQ + revoke R4） | `PASS resultType=2`，答案「…客户访前准备在第一段，日均存款在第二段。」；根因 `offset=""` → `break` 打断整批，C 改 `break→continue`（`multiple_retrieval.py` 11:43）后生效 |
| 大写开图 500（GRAPH_UPPERCASE） | 大写 `http=200 docs=3 graph块=2`；根因 `retrieval_service.py:478` KeyError（`documents[query]` 只有小写键），11:46:36 修复后生效 |

**遗留未纳入本基线（下一轮再加，不冒充通过）**：端到端"两次解析 id 相同 + `ES._id==Milvus.pk`"（A 已复验 PASS，建议三条一起断言：计数不翻倍、id 集合相同、跨存储身份一致；我的脚本暂无 parse-twice 用例，避免本轮同时改脚本与判据）。

---

## 11. v5 最终（12:14–12:28，**91/91 全绿**）——总账以此为准

### 环境前置
| 时点 | date | ss1999 | 容器 | 说明 |
|---|---|---|---|---|
| 12:11:26 / 12:12:07 | +0800 | 2 | 14 | 连续两次 smoke（index 200 + qa 200 + 有引用）后才开跑 |
| 12:17:10 / 12:17:45 | +0800 | 2 | 14 | 同上（revoke 复跑前的稳定门） |

期间另有两段抖动已排除：`12:10 index 全 503`、`12:55 19995 三实例重启`（见 §10 与 v4 记录），这两段产生的红均未采信。

### 结果
| 套 | 通过 / 总数 | 时间 |
|---|---|---|
| `r13_full_check.py`（12 项，含 GLOBAL 拆 3 层） | **12 / 12** | 12:28:40 |
| `acceptance.py`（独立库 kb_20） | **34 / 34** | 12:24:39 |
| `security_acceptance.py` | **16 / 16** | 12:24:37 |
| `revoke_acceptance.py` | **21 / 21** | 12:21:58 |
| `permission_domain_scope.py`（F05） | **8 / 8** | 12:18:54 |
| **合计** | **91 / 91** | — |

### 本轮由红转绿的 4 条，全部是**我方断言缺陷**（不是产品缺陷，均已更正留痕）
| # | 原 FAIL | 真实原因 | 修法 |
|---|---|---|---|
| 1 | `GLOBAL`（refs=1） | 用 B 的 **R1 拒答题当正例**并要求 ≥2 来源 —— 结构上不可能满足（B 文档明确 R1/R2「不计入正例统计」） | 拆成 3 层：`GLOBAL_POS`(G1 正例：≥2 可解析 source + 社区 id)、`GLOBAL_REFUSE`(R1/R2：拒答 + 不得出现具体数值，引用数不设下限)、`GLOBAL_FAITH`(客户→加点映射 30/60/60) |
| 2 | `GLOBAL_POS`（可解析=0） | 把**单 host 绝对 URL** 误判"不可解析"（C 的 `toAbsoluteSource` 对已带 http 的就是原样返回）。实测两轮 source 形态还会变：12:14 全绝对、12:28 全相对键 | `_src_ok()` 只禁"重复拼接 host"，两种形态都接受，并在 detail 记录绝对/相对条数 |
| 3 | `FAQ`/`R4` 抖动 | `resultType=2` 由 Java `faqSelect`（调 LLM 做 FAQ 筛选）决定，单发会抖：实测 12:14 第 2 次命中、12:28 第 3 次命中、12:07 三次全不命中。检索层**正常**（19995 `faq_result_list=1`，`score=0.333`，字段 `faq_question/faq_answer` 齐全） | 正例允许 3 次尝试（与 revoke `ask_ok` 同纪律）；**拒绝态一律单发**。自检 FAQ-2/3/4 固定"三次全 rt=1 必须 FAIL" |
| 4 | `R3`（global 完整回答） | 判据 `len>20` 是代理指标，实测同一问三次 275/24/19 字（B 也记录 reduce 不可复现） | 改为"status==2 且非空 且（有引用 或 明确拒答语义）"，既能放过合法短拒答，也不放过空回答 |

### 本轮发现并已适配的 **schema 变更**（非产品缺陷，需 C 确认是否刻意）
`search_config` 出现函数唯一索引：
```sql
UNIQUE KEY `uk_search_config_default` (((case when is_default=1 and is_del=1 then 1 else NULL end)))
```
即**全局只允许一行"默认助手"**。影响：`revoke_acceptance.py` 原夹具（r13_reader 自有 `is_default=1`）报 `1062 Duplicate entry '1'`；已改为 `is_default=0` + 显式 configId（权限走 `create_by` 归属，语义不变）。同时 `permission_domain_scope.py` 的 reader 配置也改为"取任一自有配置，缺则补一条 is_default=0"。
> 这条同时回答了 team-lead 待裁语义题的现状：`getDefaultConfig()` 仍按 `create_by` 过滤，**非 admin 用户永远取不到默认助手** → 不传 configId 一律 403（admin 也 403 是因为前置 `assertAccessible` 不回落，见 §给 C 的根因）。

### 断言自检
**87/87**（新增 FAQ-1~4、GLOBAL-1~6、GREFUSE-1~3、GFAITH-1~3、GRAPH_LOCAL-4、GID-1~5、GUP-1~3、ONLY-1~3、COVERAGE-1~3、S7-11、F05-OOD/5XX）。

---

## 12. v6 新增断言（12:30–12:34）与最终状态

> 说明：§11 的 91/91 是**12:14–12:28 最后一次全绿**的完整快照。之后我又按 TL/C/A 的新裁决加了两类断言，
> 但恰逢 19529 反复重启（12:31 起 `ss -lnt|grep 19529` 反复 0/1），**无法在稳定窗口内给出全量绿**。
> 下面把"已按裁决判红"的两项与"环境不可用"分开写清，不混算。

### 12.1 按 TL 新口径新增/修改的断言

| 断言 | 变更 | 当前实测 |
|---|---|---|
| `GRAPH_IDENTITY` | 图空结果契约改为 **200 + data.reason**（TL 已批准 B 改）。判定一刀切：http 5xx 或 body `code=500` → **FAIL（故障伪装业务空）**；`200+code=200+result_data=[]+reason` → **INFO/EMPTY_LEGIT**（允许空，但不计正例） | 12:31 直连正常（`code=200` 4 块 / `count=0`）；12:33 起 19529 掉线 → INFO（环境不可用） |
| `GRAPH_PROVENANCE`（新增，TL 的 F04 判据） | 要求 `exact_chunk > 0` **且** 引用可解析（`metadata.source` 在 ES 命中 >0，悬空即 FAIL） | **12:31 直连实测应判 FAIL**：4 块全部 `provenance_quality=entity_content_recovered`、`exact_chunk=0`、`identity_stability=unknown` → 与 B/C 的结论一致：图 `chunk_pk_list` 是抽取时刻旧 ES `_id`，与当前 ES 交集为 0，只能重解析+重建图才转绿。**归"数据代次悬空"，不计环境** |
| `GLOBAL_FAITH` | 改为 **3 次多数票**（C 实测同题 30/60/60 与 30/20/20 并存，属 reduce 非确定）；**不下放到单跳数值题**（单跳是稳定取错行，必须单值判 FAIL） | 12:33 实测 `多数票=2/2`、映射 30/60/60 正确 → PASS |
| `GLOBAL_POS` | detail 记录 `configId=1`（A 的纪律：refs 条数受 score_threshold/top_k 影响） | 12:33 refs=1（阈值口径下 1 条属正常），当轮 FAIL 只因不足 ≥2；**该条我维持"≥2"判据并记录 configId**，不做放宽 |

### 12.2 F05 按 TL 裁决（configId 语义）新增两条 —— **当前应判红，归实现未跟上**

TL 裁决：**允许回落系统默认助手**；无默认时返回 **400 + 明确文案（errorCode 4014，不得复用 30016）**。
12:32:23 实测（admin，不传 configId，`search_config` 存在唯一默认 id=1）：

```
F05-A5 回落系统默认助手            -> FAIL  http=403 status=None answer_len=0（被当成越权）
F05-A6 拒绝态不得复用 30016        -> FAIL  http=403 errorCode='30016'
其余 7 条（跨域 403 / 引用域内 / 无 kb_10 痕迹 / 未指定助手不 5xx→现并入 A5） -> PASS
```

所以 F05 当前 **7/9**：2 条红是**裁决已下、实现未跟上**的缺口（C 侧），不是我方夹具、也不是环境。
`无默认`那一支（400+4014）需要删掉 `search_config` 唯一默认行才能构造，会破坏所有用户回落链，故记
**UNVERIFIED（不伪造通过）**，等 C 提供可 mock 的租户/开关再补。

### 12.3 环境（12:31–12:34，均不计产品缺陷）
- 19529 在图侧改动重启期间反复 0/1：`GRAPH_*` 四项一律记 **INFO 环境不可用**（脚本已内置 `_port_pids/_listening` 前置守卫，并落 `precheck_ports.json`）。
- 12:33 出现 `NORMAL Read timed out`、`TABLE http=500` —— 同一窗口内网关/检索在重启，未采信。

### 12.4 当前可对外引用的口径
- **能力矩阵**：`r13_full_check` 现有 **13 项**（NORMAL / FAQ / GLOBAL_POS / GLOBAL_REFUSE×2 / GLOBAL_FAITH / VERSION / TABLE / GRAPH_LOCAL / GRAPH_IDENTITY / GRAPH_PROVENANCE / GRAPH_UPPERCASE / INTERNAL_GUARD）。
- **最后一次全量绿**：12:14–12:28，**91/91**（§11，13 项里当时是 12 项）。
- **新增后待复跑**：`GRAPH_PROVENANCE`（按判据应红，属数据代次）与 F05 的 A5/A6（按裁决应红，属实现缺口）。
- 断言自检：**91/91**（新增 GID-6/GID-7/GPROV-1~3，覆盖 TL 要求的"500+reason 判 FAIL""200+空+reason 记 INFO""exact_chunk=0 判 FAIL""引用悬空判 FAIL"）。
