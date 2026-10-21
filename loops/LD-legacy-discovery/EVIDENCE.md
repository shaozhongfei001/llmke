# Current LD evidence

本次为 TL 覆盖施工后的第一批记录。开发自检已运行；**独立 QA 未执行**，本批次不能 DONE。
包内 `docs/reviews/**` 的历史日志不作为本次结果。

## 1. 运行环境（唯一声明口径）

| 项 | 值 |
|---|---|
| 框架版本 | `VERSION` = 1.1.0 |
| 解释器 | CPython **3.12.13**（`uv python install 3.12`，独立 `.venv`） |
| 依赖 | 未按 `requirements.lock` 原样安装（该文件不可解析，见 `FAILURES.md` FAIL-2026-10-21-03）；按脚本真实导入安装最小可验证集 |
| 数据库/外部服务 | **未连接**（`real_DB_or_business_services_connected: false`） |

## 2. 门禁结果（本次实跑）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `make contract-all`（generate + check） | 0 | `PASS (18 contracts)` / `PASS (18 contracts, semantic + exact linkage)` |
| `make rules-check` | 0 | `rule-mirror: PASS` |
| `make trace-check` | 0 | `trace-check: PASS` |
| `make p0-check` | 0 | `p0-check: PASS (integrity)` |
| `make security-check` | 0 | `PASS (364 file(s) scanned)`（移除仓根回执后） |
| `make framework-test` | 0 | `127 passed` |
| `make baseline-check` | 0 | `baseline: PASS`（技术制品；不代表业务就绪或独立 QA） |
| **`make framework-verify`（合计）** | **0** | **全绿** |
| **`make p0-gate`** | **2** | **按预期拒绝**：P0-01/02/03/04 均 `strict requires CLOSED` |
| `make run-dev LOOP=LD-legacy-discovery EXECUTOR=legacy-owner` | 0 | `inventory_gate` pass，STATE revision 1→2 |
| `make discovery-verify` | 0 | `reuse-check: PASS inventory` / `p0-check: PASS (integrity)` / `trace-check: PASS` |
| `make memory-check LOOP=LD-legacy-discovery` | 0 | PASS |

`discovery-verify` 是 `independent_qa_gate` 的 catalog argv；**本次由开发身份执行，只构成
DEV_SELF_CHECK 候选，不构成外部独立 QA 签署**。

## 3. 负例（证明门禁非空转）

| 负例 | 命令 | 结果 |
|---|---|---|
| 四 P0 未关闭时武装 L1 | `loop_guard.py arm --loop L1 --to legacy-owner --executor tech-lead --expected-revision 1` | FAIL：`P0-01..04 strict requires CLOSED` |
| 无独立 QA 时结束 L0 | `loop_guard.py finish --loop L0-contract-baseline` | FAIL：`independent_qa_gate: DONE requires all gates pass` |
| 非 baton holder 执行门禁 | `loop_guard.py run-gate --loop LD-legacy-discovery --gate inventory_gate --executor tech-lead` | FAIL：`executor does not hold baton` |

## 4. 本批次不证明的事项

- 不证明 12 项源码资产可直接复用（`SOURCE-ASSETS.yaml` 全部 `CANDIDATE_UNVERIFIED`、`decision: null`）。
- 不证明 37 表 / 482 字段与实际 DDL 一致（`DATABASE-ASSETS.yaml` 全部 `CANDIDATE_UNVERIFIED`，
  `source_schema_strategy: UNDECIDED_SHARED_OR_NEW_DATABASE`，`actual_ddl_sha256: null`）。
- 不证明 506 条接口清单等于运行时可路由能力（`INTERFACE-ASSETS.yaml` 全部 `INVENTORY_UNVERIFIED`，
  `runtime_evidence: 0` 条）。
- 不证明任何业务功能已交付；L1–L4 仍 `BLOCKED`。

## 5. 506 条接口清单 vs 生产快照（2026-10-21 实跑）

- 工具：`tools/verify_interface_inventory.py`（只读；按「方法 + 拼接后完整路径」建路由表后逐条匹配）
- 结果：**504/506 存在**（Java 438/440、Python 66/66）；**1 条仅存在于注释**
  （`API-0345 GET /ai/getRerankModelInfos`，独立复现 P0-01 已登记事实）；
  **1 条行号漂移 11 行**（`API-0425`，路径与 handler 均存在）；0 条文件缺失。
- 产物：`evidence/interface-inventory-check.json`、`evidence/interface-inventory-check.md`、
  `evidence/INTERFACE-INVENTORY-DIFF-V1.0.md`
- 边界：只证明「源码里有声明」，**不证明运行时可路由、不证明有调用**，
  因此不构成 P0-01 关闭。

## 6. CODE-01 解耦可行性回放（2026-10-21 实跑）

- 工具：`spike/build_shimmed.py` + `spike/run_arm.py` + `spike/parity_check.py`（原仓只读，副本落 `/tmp`）
- 结果：25 处 `server.*` 导入改写（14 文件）后，**5/5 样本逐字段一致**
  （txt / html / 自建纯文本 docx / 仓库内 M0 与 M1 docx；块数 4/1/6/95/71 两臂相同）
- 三条硬条件：`parser/__init__` 全量导入使原包**导入即失败**（缺阿里云 SDK）、
  docx 导入期需 21 个重型依赖、OCR 在**构造期**加载模型（`image_parser.py:21`）
- 未覆盖：PDF、图片/图文关联、表格切分、分块与 offset —— 缺模型，属显式缺口
- 产物：`S1-SPIKE-CODE-01-RESULT-V1.0.md`、`spike/PARITY-REPORT.md`、`spike/parity-report.json`

## 7. 解析方案选型：doc2md vs deepdoc（2026-10-21）

- 对比报告：`PARSER-DESIGN-COMPARISON-V1.0.md`（六维设计对比）
- 实测记录：`PARSER-CONTRACT-PROBE-V1.0.md`（6 份自建样本，只读执行，不写 doc2md 的 DB/vault）
- 实测结论：三类 PDF 分流正确（数字 677 字符→PDF_DIGITAL；扫描 0 字符→PDF_SCANNED_OR_IMAGE；
  加密→不试口令直接判扫描链路）；OCR 真值表 48 组合无静默成功；
  **DOCX 路径表格与图片丢失**（`table_count=0`、`figure_count=0`）
- 选型建议：PDF/OCR 引用 doc2md 并保持独立组件；DOCX 暂不引用（倾向 deepdoc 适配 + 向 doc2md 提需求）
