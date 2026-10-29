# 外部评审提示词 —— 图谱解析构造 / GraphRAG / 图谱社区

> 用途：把本文件整段交给外部专家智能体，作为评审任务的输入。
> 仓库：https://github.com/shaozhongfei001/llmke （public，匿名可读）
> 分支：`main`，基线 commit `a144020`

---

## 0. 你的角色与目标

你是 GraphRAG / 知识图谱工程的外部评审专家。请**只读代码与文档**（不要执行、不要改代码），对以下三项给出可落地的判断：

```
A. 图谱解析构造（文档 → chunk → 实体/关系抽取 → 建图）是否工程上站得住
B. GraphRAG（local 子图检索 / global 社区检索 / 路由）是否构成完整闭环
C. 图谱社区（检测 → 摘要 → 检索）是否只是"代码存在"，还是真的能支撑问答
```

**核心判断标准不是"能不能跑"，而是"能否交付给客户作为知识图谱能力"。**
本项目已出现过"接口 200、页面空白、数据为空"这类**静默失败**，请特别警惕"看起来有实现、实际没接入"的形态。

---

## 1. 仓库目录地图（按重要性排序，其余目录可跳过）

```
contracts/                                   ← 先看这里（合同层）
  schema/llmke-core.json                     GraphQueryRequest/Response/Evidence/Health
  api/llmke-graph.openapi.yaml               只有 /v1/graph/query 与 /v1/graph/kb/{id}/health
  ontology/                                  ⚠ 空目录（只有 .gitkeep）—— 重点评审对象

services/rag-alg/index_data_service/index_graph_service/     ← 图谱主战场（4298 行）
  graph_extract.py        (211)   抽取入口：generate_graph_relations / process_relation_response
  graph_types.py          (308)   实体/关系类型体系（硬编码，无合同依据）
  prompt_config.py        (82)    抽取 prompt
  base.py                 (92)    ES 读写、空间名、默认类型表
  graph_service.py        (928)   建图/写顶点写边/子图查询
  graph_fun_tool.py      (1093)   最大文件：图工具函数集合
  graph_community.py      (158)   社区检测：detect_communities / community_id_for
  graph_summary.py        (819)   社区摘要：generate_community / query_community / 写 ES
  graph_api_start.py      (122)   Flask 路由（10 个端点）
  utils.py                (263)

services/rag-alg/alg_retrieval_service/app/view/api/
  retrieval_global_view.py                   global 检索：调 /query_community → community_summary_list
  retrieval_local_view.py（同目录）           local 检索：子图

services/rag-java/rag-parent/rag-qa-service/.../AiServiceImpl.java
  ↑ global map-reduce 的真实实现位置（约 831 / 2220 / 2250 行）
  注意：只有 publicQuestion()（/qa/ai/question）有 global；
        publicQuestionRe()（/qa/ai/question_re，UI 实际调用）没有 → 假开关

services/rag-java/rag-parent/rag-index-service/.../
  KnowledgeBaseListAppServiceImpl.graphParse()   解析任务入队（file_parse_task）
  remote/GraphSearchClient.java                  Feign，仅查询侧

frontend/plateform/src/components/KnowledgeBaseZh/
  KnowledgeAnalyGraph/index.tsx    图谱增强页（任务列表 + 可视化入口）
  GraphCanvas.tsx                  自研 SVG 力导渲染（替代静默失败的 vendored 组件）
  GraphDetail.tsx                  节点/边详情

platform/r12/qa/                   证据与回归脚本（要看"怎么测的"，不看实现）
docs/reviews/R14-EXTERNAL-REVIEW-20261029.md   本批次的交付现状/契约缺口/待评审问题
docs/SDD-ENGINEERING.md            目标状态（含 generation 测量切片）
```

**可跳过**：`services/rag-alg/alg_doc_parse_service/deepdoc`（第三方 PDF 解析）、
`services/rag-alg/alg_llm_inference_service`（推理封装）、`platform/r12/dist`、`node_modules`。

---

## 2. 建议阅读顺序（4 轮，每轮给出"看什么 / 判断什么"）

### 第 1 轮：合同层（先看，否则后面无法判断"偏离"）

```
读  contracts/schema/llmke-core.json
读  contracts/api/llmke-graph.openapi.yaml
读  contracts/ontology/            （注意：是空的）
读  docs/SDD-ENGINEERING.md 中 generation / evidence / 测量切片相关段
```

**请判断**：

```
1. 合同要求的 required 字段（generation、GraphEvidence 的 evidence_id/node_ids/edge_ids/source_refs）
   在实现里有多少落地？（已知：0 落地，见第 3 节事实表）
2. 本体合同缺失的后果有多大？是否足以判定"类型体系无依据"？
3. 合同只覆盖 query/health，不覆盖"解析/抽取/社区生成"——这是合理边界还是重大缺口？
```

### 第 2 轮：抽取构造（最容易出质量问题的地方）

```
读  graph_extract.py          重点：generate_graph_relations / process_relation_response
读  graph_types.py            重点：类型表是什么、从哪来、默认值是什么
读  base.py                   重点：entity_types 默认值与"未指定"的判定
读  prompt_config.py          重点：prompt 是否给了类型约束、是否要求输出 JSON、失败如何降级
读  graph_service.py 中写入顶点的部分（属性有哪些、file_id 怎么来）
```

**请判断**：

```
1. 抽取是"整篇一次 LLM"还是"按 chunk 分批 + 合并"？跨 chunk 的同一实体如何归一？
2. 实体归一（别名/同义/大小写/全半角）是否有稳定策略？只靠停用词过滤是否过粗？
3. 关系方向如何确定？_orient() 的启发式是否可靠（会不会把"A 是 B 的客户"反向）？
4. 类型体系（16 类）是否覆盖银行业务？分类落"其他"的比例如何被监控？
5. 抽取失败（LLM 返回非 JSON / 超时 / 0 三元组）如何降级？是否会把"失败"记成"成功但空图"？
```

**已知历史缺陷（本批次已修，请复核修法是否彻底）**：

```
① 类型表默认值是通用 NER 8 类（人/机构/位置/时间/角色/疾病/药品/项目）
   → 修法：默认 None；显式传通用 8 类也视为"未指定"→ 升级业务类型表
② 停用词表含"客户/公司/企业/产品/借款人"→ 业务主实体被整条丢弃
   → 修法：只保留结构性词（下表/合计/单位/序号）
③ 金额 2,983,333.33 的逗号切断三元组内部键 → KeyError
   → 修法：内部键统一 \x1f，展示仍用逗号
④ 空间名传中文展示名 → ES 索引 kb_9 查不到 → 抽取拿不到文本
   → 修法：Java 传 primitiveName
请评估：这四条修法是否只是"打补丁"，是否存在同类未覆盖项（如日期、百分比、带单位的数字）。
```

### 第 3 轮：建图与查询

```
读  graph_service.py    重点：create_space / 顶点边 schema / batch 写入 / 子图查询
读  graph_fun_tool.py   重点：1093 行里哪些是"一次性脚本"混进了运行时代码
读  graph_api_start.py  重点：10 个 Flask 端点的入参校验与错误返回
```

**请判断**：

```
1. 空间生命周期：g_kb_9 是知识库级，没有代次分区。V0/V1 混图是否可接受？
2. 写入幂等性：重复解析同一文件会不会产生重复顶点/边？靠什么去重？
3. 图谱查询的边界（跳数、节点上限、超时）是否有硬约束？会不会在大图上拖死服务？
4. graph_fun_tool.py 职责是否过载（1093 行 + 混杂）？是否应拆分？
```

### 第 4 轮：社区与 GraphRAG 闭环（本次评审重点）

```
读  graph_community.py   全部 158 行
     detect_communities(g, resolution=1.0, min_community_size=3, max_level=1)
     community_id_for(namespace, level, members)
     load_graph / community_triples / community_file_ids
读  graph_summary.py     重点：
     generate_community(payload)          社区 → 摘要 → 写 ES
     write_summary_indexes()              索引名 community_summary_{kb}
     resolve_sources_by_entities / resolve_chunk_refs   摘要回指原文
     query_community / _select_communities / _community_score
读  retrieval_global_view.py   重点：/query_community 的入参、社区结果如何变成检索结果
读  AiServiceImpl.java 的 global 分支（831 / 2220 / 2250 附近）
读  frontend/.../KnowledgeAnalyGraph/index.tsx  重点：这一页到底是"任务列表"还是"图谱视图"
```

**请判断**：

```
1. 社区检测用的是什么算法（Louvain？）、是否有层级（max_level=1 意味着只有 L0/L1？）
   resolution=1.0、min_community_size=3 这两个参数对银⾏业务语料是否合理？
2. 社区摘要的输入是"成员实体的三元组 + chunk 引用"吗？摘要是"事实罗列"还是"叙述式报告"？
   能否直接用于回答"这家公司的整体授信策略是什么"这类全局问题？
3. global 路由：_select_communities 按 _community_score + 2-gram 匹配打分，
   这种朴素匹配在多轮对话/同义改写下的召回是否够用？是否需要向量召回？
4. local / global 的路由决策在哪一层？现在是"用户手动开关"，缺失自动路由是否算缺陷？
5. 社区是"全量重建"还是增量？摘要与图数据不一致时如何发现（没有版本号的话）？
6. 社区摘要如何回指原文（chunk）？能否满足"引用可核验"？
```

---

## 3. 已核实事实（2026-10-29 本机实测，请勿重复挖，直接作为前提）

### 3.1 图谱链路达成度矩阵

| 能力 | Python 实现 | Java 接入 | UI 入口 | 实测数据 | 结论 |
|---|---|---|---|---|---|
| 文档解析 → chunk | ✅ | ✅ | ✅ | kb_9 正常 | 通 |
| 三元组抽取 | ✅ graph_extract | ✅ 任务入队 | ✅「图谱解析」按钮 | gps=3 成功 | 通 |
| 建图（Nebula） | ✅ graph_service | ✅ | — | g_kb_9 = 89 节点 / 62 关系 | 通 |
| 子图查询（local） | ✅ | ✅ GraphSearchClient | ✅ | 51 节点 / 50 边渲染 | 通 |
| **社区检测** | ✅ graph_community（158 行） | ❌ **零调用** | ❌ 无 | 未验证 | **仅代码存在** |
| **社区摘要** | ✅ generate_community | ❌ **零调用** | ❌ 无 | ES `community_summary_kb_9` = **7 条**（手工脚本生成） | **旁路数据** |
| **global 检索** | ✅ retrieval_global_view → /query_community | ⚠ 仅 `/qa/ai/question` | ❌ UI 的 `question_re` 未实现 → **假开关** | 未做端到端 | **半通** |
| Evidence 回指 | ❌ | ❌ | ❌ | — | 契约 required 未落地 |
| generation 隔离 | ❌ | ❌ | ❌ | 空间为 g_kb_9，无代次 | 契约 required 未落地 |

### 3.2 关键代码事实（grep 结果，可直接引用）

```
Java 全仓 grep "query_community|generate_community" → 0 命中
  ⇒ 社区能力从未进入产品调用链，只有 Python 端点 + QA 脚本在用

UI 调用 /qa/ai/question_re → publicQuestionRe() 通篇无 global 处理
只有 /qa/ai/question → publicQuestion() 有 global map-reduce
  ⇒ 用户勾选 global 的请求，服务端这条路径不读该参数

ES 索引 community_summary_kb_9 有 7 条文档（31.3kb）
  ⇒ 社区摘要"能生成"，但生成入口是手工/脚本，不是产品流程
```

### 3.3 已知未修（评审时请纳入风险）

```
① 图服务 Nebula 会话池 broken pipe 后不自愈（500 → 重启服务 → 200）
② 历史已解析行的 edgeCount 恒 0（边属性 file_id 为空，需重建空间）
③ 旁路脚本建的图与 App 解析的图混在同一空间，无 provenance 字段
④ 空间名/ES 索引名/权限分桶三套标识靠人肉一致 → 已因此产生 4 次故障
⑤ 问答出现"语义反转"：把"信用方式分项限额 1000 万"答成"最高额度 1000 万"
   （原文为 8000 万总额中该方式不超过 1000 万），且失败前已吐出半句
```

---

## 4. 请重点回答的 10 个问题（按优先级）

| # | 问题 | 期望的结论形态 |
|---|---|---|
| G1 | `contracts/ontology/` 为空，是否构成"类型体系无合同依据"的阻断级缺陷？ | 阻断 / 可先放行 |
| G2 | 抽取按 chunk 分批时，跨 chunk 实体归一的正确做法是什么？当前实现属于哪一档？ | 现状评级 + 目标做法 |
| G3 | 停用词只保留"结构性词"，是否会引入噪声（下表/合计类实体）？边界在哪？ | 具体规则建议 |
| G4 | `_orient()` 的关系方向启发式，在银行业务语料上的失效模式有哪些？ | 失效清单 |
| G5 | 社区检测参数（resolution=1.0 / min_size=3 / max_level=1）是否合理？ | 给出建议取值与依据 |
| G6 | 社区摘要应为"事实罗列"还是"叙述式报告"？现有 7 条摘要是否达到可用于 global 问答的质量？ | 质量判定 |
| G7 | global 检索的 2-gram 打分是否要替换为向量召回？代价与收益？ | 选型建议 |
| G8 | local / global 是否应自动路由？若应，判据放在检索层还是生成层？ | 架构建议 |
| G9 | 社区何时重建（每次解析 / 定时 / 手动）？增量可行吗？ | 策略建议 |
| G10 | 社区摘要如何回指原始 chunk 以满足"引用可核验"？ | 最小可行设计 |

---

## 5. 输出格式要求

请按以下结构输出，每条结论必须能指到**文件:行**或**具体函数**：

```
A. 总体判定
   A1 能否作为"知识图谱能力"交付（可以 / 有条件 / 不可以）+ 一句话理由
   A2 三个最严重的缺陷（按影响排序，每个给证据位置）

B. 分项评审（逐条对应 G1–G10）
   Bn 【结论】… 【证据】file:line / 函数名 … 【风险】… 【建议】…

C. 与合同的偏离清单
   表格：合同条款 | 实现现状 | 偏离级别（阻断/严重/一般）| 修复代价

D. 不该做的事（你认为当前方案里"做了但方向错"的部分）

E. 若只能改三处，改哪三处（给顺序与理由）
```

**约束**：

```
· 不要相信 README 与代码一致——本项目已出现"文档写了、代码没实现"
· 不要把"接口返回 200"当作"功能可用"——已有多例 200 + 空数据
· 不要评价前端视觉，除非它阻碍了能力验证
· 指出问题时请区分「实现缺陷」与「契约缺失」，这两类修复责任不同
```

---

## 6. 一句话背景（帮助你理解为什么这些问题重要）

项目此前经历过一次"看起来全绿、实际用户一点就报错"的验收：
页面能点、开关能开、接口能 200，但**开关背后的路径没实现、列表背后的数据不存在、组件失败不报错**。
所以本次评审的价值不在"找出 bug"，而在**判断这套 GraphRAG 的构造是否真的成立**。
