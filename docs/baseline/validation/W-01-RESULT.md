# W-01 / W-01b 窗口实施结果

日期：2026-10-21　工作树：`~/data/dev/llmke-r8`（`round8/delivery`）
裁决：业主选**乙**（放弃 r5，W-01 与建批次在同一次冻结内完成），并批准三个冻结面文件。

---

## 1. 结论

| 项 | 结果 |
|---|---|
| 门禁内测试 | **145 → 193 passed**（+39 模块测试 +9 新增测试） |
| `framework-verify` | **exit 0** |
| r7 开发门禁 | **7/7 pass**（scheme=3） |
| r7 QA | **QA_PENDING / LOCAL_QA_CANDIDATE**（未签名，不得称通过） |
| `p0-gate` | **exit 2**（四项 P0 仍 OPEN，L1–L4 仍 BLOCKED） |
| 冻结 | `revision=8`、控制面 **208** 文件、`baseline_version=1.1.1` |

---

## 2. 改了什么

| 文件 | 改动 | 类型 |
|---|---|---|
| `Makefile` | `framework-test`: `pytest tests/` → `pytest tests/ modules/` | L1 收集缺口 |
| `scripts/baseline_support.py` | 新增 `CODE_ROOTS`/`code_files`/`code_digest`/`CODE_DEPENDENT_GATES`；`DIGEST_SCHEME=3` | L2 绑定缺口 |
| `scripts/loop_guard.py` | 记录 `code_sha256`；scheme≥3 且门禁属 `CODE_DEPENDENT_GATES` 时比较它；**W-01b**：`evidence-check` 不再跳过 `QA_PENDING` 记录 | L2 + 假绿修复 |
| `tests/test_code_digest.py`（新增） | 9 条：口径、变更检测、窄绑定、scheme=2 兼容、QA 候选过期可见 | — |
| `docs/baseline/BASELINE-AUTHORITY.yaml` | `change_list` 增 `W-01`（含 `approved_by` 与实测缺口依据） | 授权留痕 |

**刻意不做**：不把业务代码并入 `control_digest`（否则每次改代码作废全部门禁，重演 P-03 前的返工）。
`VERSION` 保持 `1.1.1`：W-01 不改变任何契约与 pass 条件，只补证据绑定范围。

---

## 3. 关键验证（全部实跑）

### 3.1 W-01：代码绑定

```
evidence-check（基线）            → PASS
在 assembler.py 追加一行注释       → FAIL: independent_qa_gate: implementation code changed; evidence STALE (exit 1)
git checkout 复原                 → PASS
```

**这条是本次窗口唯一的"绑定生效"证据。** 同一实验在 W-01 之前是 PASS（`digest_scheme=2` 不绑业务代码），
差异即结论。

### 3.2 W-01b：候选过期必须在读数阶段可见

首次实验之所以"没测到"，是因为 `evidence_errors` 有 `if status!='pass': continue`——
**`QA_PENDING` 记录被整条跳过**，于是"候选已过期"时 `evidence-check` 仍打印 PASS。
真正的拦截只在 `accept_qa`。这不影响门禁强度，但会误导读数。修复后：

- `QA_PENDING` 也参与 `stale_reasons` 判定；
- 不要求签名（未接受本来就没有签名）；
- 新增两条测试锁定：候选有效 → PASS；候选过期 → 非 0 且指名门禁。

### 3.3 对抗检查（证明没有放水）

| 动作 | 结果 |
|---|---|
| `contracts/` 加一个文件 | **8/8 STALE**（7 条开发 + QA），并报 `frozen control file set changed` |
| `docs/` 加一个文件 | **仅 `traceability_gate`** STALE |
| 证据日志追加一行 | `baseline_gate: evidence hash mismatch` |
| 复原后 | `evidence-check: PASS` |
| `p0-gate` | **exit 2** |

---

## 4. 批次处置

| 批次 | 状态 | 说明 |
|---|---|---|
| r5 | `SUPERSEDED` | 业主选乙；证据与日志原样保留 |
| r6 | `SUPERSEDED` | 建批后才发现 W-01b 需改 `loop_guard`（冻结面变），故作废重建 |
| **r7** | **`QA_PENDING`** | 当前候选；7 条开发门禁 pass |

r6 → r7 这次作废是**我自己的流程失误**：W-01 验收实验做晚了，导致"先冻结、后改脚本"。
教训与 r3 同源，已再次确认纪律：**验收实验必须前移到冻结之前**。

---

## 5. 冻结与候选指纹

| 项 | 值 |
|---|---|
| `FROZEN-MANIFEST` | `revision=8`、208 文件 |
| `baseline_sha256` | `59ab8258b3633271c794ad8a15923f8c879248715ba7f069b933801ff4100618` |
| `source_sha256`（QA 载荷） | `fe13c43d3aed515a5920a17d65372882385871d78e8a8f574041c80b502ccdec` |
| `subject_sha256` | `c6b8d31603eb73cf95163c0f4dfedafa11d55633671252ffddd4d6f4cf833549` |
| QA 载荷 | `docs/baseline/validation/qa-payload-r7.json`（有效期 1 小时，签署前需重新生成） |

---

## 6. 未关闭项

| 项 | 状态 | 责任方 | 缺什么 |
|---|---|---|---|
| r7 独立 QA 签名 | **BLOCKED** | `qa-owner` | 信任根 `approved_baseline_sha256` 仍指旧基线；且实现者不得自签 |
| P0-01…P0-04 | **OPEN** | interface/data/security/index-owner | 见 `P0-INPUT-INDEX.md` |
| P-02 语义 | BLOCKED | `qa-owner` | 三选一书面确认 |
| `requirements.lock` | BLOCKED | `baseline-owner` | 批准 |
| L3 独立 `framework.modules` 门禁 | 未做（方案 §3.4 已注明） | tech-lead | 需要下一次冻结窗口 |

---

## 7. 回退

`git revert` 本窗口提交 + `python3 scripts/freeze_baseline.py --write`。
注意：回退会让 r7 记录立即 STALE，需按 P-06 置终态并另建批次，**不得**就地重跑旧记录。
