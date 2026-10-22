# T1 版本一致性登记（逐文件定性，非批量替换）

- 执行轮次：第三轮（B 策略）
- 判定规则：**`VERSION` 是「执行基线版本」的唯一来源**；
  其余文件中的 `version:` / `baseline_version:` 需逐个定性，不得批量替换
- 事实基线：`VERSION=1.1.1`、`FROZEN-MANIFEST.baseline_version=1.1.1`（本轮收口前为 revision 5）

## 1. 定性结论

受控范围内共 **41 个文件**含字符串 `1.1.0`，但语义分四类：

| 类别 | 含义 | 处理 | 涉及 |
|---|---|---|---|
| A 执行基线 | 「技术施工基线」的版本 | **改为 1.1.1** | `AI_GUIDE.md`、`README.md` |
| B 批次执行基线 | 该批次跑在哪条基线上 | **仅未执行批次改为 1.1.1**；历史批次保留 1.1.0 | `loops/_template`、`L1`–`L4` 改；`L0`、`L0-r2`、`LD`、`LD-r2` 不改；`r3`/`r4` 已为 1.1.1 |
| C 契约包版本 | 合同包自身版本，与执行基线无关 | **不改** | `contracts/registry.yaml`（`baseline_version` 与各 `version`）、`contracts/**` 各合同、`contracts/README.md` |
| D 文档自身版本 | 各说明文档的版本号 | **不改** | `docs/PROJECT-BRIEF.md`、`docs/SDD-ENGINEERING.md`、`docs/DESIGN-TRACE.md`、`docs/adr/ADR-INDEX.md`、`docs/policies/*.yaml`、`docs/roles/ROLE-MATRIX.yaml`、`docs/baseline/*.yaml`、`docs/PROJECT-PLAN.yaml` |
| E 历史标记 | 授权记录中的「V1.1.0 → V1.1.1」 | **不改** | `docs/baseline/BASELINE-AUTHORITY.yaml` |

> 为什么 C/D 不改：`contracts/registry.yaml` 的 `baseline_version` 与各合同 `version` 表达的是**契约包版本**。
> 本轮没有修订任何合同内容，改版本号等于宣称发生了一次不存在的契约修订，并会污染溯源。
> 已把该口径写入 `BUILD-INFO.txt` 的「版本口径」段，避免后人再当成遗漏。

## 2. 实际改动清单（本轮唯一一次冻结前完成）

| 文件 | 原值 | 新值 | 理由 |
|---|---|---|---|
| `AI_GUIDE.md` | `# LLMKE 技术施工基线 V1.1.0` | `V1.1.1` | A 类，人类入口页，必须与 `VERSION` 一致 |
| `README.md` | `# LLMKE V1.1.0 技术施工冻结基线` | `V1.1.1` | A 类，同上 |
| `loops/_template/LOOP.yaml` | `baseline_version: 1.1.0` | `1.1.1` | B 类，未来批次模板 |
| `loops/L1/LOOP.yaml` | `1.1.0` | `1.1.1` | B 类，未启动，将在新基线上执行 |
| `loops/L2/LOOP.yaml` | `1.1.0` | `1.1.1` | 同上 |
| `loops/L3/LOOP.yaml` | `1.1.0` | `1.1.1` | 同上 |
| `loops/L4/LOOP.yaml` | `1.1.0` | `1.1.1` | 同上 |
| `BUILD-INFO.txt` | 无版本口径段 | 新增「版本口径」 | 固化规则，防止再次混淆 |

## 3. 刻意不改的项（含理由）

| 文件 | 现值 | 不改的理由 |
|---|---|---|
| `loops/L0-contract-baseline/LOOP.yaml` | 1.1.0 | 已执行批次，1.1.0 是它当时的事实；改动等于改写历史 |
| `loops/L0-contract-baseline-r2/LOOP.yaml` | 1.1.0 | 同上（QA_PENDING，仍有历史证据） |
| `loops/LD-legacy-discovery/LOOP.yaml` | 1.1.0 | 已产生门禁证据 |
| `loops/LD-legacy-discovery-r2/LOOP.yaml` | 1.1.0 | DONE，已签 QA 绑定该基线 |
| `contracts/registry.yaml` | 1.1.0 | C 类契约包版本，未发生契约修订 |

## 4. 一致性验证（改动后、冻结前执行）

| 检查 | 期望 | 实跑 |
|---|---|---|
| `VERSION` 与 `FROZEN-MANIFEST.baseline_version` | 一致（冻结后） | 由 `freeze_baseline.py --write` 强制 |
| 未执行批次 `LOOP.yaml` 的 `baseline_version` | 全部 1.1.1 | `_template`/`L1`–`L4`/`r5` 均为 1.1.1 |
| 历史批次 `LOOP.yaml` | 保持 1.1.0 | `L0`/`L0-r2`/`LD`/`LD-r2` 仍 1.1.0 |
| `AI_GUIDE.md` / `README.md` 首行 | V1.1.1 | 已改 |
| `trace-check` | PASS（plan/actual 批次集一致） | 见 r5 建立后的实跑记录 |
| `baseline-check` | PASS（一次性冻结后） | 见本轮结果文档 |

## 5. 遗留（不在本轮范围，已登记）

- `loops/_template/LOOP.yaml` 只有 1 条门禁（`contract_generate_gate`），而实际批次有 8 条。
  模板并非可直接武装的批次定义；新批次必须用真实门禁集构造（r3/r4/r5 均如此）。
  **风险**：若有人直接用 `new_loop.py` 建批次并 arm，会得到只有 1 条门禁的弱批次。
  建议下个窗口给 `new_loop.py` 增加「门禁数不足则拒绝 arm」的校验，或让模板携带完整门禁集。
