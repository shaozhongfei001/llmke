# NEXT 检查点（持续模式）

> 恢复会话时按本文件顺序读：本文件 → `docs/r15/V2-CONTINUOUS-TASK.md`（主任务书）
> → `docs/design/unified-documents-v2/IMPLEMENTATION-QUEUE-V2.md` → 双仓库实际 `git status`。

## 0. 持续实施检查点（2026-10-31 更新）

```
任务书路径/版本：docs/r15/V2-CONTINUOUS-TASK.md（2026-10-30，sha256 697649d1b734…3309）
双仓库：llmke-v2 @ design/v2-input-engine-adoption-20261030-2101（干净）
        doc2md    @ fix/017-ir-emission-wiring（干净，main 未动）
续跑机制：宿主无 Goal/Stop hook、无 codebuddy CLI 可注册 → 已启用本地 Automation
        id=llmke-v2（每小时，ACTIVE，读本文件+任务书续跑）；
        跨进程自动恢复 = MANUAL_RESUME_ONLY（无宿主原生恢复入口，不声称无人值守）
当前环境：llmke 工具 venv（3.10.12，合同检查）；doc2md 工具 venv（3.11.7 + markitdown 0.1.9
        + openpyxl）；真实模型：llmke 栈 18092 端点；doc2md 只用 markitdown/原生读取器
已验证能力（本候选，非门禁）：合同生成联动、ParseArtifact 仓、doc2md 适配器、
        DOCX/XLSX 原生表格进 IR、快照投影（正文/表格双通道）、线上只读对照、
        摄取集成层 + 解析任务影子钩子（默认不动作）、临时索引/集合回环（v2rt_* 写读删，已清理）、
        向量通道（真实 bge-m3 + 克隆 _kb_9 schema）recall@1 全中、
        投影载荷按生产 33 字段补齐（10 必填给值、13 恒空显式空、版面占位并标 unavailable）
当前失败/根因：无阻断性失败；既有 5 项 doc2md CLI-help 失败（typer 版本）待修
活作业：无
真实外部阻塞：HippoRAG 版本/离线依赖（U-03）；真实生产 DDL 与恢复副本权限（U-07）；
        P0/正式门禁/独立QA/发布授权（保持真实状态）
下一精确动作（按任务书 A→B→C→D→Q）：
  B1 状态：隔离候选写入/回退已成立（v2cand_*，基线未变）；真实上传被 D-01 阻断（缺 libreoffice-writer，需 root）
  C1 状态：hipporag 2.0.0a4 已装成并真跑 index/retrieve（本地 LLM+embedding）；66 个真实块
     197 实体/253 事实、跨文件命中可回指；引擎按 chunk-md5(text) 合并、SourceMap 保多来源；
     已修引擎持久化目录污染（沿用旧 save_dir 会捞出历史 chunk）；社区/断网 wheelhouse 未做
  D-01b 状态：**已闭环**——系统上下文解析模型 + 按 create_by 反查 user_id 并写入 param
     + 纯文本跳过转换；候选 jar（必须 -am 构建）已接管 18082；file 999014 走通
     上传→调度→/parse→ES+Milvus→回调置 SUCESS（task=4、error 空）
     边界：无 UserContext 且 create_by 为空的纯 API 上传仍会 userId=0 判"用户不存在"
  A2 状态：magic-pdf 1.3.12 可装、GPU 6GB 可用；HF 不可达、ModelScope 可达（权重改走此源）；未装未跑
  B1 状态补充：真实检索服务（19995）可查候选快照（search_policy=2），两臂返回同一表正文；
     载荷已补 metadata.pk；候选命名须与检索拼名规则一致（已加 --retrieval-compatible）
  B1 已完成：读路径切换（legacy/snapshot，按库灰度、可回退，开关已登记）；D-05 删除漏清理已修并验证
  B1/C1 下一步：C1 扩到 333/329 全量与跨文档路径；社区/global 仍未消费真实产物
  B1 已完成部分：ingest_pipeline（adapter→commit→project 集成层，三档开关，shadow 禁止写索引）
     + controller 影子钩子（默认三条 env 不满足即不动作；失败不影响解析任务）
  A2 MinerU/OCR 路线并行准备（扫描 PDF），不阻塞原生 Office
  C1 选定并固定 HippoRAG 版本，独立环境安装 + native_id→input_unit→SourceRef 映射
  D1 取真实 DDL（只导结构）→ 隔离恢复副本 → 迁移草案验证 parse_artifact_id
  Q1 固定真实样本与失败反例（333/329 已有；补新上传文件）
成功后：提交并更新本文件；失败后：先判 producer/投影/消费者/数据/运行版本哪一层
副作用/回退：doc2md dev 库 gits_ke 新增 3 条 content/instance（未删改既有）；
        产物在 /tmp/doc2md-ws（可重建）；未改任何线上索引
暂停与授权：用户已书面授权持续实施；P0/QA/发布语义不变
```

---


## 1. 现场

| 项 | 值 |
|---|---|
| 工作树 | `~/data/dev/llmke-v2`（仓外独立工作树，与 `llmke`、`llmke-r12` 并列） |
| 分支 | `design/v2-input-engine-adoption-20261030-2101` |
| 起点 HEAD | `419a87d`（= 补丁基线 `3fea44e` + 1 个 handoff 提交） |
| 主仓 `~/data/dev/llmke` | 未触碰（HEAD `a144020`，405 项历史未提交改动仍在） |
| R12 工作树 `~/data/dev/llmke-r12` | 未触碰（HEAD `419a87d`；`graph_types.py` 的 B01 改造 + `platform/r15` 运行产物仍是**未提交**状态，不丢） |
| 工具环境 | 仓外独立 venv（Python 3.10.12），按 `docs/design/unified-documents-v2/validation-requirements.lock` 安装；`lazy-object-proxy` 实为 1.12.0（锁要 1.13.0，索引不可得，见 U-06） |

## 2. 已完成（本分支）

1. ZIP/补丁/清单核验通过，补丁 59 文件已在隔离分支应用（无 `.rej`）。
2. 通用生成链路补齐"仓内解析 + 禁网"：`scripts/contract_runtime.py`（`bundle_local_refs`/`no_network`）、`scripts/contract_toolchain.py`。
3. `make generate` / `make check` 全 PASS（27 合同，17 个 generated 产物精确相等）。
4. `make contract-v2-check` 目标新增：离线检查 + 样例校验 + 95 条测试。
5. `docs/baseline/TRACE.yaml` 补登 9 条 V2 合同，`decision_id=DOC2MD-UNIFIED-2.0.0`。
6. 交付文档：接入报告、统一实施队列（VL0–VL7，20 个任务）、本检查点。
7. **VL1-01 ParseArtifact 产物仓实现候选**（2026-10-30）：
   - 代码 `services/rag-alg/index_data_service/parse_artifact/{__init__,store,__main__}.py`（仅封装+校验+提交，不含解析/分块/图）
   - 测试 `tests/test_parse_artifact_store.py` 19 项（4 正例 + 15 反例）、`make ingest-slice-test`
   - 实测：两组合成样例提交成功并通过 V2 `ParseArtifact` 合同校验；CLI `python -m parse_artifact … --validate` 端到端 PASS
   - **未起 loop、未过独立 QA**：`AI_GUIDE` 规定 L1–L4 因 4 项 P0 OPEN 默认 BLOCKED，登记 implementation loop 需先由业主/流程所有者解除该阻塞，本轮不代改
8. **VL1-02 doc2md 适配器候选**（2026-10-30）：
   - 代码 `services/rag-alg/alg_doc_parse_service/adapter_doc2md/adapter.py`（命令模板 / 目录定位 / 能力探测 / producer 指纹）
   - 测试 `tests/test_doc2md_adapter.py` 7 项，与 VL1-01 合跑 `make ingest-slice-test`（26 passed）
   - 行为约定：上游缺 `document_ir.json` 或 `metadata.content_uid` → `UPSTREAM_IR_MISSING` 且**不写快照**；命令非零退出 → `DOC2MD_EXIT_NONZERO`；缺入口 → `DOC2MD_ENTRY_MISSING`
   - 真实运行被阻（U-08/U-09）：doc2md 两条解析路径都不产出 IR；本机缺 `markitdown` 且共享环境不许装。只读 dry-run 证据：`parse-markitdown --limit 1 --dry-run` → `Candidates: 2 / In-scope: 0`
9. **CR `BL-2.0.0-02` + text-only 登记路径**（2026-10-30）：
   - 合同新增 `$defs/LegacyTextArtifact`（`llmke-legacy-text-artifact/1.0`）：三件套、`state` 只能 `PARTIAL`、能力枚举只允许 `text/source_alignment`；`ParseArtifact` 一字未改
   - 代码：`store.commit(..., mode="text_only")` / `build_text_only_artifact()`；CLI 增 `--mode {v2,text_only}`；适配器增 `parse_to_legacy_artifact()`
   - 硬约束：目录里有 `document_ir.json` 时拒绝 text-only（`IR_PRESENT_USE_V2_PATH`）；声明结构性能力会被 schema 拒
   - 实测：`--mode text_only --validate` → `COMMITTED`，`PARTIAL`，3 件，合同 PASS；`make contract-all` / `contract-v2-check`（95 passed）仍 PASS
10. **VL1 真实上游实证**（2026-10-30，详见 `EVIDENCE-VL1-REAL-UPSTREAM-20261030.md`）：
   - 从既有 LLMKE 库 `kb_9` 取真实文件（`docx-table.docx` 36944B、`R12FIX-credit-ledger.xlsx` 5340B），经 MinIO S3 接口只读取件
   - 用 doc2md `d9e4f98` + 仓外独立 venv（Python 3.11.7、`markitdown 0.1.9`）跑通 scan→copy-to-vault→route-parsers→parse-markitdown
   - 真实产物只有三件套、**无 `document_ir.json`**、metadata 无 `content_uid`（U-08 由推断变实测）
   - 两份都经 text-only 通路登记成功：`COMMITTED` / `PARTIAL` / 合同 `PASS`；快照 `parsed_text.md` 与上游**逐字节一致**
   - PDF 路径仍未通：`pdf-digital.pdf` 路由到 MinerU，本机无 `magic_pdf`
   - 副作用：doc2md dev 库 `gits_ke` 新增 3 条 content/instance 与对应 route/parse 记录（未删改既有行）；产物在 `/tmp/doc2md-ws`（未入仓）
11. **过程中修 doc2md（U-08 的一半）**（2026-10-30）：
   - doc2md 仓新分支 `fix/017-ir-emission-wiring`，commit `28ec528`（未动其 `main`）：markitdown 写盘路径接上 `build_from_markitdown_text` + `validate_document_ir` 自校验 + 写 `document_ir.json`；`parsed_metadata.json` 补 `content_uid`；manifest 追加 `document_ir_path/ir_schema_version`
   - 真实产物由 3 件变 4 件，过 doc2md 自带 IR 校验；平台改走 `--mode v2`（`llmke-parse-artifact/2.0`），合同 PASS
   - 但 IR 是文本降级（block 全 `inline_text`）→ 平台把 `quality.state` 压到 `PARTIAL` 并留警告；`derive_quality` 的降级判据只看**引用类型**（不看 provenance 名字，合成样例会误判）
   - doc2md 回归：5 failed / 1492 passed / 133 skipped，改动前后一致（5 项为既有 typer CLI help 问题）
12. **VL1-03 第一步：快照投影 + 线上只读对照**（2026-10-30）：
   - `services/rag-alg/index_data_service/rag_projection/`：确定性窗口分块（段落边界、MD 码点区间、
     `parse_artifact_id` 随 chunk、主键沿用 `chunk|index|file_id|seq|sha1(text)`）；不写任何存储
   - 开关 `INGEST_PROJECTION_MODE=legacy|snapshot|shadow`，默认 legacy，未知值 fail-closed
   - 11 项测试（slice 精确、覆盖完整、确定性、篡改/覆盖缺口拒绝、empty→EMPTY、text-only 快照可投影）
   - 真实对照（只读 `_count`）：333 docx 快照 1 vs 线上正文 1 + 表格 1 → 差 **-1**；
     329 xlsx 快照 1 vs 线上 0 + 表格 1 → 差 0
   - 结论：线上是**双通道**（正文 + `table_chunks_*`），本投影目前单通道，表格整段留在正文里；
     因此 `snapshot` 不能直接切，必须先补表格通道（依赖 MinerU IR）

## 3. 失败/未通过（如实保留，未绕过）

| 检查 | 状态 | 归属 |
|---|---|---|
| `make trace-check` | FAIL：`planned/actual loop set mismatch`（`loops/R12-real-rag` 未登记进 `PROJECT-PLAN.yaml`） | 既有，U-04 |
| `make baseline-check` | FAIL：冻结控制面漂移（既有 `.gitignore`；本次追加 `contracts/*`） | 需授权重冻结，U-05 |
| `make security-check` | FAIL 1861 条（R12 平台配置含真实连接串/口令/个人路径） | 既有，本次新增 0 |
| `pytest tests/` | 279 passed / 3 skipped / 1 failed（`test_framework_repo_itself_is_clean`，同上） | 既有 |

## 4. 待定（阻塞后继，不影响本分支其他工作）

- ~~U-01 `relations.v1.json` `reverse_dedup` 与 B01 domain/range 判定矛盾~~ → **已关闭**：CR `BL-2.0.0-01` ADOPTED，合同已改写并新增 `direction_resolution`；`make contract-all` 与 `make contract-v2-check` 复跑 PASS。
- U-02 doc2md 制品/授权 → **部分解除**：doc2md 源码在本机工作区可读（HEAD `d9e4f98`，设计记载的交接基线 `52a63ec` 为其祖先）。仍缺：制品/源码 hash 登记、四类格式真实运行、与包内 `doc2md.zip SHA 63eede32…` 的对应关系。
- **U-08 上游缺 IR 出口**：doc2md 两条解析路径都不产出 `document_ir.json`，`parsed_metadata.json` 也没有 `content_uid`。**部分处置**：CR `BL-2.0.0-02` 已给 text-only 产物合法登记位（`LegacyTextArtifact`，PARTIAL、不得声明结构能力）；要真正走 `ParseArtifact` 仍需 doc2md 补 IR 出口。
- ~~U-09 真实解析依赖缺口~~ → **已解除（2026-10-30）**：仓外独立 venv（Python 3.11.7 + `markitdown 0.1.9`）已装机，doc2md 四步 CLI 真跑通；共享算法环境未改。
- **PDF/MinerU 路径仍缺**：`pdf-digital.pdf` 被路由到 MinerU，本机无 `magic_pdf`；PDF 结构化解析需另装重依赖（与 U-03 同类）。
- U-03 HippoRAG 版本/离线依赖（VL3 前置）。
- U-07 真实 DDL 与恢复副本（VL5-02 前置）。

完整清单见接入报告 §6。

## 5. 活作业

无。未启动任何长跑服务、未建索引、未改数据库、未推远端。

## 6. 下一精确动作

按 `IMPLEMENTATION-QUEUE-V2.md`：

1. ~~为 U-01 出 CR~~ 已完成（`BL-2.0.0-01`）。
2. ~~启动 VL1-01~~ 已完成实现候选（见 §2.7），待 loop 登记决定后再补门禁证据。
3. ~~VL1-02 适配器 + 真实上游实证~~ 已完成（§2.8–§2.11）。~~VL1-03 第一步~~ 已完成（§2.12）。下一步：
   - **4a（可立即做）**：补**表格通道**投影 —— 从 IR 的 `table_ref`/表格矩阵产出 `table_chunks_*` 等价单元，并让 shadow 对照变成"正文 + 表格"两通道同时比。当前 IR 是文本降级，需要先接 MinerU 路径。
   - **4b（可并行）**：把投影接进解析服务实时链路 + `parse_artifact_id` 落库（需迁移草案，先在恢复副本验证，不直接动生产库）。
   - **4c（需上游/需裁定）**：MinerU 路径 IR 接线 + `magic_pdf` 依赖（表格坐标/表头路径只能从这条拿）。
   - **不要**先开图引擎，也不要在 RAG/图侧重新解析原件兜底；`snapshot` 模式在 4a 完成前不得切换。
4. 合入 B01 实现时按 CR `BL-2.0.0-01` 复核四项判据（已在接入报告 §2.3 记录一次实测）。
5. 若要正式计门禁：需业主/流程所有者先决定 L1–L4 的 P0 阻塞如何处置（U-04 同类问题），再由 `make new-loop` 建 `VL1-*` 并登记进 `docs/PROJECT-PLAN.yaml`（否则 trace-check 会新增一条 loop 漂移）。

## 7. 恢复条件

- 若会话中断：先 `git -C ~/data/dev/llmke-v2 status`，确认无残留 index/临时文件，再按 §6 接续。
- 不要重复解压 ZIP、不要重复 `git apply`（会冲突）、不要把 `~/data/dev/llmke` 的 405 项改动重置。
- 改动任何 `contracts/**` 或 `scripts/contract_{runtime,toolchain,registry}.py` 后，`generated/` 必须重新 `make generate`，否则 `make check` 会以 DRIFT 失败（这是设计意图，不是环境问题）。

---

## 执行契约（2026-10-31 补，因"汇报即停"被指出）

1. **阶段完成 ≠ 回合结束**：完成一个阶段后，不得以"下一动作是……"作为回复收尾；
   必须在同一回合内继续调用工具执行下一动作，直到遇到真实阻塞（缺权限/缺外部输入/需重启他人在用的服务）
   或本回合工具预算耗尽。
2. 回合收尾只允许两种形态：
   - 阻塞：说明卡在哪一层、需要什么、其他可并行事项已推进到哪；
   - 预算耗尽：列出**本回合已完成**的改动与**已开始的下一动作进度**，不写"计划"。
3. 每次收尾前自检：`下一动作` 是否已经执行了至少一步？没有就继续做。
4. "下一动作"只作为内部状态，不写进面向用户的结尾句。
