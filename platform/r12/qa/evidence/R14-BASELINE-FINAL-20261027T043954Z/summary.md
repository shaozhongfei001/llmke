
---

## 13. v7 新增断言后的首次全量（12:39–12:48）—— 10/13，3 条 FAIL 已分类

> 前置（12:46:59）：`qa pid=983520 start=12:42:50`，`jar mtime=12:46:08` → **再次 STALE_JAR（jar 比进程新 198s）**；
> E 的 12:33:10 就绪信号有效，但 C 在 12:39:47 / 12:46:08 又两次替换 jar，本轮与之重叠。
> 期间我自己的一处误判也记下来：用 `Authorization: x`（非法 token）探活得到 500，属**探针错误**；
> 换真实 token 后 configId=1 立刻 200。附带发现：**非法 Authorization 头 → 500（应为 401）**，已单列。

### 13.1 结果

| 断言 | 结果 | 复测 | 判定 |
|---|---|---|---|
| NORMAL / FAQ / VERSION / TABLE / INTERNAL_GUARD | PASS | — | — |
| `GLOBAL_REFUSE/R1` | PASS | 12:48 再跑仍 PASS | 拒答正确、无编造数值 |
| `GLOBAL_REFUSE/R2` | **FAIL** | **12:46、12:48 连续 2 次 http=500** | **产品缺陷（global 路径对个别问题 500）**，归 C/B |
| `GLOBAL_FAITH` | PASS | 多数票 2/2，映射 30/60/60 | reduce 忠实度达标 |
| `GLOBAL_POS` | **FAIL** | 12:28 refs=3 PASS；12:46、12:48 均 refs=1（同 configId=1） | **不稳定**：同一配置两轮 3 条、两轮 1 条。"≥2 来源"已证明可达，但当前不稳；需 B 确认语料能否稳定支撑 |
| `GRAPH_LOCAL` / `GRAPH_IDENTITY` / `GRAPH_UPPERCASE` | PASS | — | 图块进上下文、identity 键与 count 正常、大小写成对 200 且都有 graph 块 |
| `GRAPH_PROVENANCE` | **FAIL（按设计）** | 12:31、12:46 两次一致 | `exact_chunk=0`、4 块全 `entity_content_recovered`、`identity_stability=unknown` → **数据代次悬空**，需重解析+重建图 |

`r13_full_check`：**10 / 13**（不含 INFO）。

### 13.2 新增的两条事实（供 C 修）

1. **`GLOBAL` + R2 问 → 500**：问题「海川电子材料股份有限公司被列为关注类，需要计提多少比例的贷款损失准备？」（globalMode=true，configId=1）连续两次 500；同一路径 R1 问（据答位）200。→ global 分支对"有实体但无该事实"的问题处理异常。
2. **非法 `Authorization` 头 → 500（应为 401）**：`Authorization: x` 请求 `/qa/ai/question` 得 500；合法 token 正常。属错误码/鉴权解析路径问题，与 F08"拒绝态必须 401/403"口径冲突。

### 13.3 环境
- 12:38:39–12:42:50 之间 qa 两次重启（含 12:39:47 jar 替换在进程之后）；12:46:08 又一次 jar 替换 → 本轮 12:39 那次扫描全 500 属 STALE_JAR，已作废（`qa_500_incident.md`）。
- 19529 在 12:31–12:34 抖动后恢复，图侧 4 项本轮稳定 PASS（PROVENANCE 按判据红）。

### 13.4 口径

- 断言自检 **91/91**。
- 本次全量为"新增断言后"的首个可读快照：**10/13**；三条 FAIL 中 **1 条按设计应红（数据代次）**、**1 条产品缺陷（R2 500）**、**1 条稳定性待 B 确认（POS refs）**。
- 未纳入：`F05` 本轮未跑（qa 两次重启中断），上一轮 12:32 为 7/9（A5/A6 按 TL 裁决应红：admin 不传 configId 仍 403+30016）。
# FINAL RUN 20261027T043954Z
2026-10-27T12:39:54+0800
ready_signal=2026-10-27 12:33:10 (E)
ss1999=2
containers=14
ports_listening=12
proc 953518 27 12:38:39
proc 953521 27 12:38:39
## 复跑前置 2026-10-27T12:46:59+0800
qa pid=983520 start=27 12:42:50
jar 12:46:08
invalid_token_probe=500 (发现：非法 Authorization 头导致 500，应为 401)

---

## 14. v8 最终全量（12:52–13:10）—— **90 / 93**，代码代次已对齐

### 14.1 代次凭证（E 的 diag，我照抄入证）
```
SERVICE              PID       JAR_TS       PROC_TS      DELTA
rag-index-service    1033963   1793076363   1793076614   -251s   （jar 旧于进程 = 已加载）
rag-qa-service       1038952   1793076368   1793076655   -287s   （jar 旧于进程 = 已加载）
STALE_count = 0        （r12ctl status 无任何 [STALE_JAR]）
```
首条端到端验证（12:51:20，admin token）：
- `configId=1` → **200 + SSE + `"reference"` 存在**；
- **不传 configId → 200**（C 的 FIX-15c `resolveDefaultConfigOrNull` 生效，回落系统默认助手成功）。

### 14.2 结果

| 套 | 通过 / 总数 | 时间 | 耗时 |
|---|---|---|---|
| `r13_full_check.py`（13 项） | **10 / 13** | 12:52:10 | 73s |
| `acceptance.py`（独立库，全场景） | **34 / 34** | 12:55:02–13:10 | 842s |
| `security_acceptance.py` | **16 / 16** | 12:53:33 | 3s |
| `revoke_acceptance.py` | **21 / 21** | 12:54:11 | 50s |
| `permission_domain_scope.py`（F05，9 项） | **9 / 9** | 12:53:36 | 10s |
| **合计** | **90 / 93** | — | — |

### 14.3 三条 FAIL（逐条定性，全部可复现）

| # | 断言 | 实测 | 定性 |
|---|---|---|---|
| 1 | `GLOBAL_POS` | `refs=1`（12:52）；同 `configId=1` 在 12:28 曾 `refs=3` | **稳定性待定**：≥2 已证明可达但不稳；A 的阈值矩阵 + B 的"社区主题互不重叠"共同解释。**未放宽判据** |
| 2 | `GLOBAL_FAITH` | **多数票 1/3**：第 1 次 30/60/60（全对），第 2、3 次**答案里完全没有加点段**（三个客户都取不到值） | **产品不稳定（reduce）**：不是措辞差异，是**漏答问题的后半句**。C 提过 reduce 非确定，但这里是"整段缺失"，已超出"取多数可容忍"的范围 |
| 3 | `GRAPH_PROVENANCE` | `exact_chunk=0`；5 块全 `entity_content_recovered`；**1 条 source 在 ES 查不到**（`…/credit-ledger.xlsx/V0/…`） | **数据代次悬空**（TL 的 F04 判据）。除"chunk 身份悬空"外，本次还出现**文件级悬空**，需重解析+重建图 |

### 14.4 本轮由红转绿
- `F05-A5/A6`：8/8 → **9/9**（FIX-15c 生效，回落 200；A6 因回落成功而自然成立）
- `GLOBAL_REFUSE/R2`：12:46 连续 2 次 500 → 本轮 **200 + 拒答 + 无编造数值**（C 修掉了）
- `GRAPH_LOCAL`：`含graph标记=3/3`；`GRAPH_UPPERCASE`：大写 4 docs / 3 graph 块（`search_type` 均含 graph）
- `GRAPH_IDENTITY`：5 块、`code=200`、两键存在、`count=0`

### 14.5 口径与未纳入
- 断言自检 **91/91**。
- 未纳入（下轮）：A 的 parse-twice 三条；`verify_global_citations.py` 三态（PASS/MIS_CITED/NO_SUPPORT）并入 `GLOBAL_POS`；`filesParse.file_ids` 不被消费 → 重解析用例须校验 `gmt_modified`/chunk 变化；`multi_version` 分支（`/index/kbFile/multiVersion` 经网关 401/30021）记 UNVERIFIED。
- 环境：12:38–12:50 之间 index/qa 共 3 次重启 + 2 次 jar 覆盖（STALE_JAR），相关轮次已作废；19529 自 12:40:16 起稳定。

---

## 15. 冻结期权威基线（13:10–13:13）—— **92 / 93**，唯一红项 = 数据代次

### 15.1 代次与守卫凭证
```
r12ctl status            STALE_count = 0
diag                     index pid=1033963 DELTA=-251s / qa pid=1038952 DELTA=-287s（已加载 12:46 批次）
19529 pid（批前/批后）    1061358 / 1061358   ← 整批 pid 未变，图侧结果有效
非法 Authorization 复测   401 + {"errorCode":"30022","errorMsg":"没有token"}（C 的 FIX 生效，非 5xx）
```

### 15.2 结果（分层）

| 套 | 通过 / 总数 | 时间 |
|---|---|---|
| `r13_full_check.py`（13 项） | **12 / 13** | 13:11:49（69s） |
| `acceptance.py`（独立库，8 场景 34 断言） | **34 / 34** | 12:55–13:10 |
| `security_acceptance.py`（16 项） | **16 / 16** | 12:53:33 |
| `revoke_acceptance.py`（21 项） | **21 / 21** | 12:54:11 |
| `permission_domain_scope.py`（9 项） | **9 / 9** | 12:53:36 |
| **合计** | **92 / 93** | — |

### 15.3 分层总账（TL 要求的口径，不只看通过率）

| 分类 | 数量 | 明细 |
|---|---|---|
| **产品缺陷（本轮确认）** | **0** | — |
| **夹具/断言缺陷（我方，已修）** | 3 项已修 | ① `GLOBAL_POS` 判据"≥2 来源"：采纳 B 的证据（加点规则集中在单社区 + 修复后引用更准，12:28 的 refs=3 反而是**错引用**）→ 改为"≥1 可解析 + 社区 id"，跨 2 社区单列为**覆盖度指标**（本轮 coverage=1，不并入正例）；② `GLOBAL_REFUSE` 拒答关键词漏了当前文案「现有社区摘要不足以回答该问题，未生成推测性答案」→ 已补，仍保留"不得出现具体数值"硬约束；③ `FAQ`/`R3` 重试与代理指标问题（前几节已记） |
| **数据代次** | **1** | `GRAPH_PROVENANCE`：`exact_chunk=0`、4 块全 `entity_content_recovered`、`chunk_pk_list ∩ 现役 ES _id = 0` → **必须重解析+重建图**；这是本轮唯一"应该红且确实红"的断言 |
| **环境（已排除，不采信）** | 2 类 | ① 12:50:39–12:54:30 19529 被外部 restart 4 次（每次 stop 卡 30s→SIGKILL，断约 50s）；② 12:29–12:50 多次 jar 覆盖导致 `NoClassDefFoundError`（`PermissionEnums` / `ErrorAttributeOptions`）→ 相关轮次已作废 |

### 15.4 期间观测到的一次 GLOBAL 异常窗口（已恢复，供 B 复核）
13:10 那轮曾出现 `R1/R2/FAITH` 全部返回「现有社区摘要不足以回答该问题，未生成推测性答案」且 `sources=[]`（3 次一致）；
13:11 复跑即恢复为「事实中未提及 [L0-…]」+ refs=1，FAITH 30/60/60。发生在 B 12:50–12:54 部署后的收敛期，
**不判产品缺陷**，但建议 B 保留观察（若再现则属 reduce/摘要收敛的稳定性问题）。

### 15.5 断言自检
**92/92**（本轮新增/修改：GLOBAL-3 由"1 条 source 判 FAIL"改为判 PASS（B 证据）、GLOBAL-7「0 条可解析必须 FAIL」、拒答关键词补充）。

---

## 16. 按 B 的根因新增"假拒答=环境事件"判据（13:10 那轮正式作废）

### 16.1 根因（B 定位，我这边时间线完全对齐）
```
13:10:41  index_vector 重启      ┐
13:10:47  index_fulltext 重启    ┘ 同一时刻 GLOBAL 全类别变成"无来源拒答"
13:10    我这轮：R1/R2/FAITH 全部 = 「现有社区摘要不足以回答该问题，未生成推测性答案。」+ sources=[]
13:11     立即复跑：全部恢复（30/60/60、refs=1）
```
机制：`_load_summaries()` 读 ES `community_summary_kb_9` 异常后被 `return []` 吞掉 →
`query_community` 把"读不到社区"当成"该库没有社区" → 输出"不足以回答"。
**即：基础设施故障被写成了模型结论（假拒答）**，比 5xx 更危险——它看起来像正常行为。

→ **13:10:18–13:11:14 那一轮（`CAPS-20261027T051018Z`）正式作废，归环境事件**，不计产品 FAIL。

### 16.2 判据已落成代码 + 自检（B 建议，采纳）
```
若同批 GLOBAL_POS 也无任何可解析来源，
且本条答案命中环境拒答文案（不足以回答 / 未生成推测性答案）、且 refs 为空
→ 记 INFO/ENV_EVENT（不计 PASS 也不计 FAIL）
若只有个别题这样、同批 POS 正常 → 仍判产品 FAIL
```
`_is_env_refusal()` 纯函数 + 自检 4 条：`ENVREF-1`（环境态→不判 FAIL）、`ENVREF-2`（个别题→必须判 FAIL）、
`ENVREF-3`（有引用则不算环境）、`ENVREF-4`（正常拒答文案不算环境）。

### 16.3 另一处判据修正（B 指出，已改）
`GRAPH_PROVENANCE` 的 source 存在性查询从"只查 `kb_9`"扩为
**`kb_9` + `table_chunks_kb_9` + `table_summary_kb_9`** 三索引合计，detail 输出"命中索引"分布。
理由：台账类块的 source 只存在于 `table_chunks_kb_9`（实例：`…/credit-ledger.xlsx/V0/…` 在 kb_9 命中 0、在 table_chunks 命中 1），
只查 kb_9 会把**所有表格引用都判成悬空**（假红）。改后该断言只剩 `exact_chunk=0` 一个真因。

### 16.4 B 的三态契约（记入下轮断言种子，本轮未实现）
```
社区摘要读不到        -> 500 + data.error=summary_store_unavailable（可监控/可重试）
确实没有社区摘要      -> 200 + 提示先 /generate_community
有摘要但无该事实      -> 200 + "事实中未提及"（正常拒答）
```
B 已改代码但**需重启 19529 才生效**，冻结期不重启 → 在 B 重启前，"假拒答"仍可能出现；
本节的 ENV_EVENT 判据正是为这段不确定期准备的（有则记 INFO，不误判成产品缺陷）。

### 16.5 复跑验证（判据接入后无回归）
`--only GLOBAL` 4/4 PASS：POS（refs=1 / 覆盖度=1 / 社区 id）、R1/R2（事实中未提及 + refs=1）、FAITH（30/60/60 多数票 2/2）。
断言自检：**100/100**。

---

## 17. 批B（13:10 那轮）按秒切分 + 基建字段落地

### 17.1 B 给的秒级证据（与本轮观测完全吻合）
```
13:10:14 / 13:10:18 / 13:10:22   B 自己 3 次 G1 全部 refs=2、30/60/60、cost≈3.7s   ← 故障前对照
13:10:41  index_vector  (19526) 重启
13:10:47  index_fulltext(19527) 重启
13:10:44  graph 日志 _entity_chunk_pks ERROR 19526 连不上（/get_doc_by_col）
13:10:47~ _load_summaries   ERROR 19527 连不上（/search_by_custom_param，连续 4 次）
13:11     恢复
```
**把批B 按 13:10:41 切成两段**（B 的建议，采纳）：
| 段 | 窗口 | 观测 | 判定 |
|---|---|---|---|
| B1 | 13:10:18–13:10:40 | `GLOBAL_POS` refs=2 正常 | 有效 |
| B2 | 13:10:44–13:11:0x | `R1/R2/FAITH` 全部「不足以回答」+ sources=[] | **ENV_EVENT（19527 不可用）** |
| C | 13:11:49 起 | 全部恢复（30/60/60、refs=1） | 有效 |

即"同批 POS 正常、FAITH 全拒"不是不稳定，而是**同一批前后跨越了基础设施故障窗口**。

### 17.2 每条 global 结果现在自带基建快照（B 的建议，已落地）
新增 `_infra()`：`graph_pid`（19529 监听 pid）+ `es_ok/es_ms`（`POST 19527/search_by_custom_param` 是否 <5xx 及耗时）。
实测输出：
```
GLOBAL_POS      refs=3 可解析=3 覆盖度=1 infra(graph_pid=1061358, es_ok=True, 8.6ms)
GLOBAL_REFUSE/R1 refs=1 拒答=True    infra(graph_pid=1061358, es_ok=True)
GLOBAL_REFUSE/R2 refs=1 拒答=True    infra(graph_pid=1061358, es_ok=True)
GLOBAL_FAITH    多数票=2/2 30/60/60  infra(graph_pid=1061358, es_ok=True)
```
以后"整批拒答"时，`es_ok=False` 一眼可判环境，无需回翻他人日志。
`ENV_EVENT` 判定不变（仍要求"同批 POS 无来源"），`infra` 只作佐证与留痕——避免把"es_ok=True 但个别题无来源"也放过。

### 17.3 三态契约（B 将修，需重启 19529）
```
读不到      -> 500 + data.error=summary_store_unavailable
确实没社区  -> 200 + 提示先 /generate_community
有社区无事实-> 200 + "事实中未提及"（正常拒答）
```
B 会与图重建合并成一次重启；生效后我加 `GLOBAL_SUMMARY_STORE` 用例（负例用"空 space/临时 ES 不可达"造，不碰数据）。

### 17.4 复跑
`--only GLOBAL`：**4/4 PASS**（refs=3、覆盖度=1、社区 id；R1/R2 拒答无编造；FAITH 2/2=30/60/60）。
断言自检：**100/100**（`ENVREF-1~4` 锁"环境态不判 FAIL / 个别题必须判 FAIL"）。

---

## 18. 按 B 的三条建议落地（13:15–13:18）—— 13/14 + 1 INFO

### 18.1 更正一处措辞（B 的第 1 条）
B 原先说"修复后 refs 在 1~2"，我实测到 `refs=3`。**准确表述**：`refs ∈ [1,3]`，取决于引用覆盖到几个支撑社区
（3 = 江南评级 + 华东/北方评级 + 加点规则三个社区；1 = 全部只标 `L0-18625408`）。
**"12:28 的 refs=3 属修复前的错误引用"这句保留**；但不再写"修复后只能 1~2"。判据仍是 `≥1 + 社区 id + FAITH 数值`。

### 18.2 `stale_version` 已可读并接入（B 的"双绿陷阱"）
块级 `metadata` 实测含 `version`/`parent_file_name`，故 `_version_freshness()` 可判"是否混入旧版本块"。
本轮实测：
```
GRAPH_PROVENANCE   块数=4 exact_chunk=0 命中索引={'kb_9':4} 悬空=[] stale_version=2
GRAPH_VERSION_FRESH(INFO) 旧版本块=2：intro.pptx V0（最新 V1）、product-loan.docx V0（最新 V1）
```
处置：`stale_version` 先作**独立 INFO**（不计 PASS/FAIL），因为它归 A 的 V0/V1 收敛周期；
若 B 要求转硬判据，一行即可改成 `ok = ... and not stale`。这样既不"数字好看就判绿"，也不把两个根因混进一个红项。

### 18.3 摘要三态契约落成纯函数 + 自检（B 的第 2 条）
`_summary_store_state()` 输出五态：`store_down / no_community / no_fact / answered / unknown`，
自检 `SUMST-1~5`：
- `code=500 + data.error=summary_store_unavailable` → **store_down**（可监控/可重试）；
- `200 + 提示先 /generate_community` → **no_community**（数据前置条件缺失）；
- `事实中未提及` → **no_fact**（正常拒答）；
- 空响应空答案 → **unknown**（不得当 answered）。
> 这三态区分正是 13:10 假拒答的解药。B 的 (a) 契约端到端用例（选"有索引无 community_summary"的库）与
> (c) 真实故障机会主义观测，等他重启生效后补；(b) 单元级故障用例由 B 侧提供（已 PASS）。

### 18.4 本轮复跑（19529 pid 1061358，整批未变）
| 断言 | 结果 |
|---|---|
| NORMAL / FAQ / GLOBAL_POS / GLOBAL_REFUSE×2 / GLOBAL_FAITH | PASS |
| VERSION / TABLE | PASS |
| GRAPH_LOCAL / GRAPH_IDENTITY / GRAPH_UPPERCASE | PASS |
| `PARSE_EFFECTIVE`（新增） | PASS（status=3 文件 9，抽查 8，无块 0） |
| `GRAPH_PROVENANCE` | **FAIL**（`exact_chunk=0`，唯一红项） |
| `GRAPH_VERSION_FRESH` | **INFO**（stale=2，V0 混入） |

`r13_full_check`：**13 / 14 PASS（INFO 1 条不计入）**。四套不变：acceptance 34/34、security 16/16、revoke 21/21、F05 9/9。
**合计判定 93 / 94**，唯一 FAIL = 数据代次（等 B 重建）。

断言自检：**105/105**。

---

## 19. 按 B 判定落地：`stale_version` 做成"重建后可硬判"的开关 + 探针集合显式化

### 19.1 为什么现在不硬判（B 的归因，采纳）
当前 2 个 stale 块（intro.pptx V0、product-loan.docx V0，最新均 V1）是 **`entity_content` 兜底反查的副产品**：
图里旧 pk 全悬空 → 按实体名回查 ES → 同名 V0 也在索引里 → 命中 V0。
所以在 `exact_chunk=0` 阶段硬判，会把**"数据代次悬空"误记成"新鲜度缺陷"**（红点归因错）。
→ 现状：`GRAPH_VERSION_FRESH` 记 INFO，不计 PASS/FAIL。

### 19.2 重建后硬判：用开关，不临时改代码
```
PROV_STRICT = os.environ.get("R14_PROV_STRICT", "0") == "1"
_prov_verdict(exact, dangling, stale, strict=None)
    strict=False → ok = exact>0 且无悬空           （当前口径）
    strict=True  → ok = 上述 且 stale == 0          （重建后口径）
```
B 重建完成后我用 `R14_PROV_STRICT=1` 跑同一条命令即可（`GRAPH_PROVENANCE` 与 `GRAPH_VERSION_FRESH` 两个数一起绿才算绿）。
自检 5 条锁死语义：`PROV-1`（strict off 放过 stale）、`PROV-2`（strict on + stale=2 必须 FAIL）、
`PROV-3`（strict on + 全清才 PASS）、`PROV-4`（`exact=0` 任何口径都不得过）、`PROV-5`（有悬空任何口径都不得过）。

### 19.3 探针集合显式化（B 指出"我 0 stale、你 2 stale"的差异来源）
两次统计差异**不是数据不一致，是探针问句不同**：B 的探针命中的块（331/332/333/334）恰好没有 V1 后继；
我的探针命中 loan/intro（有 V1 后继）。
→ 现在 `GRAPH_PROVENANCE` 的 detail/extra 里固定记录：
```
探针='智造贷 授信额度 票据贴现'  top_k=5  kb=kb_9
```
B 已同意重建后统一用我这 4 块的集合，不另立口径。

### 19.4 摘要三态契约：等 B 重启后接端到端
`_summary_store_state()` 五态与 B 的实现完全对齐（`store_down / no_community / no_fact / answered / unknown`），
自检 `SUMST-1~5` 全过。(a) 端到端契约用例我用自己的 acceptance 库造 `no_community`（不碰 B 的数据）；
(b) 引 B 的单元结果并注明来源；(c) 真实故障窗口由 B 提前 1 分钟报时点，我各打一发 global 验证
`500 + summary_store_unavailable`（"真实故障下一次通过"）。

### 19.5 现状
`GRAPH_PROVENANCE` 默认口径仍 **FAIL**（`exact_chunk=0`；`悬空=[]`、`命中索引={'kb_9':4}`、`stale=2`），
`GRAPH_VERSION_FRESH` = INFO。断言自检 **110/110**。

---

## 20. 口径声明（评审必读）：`GRAPH_PROVENANCE` 的默认口径与严格口径

同一个断言有两种运行口径，**报告与审判都必须写明用的是哪个**，否则"不设开关"会让红点看起来变绿。

| 口径 | 触发方式 | 通过条件 | 适用阶段 |
|---|---|---|---|
| **默认（宽松）** | 不加环境变量 | `exact_chunk > 0` 且 无悬空引用 | 重建前（当前）。stale 只记 `GRAPH_VERSION_FRESH` = **INFO** |
| **严格** | `R14_PROV_STRICT=1` | 上述 **且** `stale_version == 0` | **重建后（正式判定用这个）** |

**当前实际使用：默认口径 → `GRAPH_PROVENANCE` = FAIL（`exact_chunk=0`）+ `GRAPH_VERSION_FRESH` = INFO（stale=2）。**

防止"洗绿"的两条硬约束（自检已锁）：
- `PROV-4`：`exact_chunk=0` 时，**任何口径都不得通过**（不能靠关掉 strict 洗绿）；
- `PROV-5`：存在悬空引用时，**任何口径都不得通过**。

### 与 B 的口径对齐（同探针、同 4 块，逐条一致）
```
探针：智造贷 授信额度 票据贴现   top_k=5   kb=kb_9
我：  blocks=4  exact_chunk=0  stale_version=2
B ：  blocks=4  exact_chunk=0  stale_version=0  recovered_stale_count=2   （entity_content 里的旧版本命中，作子属性）
→ 同一现象、同一两个文件：R12FIX-product-intro.pptx（V0，有效 V1）、R12FIX-product-loan.docx（V0，有效 V1）
```
差异原因（B 自己确认）：他的脚本把 `entity_content` 块归成一类就结束，没再判"兜底命中的是哪一代"；
我的实现读同一块的 `metadata.version` 与 `parent_file_name` 比对最新版本。**现双方已统一**：
B 输出 `blocks / exact_chunk / stale_version / recovered_stale` 四个数，我输出 `exact_chunk + stale_version`；重建后逐条对照，不一致就当场对齐口径，不留到最后。

### 重建后的执行命令（不改代码）
```
R14_PROV_STRICT=1 python3 platform/r12/qa/r13_full_check.py \
  --only GRAPH_PROVENANCE,GRAPH_VERSION_FRESH
```
两个数（`exact_chunk>0`、`stale_version==0`）**同时绿**才判绿。

---

## 21. C 的 13:19 重启复核（13:30，双实例窗口 → 标注"非权威但可比对"）

### 21.1 复核结论：FIX-15c 生效，`不传 configId` = 200
```
13:30:03 configId=1     -> 200 len=1591
13:30:18 不传configId    -> 200 len=1591   ← FIX-15c 回落成功（连续两次一致）
13:30:35 configId=1     -> 200
13:30:51 不传configId    -> 200
```
对应 `F05-A5/A6` 双双转绿：**F05 = 9/9**。
> 我 13:23:00 打过一次 500，那是**整栈中断前 26 秒**（gateway 13:23:26 起连接被拒），已作废、不计产品缺陷。

### 21.2 结果（本窗口）
| 套 | 通过/总数 | 时间 |
|---|---|---|
| `r13_full_check`（15 项） | **14 / 15** | 13:31:17 |
| `security_acceptance` | **16 / 16** | 13:32:37 |
| `revoke_acceptance` | **21 / 21** | 13:32:40 |
| `permission_domain_scope` | **9 / 9** | 13:31:02 |
| acceptance | 34/34（12:55–13:10 那轮） | 未重跑 |
| **合计** | **94 / 95** | — |

唯一 FAIL 仍是 `GRAPH_PROVENANCE`（`exact_chunk=0`）。本轮细节变化值得记录：
```
块数=2（上一轮 4）  provenance分布=['None']（不再是 entity_content_recovered）
命中索引={'kb_9':2}  悬空=[]  stale_version=0
```
→ 说明**图侧数据正在变化**（B 可能在预备重建或摘要已重写）；`provenance_quality` 从 `entity_content_recovered` 变成缺失，
`GRAPH_VERSION_FRESH` 因 stale=0 转为 **PASS**（不再是 INFO）。重建完成后这两个值必须重新取一次才算数。

### 21.3 环境：index 双实例（未清理）
```
13:25:30 起 rag-index-service 持续 2~3 个进程：1262434@13:24:28、1290105@13:28:50 …
18082 只有 1 个监听 → 其余为残留
```
按 TL/E 纪律（同端口多 pid = 结果不可信），本轮结果**标注"非权威但可比对"**：
它足以确认 FIX-15c 与拒绝态语义，但**不作为最终交付数**。已请 E 清成单实例后重跑一轮作为 R14-FINAL。

### 21.4 一个需要 A/C 确认的观测
C 报的第 5 条答案是「智造贷单户最高授信额度为人民币 **8000万元**」——这是 kb_9 的 **V1** 值（V0 是 5000万）。
即默认助手当前解析到 V1。这是否符合多版本预期口径，请 A/C 确认；我不据此判 PASS/FAIL，只登记事实。

---

## 22. B 重建图后的严格口径复跑（13:34–13:39）—— **15/15 图侧与主链全绿**

### 22.1 代次与守卫
```
19529  pid=1256188 @13:23:34（批前/批后同一 pid，B 重建后重启的那一代）
graph_service.py mtime=11:57:25 < 进程启动 → 已加载
r12ctl status  STALE_count=0；8088/18081/18082/18083/19995/19529 均监听
复跑参数：R14_PROV_STRICT=1（严判 stale）、R14_PARSE_SINCE=2026-10-27T13:20:00（校验"解析后索引真的更新"）
```

### 22.2 结果

| 套 | 通过 / 总数 | 时间 | 备注 |
|---|---|---|---|
| `r13_full_check`（15 项） | **15 / 15** | 13:36:02 | 含 `GRAPH_PROVENANCE` 严判 PASS |
| `security_acceptance` | **16 / 16** | 13:37:26 | |
| `revoke_acceptance` | **21 / 21** | 13:37:31 | |
| `permission_domain_scope` | **9 / 9** | 13:38:33 | 含 A5/A6（回落语义） |
| `acceptance` | **被阻断** | 13:39:21 起 | 见 §22.4（13:39 整栈再次被外部终止） |
| **已判定合计** | **61 / 61** | — | acceptance 待补 |

### 22.3 `GRAPH_PROVENANCE` 严判的关键变化（与 B 的数对上）
```
我的探针：exact_chunk=2  stale_version=0  块数=2  悬空=0  最新版本 V1/V1  strict=True
B 的口径：blocks=2 exact_chunk=2 stale_version=0 recovered_stale_count=0
```
**重要发现（已按 TL 的 F04 原判据兜底）**：重建后 19529 的块 `metadata` **不再返回**
`provenance_quality` / `identity_stability` / `version` / `id_origin` / `recovered_by`
（keys 里整体消失，不是值变 None）。若照旧读 `provenance_quality` 会得到 `exact_chunk=0` → **假红**。
故按 TL 定的 F04 判据直接用**存储事实**：块的 `pk` 是否存在于当前 ES 的 `_id` 集合（`pk ∩ ES._id`）。
实测 `pk=139363536840301567` 正是 ES 中 `file_id=328` 的 `_id` → `exact_chunk=2`，与 B 一致。
> 版本号改为从 `source` 的 `/Vn/` 兜底解析（`metadata.version` 同样缺失），因此 `stale_version` 仍可判。

### 22.4 acceptance 被阻断（环境，不计产品缺陷）
```
13:39:21  acceptance 启动（plan 8 场景）
13:39:2x  [S3] 上传 PDF 数字版 http=500 fileId=None
          [ERR] gateway 8088 Connection refused
13:39:29–13:41:14  ss: gw=0 idx=0 qa=0，java 进程数 1 → 3 → 7（13:39 整栈被外部终止，正在恢复）
```
**值得记录的一点**：`COVERAGE` 门控按设计判了 **FAIL**（`实际执行=['S1','S2'] 未执行=['S3'..'S8']`），
即"被中断的跑"不会再像旧实现那样以 `exit 0` 冒充通过 —— 这正是 TL 要求的 `--only` 假绿修复的延伸收益。

### 22.5 断言自检
**112/112**（新增 `GPROV-4`「pq 缺失但 pk 命中 ES → 必须 PASS」、`GPROV-5`「pq 缺失且 pk 全不在 ES → FAIL」）。

---

## 23. 最终交付数（14:08–14:13，环境干净：单实例 + pidfile 一致 + STALE=0）

### 23.1 环境前置
```
13:39:29–13:48: 又一次整栈被外部终止（8088/18081–18085/19995 全 0）
13:44:46 ports=5/6 → 13:46:07 6/6 → 13:48:14 首次 smoke 200 → 13:48:51 连续两次 200 = READY
14:08 复核：ports6=6  STALE=0
  rag-index-service pidfile=1403224  procs=1403224   （单实例，pidfile 一致）
  rag-qa-service    pidfile=1403466  procs=1403466   （单实例，pidfile 一致）
  19529 pid=1461792（重建后那一代）
```

### 23.2 台账（共 95 项）

| 套 | 通过 / 总数 | 时间 | 备注 |
|---|---|---|---|
| `r13_full_check`（15 项） | **15 / 15** | 14:08→14:12 + 复测 | `NORMAL` 首跑偶发，复测 3/3 通过（见 23.3） |
| `security_acceptance` | **16 / 16** | 14:12:03 | 3s |
| `revoke_acceptance` | **21 / 21** | 14:12:06 | 38s |
| `permission_domain_scope` | **9 / 9** | 14:13:02 | 按 400+4014 新契约实现 A5/A6 |
| `acceptance`（主链） | **33 / 34** | 13:49→14:06 | 唯一 FAIL = `S4` 解析耗时，见 23.4 |
| **合计** | **94 / 95** | — | 稳定通过 94；1 项为性能抖动（非功能缺陷、非断言问题） |

### 23.3 `NORMAL` 的偶发（**不计产品缺陷**）
```
14:08 首跑：http=200 status=3 answer='模型暂无法返回，请稍后再试!!!' refs=0   ← 模型侧瞬时
14:13 复测：3 次连续 PASS（status=2，answer_len=61/71/73，refs=3）
```
同一形态在 10:xx 首跑也出现过一次（冷调用），复测即恢复。按"连续两次同样失败才算产品 FAIL"的口径，**记为偶发，不计 FAIL**。

### 23.4 `S4` 唯一的 FAIL：解析耗时超阈值（性能抖动，需 TL 定口径）
```
S4 中文 DOCX 业务夹具 fileId=404：轮询 600s 到时仍 status=99 → 判 FAIL
但 ES 实证它在 **14:05:00** 才写入（create_time=2026-10-27 14:05:00.522802，chunk_index=0）
→ 解析**最终成功**，是耗时 ≈15 分钟，不是解析失败
同夹具历史耗时（同一脚本、同一文件）：
  03:32 27s ｜ 04:24 21s ｜ 04:55 567s ｜ 14:05 ≈900s
同批其他文件：405(xlsx) 325s、406(pptx) 33s、409(docx-table) 33s、407/408/410 0s
```
**归类：`FLAKY_PERF`（解析耗时不可控），不是功能缺陷、不是断言缺陷。**
我**没有**擅自把 S4 阈值从 600s 放宽（那属于"为了变绿改判据"）。请 TL 定：
- 口径 A：保持 600s，则该夹具在慢机上会周期性红（需保留为已知性能红项）；
- 口径 B：把 S4 阈值提到 1200s，但**必须同时新增一条"解析耗时 P95"的性能断言**，否则等于掩盖；
- 口径 C：S4 改为"最终状态 + 允许一次重试"，并单独记耗时分布（我倾向 C：判据仍是"能不能解析成功"，耗时单列）。

### 23.5 图侧 pq 字段：中间态已澄清（23 节前一版的"字段缺失"是重建中间态）
```
13:36（pid=1256188，重建刚完成）：metadata 无 provenance_quality → 我用 pk∩ES._id 兜底判 exact=2
14:07（pid=1461792，重启后新代）：provenance 分布=['exact_chunk']，pq字段=有，pk∩ES_id=2
→ 两代 exact_chunk 均为 2、stale_version 均为 0，结论一致；兜底逻辑保留（下次字段缺失仍能判）
```

### 23.6 本轮我自己的一个 bug（如实记录）
14:12 `permission_domain_scope` 崩在 `NameError: sources`：我在加 `deny_verdict` 时把 `sources()` 的定义覆盖掉了。
已修复并 `py_compile`，重跑 **9/9 PASS**；自检 **117/117** 仍全绿。属我方脚本缺陷，与产品无关。

### 23.7 断言自检
**117 / 117**（反证 70 / 正例 47）。本轮新增：`F05-DENY-1..5`（400+4014 / 5xx / 30016 / 403 / 200 五态）、`GPROV-4/5`（pq 缺失时 pk∩ES 兜底）。

---

## 24. R14-FINAL 总账（14:15–14:24，单代次复跑）

### 24.1 采集时环境（三个前置都过）
```
index pidfile=1642203 == 持端口 pid；qa pidfile=1647331 == 持端口 pid（各唯一）
STALE=0（无陈旧 jar）
队列：PENDING=0 DEAL_ING=0 RETRY_ING=0 成功=376 失败=51；status=99 合计=0
```

### 24.2 总账

| 套件 | 通过/总数 | 证据 |
|---|---|---|
| `r13_full_check`（16 项，含新增 OBS1） | **16 / 16** | `evidence/CAPS-20261027T062221Z` |
| `acceptance`（主链 S1–S8） | **34 / 34** | `evidence/20261027T061511Z` |
| `security_acceptance` | **16 / 16** | `evidence/SEC-20261027T062327Z` |
| `revoke_acceptance` | **21 / 21** | `evidence/REVOKE-20261027T062333Z` |
| `permission_domain_scope`（F05/A5/A6） | **9 / 9** | `evidence/R14-F05-20261027T062411Z` |
| **合计** | **96 / 96** | — |
| 断言自检 | **125 / 125** | `evidence/R14-SELFTEST-*` |

**两个必须同时报的数**：`exact_chunk=2`、`stale_version=0`（块数=2、悬空=0、版本 V1/V1、`pq` 分布 `['exact_chunk']`）。

**限定**：本轮基线于 **13:46 栈恢复后**采集；**13:22 / 13:39 两次外部停栈窗口内**的结果已作废（见 §24.4）。

### 24.3 三次 acceptance 的时间账（一次有效，两次作废，均属环境）

| 轮次 | 时间 | 结果 | 处置 |
|---|---|---|---|
| 第 1 轮 | 13:39:21 | S3 上传 500 + 网关 Connection refused | **作废**：13:39 整栈被外部终止（`COVERAGE` 判 FAIL，正确拒绝沉默） |
| 第 2 轮 | 13:49:17–14:06 | 33/34，S4 `fileId=404` 等 600s | **作废**：解析队列被 5 条 `status=3` 僵尸任务卡死（TL/A 已定位修复） |
| 第 3 轮 | 14:15:11–14:16:59 | **34/34 PASS（108s）** | **有效**，且完成于 14:20:43 停服之前 |

### 24.4 环境账（不判产品 FAIL，但必须留痕）

| 事件 | 时间 | 影响 | 处置 |
|---|---|---|---|
| 外部停栈 #1 | 02:26–10:05 | ES 丢 IK、alg 单元 failed | 已恢复，窗口内结果不计 |
| jar 热替换 | 10:29 构建 / 10:02 进程 | 拒绝态退化成 500 空体 | 已报 E 加 `[STALE_JAR]` 守卫 |
| 外部停栈 #2 | 13:22–13:23 | 6 个 Java 服务 + alg 全断 | 窗口内结果作废 |
| 外部停栈 #3 | 13:39:29–13:48:51 | 同上 | 作废；13:48:51 连续两次 200 后恢复 |
| 解析队列僵尸 | 13:45–14:06 | 5 条 RETRY_ING 占满并发槽 → 所有上传静默停摆 | TL 批 SQL 释放；**未改判据** |
| index/qa 优雅停止 | 14:20:43 | 18082/18083 无监听 | 14:21:17 恢复；已在总账后复跑（§24.2 的 16/16 即停后新实例） |
| 模型服务瞬时 | 14:08 | `NORMAL` 返回"模型暂无法返回" | 复测 3/3 PASS，记偶发 |
| index 孤儿 pid | 13:28–13:47 | 不监听但 pidfile 指向它 | E 清理后单实例 |

### 24.5 判据演进（归档，避免下一轮重踩）

1. **`provenance_quality` 整键消失**（重建中间态）→ 判据改为"字段优先，缺失回落存储事实 `pk ∩ ES._id`"；B 后已修，两代结果一致（exact=2）。**"字段消失"与"值变差"对读数是同一件事，都必须能区分。**
2. **`search_type` 含 graph ≠ 图来源**（B 实测）→ `exact_chunk` 只统计 `prov=='exact_chunk'`，不用 search_type 当入口。
3. **`knowledge_base_list.status=1` 是"正常"不是"待处理"** → 我第一版拿它当 PENDING 取最老等待时间，得 3409 分钟假红；改为 `file_parse_task.status=1`。
4. **`R14_PARSE_SINCE` 不能按"上传时间"判**（存量文件永远不生效/或全部假红）→ 改为按 `file_parse_task.end_time`（"本轮解析过"），并有 `PSINCE-1..3` 自检锁死。
5. **`metadata.file_id` 是 text（用 `.keyword`）、`create_time` 是 keyword（不能 max 聚合，改按时间倒序取首条）**。
6. **`--only` 选中但未执行 = FAIL**；且中断的跑以 `COVERAGE` 拒绝沉默（13:39 那轮第一次自证有效）。

### 24.6 新增可观测性断言（TL 指定，不是产品断言）
`PARSE_QUEUE_STALL`：三个信号任一成立即判"队列停摆"——
① `knowledge_base_list.status=99` 超 5 分钟未推进；② 最老 `file_parse_task.status=1` 等待超 5 分钟；③ 存在 `RETRY_ING(status=3)`。
DB 不可读时**判 FAIL 并打出原因**（观测失败本身不能当健康）。
`STALL-1..5` 自检覆盖（含"正常排队 2 分钟不得判停摆"）。

### 24.7 本轮我方脚本缺陷（如实记录）
- `sources()` 定义被我的编辑覆盖 → F05 `NameError` 崩溃；修复后 9/9。
- `PARSE_QUEUE_STALL` 首次实现把 `record()` 参数顺序写错（5 参）→ 被判成 INFO；修正后 16/16 包含该项。
- `PARSE_EFFECTIVE` 的 since 语义错两次（上传时间 → 存量假红），最终按任务结束时间，负向用例已锁。

---

## 25. R14-FINAL（第二次定稿）：C 构建后同代次复跑，97/97

### 25.1 代次与环境（C 的 14:21 构建已加载）
```
index: pid=1642203  jar 14:21:04  proc 14:21:15  DELTA -11s（进程比 jar 新 = 已加载）
qa   : pid=1647331  jar 14:21:07  proc 14:22:00  DELTA -53s（已加载）
STALE=0；ports6=6；队列 PENDING/DEAL_ING/RETRY_ING=0；status=99=0
```

### 25.2 总账

| 套件 | 通过/总数 | 时间 | 证据 |
|---|---|---|---|
| `r13_full_check`（17 项，含 `NO_RECALL_FAB`、`PARSE_QUEUE_STALL`） | **17 / 17** | 14:25:53（83s） | `CAPS-20261027T062553Z` |
| `acceptance`（S1–S8，含 S4 口径 C） | **34 / 34** | 14:27–14:44（1063s） | `20261027T062716Z` |
| `security_acceptance` | **16 / 16** | 14:23:27 | `SEC-20261027T062327Z` |
| `revoke_acceptance` | **21 / 21** | 14:23:33 | `REVOKE-20261027T062333Z` |
| `permission_domain_scope` | **9 / 9** | 14:24:11 | `R14-F05-20261027T062411Z` |
| **合计** | **97 / 97** | — | — |
| 断言自检 | **130 / 130** | 14:45 | `R14-SELFTEST-*` |

**两个必须同时报的数**：`exact_chunk=2`、`stale_version=0`（块数 2、悬空 0、版本 V1/V1、`pq` 分布 `['exact_chunk']`）。

### 25.3 S4 判据改为口径 C（TL 裁定）
```
s4_verdict(final_status, elapsed, expect, poll_timeout=1200, slow=600)
  正例：最终 status=3 → PASS；elapsed>600 → 标记 PASS_SLOW（独立观察量，不判 FAIL）
  正例：status=4 或 >1200s 未终态 → FAIL
  负例：最终 status=4 → PASS
```
本轮实测：8 个正例 `30/0/0/0/0/18/0s`（全部 <600s）；**负例（加密 PDF）耗时 975s 才到 status=4** → 已作为 SLOW 记入 `s4_slow.json`。
`SLOW` 计数在 summary 头部单列（本轮正例 0 项、负例 1 项 975s），与 PASS/FAIL 完全分开。

### 25.4 P1-01（零召回仍给确定性答案）：**止血已生效，断言转为回归**
```
实测 14:25：/qa configId=1 问「恒星项目的归口部门是哪个？」
  → http=200 status=2 refs=0 answer='抱歉未能找到您要的答案' → PASS（明确拒答）
B/C 早前同一问得到"阿里云智能 / 阿里巴巴达摩院"（零引用 + 确定性编造）
```
判据（`no_recall_verdict`，自检 `NORECALL-1..5` 锁死）：
```
refs==0 且含具体实体/数值        → FAIL（无依据作答）
refs==0 且含"未能找到/未提及/请补充" → PASS
有引用                          → 不进入本判据（不能把有依据的答案判成编造）
refs==0 且极短非拒答（"是的。"）  → 不判通过（不可判读）
```
**保留为回归断言**：若 `depend_on_kb=1` 的止血被回滚，这条会立刻红。

### 25.5 未纳入本轮断言的一项（说明理由，不是遗漏）
B 给的 `kb_26` 图增量夹具（`chunk_pk=1137290163540114561` 且 `search_type==['graph']`、关图不出现）需要**直连 19995** 并固定五个参数（`rerank/score_threshold/top_k/top_n/版本过滤`）；而 `kb_26` 没有助手配置，无法经 `/qa` 验证。
本轮时间窗优先保障 P1-01 与 S4 口径落地，故未加入断言集；若下一轮要做，按 B 的判据（`search_type == ['graph']`，不能用"含 graph"）单列一个 `GRAPH_INCREMENT` cap，不与现有 `GRAPH_*` 混算。

### 25.6 环境账（本轮新增）
```
14:20:43  index/qa 优雅停止（SIGTERM，非崩溃）→ 14:21:15 / 14:22:00 由另一路拉起
          我 14:15 的 acceptance 34/34 完成于停服之前，有效；14:22 起的用例跑在新实例上
13:52:48  19529 重启（pid 变更）；本轮图侧 pid=1461792，跑前跑后一致
```

---

## 26. R14-FINAL（第三次定稿）：98/98 断言通过，但 `R14-P2-01` 仍在（断言为窗口快照）

### 26.1 总账

| 套件 | 通过/总数 | 时间 | 证据 |
|---|---|---|---|
| `r13_full_check`（18 项） | **18 / 18** | 15:28:56（110s） | `CAPS-20261027T072856Z` |
| `acceptance`（S1–S8） | **34 / 34** | 15:17–15:28 | `20261027T071709Z` |
| `security_acceptance` | **16 / 16** | 14:23:27 | `SEC-20261027T062327Z` |
| `revoke_acceptance` | **21 / 21** | 14:23:33 | `REVOKE-20261027T062333Z` |
| `permission_domain_scope` | **9 / 9** | 14:24:11 | `R14-F05-20261027T062411Z` |
| **合计** | **98 / 98** | — | — |
| 断言自检 | **138 / 138** | 15:28 | `R14-SELFTEST-*` |

环境：`STALE=0`、ports6=6、index pid=1642203 / qa pid=1647331、19529 pid=1461792。
两个数：`exact_chunk=2`、`stale_version=0`。

### 26.2 但 `R14-P2-01` 没有修好——98/98 不能读成"缺陷消失"

**两个实测样本（同一文件类型，同一代码）**
```
file 443（14:46:18 上传）task 471：retry_times 全程=0，start_time 14:46→14:54，status=5 @14:54:00，文件→4
file 451（14:53:58 上传）task 479：retry_times 全程=0，start_time 每轮刷新，status=5 @15:17:15（**23 分钟**），文件→4
```
**结论**：`retry_times` 恒为 0（计数失效），`retry_limit=3` 对这条路径无效；
任务靠某个**外部超时**才终结，耗时 1 分钟 / 23 分钟两个样本 → **不稳定**。

**因此 98/98 的准确读法**：
> 断言集在**采集那一刻**没有观测到正在发生的无限重试，所以 `PARSE_RETRY_STORM` 判 PASS。
> 但该判据是**窗口快照**（看 `status∈(2,3)` 的任务是否原地重启且计数不增），
> 任务终结后它就不再命中。**15:03 那次 FAIL 才是这条缺陷的现场证据**（见 26.3）。

### 26.3 判据实测（活证据，非构造）
```
15:03  PARSE_RETRY_STORM FAIL：
  {'task': '479', 'file_id': '451', 'status': '3', 'retry_times': '0', 'gap_min': 9}
15:28  同一判据 PASS（任务已终结），并给出事后观察数：
  窗口内"失败 + 耗时>10min + retry_times=0"的任务 = 1（不判红，只作残留证据）
```
判据两条腿：
① `retry_storm_verdict`：同一 file_id 窗口内 task 数 > 3（覆盖"多任务重生"）
② `restart_without_counter`：status∈(2,3) 且 `start_time-gmt_create>=5min` 且 `retry_times=0`（覆盖"单任务原地重生"）
> 只写 ① 会漏；`file 451` 全程只有 1 条 task。

### 26.4 `TIMEOUT` 第三态（TL 指定）
`record(state=)` + summary 三列；`s4_verdict` 负例分支也走超时判断。
```
S4V-1 status=3/30s            -> PASS
S4V-2 status=3/700s           -> PASS_SLOW（环境慢不判产品坏）
S4V-3 status=4（正例）         -> FAIL
S4V-4 1200s 未终态（正例）      -> TIMEOUT
S4V-5 负例 status=4           -> PASS
S4V-6 负例 1200s 卡在 98       -> TIMEOUT（不是 FAIL：排查方向相反）
```
本轮 15:17 那次 acceptance 的加密 PDF **在 1200s 内到达 4**，故 S4 负例 PASS、TIMEOUT=0；
15:16 那次（file 451）卡在 98 到 1201s，被记 FAIL 是我脚本 bug，已修并自检锁定。

### 26.5 我方脚本缺陷清单（本轮累计 5 处）
1. `sources()` 定义被编辑覆盖 → F05 `NameError`（已修，9/9）
2. `record()` 参数顺序写错（5 参）→ `PARSE_QUEUE_STALL` 被判成 INFO（已修）
3. `R14_PARSE_SINCE` 用"上传时间"→ 对存量假红（改为按 `file_parse_task.end_time`）
4. `s4_verdict` 负例分支未走超时 → 卡住被记成 FAIL（已修，`S4V-6`）
5. `slow_fail` 统计用 `end_time is not null`，实测终结时 `end_time` 为 NULL → 漏计（改 `coalesce`）

---

## 27. R14-FINAL（第四次定稿）：99/99，同一代次

### 27.1 代次与环境
```
index pid=2139785（含 P2-01 修复 + 回落路径修复，进程启动 15:40:40）
qa    pid=1647331
STALE=0；ports6=6
```

### 27.2 总账

| 套件 | 通过/总数 | 时间 | 证据 |
|---|---|---|---|
| `r13_full_check`（19 项） | **19 / 19** | 15:47:46（84s） | `CAPS-20261027T074746Z` |
| `acceptance`（S1–S8） | **34 / 34** | 15:49:13–15:51:05（112s） | `20261027T074913Z` |
| `security_acceptance` | **16 / 16** | 15:51:10 | `SEC-20261027T075110Z` |
| `revoke_acceptance` | **21 / 21** | 15:51:12 | `REVOKE-20261027T075112Z` |
| `permission_domain_scope` | **9 / 9** | 15:52:12 | `R14-F05-20261027T075212Z` |
| **合计** | **99 / 99** | — | — |
| 断言自检 | **140 / 140** | 15:45 | `R14-SELFTEST-*` |

`exact_chunk=2`、`stale_version=0`。
acceptance 的 S4 负例（加密 PDF）**0s 到 `status=4`**，FAIL 0 / TIMEOUT 0 / SLOW 0。

### 27.3 `R14-P2-01`：端到端验证**已修复**（不是"白名单命中过一次"）
```
样本1 上传 15:31:37 file=460 终态=4 耗时=10s 轨迹[99→4] task 488 retry_times=1/3
样本2 上传 15:31:50 file=461 终态=4 耗时=15s 轨迹[99→4] task 489 retry_times=1/3
样本3 上传 15:32:03 file=462 终态=4 耗时=10s 轨迹[99→4] task 490 retry_times=1/3
波动 1.51 倍；每个文件只有 1 条 task；日志 R14-C-P2-01 … permanent=true
```
对比修复前（1 分钟 / 23 分钟，`retry_times` 恒 0）→ **稳定快速失败**。
脚本 `platform/r12/qa/p2_01_verify.py`，证据 `evidence/R14-P201-20261027T153136Z/`。
> 当时的对照组（正常 docx）失败，是被下面的 P3-01 挡住；修好后 docx 终态=3（15s）、pptx 终态=3（5s），
> 即"修重试计数"**没有**影响成功路径。

### 27.4 `R14-P3-01`：Office→PDF 转换不可用 + 回落路径传错扩展名（已修复，遗留一项）
**时间线**
```
15:26:48 index 重启（新 jar）
15:32    起 docx 全部 NoSuchKey …/docx-plain.pdf → status=4（4/4 复现，跨 kb_31/kb_32）
15:38    pptx 同型失败（…/product-intro.pdf）；xlsx 正常（不走该链）
15:40:40 index 再次重启（回落修复）
15:47    docx 终态=3（15s）、pptx 终态=3（5s）→ 恢复
```
**根因两段**
```
① 转换入参是 http://127.0.0.1:19000/...（匿名）→ curl 实测 **403**（桶无匿名策略）
   → 下载为空 → jodconverter NullPointerException: Could not open document: r12conv-xxx.docx
② 「回落直接解析原始 docx」只改日志与转换入参，**发给 docparse 的 file_path 仍是 .pdf** → NoSuchKey
```
**当前状态**：回落到原始文件已生效（解析可用）；**转换本身仍不可用**（LibreOffice 路径 403）。
即"功能恢复，优化项未恢复"——写进交付时不要写成"转换已修复"。

### 27.5 新增判据（都能自动抓，不靠人查日志）
| 判据 | 抓什么 | 现场验证 |
|---|---|---|
| `PARSE_RETRY_STORM` | ①同 file_id 窗口内 task>3 ②单任务原地重启且 `retry_times=0` | 15:03 FAIL（task 479 gap 9min） |
| `PARSE_CONVERT_PATH` | 窗口内 `NoSuchKey` + `.pdf` 的失败任务 | 15:40 FAIL（6 条）→ 修复后 PASS |
| `PARSE_QUEUE_STALL` | 99 孤儿 / PENDING 积压 / RETRY_ING 僵尸 | 15:43 PASS（队列健康） |
| `NO_RECALL_FAB` | 零召回 + 确定性答案 | 15:25 PASS（拒答） |
| `PARSE_EFFECTIVE` | status=3 却取不到块 / 索引未更新 | 全程 PASS |

`PARSE_CONVERT_PATH` 的统计起点改为**当前 index 进程启动时刻**（`_proc_start_of(18082)`）：
既不会让"修复前的历史行"把判据拖红，也不会因重启而漏掉新回归。

### 27.6 我方脚本缺陷（本轮累计 7 处，全部已修 + 自检锁死）
```
1 sources() 定义被编辑覆盖            -> F05 NameError
2 record() 参数顺序错（5 参）          -> PARSE_QUEUE_STALL 被判 INFO
3 R14_PARSE_SINCE 用上传时间           -> 存量假红
4 s4_verdict 负例分支未走超时          -> 卡住被记 FAIL（应 TIMEOUT）
5 slow_fail 用 end_time is not null    -> 终结时 end_time 为 NULL，漏计
6 knowledge_base_list.status=1 当 PENDING -> "最老 PENDING 3409 分钟"假红
7 SQL 里 '%NoSuchKey%' 与 %d 混用      -> ValueError（记为 FAIL，观测失败不能当健康）
```

### 27.7 环境窗口表（今日，供报告统一解释红项）
| 起 | 止 | 影响 | 归属 |
|---|---|---|---|
| 02:26 | 10:05 | ES 丢 IK、alg 单元 failed | 环境（已固化为派生镜像） |
| 10:29 | 10:31 | jar 热替换 → 拒绝态 500 空体 | 构建/部署 |
| 13:22 | 13:23 | 业务层/解析/图全断 | 外部（宽泛 pkill，含他项目） |
| 13:39 | 13:48:51 | 整栈再次全断 | 外部 |
| 13:45 | 14:06 | 5 条 RETRY_ING 僵尸占满并发槽 | 缺陷 P2-01 前身 |
| 14:20:43 | 14:22:09 | index/qa 优雅停止 | 另一路自动化 |
| 14:45:43 | 14:50:03 | 19527 两次重启 | A（并发写验证） |
| 14:53:52 | 14:57:53 | `g_kb_9` DROP→图空/半成品→回滚 | B（重建失败） |
| 15:26:48 | 15:40:40 | 转换链 403 + 回落失效 → docx/pptx 全废 | 缺陷 P3-01 |

---

## 28. P0-01 修复后复测（R14 最终版，16:00）

### 28.1 总账（同代次：index pid=2139785 / qa pid=1647331 / STALE=0）

| 套件 | 通过/总数 | 时间 | 证据 |
|---|---|---|---|
| `r13_full_check`（19 项） | **19 / 19** | 15:47:46（84s） | `CAPS-20261027T074746Z` |
| `acceptance`（S1–S8） | **34 / 34** | 15:49:13–15:51:05（112s） | `20261027T074913Z` |
| `security_acceptance` | **16 / 16** | 15:51:10 | `SEC-20261027T075110Z` |
| `revoke_acceptance` | **21 / 21** | 15:51:12 | `REVOKE-20261027T075112Z` |
| `permission_domain_scope` | **9 / 9** | 15:52:12 | `R14-F05-20261027T075212Z` |
| **合计** | **99 / 99** | — | — |
| 断言自检 | **140 / 140** | — | `R14-SELFTEST-*` |
| S3+S4 专项（P0 修复后） | **20 / 20** | 15:58:51 | `20261027T075851Z` |
| PARSE_CONVERT_PATH + GRAPH×5 + GLOBAL×3 | **10 / 10** | 15:58:26 | `CAPS-20261027T075826Z` |

### 28.2 P0-01 复测（TL 要求的三类分开记）

| 类别 | 结论 | 证据 |
|---|---|---|
| docx（修复） | **status=3** | kb_33 file=480 10s / kb_32 file=481 15s，ES 各 1 块 |
| pptx（修复） | **status=3** | kb_32 file=482 15s，ES 1 块 |
| xlsx（isConvertedFile=true） | **status=3 正常** | file=484 0s；走 `parsed/*.md`，**不进转换链** |
| xlsx（需要转换时） | **无回落，必失败** | 已知限制，**R15 待决策**；本轮未传（按 TL 口径不传） |

**核心判据（P0 的本质是路径后缀）**：解析服务收到的是
```
r12-rag/kb_33/docx-plain.docx/V0/docx-plain.docx      ✅ .docx
r12-rag/kb_32/docx-plain.docx/V0/docx-plain.docx      ✅ .docx
r12-rag/kb_32/R12FIX-product-intro.pptx/V0/R12FIX-product-intro.pptx  ✅ .pptx
```
不再是 `.pdf`。

### 28.3 归因更正（撤回我上一条的"匿名 403"）

我此前推断"转换下载走 `http://127.0.0.1:19000` 匿名 → 403 → 空文件 → NPE"。**这条是错的**：
```
C 核运行 jar 字节码：取流走 FileStorageUtils.getInputStreamByUrl → minioClient.getObject（带凭据 SDK）
对象实测：presign 200 → download 200、36716 字节、magic b'PK\x03\x04'（合法 docx，非空）
我 curl 19000 得 403，是因为那是匿名 HTTP GET，**与代码路径不同**
```
真实根因两条：
```
① LibreOffice 缺 libsw*(Writer)/libsc*(Calc)/libsd*(Impress) → 任何 office 都转不了（环境，长期存在）
② PdfConvertorUtils catch 里只把 DB 的 convertedFilePath 改了，**返回值仍是 .pdf** → 调用方拼出不存在的对象
```
> 教训与我上午那次同族：**"真实但不对题的事实"会强化错误假设**。以后写归因必须标注"这条事实来自哪条代码路径"。

### 28.4 判据修正（TL 纠正后）
```
②'-a 转换失败日志仍会出现（LO 缺过滤器，环境所致，预期，不判红）
②'-b 必须同时满足：终态=3 + ES 有该 file_id 的块 + 发给 12340 的 file_path 后缀 == 原始扩展名
```
即：**判据对着"设计意图（回落有没有生效）"写，不对着"现象（转换有没有失败）"写**。

### 28.5 `PARSE_RETRY_STORM` / 负例 / retry_times
```
PARSE_RETRY_STORM  PASS（15:59）：无 file_id >3 条 task；无原地重启未计数；99 孤儿=0
S4 负例(加密PDF)   PASS  fileId=490 最终状态=4 耗时=0s
正常文件计数抽查   file 480/481/482 → task 524/525/526 全部 status=4(retry 0)
                   → "修重试计数"没有把成功路径的计数搞乱
```

### 28.6 GLOBAL / C15 口径（必须标）
```
图状态：回滚基线 g_kb_9 = 87 顶点 / 122 边（B 今日未完成第三次重建）
结果：GRAPH_LOCAL / GRAPH_IDENTITY / GRAPH_PROVENANCE / GRAPH_UPPERCASE / GLOBAL×3 全 PASS
     exact_chunk=2、stale_version=0、版本 V1/V1
但：GLOBAL_POS refs 由 3 降为 1，社区 id 回到旧代 L0-18625408
=> 这是"**回滚基线上的现状**"，不是"重建后"，不可与重建结果对比
   引用数 3→1 提示"文件级引用仍指旧代"的问题依然存在（与 B 的 M1b 一致）
```

---

## 29. R14 收口（16:00–16:01，最后一轮）

### 29.1 最终五行
```
① r13_full_check  19/19   （16:00:06，67s，CAPS-20261027T080006Z）
② acceptance      34/34   （15:49:13–15:51:05，112s，20261027T074913Z）
③ security        16/16   （15:51:10，SEC-20261027T075110Z）
④ revoke          21/21   （15:51:12，REVOKE-20261027T075112Z）
⑤ F05             9/9     （15:52:12，R14-F05-20261027T075212Z）
合计              99/99
断言自检          140/140
S3+S4 专项        20/20   （15:58:51，P0 修复后）
GLOBAL/C15        9/9     （16:01:13，回滚基线，混合态）
```
代次：index pid=2139785（P0 修复版）、qa pid=1647331、19529 pid=1461792、STALE=0。

### 29.2 三个可引用数字的采集口径（TL 要求）

| # | 数字 | 采集时刻 | 当时代次 | 性质 |
|---|---|---|---|---|
| ① | P2-01 三次 10s/10s/15s、波动 1.51、`retry_times=1/3`、单 task | 15:31:37–15:32:16 | index=2052541（P2-01 修复首版） | **产品缺陷已修复的证据** |
| ② | `PARSE_RETRY_STORM` FAIL（task 479、gap 9min、retry 0） | 15:03 | index=1642203（**P2-01 修复前**） | **缺陷现场证据**（非环境） |
| ③ | `PARSE_CONVERT_PATH` FAIL 6 条（NoSuchKey *.pdf） | 15:40:41 | index=2139785 启动瞬间（修复窗口） | **P0 现场证据**；修复后 15:47/15:58 转 PASS |

> 同一断言在不同代次上结果相反，因此三者都必须带"采集时刻 + 代次"，否则会被读成"断言不稳定"。

### 29.3 转换不可用的归因（**第三次更正，以 C 的命令为准**）
```
✘ 19000 匿名 403（我 15:36 的推断 —— 已被否掉）
✔ 本机未安装 LibreOffice Writer/Calc/Impress 过滤器
  证据（C 的决定性实验，不经 MinIO、不经鉴权）：
    cp fixtures/R12FIX-product-loan.docx /tmp/lots/good.docx   (37,544 字节，合法 docx)
    soffice --headless --convert-to pdf --outdir /tmp/lots good.docx
      -> Error: source file could not be loaded
    dpkg -l | grep libreoffice -> 只有 core/common/math/gtk3/gnome/help/l10n
    /usr/lib/libreoffice/program 无 libsw* / libsc* / libsd*
影响：docx/pptx 每次多一次"转换失败→回落"，多 5–15s；功能可用，仅 PDF 预览降级
恢复：apt 安装（环境变更，非代码）
```
**为什么必须写成"缺过滤器"而不是"403"**：若写成 403，下一轮会有人去改 presign，改完发现仍转不了——**错误归因消耗的是下一个人的一整天**。
我这两次（14:44 人工 status=4、15:36 匿名 403）是同一族错误：**用"真实但不对题"的事实支撑结论**。

### 29.4 GLOBAL / C15（TL 定稿口径：回滚基线，不是重建后）
```
测量对象：g_kb_9 回滚基线 87 顶点 / 122 边，file_id 全 V0
Milvus 混合态：entity 42/53、triples 40/72、summary 1/0
结果（16:01）：GLOBAL_POS / REFUSE×2 / FAITH / GRAPH_LOCAL / GRAPH_IDENTITY /
              GRAPH_PROVENANCE / GRAPH_UPPERCASE = 9/9 PASS
  exact_chunk=2、stale_version=0、版本 V1/V1、violations_count=0
观测到的不稳定：GLOBAL_POS refs 三次探针为 **3 → 1 → 2**，社区 id 固定为旧代 L0-18625408
=> 判读：图能力可用，但**文件级引用仍指旧代**；refs 数值在混合态下不稳定，
   本组数不可与上午"重建后 2/2(100%)"直接对比。
```
（B 已声明其早前 `exact_chunk=2/2` 为重建前测量。）

### 29.5 环境作废统计（TL 要的数）
```
acceptance 全量 13 轮 + 1 轮专项（S3,S4）
  有效 34/34：7 轮（03:32 / 04:24 / 04:55 / 06:15 / 06:27 / 07:17 / 07:49 UTC）
  环境作废：4 轮
    · 05:39Z（13:39 外部停栈）→ 8/11，COVERAGE 判 FAIL
    · 05:49Z（13:45–14:06 队列僵尸）→ 33/34，S4 等 600s
    · 06:46Z（14:46 起，被中途终止）
    · 06:53Z（14:53 起，B 图重建窗口；其红项实为 P2-01，非环境）
  专项：07:58Z（15:58 S3+S4 20/20，P0 修复后）
r13_full_check 全量：19 项 × 5 次（15:17 / 15:28 / 15:47 / 16:00 + 早期 18 项 1 次）
  红项：PARSE_EFFECTIVE 500（14:17，停服窗口，环境）/ PARSE_CONVERT_PATH（P0）/ PARSE_RETRY_STORM（P2-01）/ NORMAL 瞬时 1 次（复测 3/3）
```

### 29.6 环境窗口表（最终版，9 条）
| 起 | 止 | 影响 | 归属 | 处置 |
|---|---|---|---|---|
| 02:26 | 10:05 | ES 丢 IK、alg 单元 failed | 环境 | 派生镜像固化；窗口内结果不计 |
| 10:29 | 10:31 | jar 热替换 → 拒绝态 500 空体 | 构建/部署 | `[STALE_JAR]` 守卫 |
| 13:22 | 13:23 | 业务层/解析/图全断 | 外部 pkill | 结果作废 |
| 13:39 | 13:48:51 | 整栈再次全断 | 外部 pkill | 结果作废；`COVERAGE` 判 FAIL |
| 13:45 | 14:06 | 5 条 `RETRY_ING` 占满并发槽 | 缺陷 P2-01 前身 | TL 批 SQL；队列恢复 |
| 14:20:43 | 14:22:09 | index/qa 优雅停止 | 另一路自动化 | 停后新实例复跑 |
| 14:45:43 | 14:50:03 | 19527 两次重启 | A（并发写验证） | S4 相关失败标窗口 |
| 14:53:52 | 14:57:53 | `g_kb_9` DROP→图空→回滚 | B（重建失败） | 该轮 acceptance 作废 |
| 15:26:48 | 15:40:40 | 转换回落返回值错 → docx/pptx 全废 | 缺陷 P0-01 | 已修复并复测 |
