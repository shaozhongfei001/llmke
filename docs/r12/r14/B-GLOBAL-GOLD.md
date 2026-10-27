# B-2 GraphRAG global 效果题（ground truth + 实测记录）

作者：B-graph（R14）
时间：2026-10-27 02:20–02:45 UTC（本机 10:20–10:45）
范围：`index_graph_service/**`（19529）、`alg_retrieval_service/app/view/api/retrieval_global_view.py`（19995）、`platform/r12/graph/**`
入口：**用户入口 `/qa/ai/question`（gateway 8088，`globalMode=true`，configId=1）**；另有一组"本地 harness"仅用于诊断（见 §4，不作为交付证据）。

> 语料状态必须一起读：kb_9 在 2026-10-27 10:20 是 **8 篇文档**；到 10:37 我复测时 ES `kb_9` 只剩 **1 篇**（`R12FIX-product-loan.docx`），社区摘要仍是旧代次（7 个，`file_ids` 全部为已失效的旧 id）。也就是说：**图/社区建立在旧代次上，语义库正在被别人重建**。这本身就是要暴露的 F04 问题，本文不绕开它，逐条标注语料状态。

---

## 1. 为什么这 4 道题算"真跨文档/跨社区"

kb_9 的图被 Louvain 切成 7 个社区（L0×6 + L1×1）。下面每道题的答案**分布在 ≥2 个社区**，且必须跨 ≥2 篇文档才能拼出：

| 社区 | 承载的事实 | 来源文档 |
|---|---|---|
| `L0-3af0d4bc` | 江南装备科技有限公司 → 信用评级 AAA / 到期日 2027-06-30 / 装备制造 | R12FIX-credit-ledger.xlsx |
| `L0-60d6fa91` | 北方重工配件厂与华东精密制造 → 信用评级 AA；到期日 2027-01-31 / 2027-03-31 | R12FIX-credit-ledger.xlsx |
| `L0-3c882b30` | 海川电子材料股份有限公司 → 五级分类 关注 / 到期日 2026-12-31 | R12FIX-credit-ledger.xlsx |
| `L0-18625408` | 智造贷：单户最高 5000万元、信用方式≤1000万元、期限 3年、**AAA+30 / AA+60 / A+100 个基点** | R12FIX-product-loan.docx、R12FIX-product-intro.pptx |
| `L0-a5a28a99` | 日均存款 ← T-CORE-001，口径 按业务日跨账户汇总/天数 | docx-table.docx |
| `L0-be7452ca` | 用电量 ← T-EXT-001，口径 月度同比 | docx-table.docx |

---

## 2. Ground truth（全部由我从原文逐字核对，未使用模型自评）

### G1（跨 2 文档 / 3 社区：属性 → 规则 映射）
**问题**：江南装备科技有限公司、华东精密制造有限公司、北方重工配件厂三家的信用评级分别是什么？按智造贷的评级加点规则，它们执行利率相对一年期LPR的加点分别是多少？

**标准答案**
| 客户 | 信用评级 | 加点 | 依据 |
|---|---|---|---|
| 江南装备科技有限公司 | AAA | **30 个基点** | 台账行3 + 产品说明书 §三「AAA级加30个基点」 |
| 华东精密制造有限公司 | AA | **60 个基点** | 台账行2 + §三「AA级加60个基点」 |
| 北方重工配件厂 | AA | **60 个基点** | 台账行5 + §三「AA级加60个基点」 |

**原文定位**
- `r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx`，表 `table-0-授信台账`，行：`江南装备科技有限公司 | 装备制造 | AAA | 5000 | 3200 | 正常 | 2027-06-30`；`华东精密制造有限公司 | 汽车零部件 | AA | 3000 | 1800 | 正常 | 2027-03-31`；`北方重工配件厂 | 汽车零部件 | AA | 2000 | 0 | 正常 | 2027-01-31`
- `r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx` §三「贷款期限与利率」：`加点幅度根据客户信用评级确定：AAA级加30个基点，AA级加60个基点，A级加100个基点。`
- 旁证 `R12FIX-product-intro.pptx`：`利率：1年期LPR加点30~100BP`

### G2（跨 2 社区 / 表 + 正文：指标口径）
**问题**：知识库里日均存款和用电量这两个对账指标，数据源分别是什么、统计口径分别是什么？

**标准答案**
- 日均存款 → 数据源 `T-CORE-001`，口径 `按业务日跨账户汇总/天数`
- 用电量 → 数据源 `T-EXT-001`，口径 `月度同比`

**原文定位**
- `r12-rag/kb_9/docx-table.docx/V0/docx-table.docx`，表 `table-0`：`日均存款 | T-CORE-001 | 按业务日跨账户汇总/天数`；`用电量 | T-EXT-001 | 月度同比`
- 旁证（数值可核对）：`r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx` 第二段「日均存款 2,983,333.33 元」

### G3（跨 3 社区：多实体聚合 + 时间过滤）
**问题**：四家授信客户的信用评级和授信到期日分别是什么？其中哪些客户的授信在 2027 年上半年（2027-06-30 之前）到期？

**标准答案**
- 江南装备科技有限公司：AAA / 2027-06-30 → **在**上半年
- 华东精密制造有限公司：AA / 2027-03-31 → **在**上半年
- 海川电子材料股份有限公司：A / 2026-12-31 → 不在（2026 年）
- 北方重工配件厂：AA / 2027-01-31 → **在**上半年
→ 2027 上半年到期的是 **北方重工、华东精密、江南装备** 三家

**原文定位**：`r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/...` 表 `table-0-授信台账` 全部 4 行（见 G1 引文，海川行：`海川电子材料股份有限公司 | 电子信息 | A | 1200 | 900 | 关注 | 2026-12-31`）

### R1 / R2（无答案拒答题，**不计入正例统计**）
- R1（沿用 R13 的既有拒答位）：`我们这类企业的授信额度与票据贴现是什么关系` — 语料中**没有票据贴现**相关内容，正确行为是拒绝作答。
- R2（本次新增）：`海川电子材料股份有限公司被列为关注类，需要计提多少比例的贷款损失准备？` — 语料只有五级分类=关注，**没有任何计提比例**，正确行为是拒答且不得给数字。

---

## 3. 实测（经用户入口 /qa，globalMode=true）

### 3.1 轮 A：改造前（语料 8 篇、社区旧代次，10:27）

| 题 | 答案要点 | 引用数 | 逐条核验 | 判定 |
|---|---|---|---|---|
| G1 | 评级 AAA/AA/AA **对**；加点「AAA 15个基点、AA 10个基点」 | 2 | 评级可回链；**15/10 在原文中不存在**（原文是 30/60/100），且引用只到 `L0-5befded4`、`L0-918cb4d7`，这两个社区摘要里根本没有加点事实 | **不达标（编造数值）** |
| G2 | 数据源 T-CORE-001 / T-EXT-001 **对**；口径「与跨账户相关」「同比和月度」 | 2 | 数据源可回链；「按业务日」「/天数」**缺失** | **部分达标** |
| G3 | 只答 3 家，漏海川；称北方/华东「无到期日」；结论「只有江南上半年到期」 | 2 | 3 条到期日事实就在社区成员里却答"未提及"；结论**错**（北方 01-31、华东 03-31 也在上半年） | **不达标（聚合错误）** |
| R1 | 「没有直接关于授信额度与票据贴现关系的信息」 | 5 | 正确拒答 | 达标（拒答位） |

证据：`platform/r12/graph/evidence/R14-B-global-{base,G1,G2,G3}-20261027T0227*.json`（含完整 SSE 帧与 reference 原文）

### 3.2 轮 B：改造后（kb_9 已被他人重建到 1 篇，10:37）

| 题 | 答案要点 | 引用数 | 逐条核验 | 判定 |
|---|---|---|---|---|
| G1 | 评级 AAA/AA/AA 对；加点「参考资料中没有提供具体的加点信息」 | 3 | 不再编造数字（改进），但**漏答**了本可回答的 30/60 | **不达标（漏答）** |
| G2 | 同轮 A | 2 | 同轮 A | 部分达标 |
| G3 | 仍称三家到期日「未提及」，结论「没有客户在 2027 上半年到期」 | 3 | 结论**错** | **不达标** |
| R2 | 「无法直接找到…计提比例」 | 1 | 正确拒答，未编数字 | 达标（拒答位） |
| 引用可打开性 | 5/5 条 reference 的 `metadata.source` 为**空** | — | 社区 `file_ids` 全为旧代次、`file_names`/`sources` 解析不出，kb_9 又只剩 1 篇 → 既无法解析对象键也无从实体反查 | **不达标（回链断）** |

证据：`R14-B-global-G1-qa-20261027T023702Z.json`、`R14-B-global-Q{6f1b3f,6c6332,fe938d}-20261027T0237*.json`

### 3.3 决定性发现：`global_answer` 在 Java 侧被丢弃（reduce 结果到不了用户）

轮 B 里 G1 从「编造 15/10 基点」变成「未提供」，表面上像是我改的 reduce 没生效。直连核对后确认：

| 入口 | 同一问题（G1）的答案 |
|---|---|
| `POST 19529/query_community`（global，直连图服务，连跑两次） | **正确且两次完全一致**：江南 AAA→30 个基点 [L0-3af0d4bc]、华东 AA→60 [L0-60d6fa91]、北方 AA→60 [L0-18625408] |
| `/qa/ai/question`（globalMode=true, configId=1） | 「参考资料中没有提供具体的加点信息」——reduce 的正确答案**不见了** |

读码定位（`rag-qa-service`，非我所有权）：
1. `AiServiceImpl.buildRetrieveDataList()`（L2348–2384）global 时把 URL 换成 `searchDocsGlobalUrl`，响应经 `RetrievedData.getDefault(rs)` 只留 `data`；
2. `combineRetrieveDataList()`（L2386 起）只合并 `documents_list / faq_result_list / log_list`，把**社区摘要当普通召回文档**往下传；
3. `RetrievedData`（`domain/entity/RetrievedData.java`）只暴露 `documents_list / table_selected_list / faq_result_list`，**没有 `global_answer` 的 getter**；全仓 `grep global_answer` 零命中。

→ **`RetrievalGlobalView` 返回的 `data.global_answer` 无人消费**，问答主链拿摘要文本重新生成第二遍答案。也就是说：
- 对用户而言，"global map-reduce" 实际退化成"把社区摘要当原文再答一次"；
- 我在 reduce 阶段做的「逐社区事实投影 + 数字逐字约束」在 /qa 路径上**全部不生效**；
- 这也解释了为什么轮 A/轮 B 的 /qa 答案措辞都像"又生成了一遍"，与图服务的 reduce 输出不同。

已把精确位置与最小改法（给 `RetrievedData` 加 `getGlobalAnswer()`，global 分支优先直接采用）转给 C-business。**在 Java 消费 `global_answer` 之前，任何 /qa 上的 global 效果测量都不能代表 reduce 的能力**——这也是轮 B 判"不达标"的主要原因之一。

### 3.4 轮 C：维护结束后终版测量（10:52，A 已把社区写入改为整代替换）

`platform/r12/graph/r14_b_final_measure.py`，证据 `platform/r12/graph/evidence/R14-B-FINAL-20261027T025229Z.json`。

| 题 | http/cost | 引用数 | source 可解析 | 答案要点 | 判定 |
|---|---|---|---|---|---|
| G1 | 200 / 7.7s | 3 | 3/3 单 host（`…/R12FIX-product-loan.docx/V0/…`） | 评级 AAA/AA/AA **对**；加点「没有提供具体的加点规则」 | **不达标（漏答）** |
| G2 | 200 / 4.0s | 2 | 1/2（`docx-plain.docx`；`L0-be7452ca` 为空） | 数据源对；口径仍是「跨账户」「同比和月度」，缺「按业务日」「/天数」 | **部分达标** |
| G3 | 200 / 13.0s | 3 | 2/3 | 仍称三家「到期日信息不足」，结论「没有客户在 2027 上半年到期」 | **不达标（结论错）** |
| R2 | 200 / 2.4s | 1 | 0/1 | 正确拒答，未编数字 | 达标（拒答位） |

本轮进步（相对轮 B）：**引用 source 恢复为单个可解析对象键**（3/3、1/2、2/3）。原因是我在 §5 里补的"按实体内容反查"三级解析 + A 把社区写入改成整代替换后 ES/Milvus 不再堆积旧行。

**本轮新增一个必须单列的缺陷**（local，开图 configId=1）：
```
refs=0   cost=7.5s
answer: 根据智造贷的评级加点规则，AAA级信用评级对应的基点加成是15基点。
        因此，江南装备科技有限公司执行的利率相对一年期LPR要加15基点。
```
**引用为空（refs=0）却输出了原文里不存在的具体数值 15 基点**。这属于任务书明令禁止的"模板伪答案/无依据作答"，且比"答错"更危险：用户看不到任何来源，却拿到一个精确数字。
（同题在图服务直连下是 30 个基点且有出处；此处 15 基点是主链在无上下文时的自由生成。）
→ 建议：主链在 `documents_list` 为空时**必须拒答**，不得生成带数值的答案。此项归问答主链（Java/检索），不属我文件，已一并上报。

### 3.5 结论（轮 A–C 汇总，不粉饰）
- **经 /qa 的正例 3 题，轮 A/B/C 都 0 题完全达标**（G2 一直"部分达标"）；拒答位 R1/R2 达标。
- 但"经 /qa 不达标"不能直接算成 reduce 的能力结论：§3.3 已证明 **Java 丢弃 `global_answer`**，/qa 上看到的是"社区摘要当原文再生成一遍"。同一问题直连 `POST 19529/query_community` 时，reduce 给出的答案是**正确且可复现**的（三家评级 + 30/60/60 基点 + 引用到正确社区）。
- 三轮的真实变化只有两条：
  1. 轮 A→B：**不再编造原文里没有的数字**（15/10 基点 → "未提供"）；
  2. 轮 B→C：**引用 source 恢复为单个可解析对象键**（3/3、1/2、2/3）——来自"按实体内容反查"+A 的整代替换写入。
- 轮 C 新增更严重的一条：**local 在 refs=0（无任何引用）时仍输出"15 基点"**。无来源却给精确数值，必须由主链改成"无召回即拒答"。

---

**关于验收矩阵里 `GLOBAL` 判 FAIL 的口径（重要，别读成能力失败）**：`r13_full_check.cap_global` 用的是
「我们这类企业的授信额度与票据贴现是什么关系」——语料里**没有票据贴现**，这正是本文 §2 的 **R1 拒答位**。
按任务书要求拒答题**不得混进正例统计**。C 修完 `global_answer` 后，该题的正确返回就是"事实中未提及" +
只引用一个社区（`refs=1`），而断言要求"≥2 条可解析来源"，**题与断言不匹配**，结构上不可能通过。
建议拆两条：`GLOBAL-POS` 用 G1（期望 30/60/60 + `refs≥2` + 单 host source）；`GLOBAL-REFUSE` 用 R1/R2
（断言"含拒答语义且**不出现任何具体数值**"，引用数**不设下限**）。另：**不得断言答案逐字固定**——
实测 reduce 输出非严格可复现（同题两次：6 行 vs 4 行）。

### 3.6 local（开图 vs 关图）实测与兜底改动

同题 `江南装备科技有限公司的信用评级是AAA，按智造贷的评级加点规则，它执行利率相对一年期LPR要加多少基点？`

- **开图**（configId=1，`enabled_graph=true`）：检索日志显示 `POST 19529/query_graph_data` 200、`entity_list=['评级授信','跨账户','3个工作日','客户信用评级','60个基点']`，但返回 `查询成功，共0条文本数据` → **命中实体、正文回填 0 条**；最终引用 1 条，`search_type=['milvus','es','es']`，**无 `graph`**。
- **关图**（configId=6，`enabled_graph=false`）：不调用图服务。引用 1 条，内容与开图**完全相同**。

→ 结论：当时图对上下文**零贡献**，开/关图答案与引用块集合一致。根因是 F04 代次漂移（图顶点的 `chunk_pk_list` 是旧 ES/Milvus id，kb_9 又被重建到 1 篇）。

**兜底改动（`graph_service.fetch_chunk_documents`）**：当 Milvus pk 与 ES `_id` 两级都取不到正文时，用图检索**已经算出的实体名**在当前代次 ES 文本块里按内容回取，命中块打 `recovered_by=entity_content` + `recovered_entities`，与精确回填可区分。
实测（`POST 19529/query_graph_data {"query":"江南装备科技有限公司的信用评级"}`）：
```
code 200 查询成功，共1条文本数据
 - R12FIX-product-loan.docx | recovered_by entity_content | len 459
   | source r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx
```
即图重新有了非空正文、可解析来源。10:58 过滤后复测（19529 直连）：4 条、`ents` 全部非空、`source` 单 host 可解析，含真正的答案来源 `R12FIX-credit-ledger.xlsx`；同次 `entity_list=['评级授信','AA','客户信用评级']`——**问题里的主体"江南装备科技有限公司"没有被识别成图锚点**（尽管它是图中真实顶点），归 M1/NER 抽取问题。

**但"经 /qa 的开/关图对照"到 11:00 仍未取得可用结论**，原因如实记录（不是"图无效"）：
- 10:42–10:44 本机进入维护（`platform/r12/run/.maintenance`、18082/19995 被优雅停止）；E 说明 10:42–10:44 有一次滚动重启，要求该窗口的 5xx 复测。
- 11:58 前复测 `/qa`（configId=1，`enabled_graph=true`）连续三次：`refs=0`、耗时 1.1s / 1.7s / 7.5s、检索服务侧**没有对应请求日志**，而答案给出**互不相同且精确的数值**（15 基点 / 50 基点 / 30 基点，其中 30 恰好正确）。`resultType` 为空（不是 FAQ 直答）。
- 即：**无召回也能产出精确数值**（旧两轮已记 15 基点），这属"模板伪答案"，必须由主链改成"无召回即拒答"；在此之前，"开/关图对照"没有可信的引用块集合可比。

**10:15 突破（链路级缺陷修掉后，图确实进入了上下文）**：A-data 复现出一条链路级丢结果——图服务在"空间不存在"时返回 `data=None`，检索侧 `retrieval_graph` 硬取 `data['result_data']` → KeyError → `except` 里 **return（不是 continue）** → 多 KB 组合里只要有一个 KB 没有图空间，**后续 KB 的图结果全丢且对外仍 200**。我把 `:788` 补成与另外三处同形的空结果（`result_data: []` + `reason: space_not_found`），随后直连检索服务验证（`knowledge_base_name=["kb_5","kb_9"]`，kb_5 无图空间）：

```
docs 3
 - r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/…   search_type ['milvus','es','es']   len 221
 - r12-rag/kb_9/R12FIX-product-loan.docx/V1/…    search_type ['es','es','graph']    len 459   ← 图贡献块
 - r12-rag/kb_5/table-ledger.xlsx/V0/…           search_type ['milvus','milvus']    len 258   ← kb_5 未被跳过
```
证据：`platform/r12/graph/evidence/R14-B-local-graphblock-multikb-20261027T031546Z.json`。
即：**图贡献块有非空正文（459 字）、来源是单个可解析对象键**，"图对上下文零贡献"的观察在修掉这条链路缺陷后不再成立。
仍未完成：`/qa` 口径的开/关图对照——11:15 起 gateway 8088 再次不可用（connection refused，另一次滚动重启），需在入口恢复后重跑；另外我打的 `provenance_quality` / `identity_stability` 在**检索服务合并阶段被丢掉**（返回的 metadata 里这两字段为 None），审计标注需在 `alg_retrieval_service` 侧透传，属他人文件，已上报。

**11:18 网关恢复后的 `/qa` 开/关图对照（结论很严重）**：证据 `platform/r12/graph/evidence/R14-B-FINAL-20261027T031832Z.json`

| 配置 | 引用数 | 答案 | 判定 |
|---|---|---|---|
| **开图**（configId=1，`enabled_graph=true`） | **0** | "AAA 级对应的加点基数是 **20 基点**" | 无引用 + 数值编造（正解 30） |
| **关图**（configId=6，`enabled_graph=false`） | **3** | "执行利率相对一年期LPR要加 **60 个基点**" | 有引用，但数值错（AAA 应为 30，60 是 AA） |

`local 引用块集合：on=0 off=3 交集=0` ← **这一格度量作废，见下方更正**；`开图时带图标记/图回填的引用块：0`。

**度量更正（A-data 2026-10-27 实测指出，我采纳）**：`order_num = str(create_uuid())`（`retrieval_fun_tool.py:491`）是**每请求现造**的——同一批 chunk（`pk` 相同、顺序相同）连续两次请求，`order_num` 两次全不同。因此用 `order_num`（或答案里的 `[retrive-tag id=…]`）做**跨请求**引用交集，**结构上恒为 0**，与开/关图无关；`交集=0` 不能作为"开图更差"的证据。稳定键应为**文档顶层 `pk`**（= ES `_id` / Milvus pk；注意 `metadata.pk` 已被检索层白名单丢掉，`pk` 只在顶层），或 `(metadata.id=document_id, metadata.chunk_index)`。测量脚本已改为按顶层 `pk` 比集合（`r14_b_final_measure.py`），重跑时遇 503（又一次服务滚动），待稳定后补。

→ **仍然成立的事实**：开图 `refs=0`、关图 `refs=3`（这是**计数**，不依赖 order_num）；开图答案"20 基点"、关图"60 基点"，正解 30，两者都错。

**归因更正（A-data 定位 + 我独立复现，2026-10-27 11:40）——`filterDocs` 不是元凶，真因是 19995 直接 500**：
```
POST 19995/retrieval_documents  enabled_graph=true
  「信用评级为AAA的公司执行利率需要加多少个基点」 -> HTTP 500
  「信用评级为aaa的公司执行利率需要加多少个基点」 -> HTTP 200
  同一大写查询 + enabled_graph=false               -> HTTP 200
根因：app/retrieval_service.py  :375-379 只把小写形式放进 queries，:478 却用原始大小写取键 → KeyError
```
→ 只要查询含大写 ASCII（`AAA`/`AA`、`T-CORE-001`、`PRD-CORP-LOAN-2026-01`、任何英文缩写），**开图必 500**，Java 拿不到 `documents_list`，引用必然为空。这也解释了"答案对但零引用"：答案来自模型自身知识，检索结果根本没参与。
**纯中文对照（把两条缺陷分开）**：`智造贷单户最高授信额度是多少` → 开图 `200, refs=3`（2 条 `search_type` 含 `graph`）；关图 `200, refs=3`（无 graph）。即 **`filterDocs` 未损坏**，不触发 500 时开图引用正常。
证据：`R14-B-local-{on-cn-on,off-cn-off}-20261027T034126Z.json`。已明确告知 C：**只改 `:478` 的键大小写，不要动 `filterDocs`**（我上一条建议已撤回）。

原"两条缺陷"表述作废，更正为：
1. **检索层键大小写不一致 → 含大写 ASCII 的查询开图 500**（真缺陷，属检索层/C）；
2. **`order_num` 每请求随机** —— 独立缺陷，使"引用→文档"的映射**跨请求不可解析**（不只影响对照，也影响"刷新页面/重放历史答案后引用点不开"）。建议改为由 chunk 身份派生（`pk` 或 `document_id+chunk_index`）。

**"图确有贡献"的正面结论只在算法侧成立**（§3.6 前面的多 KB 直连证据：graph 块 459 字正文 + 单 host 可解析来源）；到用户入口这一层目前是负向的。

**11:38 C 修完 `global_answer` 消费后复测（有答案题 G1）**：`/qa`（globalMode=true, configId=1）返回
`江南…加点是30个基点[L0-18625408]` / `华东…60个基点[L0-18625408]` / `北方…60个基点[L0-18625408]`，`refs=3`、`source=…/R12FIX-product-loan.docx/V0/…` 单 host。证据 `R14-B-global-G1-c-fix-20261027T033835Z.json`。
即 **reduce 答案原样到达用户**（带社区 id、带可解析 source）。C 送的 payload 字段已够，不需补 `config`/`levels`。
**同时收回一条我此前的说法**：reduce 输出**不是严格逐字可复现**——同问题同参数连打两次，一次 6 行（含三家评级 + 三个加点），一次 4 行（评级三句被省）。此前"两次一致 ⇒ 可复现"的结论作废，改为：**验收须按"单次答案能否回指事实"判，不得按"两次逐字相同"判**。

**11:36 网关恢复后的最终一轮（/qa，证据 `R14-B-FINAL-20261027T033636Z.json`）**

| 配置 | refs | 答案 | 关键 |
|---|---|---|---|
| 开图 configId=1 | **0** | "…要加 **30 个基点**" | **数值正确，但零引用**——正确结论没有任何出处可核验 |
| 关图 configId=6 | **3** | "…要加 **60 个基点**" | 有引用，数值错（60 属 AA，正解 30） |

即：**开图 = 答案对但引用全丢；关图 = 有引用但答案错**。`refs=0` 稳定复现，且这次答案正确让危害更隐蔽（用户无从判断真假）。
另两条影响断言写法的事实：① **`/qa` 的 reference 对象没有顶层 `pk`**（keys：`metadata/order_num/page_content/parsedFilePath/score/type`），稳定身份只能用 `(metadata.id=document_id, metadata.chunk_index)`——测量脚本已据此改；② `order_num` 仍随机，跨请求不可对账。
关图三条引用（可核对）：`R12FIX-product-loan.docx/V1`(chunk0, `['es','es']`)、`R12FIX-product-intro.pptx/V1`(chunk0)、`R12FIX-credit-ledger.xlsx/V0`(chunk0)。

**数值正确性 vs 引用可解析性（必须分开记，C 2026-10-27 提出，我采纳）**：修复 500 后 local 侧出现"200 + refs 非空但数值错"——`信用评级为AAA…` 两次分别答 `100`/`60` 基点。核对 ES 正文后确认：**V0 与 V1 都是「AAA级加30、AA级加60、A级加100」**，所以 100 是模型把 **A 级那一行**套到 AAA 上、60 是把 AA 行套上去——**chunk 内容正确、取值映射错误**，属效果侧（模型 + 单块作答），不是检索/文档缺陷。故任何"引用非空即通过"的写法都会掩盖它。
另附多版本观察（属 C/A 的域）：`R12FIX-product-loan` 的 V0（最高 5000万）与 V1（8000万）**同时可被召回**，同题下模型可能拿到冲突数值（实测"最高授信额度"答 8000万，取到 V1）——数值正确性的判定依赖"当前有效版本"口径。
**`order_num` 结论撤回**：我此前称它是"引用打不开的直接原因"**无证据**——我从未观测到"有 source 却打不开"，只观测到 `refs=[]`（已查明为 500）。事实只有两条：A 实测同批 chunk 两次 `order_num` 不同；`/qa` reference 无顶层 `pk`，稳定身份只能用 `(metadata.id, metadata.chunk_index)`。若确有历史引用问题，应持久化 `file_id/source/version` 而非把 `order_num` 确定化（产品需求，需 TL 定性）。

**TL 裁决已执行（2026-10-27）：业务空结果改 200，500 只留依赖故障**
- `:797` 空间不存在 → `200 + reason=space_not_found`；`:824` 抽不到实体 → `200 + reason=no_entity_extracted`；`:843`/`:855` 无相关顶点 → `200 + reason=no_vertex_matched`；**`:795` 图检索异常保留 500**。
- 实测：`kb_5`（无图空间）→ `body code=200, reason=space_not_found, result_data=0`；`kb_9` 无实体查询 → `200, reason=no_entity_extracted`；正常题 → `200, n=5, identity_violations_count=0`。
- 语义：**200 = 业务结果（含合法空），500 = 依赖故障**，验收可一句断言"5xx 即失败"。

**仍不满足的一条（如实记）：global 的引用只到社区、不到 chunk**
global 返回的引用块是社区摘要（`order_num=gc-<community_id>`、`search_type=['graph_community']`），因此"每条关键结论可回链到**具体 chunk**"**目前做不到**——只能回到"哪个社区 + 社区携带的 source（首个成员文件）"。要满足，需要在社区摘要落库时持久化 `chunk_refs`（成员 chunk 的 pk/source/offset），引用卡片取第一条 chunk 而不是文件。这是 C15 的实质缺口，不能算通过。

**source 契约最终形态＝桶内相对对象键（C 2026-10-27 定，我撤回旧建议）**：`source = r12-rag/kb_9/…`，**不含 scheme、不含 host**。理由：前端 `components/CommonEditor/utils/tools.ts:149` 是 `` `/minio/${source}` ``，下绝对 URL 会拼成 `/minio/http://host/...` 必然打不开；presign 的 key 入参也正好是它。
我此前建议的"Java 判断已带 scheme 就不补 endPoint"（方案 b）**已撤回**——那是建立在"Java 一定加 host"的旧行为上；C 的 `toObjectKey()`（去掉 scheme+host / 前导斜杠 / `/minio/` 前缀 / 重复桶名）从根上让"双 host"不可能出现，分支更少。
**引用断言判据随之更新**：`source` 应满足「**无 scheme、无重复 host、以 `r12-rag/` 开头**」，而不是"单 host 绝对 URL"。jar 重启后旧证据里的绝对 URL 形态会变成相对键，**属预期契约变更，不是回归**；`platform/r12/qa/**` 的断言需 F 同步（我不改他人文件，已提醒 C 在重启通知里写明）。

**"图不产生新证据"是架构性的，不只是本环境没样本（A-data 补充，我实测量化）**
数据模型决定：图侧回取链是 `graph_entity/graph_triples.chunk_pk_list → ES _id → ES 文档`（`graph_fun_tool.get_document_chunk()` 用 `ed["_id"]`）。**图能返回的块，一定是 ES 里已存在的块**——它不生成新文本、新证据。因此图的可能价值只有两种：改变召回集合（牵出别路召不回的块）或提供实体/跳转路径（解释性）。
**可判定的"增益"判据（比"看起来更好"硬）**：存在 `search_type == ['graph']`（**仅图**）的块，且该块在关图对照中缺席。
**我按此判据量化了本轮全部证据**（33 个证据文件、96 条引用），且**必须分两层说，否则会被读成"图从未单独产出任何东西"**：
1. **chunk 级**：`search_type == ['graph']` 的块 = **0/96**（分布：`milvus+es` 20、`milvus+es+graph` 7、`milvus` 2 …）→ **图从未单独召回过任何原文块**；
2. **文档级**：`graph_community` **64 条是图独有的摘要型文档**（社区检测+摘要只能由图侧产出，ES/向量/全文不产生它），但它是**聚合产物、不携带新原文证据**。
两句合起来才是完整结论：**图能"独自产出摘要"，但不能"独自产出新原文"**。因此"图不产生新证据"仍成立，只是产出物类型不同；`仅图块` 判据依然正确（针对块），而 `graph_community` **不应被计为"增益"**——它不是原文证据。
要造出这种样本，需要：答案块与问题在字面上毫无重叠、向量也拉不开，但通过实体（问题里出现实体 X）与图连通；同时关图时它不该进 top_k。属 Loop 2 的样本设计。

**运行态样本（A-data 2026-10-27 在 19529 实测，佐证两层正交，不只是合成例）**：
`query_graph_data`（kb_9，"智造贷单户最高授信额度是多少"）返回中出现
`id_origin=pk_from_caller → identity_stability=stable_derived → provenance_quality=entity_content_recovered`
三值同时存在的记录 —— 即**身份层已稳定、出处层仍如实降级**，两层互不替代得到运行态证明；同批还有 `id_origin=None → unknown`（11:00 前写入、不回填）。`identity_violations=[] / count=0` 正常。

**AAA 题的错值归因（A 实测 + 我复现一致性）**：直连 19995（`enabled_graph=true, enabled_rerank=true, top_k=10`）命中的正文里就写着
「AAA级加30个基点，AA级加60个基点，A级加100个基点」→ **语料与召回都没问题，错在生成侧（faithfulness）**，不应记到 C14/C15 或回头查图召回。
**候选收缩是配置相关的质量风险（非缺陷）**：同一题在直连默认阈值（0.05）下 `documents=1`；而在 `/qa` configId=1（`score_threshold=0.001`）下我实测 `refs=3`。即"候选被 rerank+阈值收缩"确实存在，但收缩程度取决于配置，记录为质量风险、不判 FAIL。

**11:51 最终 local 复测（C 修完 `:478`、19995 单实例；证据 `R14-B-local-{on-final-cn-on,on-final-up-on,off-final-cn-off,off-final-up-off}-*.json`）**

| 用例 | http | refs | 含 graph 标记 | 答案 | 判定 |
|---|---|---|---|---|---|
| 纯中文 开图 | 200 | 3 | **3/3** | 最高额度 8000万（=V1） | 不 500 ✅、图进上下文 ✅ |
| 纯中文 关图 | 200 | 3 | 0/3 | 8000万（同源同值） | 基线 |
| 大写 AAA 开图 | **200**（改前 500） | 3 | 2/3 | "AAA 加 **100** 个基点" | 不 500 ✅、**数值错**（正解 30） |
| 大写 AAA 关图 | 200 | 3 | 0/3 | "AAA 加 **100** 个基点" | **同样的错** |

→ **两条硬结论**：
1. **大写 500 已消除**，图块稳定进入上下文（CN 用例 3/3 带 `graph`），B-3 的"不 500 + 图标记非空"判据成立；
2. **数值错误与图无关**：开图/关图给出完全相同的错值 `100`，引用块集合相同（同一 `product-loan.docx/V1` + `credit-ledger.xlsx/V0` + `product-intro.pptx/V1`），说明**图并入的块与向量/全文召回的是同一批块，没有带来新证据**；错值来自主链模型把「A级加100个基点」那一行套到 AAA（同文档 `AAA级加30个基点` 就在同一块里）。
因此本环境当前**无法证明"图带来了额外能力"**——只能证明"图通路已接通且贡献块有正文/来源"。要证明增益，需要构造"仅图可达、向量/全文召不回"的样本（例如跨文档多跳且字面无重合），这属后续 Loop 2 的样本设计，不在本轮。

**与 F 的 GRAPH_LOCAL PASS 并存、不矛盾（务必两条都写）**：F 在 11:34 洁净轮测得 `PASS [GRAPH_LOCAL] http=200 docs=5 graph_docs=5 有正文的图块=5`（`platform/r12/qa/evidence/R14-BASELINE-CLEAN-20261027T032432Z/`）——那是**直连 19995**，证明"图块进入上下文"。而本表是**用户入口 /qa**，证明"引用回链断裂"。因此能力矩阵应拆成两条：①local 图块进入上下文（算法侧，已 PASS）；②local 引用可核验（用户入口，FAIL）。合并成一条会得出相反的结论。
**断言位置区分（勿混）**：`identity_violations(_count)` 在 **19529 响应 `data` 顶层**（19995 自己组合响应，不会转发，故"19995 上拿不到"是设计而非丢失），可直接直连 19529 断言；`provenance_quality` / `identity_stability` 在每个块的 `metadata` 里，**才是**被 19995 白名单吃掉的那组，需等 C 补齐。
**offset 解析的两种处置（同行代码、结论相反）**：图分支 `multiple_retrieval.py:457-462` 解析失败只 `logger.info` 并照常 append（图块已降级安全，无需改）；FAQ/稠密分支 `:210-215` 解析失败是 **`break`**，直接丢掉整批后续命中（与 A 报的 `except→return` 同属"单条异常打断整批"，建议一并改成 `continue`/置 None）。

---

## 4. 诊断（本地 harness，仅用于定位原因，**不作为交付证据**）

同一份代码、同一模型端点（18092 qwen2.5-7b-instruct）、`temperature=0, seed=42`：

| 题 | 结果 | 说明 |
|---|---|---|
| G1 | 连续两次**完全一致且全对**（AAA→30、AA→60、AA→60，引用分别指向 `L0-3af0d4bc` 与 `L0-18625408`） | 说明"事实齐备时，链路能给出可回链的正确答案" |
| G2 | 数据源对；口径仍不完整 | 图里只有 `日均存款 -口径-> 跨账户`，缺「按业务日」「/天数」＝**抽取阶段丢事实**，不是 reduce 的错 |
| G3 | 三家评级+到期日全对，海川`到期日`答对、`评级`答"事实中未提及" | 海川评级 A 根本没进图（抽取缺失） |
| R2 | 正确拒答 | — |

命令与证据：`platform/r12/graph/global_dev.py`（只读，不写库）+ `/tmp/show_facts.py`（打印 reduce 实际看到的投影事实）。

---

## 5. 我改了什么（都在我的所有权内）

1. `graph_summary.py`：global 从"把 7 条摘要塞一个 prompt 做单次 reduce"改成
   **社区相关性选择 → 逐社区确定性事实投影（map）→ 汇总（reduce）**；
   reduce 前置硬约束（数字/日期/评级逐字来自事实、每条结论标 `[community_id]`、缺失写"事实中未提及"）；
   `temperature=0, seed=42` 让答案可复现（`graph_fun_tool.requests_llm` 新增可选参数，默认行为不变）。
2. `graph_summary.py`：`sources`（原文对象键）落库与读取时解析：`file_id → 文件名 → 实体反查原文内容` 三级；
   三级全失败就**不下发 source**（宁可空，不给错的绝对 URL——空则 Java 走自身回落，而不是拼出双 host）。
3. `graph_community.py`：修掉崩溃残留的半改（`uuid4()` 还在但 `import uuid` 已删），改为确定性 `community_id_for(namespace, level, members)`。
4. `retrieval_global_view.py`：`metadata.source` 下发**相对对象键**（修双 host 的直接改动）+ 修 `title` 的 `L1-L1-` 双前缀。
5. `graph_service.py`：回取的每个块都打**两层正交标注**（设计来自 A-data，2026-10-27）：
   - 出处层 `provenance_quality ∈ {exact_chunk, entity_content_recovered}`
   - 身份层 `identity_stability ∈ {stable_derived, unknown, invalid_mixture}`（由写入时落库的 `metadata.id_origin` 推出，图谱侧不重算哈希；`pending_deterministic` 已在 2026-10-27 收敛后退役）
   两层**不得互相替代**：`identity_stability=stable_derived` 只说明"是同一块"，**不能**把 `entity_content_recovered` 升格成精确出处。实测（19529）：旧文档 `id_origin_raw=None` → `identity_stability=unknown`、`provenance_quality=entity_content_recovered`，符合预期。
   另加**硬约束**：块级回取里出现 `derived_community` 说明 `chunk_pk_list` 与社区摘要混用，属数据错误——默认 loud-fail（`logger.error` + `identity_stability=invalid_mixture` + `identity_violation=derived_community_in_chunk_level`），设 `GRAPH_STRICT_ID_MIXTURE=1` 时直接抛错。合成样本四例已验证：`derived_chunk_index→stable_derived`、`pk_from_caller→stable_derived`（收敛后；收敛前为 `pending_deterministic`）、兜底块→`unknown`（出处层 `entity_content_recovered`）、`derived_community→invalid_mixture`，严格模式按预期抛错。
   **可断言性**（"只写日志的 loud 在自动化里等于静默"）：`query_graph_data` 响应 `data` 顶层同时返回
   `identity_violations: []` 与 `identity_violations_count: 0`（有违规时元素形如
   `{"pk":"4","chunk_pk_list_from":"graph_entity","reason":"derived_community_in_chunk_level","source":"…"}`），
   验收可直接断言 `identity_violations_count == 0`，不依赖抓日志、也不需要切环境变量。线上实测：`count=0`、`len==count`。
   **端到端可审计性前提（重要）**：以上两层标注**只在算法侧（19529 内部响应）成立**。`alg_retrieval_service/app/retrieval_fun_tool.py:460-495` 在融合阶段用**硬编码白名单**重建 `metadata`，`provenance_quality / identity_stability / recovered_by / recovered_entities / recovered_es_id / recovered_chunk_ref / id_origin` 以及 `title`、`search` 全部被丢弃（A-data 已定位并发 C）。因此：① 对账/取证要**直连 19529 或 ES**，不要从 19995 的返回里取；② 在 C 补齐白名单前，任何"检查这两个字段"的断言都**不能写在 19995/网关响应上**（必红）。
   接口纪律（四条）：① `code==200` 必含这两个键（可为空/0）；② `code!=200` 不必带；③ `count == len(list)` 恒成立——因此二者由 `_identity_violation_fields()` **唯一一处**产出，禁止各处自算；④ `GRAPH_STRICT_ID_MIXTURE` 只用于 CI/变异复验，不进生产判断。
   **事实核对**：`_query_graph_data` 里 `code=200` 的返回路径**只有 1 条**（即上述带键的最终返回）；三条早退（抽不到实体 / 图里无三元组 / 无相关顶点）实际返回的是 `code=500`，按第②条本就不带这两个键。

---

## 6. 仍未解决（需别人/需决策）

| # | 问题 | 归属 |
|---|---|---|
| 1 | 社区 `file_ids` 全为旧代次 → 引用回链断（F04 活体） | 需"解析完成 → 图抽取 → 社区重建"的编排顺序；A/C |
| 2 | 图抽取丢事实：海川「评级 A」、日均存款口径「按业务日/天数」都没进图 | 抽取质量（M1），需改 prompt/模型，属我但需确认再动 |
| 3 | 7B 模型在跨社区「属性→规则」映射上不稳定（同一问题 /qa 与本地 harness 出现不同答案） | 模型/解码；需固定更强模型或把映射做成确定性查表 |
| 4 | MinIO 无匿名读策略 → 浏览器打不开引用原文（已由 TL 决定改 presigned URL，C+D） | C/D |
| 5 | ~~社区摘要写入仍"只 insert 不 upsert"~~ → A 已改为整代替换（ES `_id`/Milvus `pk` 内容寻址 + 写后清旧代），实测两次 generate 幂等 | 已关闭（A） |
| 6 | **引用精度边界**：`recovered_by=entity_content` 是"按实体名匹配到的当前文档"，不保证是"产出该结论的那篇"。实测 `L0-a5a28a99`（T-CORE-001/日均存款/跨账户）解析到了 `docx-plain.docx` 而非 `docx-table.docx`（两篇都含"日均存款"）。已在 metadata 打 `provenance_quality=entity_content_recovered` + `recovered_chunk_ref{document_id,file_id,chunk_index,source}`，前端不得当精确引用渲染；精确 provenance 需图边/顶点携带稳定 doc 身份或落 mentions | 我（已加标注；精确化待 mentions） |
| 8 | **F04 尚未闭环（口径与行号均已更正）**：chunk 主键在**端到端**仍不稳定。根因链：`alg_doc_parse_service` 在交给索引层前给每个 chunk 写死随机 pk —— `server/controller.py:407/499/565`、`deepdoc/splitter/table.py:33/48/89/107`（均 `create_uuid()` = `uuid.uuid4().int`，已逐行核实）→ `metadata.pk` 非空 → 索引层 `index_fulltext_service/.../controller/es.py:192-194` 的 `if meta.get("pk"): ids = meta["pk"]` 命中"pk 优先" → 内容寻址分支（`:200-207`）不执行 → ES `_id` / Milvus `pk` 每代都变。因此**每次重解析 `chunk_pk_list` 仍会悬空**，我的"按实体内容回取"是当前唯一缓解手段。准确口径：写入层幂等 PASS／端到端不翻倍 PASS／**端到端代次稳定 FAIL**（`es_kb_service.py:217` 是 `update_doc()` 的"按 pk 先删再插"，不是本根因） | C（解析服务）；A 已把 7 处清单与改法发给 C |
| 7 | local 在 `refs=0` 时仍产出含数值的答案（轮 C：15/50/30 基点三次不同） | 问答主链（Java/检索），需"无召回即拒答" |
| 11 | **审计标注在检索层被白名单丢弃**：`alg_retrieval_service/app/retrieval_fun_tool.py:460-495` 硬编码重建 metadata，`provenance_quality/identity_stability/recovered_*/id_origin` 与 `title`、`search` 全丢 → 两层可审计**只到算法侧**，端到端（Java/前端）不可审计。阻塞项在检索层白名单。**最危险的不是"字段缺失"，而是白名单保留了 `search_type`/`source`、丢掉了出处质量**——外观"有 graph 标记"、质量不可判，容易产出假绿。断言纪律（A-data 建议，我采纳，并收敛成**三态**而不是二值）：**若 `search_type` 含 `graph` 但 metadata 无 `provenance_quality` → 记为 `UNVERIFIED_WHITELIST`/`BLOCKED` 并计数**：
① **不得判 PASS**（这是假绿，两边完全一致）；
② **也不建议直接判 FAIL** —— FAIL 在报告语义里是"产品缺陷"，会把人指到图实现上，而真因是检索层白名单；
③ 单列阻塞项并注明"被 `retrieval_fun_tool.py:455-495` 白名单阻塞，待 C 补齐"。
若 TL 的最终口径是"不可验证即 FAIL"，以 TL 为准，但**归因必须写清**——既不删失败凑 PASS，也不把阻塞项伪装成产品缺陷。另：`order_num = str(create_uuid())`（`:491`）**每请求随机**，不能当"引用 id 稳定/可跨请求对账"的证据 | C（检索层）；A 已定位并同步 F |
| 11b | 透传改法建议（给 C 的执行口径）：**黑名单排除** `base64`、`boxes`、`table_html_content`、`page_content`（本就是顶层）、`att_id`/`main_id`/`pic_url_list`；**保留** `offset`/`position`/`page_number`/`page_size`（前端定位用），可只在非空时透传。**不建议**用 `search_type` 借道（`graph_exact`/`graph_recovered`）——那是前端渲染引用标签的字段（D 的域），属"用契约换可用性"，等 C 补透传更稳 | C；D 若参与需评估标签语义 |
| 10 | **业务空结果被伪装成故障**：`query_graph_data` 三条早退（抽不到实体/无顶点）返回 `code=500`。而验收口径写"5xx 即失败"，任何"图上确实没答案"的合法查询都会被判失败。已先把三条早退的 data 形状统一（`result_data: []` + `reason ∈ {no_entity_extracted, no_vertex_matched}`），**返回码 200/500 的语义变更待 TL 裁**（改则需同步 F 的断言与 CAPABILITY-MATRIX 口径）。附带修掉一个真缺陷：其中两条原用 `documents_list` 键，调用方 `retrieval_graph` 取 `data.result_data` 会 KeyError → 被 except 吞掉 → **多知识库时静默跳过后续库** | 我（形状已修）；语义待 TL |
| 9 | `recovered_chunk_ref.id_origin` 采用**枚举**而非布尔，且取值来自**写入时落库的事实**（A 在 `controller/es.py:194-213` 判定、`:238` 落库 `metadata.id_origin`），图谱侧不重算哈希 → 不会出现"两边公式版本不一致、两个 id 都合法"的歧义。映射：`derived_chunk_index→derived_chunk_index`、`derived_parsed_chunk_index→derived_parsed_chunk_index`（**已不是预留占位**：A 已把派生序号改为"优先 `parsed_chunk_index`、缺失退回 `chunk_index`"，实测两分支都能产出，见 A-IDENTITY §6.1）、`derived_community→derived_community`、`pk_from_caller→pk_from_caller`（**已收敛，见下**）、`random/缺失→unknown`。
**命名约束（A-IDENTITY §6.0 第 3 条，已按 A 收紧后的版本落实）**——**三条分开，不能一刀切 lower**：
1. **ES 索引名**：必须 `lower()`（ES 硬限制不允许大写索引名）。`graph_summary._idx()` 已覆盖 `community_summary_<kb>`（写/删/读）、`file_id_to_names` 的索引、`_es_search` 的索引。
2. **Milvus 集合名**：**保持原样，不 lower**（`mv_collection = f"community_summary_{kb}"`）；只有"进派生种子"那一路用 lower。原因：chunk/table/faq 的写入方（`alg_doc_parse_service` → 19526）传的是原样 `primitive_name`，若社区摘要这类写入方单独把集合名 lower，同一个大写 KB 会分裂成 `_KB_17` 与 `_kb_17` 两个集合——表现为"摘要写进去了但读不到"，两边各自自洽、日志都成功，比"大小写不一致"隐蔽得多。真要统一必须**所有写入方一起改 + 迁移**。
3. **Nebula 图空间名 `g_<kb>`**：不 lower，仍用原始名。
现状 kb_1–kb_16 全小写，改动今天空转安全，但可避免"将来建了大写 KB，读侧静默查不到"这类极难归因的问题。
**「ES 7 / Milvus 65」不对称的完整因果链（三要素，缺一不可；A-data 归纳，我复核行号后修正）**：
1. **ES 每轮被清**：`platform/r12/bin/graph-refresh.sh:47` `curl -sS -X DELETE "$ES/community_summary_${KB_NAME}"`（文件共 53 行，**不是 :64**）→ 每次刷新先整删 ES 索引再重建，所以 ES 永远只有最后一批（7 条）。
2. **Milvus 每轮在追加**：写入侧当时是纯 insert + `pk=create_uuid()`（随机）→ 只增不减。
3. **Milvus 想删也删不掉**：`del_community` 的 Milvus 半边打到当时不存在的 `/del_collection` → 404 被当"已执行" → 集合从未被删。
→ 单说"只 insert 不 upsert"只能解释"Milvus 为什么涨"，**解释不了"ES 为什么不涨"**，而后者正是让人误判"去重已经做了"的原因。不对称的根因是：同一个"清理"动作，ES 半边真实生效、Milvus 半边一直是 404。

**三条清理路径语义不同，别混用**：① `graph-refresh.sh` 那条 `DELETE $ES/community_summary_*` = **只清 ES 的半清理**（历史遗留，制造不对称的地方；建议删掉或改调 `del_community`，属 E 的脚本）；② A 的写入层 = **整代替换**（不 drop，按 `community_id` 派生 pk 先删旧代再写新代，两侧同时收敛，日常重算用这条）；③ `del_community` = **两侧都删**（ES `del_index` + Milvus `del_collection`，现才真生效；用于整 KB 重建/回滚）。
**两条 id 生成路径并存且都合法（不是漂移）**：①解析链路＝解析服务算确定性 pk → 写入层"pk 优先"直接用（落 `pk_from_caller`）；②非解析链路＝写入层自行派生（落 `derived_*`）。两套公式现字段一致（都 `parsed_chunk_index` 优先 + `index_name.lower()`），但解析服务若 pop 掉 `parsed_chunk_index`，非解析链路会退回 `chunk_index` → 此时 `derived_chunk_index` 与 `derived_parsed_chunk_index` 两个值**同时合法存在**，枚举正好用于区分，不要当 bug。实测旧文档（本轮之前写入）无该字段 → `unknown`（`raw=None`），**不做回填**（回填＝重写文档＝新代，会让对账中的引用全部换代）。**收敛已执行（2026-10-27，A 的 e2e 四判据全部满足：C 已改且 12340 已重启 / 纯文本与含表格夹具各解析两次 id 完全相同 / 落库仍为 `pk_from_caller` / `parsed_chunk_index` 已保留到索引入参）**：`pk_from_caller` 已并入 `_STABLE_ID_ORIGINS` → `identity_stability=stable_derived`，枚举值由 `pk_from_caller_pending_deterministic` 收成 `pk_from_caller`。实测三例：`pk_from_caller→stable_derived`、`derived_parsed_chunk_index→stable_derived`、缺失→`unknown`。**注意范围**：只有重解析过的文档才带 `id_origin`，11:00 前写入的旧文档仍是 `unknown`（不回填，属设计）——不是数据不一致。精确回填路径仍优先，`entity_content_recovered` 不因身份层变稳而放宽；A 的"可收"判据为三条同时成立：C 已改且解析服务已重启、纯文本与含表格两类夹具各跑两次 id 完全相同、落库样本仍是 `pk_from_caller`（证明稳定来自解析侧而非写入层接管） | A（字段已上线）；C（解析侧确定化） |

## 7. 测量前提（复现须知）

- 语料：`r12-rag` 桶内 `kb_9/**` 共 17 个对象（8 篇文档 + parsed）；`table_chunks_kb_9` / `table_summary_kb_9` 承载表格正文。
- 社区：ES `community_summary_kb_9` 7 条（L0×6 + L1×1），Milvus 同名集合另有历史重复行。
- 复现命令：`platform/r12/venvs/graph/bin/python platform/r12/graph/r14_b_probe.py global --query "<题>" --tag <标签>`
- 证据目录：`platform/r12/graph/evidence/`
- **判定纪律**：任何"通过"必须能指回上面 §2 的原文行；指不回去的一律记不达标，不挑题。
