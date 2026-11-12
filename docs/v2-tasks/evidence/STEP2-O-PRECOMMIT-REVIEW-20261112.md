# STEP2-O 提交前合规复核（T-D2MD-17 / 2026-11-12）

> 触发：本轮改了 `services/.../kb_ingest_service.py`（**源代码变动会使旧证据失效**），且 STEP2-G~N 与代码/测试/脚本全部留在本地工作树待「提交一次 git」。
> 本文件按工作区纪律做「审查 staged diff；新增边界需 CR 与兼容去向」，并给出**可直接使用**的提交清单。**未执行 `git add` / `git commit`**。

---

## 一、变更清单

### 已跟踪文件（`git diff --stat`，3 个）

| 文件 | 变化 | 性质 |
|---|---|---|
| `docs/v2-tasks/CHECKPOINT.md` | +169 | 检查点（视图） |
| `docs/v2-tasks/TASKS.yaml` | +24 / −7 | 台账事实 |
| `services/rag-alg/index_data_service/kb_ingest_service.py` | **+12 / −1** | **唯一源代码改动** |

代码 diff 全文（可复核）：
- `create_app()` 新增 `service_is_default` 标志（默认构造 True、注入 service 为 False）；
- `ingest()` 的 service 分支：当 `service_is_default and (req.graph_root or req.graph_api)` 时按请求重建 `_build_service(...)`，否则沿用原 service。

### 未跟踪文件（14 个，`git ls-files --others --exclude-standard`）

- 交接与证据 9 个：`HANDOVER-20261112.md`、`evidence/STEP2-G/H/I/J/K/L/M/N-*.md`
- 脚本 3 个：`scripts/p6_request_graph_root_probe.py`、`scripts/p6_window_ingest.py`、`scripts/p6_delta_rebuild_probe.py`
- 测试 2 个：`tests/test_kb_ingest_request_graph_root.py`、`tests/test_p6_graph_root_semantics.py`

### 边界核对

- `contracts/`、`generated/`、`contracts/registry.yaml`、`FROZEN-MANIFEST.json` **均未改动**（`git status --short` 为空）。
- 敏感扫描：待提交文件与 diff 中的凭据赋值、连接串、私钥标记等模式 **0 命中**；未跟踪文档不含凭据值（窗口前置核对时 18097 的凭据只出现在工具输出，未写入任何文件）。
- 提交守卫如实留痕：首次 `git commit` 前的 staged 敏感复查曾因上一行写出扫描模式字面量而**自引用误报 1 条并 fail-closed 中止**（未产生提交）；核实为文档文字后去掉模式字面量、重新 stage，复查通过方才提交。该失败记录不删。

---

## 二、门禁复核（按统一入口约束：venv 解释器 + `MAKEFLAGS=--no-print-directory`，输出写仓外避免证据日志自引用）

解释器：仓内无 `.venv`、`llmke-v2-toolenv` 已不存在；实测 `/home/szf/data/dev/hipporag-toolenv/bin/python` 具备 `openapi_spec_validator`，以 `LLMKE_PYTHON` + `PATH` 固定之。
日志：`coordination/p6-window-20261112/gate-{check,contract-v2,security,security-baseline}.log`。

| 门禁 | exit | 结果 |
|---|---|---|
| `make check` | 2 | **FAIL**：`DRIFT: inputs/generators/registry/toolchain/dependencies changed`、`LINKAGE: report contract set mismatch` |
| `make contract-v2-check` | 0 | **PASS**（2 个离线校验 PASS + `95 passed in 21.38s`） |
| `make security-check` | 2 | **FAIL**（`3265 findings`） |
| 相关 Python 测试 | 0 | **102 passed**（5 个文件） |
| 3 个新脚本 `py_compile` | 0 | OK |

### 基线判别（关键：不得把既有红说成本轮引入，也不得删失败凑 PASS）

**`make check` 的失败与本轮无关**，证据：
- `scripts/contract_toolchain.py:22-32` 的 `fingerprints()` 只哈希 `contracts/registry.yaml`、各合同输入、generator/checker、`requirements*`、`contract_{toolchain,runtime,registry}.py`。**本轮新增的 `scripts/p6_*.py` 不在哈希范围**；本轮也未触碰任何 `contracts/` 文件。
- 直接比对：`generate-report.json` 登记 **18** 个合同、`registry.yaml` 现有 **29** 个 → `LINKAGE: report contract set mismatch`；14 项指纹漂移全部是合同源与 toolchain 文件（如 `contracts/api/llmke-document-pipeline-v2.openapi.yaml`、`contracts/ontology/*.json`、`contracts/registry.yaml`）。
- 即：**历史上海扩展了 registry 却未重跑 `make generate`**，属独立的合同基线批次问题。

**`security-check` 的失败与本轮无关**：仅扫描已提交文件（`security_scan.py --tracked-sensitive`，无 `--all-files`）即 **FAIL 2377 findings**；全树扫描 3265。已提交文件中有 308 个含 `/home/szf/` 路径，`scripts/v2_make_review_pkg.sh`、`scripts/v2_graph_worker.py` 等既有文件也命中 `PERSONAL_ABSOLUTE_PATH` / `REAL_CREDENTIAL`。
- 本轮新文件贡献 **17 条**，全部为 `PERSONAL_ABSOLUTE_PATH`（证据文档中的真实运行路径 + 3 个脚本硬编码数据根），与基线同类，非真实凭据。
- 按纪律**未改 `.security-allowlist`**（安全边界变更需 review/CR）、**未删任何失败**、未对路径做脱敏伪装（证据必须保留可复跑的真实路径）。

> 收口判定（D-5 不扩大范围）：`make generate` 会从空目录重生成 29 个合同的 `generated/` 产物，属独立合同发布批次；安全 allowlist/路径脱敏规范属独立安全批次。**两者均另立 backlog，不在本轮提交内处理**，本轮也不擅自让门禁变绿。

---

## 三、CR 与兼容去向判定

**判定：本次源代码改动不新增契约边界，无需新增 CR；但必须随提交写明兼容去向。**

理由：
1. `IngestRequest.graph_root` / `graph_api` 本就在契约 `02-CONTRACTS.md` §1.1 字段集中，`extra="forbid"` 字段集未变；本次只是让 service 路径**消费已有字段**（与旧 `runner` 兼容缝行为对齐），未新增字段、未改 schema、未改错误码。
2. **默认值语义保持向后兼容**：请求不传 `graph_root`/`graph_api` 时仍使用启动期 env 绑定；由 `tests/test_kb_ingest_request_graph_root.py::test_omitting_graph_root_keeps_startup_binding` 覆盖。
3. **注入缝保持**：外部传入 `service` 时不重建，`test_injected_service_is_not_replaced` 覆盖。
4. 变异复验：用 `git show HEAD:` 未修复版跑同一测试 → `3 failed / 3 passed`，证明断言非空转。
5. 生产窗口（STEP2-M）已实证请求级 `graph_root` 生效（delta 响应 `root=<app>/graph-root/kb_9`），且 8 端口/health 全绿。

**兼容去向（建议写入 commit message）**：
> `kb_ingest_service`: 让 `/kb/ingest` 的 service 路径消费契约已有的 `graph_root`/`graph_api`（原先仅旧 runner 缝透传，service 路径静默忽略，图根被启动期 env 绑死）。未传时仍回退 env；注入 service 的调用方行为不变。P6-L17 切读前置。

若 Owner 认为「实现从忽略变为消费」属于边界语义变更，可要求补 CR —— 本判定可推翻，不隐蔽。

---

## 四、可提交清单（供「提交一次 git」指令直接使用）

按纪律**不用宽泛 `git add .`**；以下为精确文件列表：

```
git add docs/v2-tasks/HANDOVER-20261112.md \
  docs/v2-tasks/TASKS.yaml docs/v2-tasks/CHECKPOINT.md \
  docs/v2-tasks/evidence/STEP2-G-PROD-ARTIFACTS-MISSING-20261112.md \
  docs/v2-tasks/evidence/STEP2-H-PROD-8FILE-REBUILD-DECISION-20261112.md \
  docs/v2-tasks/evidence/STEP2-I-HANDOVER-RECON-20261112.md \
  docs/v2-tasks/evidence/STEP2-J-REQUEST-GRAPH-ROOT-20261112.md \
  docs/v2-tasks/evidence/STEP2-K-GRAPH-ROOT-SEMANTICS-20261112.md \
  docs/v2-tasks/evidence/STEP2-L-DESIGN-DECISION-20261112.md \
  docs/v2-tasks/evidence/STEP2-M-PRODUCTION-WINDOW-20261112.md \
  docs/v2-tasks/evidence/STEP2-N-DELTA-REBUILD-VERIFY-20261112.md \
  docs/v2-tasks/evidence/STEP2-O-PRECOMMIT-REVIEW-20261112.md \
  services/rag-alg/index_data_service/kb_ingest_service.py \
  scripts/p6_request_graph_root_probe.py scripts/p6_window_ingest.py \
  scripts/p6_delta_rebuild_probe.py \
  tests/test_kb_ingest_request_graph_root.py tests/test_p6_graph_root_semantics.py
```

提交前复核建议：`git --no-pager diff --cached --stat` 与 `git status --short` 逐项对照本清单，确认无 `contracts/`、`generated/`、`.env`、`*.pyc`、备份目录 `coordination/p6-window-20261112/`（仓外，不会进提交）。

**注意**：`STEP2-G/H` 与 `HANDOVER-20261112.md` 是**上一执行者**留下的未跟踪文件，本轮只做核证与事实纠正、未改写其内容；提交时一并入库，但不应署为本轮产物。

---

## 五、纪律留痕

- 未执行 `git add` / `git commit`，`git diff --cached --stat` 为空。
- 未改 `.security-allowlist`、未跑 `make generate`、未手改 `generated/`、未删任何失败记录。
- 门禁日志（含 FAIL）全部保留在 `coordination/p6-window-20261112/`，不回显凭据值。
- 运行树副本 `llmke-runtime/app/.../kb_ingest_service.py` 已在生产窗口同步（两份 md5 一致），但**运行树在仓库外，不进本次提交**；需在部署侧另行留痕。
- `T-D2MD-17` 保持 `IN_PROGRESS`、`T-D2MD-18` 保持 `TODO`；未签 `QA_PASS`。
