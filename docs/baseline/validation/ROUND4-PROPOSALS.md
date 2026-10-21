# 第四轮发现的控制面缺陷提案（P-08 / P-09 / P-10）

> **状态：提案，未实施。** 三项都涉及冻结控制面或信任根；
> 未获 `baseline-owner`（P-08/P-09）与 `qa-owner`（P-10）批准前不改。
> 本轮已冻结 r5，任何控制面改动都会让 r5 候选作废——因此只提不动。

---

## P-08 扫描范围应固定，且「源码敏感信息」与「产物敏感信息」分开判定

### 现象（本轮实测）

| 事实 | 证据 |
|---|---|
| `security-check` 的扫描对象是**整个工作树**（`tree_files`） | `scripts/security_scan.py:70-83` |
| 因此文件数随门禁执行而变：502 → 503 → 507 → 508 | 每跑一次门禁新增 1 个 `evidence/*.log` |
| 证据日志共 **55 个**（`loops/**` 45 个 + `docs/reviews/**` 归档 10 个） | 扫描清单 `loops/L0-contract-baseline-r5/evidence/security-scan-scope.json` |
| 「个人绝对路径」豁免只覆盖 `loops/*/evidence/*.log` | `EVIDENCE_LOG_RE`；`docs/reviews/**/evidence/*.log` 不在豁免内 |
| **本轮真实事故**：`db-entity-check.json` 写入源码绝对路径 → 39 处 `PERSONAL_ABSOLUTE_PATH` | 已修（改为相对路径 + 生成器自检拒绝绝对路径），见 `loops/LD-legacy-discovery/FAILURES.md` |

### 问题本质

「扫什么」不固定 → 门禁结果不可复算；「源码里有路径」与「产物里有运行路径」被混为一类判定 →
要么反复误报（产物），要么靠逐条豁免（易漏）。

### 提案

1. 扫描分两轮，输出两个独立计数：
   - **源码轮**：`git ls-files`（受控集合）→ 五类判定全开（凭据/连接串/私钥/个人路径/生产主机）；
   - **产物轮**：`loops/*/evidence/*.log`、`docs/reviews/**/evidence/*.log`、`docs/baseline/validation/*` →
     **仅**判定凭据/连接串/私钥/生产主机（**个人路径不比**，因为运行日志天然含宿主路径）。
2. 输出格式改为 `PASS (source=NNN, artifacts=MMM; personal_path_skipped=K)`，两个数字都必须显式。
3. 新增「产物生成器自检」约定：任何写入仓库的 JSON/MD 产物，生成时若含宿主绝对路径**必须拒绝写入**
   （`db_entity_check.py` 已示范实现）。
4. **不放宽**任何凭据类判定；产物轮同样扫描私钥、连接串、生产主机。

### 影响面与验证

| 项 | 内容 |
|---|---|
| 影响 | `security_scan_gate`、`framework-verify`、所有批次的 QA 门禁 |
| 旧 QA 失效面 | **否**（只细分判定与计数，不放松凭据类） |
| 正例 | 干净源码 + 含宿主路径的证据日志 → PASS，且 `personal_path_skipped ≥ 1` |
| 反例 1 | 源码里写宿主路径 → 必须 FAIL |
| 反例 2 | 证据日志里写一条**真实口令赋值**（形如 口令字段=真实值）→ 必须 FAIL |
| 反例 3 | 产物 JSON 含宿主路径 → 生成器拒绝写入（而非事后扫描发现） |

---

## P-09 QA 载荷的绑定范围应与门禁证据一致（现在不一致）

### 现象

| 组件 | 绑定对象 |
|---|---|
| 门禁记录（`run_gate`） | `control_digest`（P-03 已改）+ `baseline_sha256` |
| **QA 载荷（`qa_payload.py`）** | **整树 `snapshot()`** + `baseline_sha256` |

后果（本轮可直接复现）：
- 在 `qa-run` 之后改动 **任意** `docs/**.md`；
- `evidence-check` 仍判 **PASS**（因为 control 未变）；
- 但 `qa_payload.py` 报 `candidate evidence changed`，**载荷无法生成**。

即：同一候选，两个组件给出相反结论。安全方向上是「更严格」，但语义不一致会让接手人误判
「到底哪个才算候选有效」。

### 提案

1. `qa_subject` 增加 `digest_scheme: 2` 与 `control_sha256`；载荷生成与 `accept-qa` 一律按 `control_digest` 校核；
2. 旧 QA 记录（无 `digest_scheme`）按 `legacy` 语义继续用整树，不回溯改写；
3. 与 P-03 保持同一套判定函数（复用 `stale_reasons`），避免两处逻辑漂移。

### 影响面与验证

| 项 | 内容 |
|---|---|
| 影响 | `scripts/loop_guard.py`（`qa_subject`/`verify_qa`）、`scripts/qa_payload.py` |
| 旧 QA 失效面 | 否（`legacy` 兼容） |
| 正例 | `qa-run` 后改 `docs/**` → `evidence-check` 与载荷生成**都** PASS |
| 反例 | `qa-run` 后改 `contracts/**` → 两者**都** FAIL |

---

## P-10 信任根缺少基线批准的审计字段

### 现象

信任根只有一个标量 `approved_baseline_sha256`。每次重冻结都要覆盖它，于是：

- **看不出「上一版批准了哪条基线」**（覆盖即丢失）；
- 无法回答「这条签名当时批准的是不是这个基线」（只能靠外部文档）；
- 无法表达「批准有时间窗口」或「某基线被撤销」。

本轮就卡在这里：锚点仍是 `c8a73c37…`，而 r5 是 `213c6ebc…`；更新动作本身**没有留下任何机器可读记录**。

### 提案

1. 信任根新增**追加式**字段：

   ```yaml
   baseline_approvals:
     - sha256: <40 或 64 位>
       approved_by: <principal_id>
       approved_at: <ISO8601>
       reason: <重冻结原因>
       superseded_at: <ISO8601 或 null>
   ```

2. `verify_envelope` 判定：当前 `baseline_hash(root)` 必须命中列表中 `superseded_at == null` 的条目；
3. 兼容：若只有旧标量 `approved_baseline_sha256`，视为单条记录（`legacy` 语义）；
4. 撤销：把某条 `superseded_at` 填值即可，**历史签名仍可追溯，但不再被接受**。

### 影响面与验证

| 项 | 内容 |
|---|---|
| 影响 | 信任根文件格式、`scripts/baseline_support.py::verify_envelope` |
| 旧 QA 失效面 | 否（标量兼容） |
| 正例 | 列表含当前基线 → 签名通过；`superseded_at` 非空 → 拒绝并说明原因 |
| 反例 | 列表不含当前基线 → 拒绝，错误信息给出「已批准列表 vs 当前值」 |

---

## 三项的共同实施前提

1. 任一项实施 → 改控制面 → **r5 候选作废** → 需 r6 重跑 + 重签；
2. 因此建议与下一次批次建立**合并到同一次冻结**（一次改完、一次冻结、一次重跑）；
3. 实施顺序建议：**P-09（一致性）→ P-08（可复算）→ P-10（审计）**；
   P-10 只需改信任根格式与一个函数，但要 `qa-owner` 同意其审计语义。

## 本轮明确不做的

- 不改 `security_scan.py`（会作废 r5）；
- 不改 `qa_payload.py`（同上）；
- 不改信任根（属自签红线）。
