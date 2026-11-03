# 给 CodeBuddy TL 的分工派任务提示词（深审自证批次 T-A1–T-A4）

你是本批次的执行负责人（TL），负责**实际修改代码并产出自证证据**，供独立评审方复核。
评审方只读、不复改你的代码；你产出的每条证据都会被评审方在本机复跑，**输出不一致即打回**。

不能以计划、盘点或“已阅读”结束；阶段汇报后继续，不询问“是否继续”。

## 1. 总目标（固定范围，不扩大）

完成 `docs/v2-tasks/TASKS.yaml` 中 T-A1..T-A4 四项自证：

- T-A1（D7/P0-1）：点引用能**打开原文并高亮 locator**（真实上传文档）。
- T-A2（D6）：**纯图 route** 真实生效（seed 实体 + 无 rerank 兜底的 GRAPH trace + 禁用对照）。
- T-A3（D4）：community.json 的输入**逐跳可溯源到 HippoRAG 抽取事实**。
- T-A4（B01）：r12 复跑 + 变异/基线复演 + 合入 V2 的迁移方案。

## 2. 导读：按顺序读（全部为完整绝对路径）

### 2.1 必读（先读这 6 个）

1. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/TASKBOOK.md`（入口与切换条件）
2. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/TASKS.yaml`（T-A1..T-A4 状态，唯一台账）
3. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/PROMPT-TL-START.md`（D0–D10 验收判据，本批次是它的收口子集）
4. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/REVIEW-AUDIT-DISPATCH.md`（本批次任务与评审方 R1–R4 对照表）
5. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/CHECKPOINT.md`（当前进展与“不得重复执行”清单）
6. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/ENV.md`（环境位置与变量名；口令不抄值）

### 2.2 评审依据（评审方结论，你必须对着这些缺口修）

7. `/home/szf/data/dsh/graph-rag/LLMKE_ee72f79_独立评审_20261103.md`（P0-1 打开原文、P0-2 B01、P1 系列）
8. `/home/szf/data/dsh/graph-rag/LLMKE_长程任务目标达成度核对_20261103.md`（D4/D5/D6 部分达到、D7/D8/D9/D10 未达到）
9. `/home/szf/data/dsh/graph-rag/LLMKE_深审分工与进展_20261103.md`（R2 已发现：api.py query 未传 seeds）

### 2.3 按任务读（T-A1）

10. `/home/szf/data/dev/llmke-v2/services/rag-java/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/application/service/impl/AiServiceImpl.java`
    - `:381-404` question_re global 分支（缺口：reference 不做 file_id→convertedFilePath 反查）
    - `:657` publicQuestion 方法起、`:728-759` R13-GRAPH-11 反查逻辑（可复用）
    - `:3055` retrieveDocs4Plat（无 global 分支，仅记录）
11. `/home/szf/data/dev/llmke-v2/frontend/plateform/src/pages/HomePage/IntelligentChat/AIChat/index.tsx`（`:245-280` 自动滚动、`:340,420,435-436` convertedFilePath/filePath 消费、`:552` v2-chat-shell）
12. `/home/szf/data/dev/llmke-v2/frontend/plateform/src/pages/HomePage/IntelligentChat/AIChat/chat-shell.css`
13. `/home/szf/data/dev/delivery/review-ee72f79/03_补充材料/PAGE-CITATION-E2E-20261103.md`（页面实测边界）

### 2.4 按任务读（T-A2）

14. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/api.py`（`:232-249` query 未传 seeds）
15. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/engine_hipporag.py`（`:114-193` trace 与 rerank 兜底）
16. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/merged_rerank.py`（route 编排）
17. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/capabilities.py`（`:33-37` retrieve_graph_route NOT_VERIFIED）

### 2.5 按任务读（T-A3）

18. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/global_report.py`（`:292` 写 community.json、`:149-214` assemble_answer）
19. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/community.py`
20. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/graph_engine_adapter/export.py`
21. `/home/szf/data/dev/llmke-v2/docs/design/unified-documents-v2/EVIDENCE-COMMUNITY-REPORT-20261031.md`（旧口径 29 事实/5 社区）
22. `/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/S3-retrieval-shim.md`（新口径 68/72 事实，§7.3 可复现性）

### 2.6 按任务读（T-A4）

23. `/home/szf/data/dev/delivery/review-ee72f79/03_补充材料/B01-r12-0bac08a.patch`（修复本体，r12 轨）
24. `/home/szf/data/dev/delivery/review-ee72f79/03_补充材料/B01-evidence-100e261.md`（28 passed/变异 3 组/基线 20 failed 归因）
25. r12 工作树：`/home/szf/data/dev/llmke-r12`（HEAD 应含 `0bac08a`、`100e261`）
    - `/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service/graph_types.py`
    - `/home/szf/data/dev/llmke-r12/tests/test_graph_direction_b01.py`
26. `/home/szf/data/dev/llmke-v2/services/rag-alg/index_data_service/index_graph_service/graph_types.py`（`:283-289` V2 树仍是旧 sorted() 实现）
27. `/home/szf/data/dev/llmke-v2/docs/design/unified-documents-v2/06_STANDARD_INPUT_AND_GRAPH_ENGINE.md`（`:126` §6.1 已接线/不宣称、§7 尚缺）

### 2.7 通用规则

28. `/home/szf/data/dev/llmke-v2/AI_GUIDE.md`
29. `/home/szf/data/dev/llmke-v2/docs/policies/AGENT-RULES.yaml`
30. `/home/szf/data/dev/llmke-v2/.codebuddy/rules/v2-task/RULE.mdc`

## 3. 每项任务的退出条件与禁止

### T-A1（D7 打开原文）
- 改：question_re global 分支补 file_id→convertedFilePath 反查（复用 R13-GRAPH-11），必要时前端补 drawer 打开逻辑。
- 退出条件：真实上传文档（非 F001–F012/999010）在页面“点引用→抽屉→打开原文→高亮 locator”全程成立；截图+日志+代码 diff 进 `/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/A1-open-original.md`。
- 禁止：用演示语料；“reference 有数据”冒充“可打开”；只改前端不改 Java 反查。

### T-A2（D6 纯图 route）
- 改：`api.py` 的 QueryRequest 增加/接通 seed（`query_seed_recognition`→`retrieve(seeds=…)`）。
- 退出条件：同语料两组对照——A 组 seed 命中、`graph_calls>0`、`rerank_fallback=false`、命中来自图检索；B 组禁用图→`DENSE_FALLBACK`+原因；trace 原样贴入 `/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/A2-pure-graph-route.md`；随后把 `capabilities.retrieve_graph_route` 升 VERIFIED（附证据路径与 sha256）或保持 NOT_VERIFIED 并写明缺项。
- 禁止：用 rerank 兜底后的命中当纯图证据；把 DENSE_FALLBACK 标成 GRAPH。

### T-A3（D4 社区同源）
- 产：一条事实从 openie 输出→`normalize.build_store` 断言→`export_facts`→`build_communities`→`community.json` 的逐跳溯源脚本+输出；孤点保留；引用校验 0 失效；同快照两次 community.json sha256 相同。写入 `/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/A3-community-lineage.md`。
- 禁止：只贴文档不贴命令；用 legacy 图服务数据冒充；用 HippoRAG 内部相似图当社区。

### T-A4（B01）
- 复跑（r12 工作树）：`cd /home/szf/data/dev/llmke-r12 && python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q`（应为 28 passed）；
  变异复演 3 组（复现 B01 的 sorted() 版本应约 23 failed）；基线 20 failed 在干净 worktree 复演。
- 产：合入 V2 的迁移方案（`0bac08a` 合入路径、存量 `g_kb_9` 清库重写范围/顺序/回滚）。写入 `/home/szf/data/dev/llmke-v2/docs/v2-tasks/evidence/A4-b01-rerun.md`。
- 禁止：改 `/home/szf/data/dev/llmke-v2/docs/r15/` 下任何文件；动运行中服务；推远端。

## 4. 证据纪律（评审方会逐条复跑）

- 每条结论 = 命令 + 真实输出 + 绝对路径:行号；找不到就写 UNVERIFIED，不许补理由。
- `TASKS.yaml` state 只允许 TODO/DOING/BLOCKED/VERIFIED；VERIFIED 必须填 evidence 路径。
- 评审方标准：你贴的每条命令，评审方在本机复跑输出一致才通过；不一致即打回并注明断点。
- 单文件单写者；先改合同源再 `make contract-all`；不 reset/clean/checkout、不推远端、不发布。
- 口令只从 ENV.md 指定位置读取，不抄值、不入仓、不入日志。

## 5. 接续与检查点

- 每完成一项：更新 `/home/szf/data/dev/llmke-v2/docs/v2-tasks/TASKS.yaml`（state+evidence）、
  追加 `/home/szf/data/dev/llmke-v2/docs/v2-tasks/CHECKPOINT.md`（下一精确动作）。
- 单项阻塞只影响依赖项，转做其余任务；只有真实外部阻塞才停并写恢复条件。

## 6. 现在开始

第一步：三工作树 `git status`（`/home/szf/data/dev/llmke-v2`、`/home/szf/data/dev/llmke-r12`、`/home/szf/data/dev/llmke`）+ 读第 2.1 节 6 个文件，然后按 T-A4（不依赖代码修改，可先交）→ T-A2 → T-A1 → T-A3 的顺序开工。不要以复述本文件结束。
