# NEXT 检查点（2026-10-30，V2 设计与契约接入后）

> 恢复会话时按本文件顺序读：本文件 → `docs/design/unified-documents-v2/ADOPTION_REPORT_20261030.md`
> → `docs/design/unified-documents-v2/IMPLEMENTATION-QUEUE-V2.md` → 实际 `git status`。

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
   - 测试 `tests/test_parse_artifact_store.py` 19 项（4 正例 + 15 反例）、`make parse-artifact-test`
   - 实测：两组合成样例提交成功并通过 V2 `ParseArtifact` 合同校验；CLI `python -m parse_artifact … --validate` 端到端 PASS
   - **未起 loop、未过独立 QA**：`AI_GUIDE` 规定 L1–L4 因 4 项 P0 OPEN 默认 BLOCKED，登记 implementation loop 需先由业主/流程所有者解除该阻塞，本轮不代改

## 3. 失败/未通过（如实保留，未绕过）

| 检查 | 状态 | 归属 |
|---|---|---|
| `make trace-check` | FAIL：`planned/actual loop set mismatch`（`loops/R12-real-rag` 未登记进 `PROJECT-PLAN.yaml`） | 既有，U-04 |
| `make baseline-check` | FAIL：冻结控制面漂移（既有 `.gitignore`；本次追加 `contracts/*`） | 需授权重冻结，U-05 |
| `make security-check` | FAIL 1861 条（R12 平台配置含真实连接串/口令/个人路径） | 既有，本次新增 0 |
| `pytest tests/` | 247 passed / 3 skipped / 1 failed（`test_framework_repo_itself_is_clean`，同上） | 既有 |

## 4. 待定（阻塞后继，不影响本分支其他工作）

- ~~U-01 `relations.v1.json` `reverse_dedup` 与 B01 domain/range 判定矛盾~~ → **已关闭**：CR `BL-2.0.0-01` ADOPTED，合同已改写并新增 `direction_resolution`；`make contract-all` 与 `make contract-v2-check` 复跑 PASS。
- U-02 doc2md 制品/授权 → **部分解除**：doc2md 源码在本机工作区可读（HEAD `d9e4f98`，设计记载的交接基线 `52a63ec` 为其祖先；统一批量入口 `backend/app/extensions/intake/batch.py`）。仍缺：制品/源码 hash 登记、四类格式真实运行、与包内 `doc2md.zip SHA 63eede32…` 的对应关系。
- U-03 HippoRAG 版本/离线依赖（VL3 前置）。
- U-07 真实 DDL 与恢复副本（VL5-02 前置）。

完整清单见接入报告 §6。

## 5. 活作业

无。未启动任何长跑服务、未建索引、未改数据库、未推远端。

## 6. 下一精确动作

按 `IMPLEMENTATION-QUEUE-V2.md`：

1. ~~为 U-01 出 CR~~ 已完成（`BL-2.0.0-01`）。
2. ~~启动 VL1-01~~ 已完成实现候选（见 §2.7），待 loop 登记决定后再补门禁证据。
3. 下一步 **VL1-02**（doc2md 解析适配器）：先做只读核对——登记 doc2md 实际 commit/依赖 hash，用其 `backend/app/extensions/intake` 批量入口对 docx/pdf/xlsx/txt 各跑 1 份，产出真四件套；再把产物交给 VL1-01 的 `commit()` 落快照。**不要**先开图引擎，也不要在 RAG/图侧重解析原件兜底。
4. 合入 B01 实现时按 CR `BL-2.0.0-01` 复核四项判据（已在接入报告 §2.3 记录一次实测）。
5. 若要正式计门禁：需业主/流程所有者先决定 L1–L4 的 P0 阻塞如何处置（U-04 同类问题），再由 `make new-loop` 建 `VL1-*` 并登记进 `docs/PROJECT-PLAN.yaml`（否则 trace-check 会新增一条 loop 漂移）。

## 7. 恢复条件

- 若会话中断：先 `git -C ~/data/dev/llmke-v2 status`，确认无残留 index/临时文件，再按 §6 接续。
- 不要重复解压 ZIP、不要重复 `git apply`（会冲突）、不要把 `~/data/dev/llmke` 的 405 项改动重置。
- 改动任何 `contracts/**` 或 `scripts/contract_{runtime,toolchain,registry}.py` 后，`generated/` 必须重新 `make generate`，否则 `make check` 会以 DRIFT 失败（这是设计意图，不是环境问题）。
