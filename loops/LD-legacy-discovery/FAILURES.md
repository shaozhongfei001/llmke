# FAILURES.md

Append-only run failures; actual failures are never deleted to obtain PASS.

---

## TL 覆盖施工期发现（2026-10-21，V1.1.0 补丁应用到本仓）

### FAIL-2026-10-21-01 `make security-check` 命中 PERSONAL_ABSOLUTE_PATH

- 现象：仓根 `.llmke-baseline-applied.json` 第 4 行命中扫描器的 `PERSONAL_ABSOLUTE_PATH` 规则
  （命中的前缀形如 `/home/<user>/`，此处不回显原值）。
- 根因：覆盖工具 `apply_patch.py` 把回执 `.llmke-baseline-applied.json` 写在**目标仓根目录**，
  回执内含备份目录绝对路径；本仓根目录位于形如 `/home/<user>/…` 的路径下，因此命中该规则。
  参考环境未复现，是因为其项目根不在 `/home/<user>/` 下。
- 处理（不改动任何冻结控制文件）：回执副本另存到备份目录 `receipt.json`，随后从仓根移除该运行时产物；
  备份目录的 `JOURNAL.json` 仍持有 `target` 与逐文件前像，回退能力未削弱。
- 复验：移除后 `make security-check` → `PASS (364 file(s) scanned)`。
- 遗留：再次运行覆盖工具会重新生成该回执；提交前必须排除仓库根目录下的此文件（禁止 `git add .`）。
- 状态：**CLOSED**（证据：`loops/LD-legacy-discovery/evidence/inventory_gate.log` 之后的门禁复跑记录见 `EVIDENCE.md`）

### FAIL-2026-10-21-02 `tests/test_security_scan.py::test_framework_repo_itself_is_clean` 失败

- 现象：框架自检要求框架仓自身通过自己的扫描器；实际 `git ls-files` 为空 → 扫描器 fail-closed 报
  `scope is empty — 0 file(s) to scan`。
- 根因：本仓为全新工作区（`尚无提交`，全部文件未跟踪），索引为空，门禁正确地拒绝「空扫描冒充干净」。
- 处理：逐文件/目录显式入库框架文件（337 个），填充索引使门禁有真实扫描范围；**未创建任何提交**。
- 复验：入库后 `make framework-verify` → `exit=0`，`127 passed`，其中该项转 PASS。
- 遗留：首次提交需用户显式授权；未提交前该门禁依赖索引状态。
- 状态：**OPEN（等待用户授权首次提交后复跑确认）**

### FAIL-2026-10-21-03 `requirements.lock` 不可解析，无法按原样安装

- 现象：`uv venv --python 3.12 .venv` 成功，但 `uv pip install -r requirements.lock` 失败：
  `Because you require pip==25.0.1 and pip==26.2.1, we can conclude that your requirements are unsatisfiable.`
- 根因：锁定文件存在重复且冲突的固定项（`pip` 两个版本；`attrs`、`charset-normalizer`、`packaging`、
  `PyYAML`、`six`、`typing_extensions` 重复出现），且含与框架无关的重型包
  （`vtk`、`cadquery-ocp`、`casadi`、`nlopt`、`trame*`、`scikit-learn` 等）。
- 处理：不改冻结文件。按脚本真实导入建立最小可验证依赖集
  （`jsonschema` 4.23.0 / `referencing` / `jsonschema-path` / `jsonschema-specifications` /
  `openapi-spec-validator` / `requests` / `PyYAML` / `pytest`），装在 Python 3.12.13 独立 venv。
- 复验：`make framework-verify` 全绿，127 passed（见 `EVIDENCE.md`）。
- 遗留：锁定文件需由 baseline-owner 去重/收敛；当前结论仅在本环境解释器与已装依赖集下成立。
- 状态：**OPEN（需 baseline-owner 修订锁定文件）**

### 2026-10-20T17:05:04.601696+00:00 inventory_gate

executor does not hold baton

### 2026-10-20T17:13:51.779942+00:00 inventory_gate

prior evidence invalid: inventory_gate: source/baseline changed; evidence STALE

## FAIL-2026-10-21-05 LD inventory_gate 证据 STALE 且预算耗尽

- 现象：新增 `docs/integration/DOC2MD-WORKSPACE-DECISION.md` 使源码快照由
  `488ea2a5…` 变为 `69da69fc…`，`inventory_gate` 的 pass 记录（@488ea2a5）判为 STALE；
  attempts 已 3/3，**无法重跑**。
- 根因：与 L0 同源——`docs/**` 在快照范围内，任何文档新增都会使既有证据失效；
  本批次在写入该文档前已用掉 2/3 预算。
- 状态：**BLOCKED**（待 L0 的新批次或 owner 决议后一并重跑；不得手工重置 attempts）。
- 教训：文档类产出应**批量合并**后一次性重跑，或优先落在 `docs/approvals/`、`docs/baseline/validation/`
  等不参与快照的目录（本次已按用户指定路径写入，代价如实记录）。
