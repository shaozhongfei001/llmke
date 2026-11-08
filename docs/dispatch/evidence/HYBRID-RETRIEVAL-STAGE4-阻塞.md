# HybridRetrieval 阶段 4 现状与阻塞登记（下线 V1 冗余）

日期：2026-11-06。loop：HYBRID-RETRIEVAL-1。执行身份：tech-lead（TL）。

## 结论：下线 Nebula/19529 的前提不满足，暂缓破坏性下线

红线「阶段 4 下线前必须先确认 global 已切到 18094」在 **Java 侧已满足**，但 **19995 侧与建图侧未切**，
直接下线会断链。已如实登记，不做破坏性下线。

## 只读确认结果（实测）

| 链路 | 现状 |
|---|---|
| Java 检索 | `search-docs-url → 19532 → 18094 /v2/graph/query` ✅ 已切 V2，不依赖 Nebula |
| Java global | `search-docs-global-url → 19532 → 18094 /v2/graph/global`（community.json）✅ 已切 V2 |
| 18094 global | 可回答：「授信额度」命中 c-2/c-3，答「北方重工配件厂 授信额度 2000 万（来源 329）」✅ |
| 19995 global | 仍优先走 19529 `/query_community`（Nebula Louvain），18094 仅为回退 ⚠️ 未切 |
| Java 建图 generate-graph | `→ 19531`（legacy_shim），**19531 未监听** ⚠️ 断链 |
| Java 建图 del_space/del_doc_entity/generate_community | `→ 19529`（legacy Nebula）⚠️ 仍依赖 Nebula |
| Nebula | graphd/storaged/metad 三容器在运行 |
| community_summary_kb_9 | ES 索引仍存在（11 doc） |

## 阻塞（3 处，都是「下线」的前置未完成）

1. **19995 global 未切 18094**：`retrieval_global_view.py` 仍以 19529 `query_community` 为主、
   18094 `/v2/graph/query`（图检索）为回退，尚未改用 18094 `/v2/graph/global`（community.json）。
   19529 日志 19:29 仍有 `query_community` 调用（kb_1004 global）。

2. **建图 generate-graph 断链**：Java `generate-graph.url → 19531`，但 19531（legacy_shim）
   无 algctl/systemd 启动配置，当前未监听。

3. **建图 del_space/del_doc_entity/generate_community 仍依赖 19529**：Java `rag-index-service`
   配置这四项仍指向 19529（legacy Nebula），未切 18094。停 19529/Nebula 会断这些写侧链路。

## 完整切换方案（需跨栈协调，逐项可回滚）

| 步骤 | 动作 | 风险 |
|---|---|---|
| A ✅ 已完成 | 19995 global 改 `retrieval_global_view.py`：主链路 19529 → 18094 `/v2/graph/global`，回退改 `/v2/graph/query` | 低（Python，可回滚） |
| B ✅ 已完成 | 启动 19531 legacy_shim（独立 nohup 启动，`LLMKE_V2_ROOT=/tmp/tl-a2-root`），修复 generate-graph 断链 | 低（启动服务） |
| C ✅ 已完成 | 改 Java `rag-index-service`：del_space/del_doc_entity/generate_community 留空（空值守卫）+ generate-graph 切 19531，编译 + 重启 | 中（已重启，服务正常） |
| D ✅ 已完成 | v2 配置 `search-docs-url` 已是 19995（三路融合），无需额外改动 | — |
| E | 验证全链路（建图 + 检索 + global）无 19529/Nebula 依赖 | 低 |
| F ✅ 已完成 | 下线 Nebula×3、19529、19532、`community_summary_kb_9`、Milvus 旧集合 kb_ve38vlwzwf* | 已执行（Owner 授权） |

## A+B 已推进（2026-11-06）

- A：`retrieval_global_view.py` 主链路切 18094 `/v2/graph/global`，新增 `_convert_global_citations`
  （citations → documents_list）。已部署 r12 + 重启 19995。验证：19995 global 命中「授信额度」
  返回 3 条引用（file_id=329/330），19529 日志无新 query_community 调用。
- B：19531 legacy_shim 独立启动（hipporag-toolenv python，cwd=v2 index_data_service，
  `LLMKE_V2_ROOT=/tmp/tl-a2-root` 与 18094 对齐）。health 正常，`generate_triple_data` 已接、
  其余（generate_community/del_space/del_doc_entity）明确 501。

## 检索质量回归修复（2026-11-06，用户实测反馈）

用户实测「英文 How should I grow tomatoes」返回碎片、中文返回连贯，暴露 3 个 global 端点回归，已全部修复：

| 问题 | 根因 | 修复 |
|---|---|---|
| 英文 query 返回中文 | qwen 语言跟随不稳，prompt 未显式指定 | `_summarize_v2_docs` prompt 显式指定输出语言 |
| 碎片拼接、过程型问题零散 | 18094 `assemble_answer` 只拼 fact，丢步骤细节 | global 命中时补充图检索原文一起生成 |
| 资料没有却编造 | LLM 对「无直接资料」倾向推测 | prompt 强制「未提及就明说，禁止推测」 |

修复后 15+ 中英文用例（过程型/事实型/清单型/数值型/时间型/否定型/跨库）全部符合预期：
- 英文→英文、中文→中文；过程型返回详细步骤；事实型准确；无资料诚实回答「资料中未提及」。

## F 执行结果（2026-11-06，Owner 已授权「数据可全面清理」）

按序下线，每步停后验证主链路 + global 均正常：

| # | 动作 | 结果 |
|---|---|---|
| 1 | 停 19532 retrieval_shim（pid 1808768） | ✅ 已停，19995 local/global 正常 |
| 2 | 停 19529 legacy Nebula 图服务（pid 780844） | ✅ 已停，19995 local/global 正常 |
| 3 | 停 Nebula×3 容器（graphd/storaged/metad） | ✅ Exited(0)，19669/19559/19779 已释放 |
| 4 | 删 ES 索引 community_summary_kb_9 | ✅ acknowledged，global 走 18094 community.json 正常 |
| 5 | 删 Milvus 旧集合 kb_ve38vlwzwf/_entity/_triple | ✅ data:[]，19995 检索正常 |

下线后保留服务健康：19995/19531/18094/19200/19527 均在监听；19531（legacy_shim 建图）、
18094（HippoRAG global）健康。主链路（19995 三路融合）+ global（18094 community.json）回归通过。

## 历史决策记录（F 执行前，已闭环）

- 步骤 C/D 已重启 Java 生产服务（rag-index-service / rag-qa-service），服务正常。
- 步骤 F 已于 Owner 授权「数据可以全面清理」后执行完毕，见上表。
- 步骤 D 已将 Java 检索切回「三路融合（19995）」，语义变化已由检索质量回归验证。
