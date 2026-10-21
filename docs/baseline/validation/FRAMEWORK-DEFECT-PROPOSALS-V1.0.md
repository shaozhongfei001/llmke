# 框架缺陷变更提案 V1.0（R-03 / R-05 / R-06 / R-07 / R-08 / R-09）

> **状态：提案，未实施。**
> 六项提案全部涉及**冻结控制面**（`scripts/**`、`docs/policies/**`、`docs/baseline/**`、`VERSION`、
> `PROJECT-PLAN.yaml`），按规则必须先提 proposal、经批准后再改，并随之重冻结与重跑门禁。
> 本文件位于 `docs/baseline/validation/`（不参与源码快照），因此写入它不会使现有证据失效。
>
> 批准角色：`baseline-owner`（冻结面变更）+ 对应领域 owner（R-05 涉 `qa-owner`，R-06 涉 `tech-lead`）。

---

## P-01（R-03）把"扫描输入"与"运行输出"分开

**现象**：`evidence-check` 反复因证据日志自污染而红。`run_gate` 在运行**结束后**才重写日志，
运行期间磁盘上是上一次内容；若上次是失败 traceback（含宿主绝对路径），
`security_scan.py --all-files` 会把它当命中，本次失败又把命中文本写回同一文件 → 永久污染。

**提案**（改 `scripts/security_scan.py`）：
1. `tree_files()` 增加排除：`loops/*/evidence/*.log` **不参与 `PERSONAL_ABSOLUTE_PATH` 检测**
   （它们是机器生成物，天然含运行路径）；
2. 但**仍参与**凭据/私钥/连接串检测（安全底线不放松）；
3. `security-check` 输出新增一行 `evidence_logs_skipped_for_personal_path=N`，把"跳过了多少"显式化，
   避免变成"静默忽略"。

**影响范围**：`security_scan_gate`、`framework-verify`、所有批次的 `independent_qa_gate`。
**旧 QA 失效面**：否。只放宽"证据日志里的宿主路径"这一类判定，不放宽凭据类。
**验证**：正例（干净日志 PASS）+ 反例（人为在日志里塞 ``/home/<user>/` 形态的路径` → 仍 PASS 且计数+1；
人为在源码里塞 ``/home/<user>/` 形态的路径` → 必须 FAIL）。

---

## P-02（R-05）QA 签名的"接受时点"与"事后复核"分离

**现象**：`qa_payload.py` 固定 1 小时有效期；`verify_envelope()` 每次校验都检查
`issued <= now < expires`。于是**已接受**的 QA 证据在 1 小时后无法复核
（实测 `FAIL: invalid approval validity window`）。

**提案**：
1. `verify_envelope(purpose='QA_ATTESTATION')` 分两段：
   - **接受时**（`accept-qa`）：仍严格检查有效期（防"签了放着以后用"）；
   - **复核时**（`evidence-check`）：只校验签名、subject 一致、密钥未撤销，**不再检查 `expires_at`**；
2. QA 记录新增 `accepted_at`（接受时刻）与 `accepted_by`，作为事后复核依据；
3. 信任根新增可选 `revoked_key_ids: []`，撤销后复核必须失败（这是唯一应让历史证据失效的条件）。

**影响范围**：`scripts/baseline_support.py`、`scripts/loop_guard.py`。
**旧 QA 失效面**：**会**。历史记录没有 `accepted_at` 字段，需一次性回填（或标记为 `legacy` 并沿用旧语义）。
**验证**：正例（过期载荷在复核时 PASS、在接受时 FAIL）+ 反例（撤销密钥后复核 FAIL）。

---

## P-03（R-06）证据摘要按"真实输入范围"绑定

**现象**：`snapshot()` 把所有源码文件（含 `docs/**` 说明文档）算进一个哈希。于是改一行文档，
7 条开发门禁 + 已签 QA 全部 STALE。

**提案**：
1. 把源码摘要拆成两个：
   - `control_digest`：`contracts/**`、`scripts/**`、`generated/**`、`tests/**`、`.codebuddy/**`、
     `.cursor/**`、`docs/policies/**`、`docs/roles/**`、`docs/baseline/**`、`docs/upstream/**`，
     以及根部的 `Makefile`/`VERSION`/`requirements*`/`.gitignore`/`.security-allowlist`；
   - `doc_digest`：`docs/**` 其余（reuse/acceptance/dispatch/adr 等说明性材料）。
2. 门禁记录同时写两个摘要；**判定是否 STALE 用 `control_digest`**；
   只有显式声明"依赖文档"的门禁（如 `traceability_gate`，它读 `docs/baseline/TRACE.yaml`）才同时比 `doc_digest`。
3. 旧记录保留整树摘要并标 `digest_scheme: legacy`，**不回溯改写**。

**影响范围**：`scripts/baseline_support.py`、`scripts/loop_guard.py`、所有 gate 记录格式。
**旧 QA 失效面**：会（格式变更），但可通过 `digest_scheme: legacy` 兼容旧记录。
**验证**：反例（改 `contracts/**` → 必须 STALE）+ 正例（改 `docs/dispatch/*.md` → 开发门禁不 STALE）。

---

## P-04（R-07）冻结元数据不得硬编码

**现象**：`FROZEN-MANIFEST.authority` 被 `freeze_baseline.py` 写成固定字符串
`user requested overlay baseline patch on 2026-10-20`；重冻结后该字段仍是旧文案，与事实不符。

**提案**：
1. 新增受控文件 `docs/baseline/BASELINE-AUTHORITY.yaml`，记录 `authority`、`authorized_by`、
   `authorized_at`、`scope`、`change_list`；
2. `freeze_baseline.py --write` 从该文件读取，并额外写入 `frozen_at`（UTC）与 `manifest_revision`（自增）；
3. 重冻结时若 `BASELINE-AUTHORITY.yaml` 缺失 → **拒绝**（不得静默沿用旧文案）。

**影响范围**：`scripts/freeze_baseline.py`、`docs/baseline/**`。
**旧 QA 失效面**：会（重冻结必然改 `baseline_sha256`）。
**验证**：反例（缺 authority 文件 → `--write` 必须失败）+ 正例（有 → 正确写入并自增 revision）。

---

## P-05（R-08）版本号与本地增量绑定

**现象**：`VERSION=1.1.0`，但内容已含本地增量（+2 批次、+1 目录、控制文件 196→198），
同名不同物，违反"不得两套并存/混用"的纪律。

**提案**：
1. `VERSION` 升为 `1.1.1`；
2. `BUILD-INFO.txt` 增加 `Local increments` 段，逐条列：r2 批次、`docs/integration/`、
   重冻结（控制文件数、变更面）、未完成的 R-xx；
3. 未来任何"改控制面但不改语义"的批次，版本号末位 +1；改语义则次位 +1（需 owner 批准）。

**影响范围**：`VERSION`、`BUILD-INFO.txt`（均在控制清单内）。
**旧 QA 失效面**：会（控制文件变化 + 重冻结）。
**验证**：`make baseline-check` 在重冻结后 PASS；`BUILD-INFO` 与 `FROZEN-MANIFEST` 的版本字段一致。

---

## P-06（R-09）为耗尽预算的旧批次提供终态

**现象**：`L0-contract-baseline` / `LD-legacy-discovery` 预算耗尽后停在 `IN_DEV`，
证据永久 STALE，框架没有 `SUPERSEDED`/`RETIRED` 状态，只能靠 `memory/BLOCKED.md` 手工说明。

**提案**：
1. `VALID_STATES` 增加 `SUPERSEDED`、`RETIRED`；
2. STATE 增加可选 `replaced_by: <loop_id>` 与 `terminal_reason`；
3. `prerequisites`：`SUPERSEDED`/`RETIRED` 一律拒绝执行门禁（与 DONE 同）；
4. `evidence_errors`：`SUPERSEDED`/`RETIRED` 的批次**不参与** STALE 判定（历史结论保留，不再要求"活着"）；
5. `attempts` 与 `evidence/**` **永久保留**，不得因为终态而删除。

**影响范围**：`scripts/loop_guard.py`；各批次 `STATE.json`。
**旧 QA 失效面**：否（只影响状态机与 STALE 判定）。
**验证**：正例（标记 SUPERSEDED 后 `run-gate` 被拒、`evidence-check` 通过且报告"历史批次"）+
反例（尝试对 SUPERSEDED 批次 `finish` → 必须拒绝）。

---

## 批准与实施顺序建议

| 顺序 | 提案 | 理由 |
|---|---|---|
| 1 | P-01、P-06 | 纯判定放宽/状态机，不改摘要语义，风险最低 |
| 2 | P-02 | 阻塞"事后可复核"，但对历史记录有兼容成本 |
| 3 | P-03 | 影响所有 gate 记录格式，需一次性迁移说明 |
| 4 | P-04、P-05 | 元数据与版本，必须与一次重冻结同时做 |

**共同前提**：任一提案实施都会改控制面 → 触发重冻结 → 使现有已签 QA 失效
（`LD-legacy-discovery-r2` 的签名已过复核窗口，实际损失有限）。
建议**合并为一次窗口**：P-01/P-06 → P-02 → P-03 → 重冻结 + P-04/P-05 → 统一重跑 → 统一重签。
