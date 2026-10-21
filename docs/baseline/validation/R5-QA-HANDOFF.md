# r5 独立 QA 交接包（含硬阻塞）

- 候选批次：`L0-contract-baseline-r5`
- 冻结基线：`VERSION=1.1.1`、`FROZEN-MANIFEST` revision **6**、控制面 **205** 文件
- `baseline_sha256 = 213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52`
- `source_snapshot_sha256 = f4f6ee2d9d5280dead4cbd748d159e4d1a05392a7cf7e6e8ce332fcc30c0078c`
- 本文件不参与源码快照与冻结控制面

---

## 1. 当前 QA 状态：**QUEUE 完成，签署未完成**

| 步骤 | 状态 | 证据 |
|---|---|---|
| 7 条开发门禁 | **全部 pass** | `loops/L0-contract-baseline-r5/evidence/manifest.json` |
| `framework-verify` | **exit 0 / 145 passed** | 本轮实跑日志 |
| `evidence-check` | **PASS** | 本轮实跑 |
| 对抗检查 3 组 | **全部按预期拒绝** | 见第 4 节 |
| QA 候选执行（`qa-run`） | **完成**：`status=QA_PENDING`、`role=LOCAL_QA_CANDIDATE`、`exit=0` | `evidence/independent_qa_gate.log` |
| **独立 QA 签名** | **未完成（BLOCKED）** | 原因见第 2 节 |
| 合并到 `main` | **未执行（条件未满足）** | — |

> `LOCAL_QA_CANDIDATE` 不是 QA 通过。它只表示「候选已按 QA 门禁的 argv 跑过一遍」。

## 2. 硬阻塞：信任根绑定的基线还是旧的

| 项 | 值 |
|---|---|
| 信任根 `approved_baseline_sha256` | `c8a73c3736db…`（窗口前的旧基线） |
| 当前 r5 冻结基线 | `213c6ebc203e…` |
| 直接后果 | `verify_envelope()` 会以 `external approved baseline digest mismatch` 拒绝任何签名 |

**为什么 TL 不能自己改**：信任根是「独立 QA 批准了哪条基线」的锚点，位于工作区之外
（`~/data/qa-keys/trust-root.json`）。由实现者修改它，等于自己决定「QA 批准哪条基线」，
独立性即刻失效。**必须由 `qa-owner` 或受保护运行环境更新。**

## 3. 待签载荷与签署步骤（由 qa-owner 执行）

载荷已生成：`docs/baseline/validation/qa-payload-r5.json`

| 字段 | 值 |
|---|---|
| `loop_id` | `L0-contract-baseline-r5` |
| `gate_id` | `independent_qa_gate` |
| `result` | PASS |
| `subject_sha256` | `732f729a452a4daf83064df6895a75df3d02e0edda354276abc07ce1e3c762f6` |
| `gate_spec_sha256` | `0d6366b55aa1…` |
| `log_sha256` | `2128ea35e312…` |
| `issued_at` → `expires_at` | 1 小时有效（见载荷） |

```bash
cd ~/data/dev/llmke

# ① 由 qa-owner 在受保护环境更新信任根的基线锚点（这是批准动作，不是技术配置）
#    把 approved_baseline_sha256 改为 213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52

# ② 立即重签（载荷只有 1 小时有效期；过期需重新 qa-run 生成新载荷）
python3 scripts/qa_payload.py --loop L0-contract-baseline-r5 --gate independent_qa_gate \
    --principal-id qa-owner-01 --out docs/baseline/validation/qa-payload-r5.json
LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json \
python3 scripts/qa_sign.py --key-file $HOME/data/qa-keys/llmke-qa.key \
    --key-id qa-ed25519-2026-10 --payload docs/baseline/validation/qa-payload-r5.json \
    --out docs/baseline/validation/qa-envelope-r5.json

# ③ 接受并收口
python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r5 \
    --gate independent_qa_gate --attestation docs/baseline/validation/qa-envelope-r5.json
python3 scripts/loop_guard.py finish --loop L0-contract-baseline-r5
```

> 第 ② 步的 `qa_payload.py` 必须在第 ① 步之后立即执行：载荷里的
> `baseline_sha256` 取自当前冻结清单，与信任根必须一致才能通过校验。
>
> 若 `expires_at` 已过，不要延长有效期；重新跑 ② 即可（`gate_spec_sha256` 与 `log_sha256` 不变）。

## 4. 独立 QA 应自行复核的清单（不要只信本文件）

| # | 检查项 | 复核方法 |
|---|---|---|
| 1 | 版本一致性 | `cat VERSION` 应为 `1.1.1`；`AI_GUIDE.md`/`README.md` 首行为 V1.1.1；`_template`/`L1`–`L4`/`r5` 的 `baseline_version=1.1.1`；历史批次仍 `1.1.0`（见 `T1-VERSION-REGISTER.md`） |
| 2 | 冻结范围 | `python3 scripts/freeze_baseline.py` → PASS；`FROZEN-MANIFEST.files` 数为 205 |
| 3 | 证据摘要 | `python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5` → PASS |
| 4 | 7 条门禁 | 读 `evidence/manifest.json`，确认 `role=DEV_SELF_CHECK`、`digest_scheme=2`、`exit_code=0` |
| 5 | 对抗性 | 重跑第 5 节三组，确认仍然拒绝 |
| 6 | 状态语义 | `r5=QA_PENDING`；`r4=IN_DEV`（历史候选，未改写）；`r3=SUPERSEDED`；`LD-r2=DONE`（历史签名，不得当作当前证据） |
| 7 | 文档一致性 | 全仓 grep `1.1.0` 只剩契约包版本与历史批次，且 `BUILD-INFO.txt` 的「版本口径」段能解释每一处 |
| 8 | 拟合并差异 | `git diff --stat main..HEAD`；并用 `git worktree` 实测合并后树哈希等于分支树（本轮已验证 `7db46fca…`） |

## 5. 对抗检查（可复跑，三组都要拒绝）

```bash
cd ~/data/dev/llmke
echo "x: 1" > contracts/_qa_probe.yaml
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5   # 期望 FAIL：7/7 STALE
rm contracts/_qa_probe.yaml

cp loops/L0-contract-baseline-r5/evidence/baseline_gate.log /tmp/bk.log
echo tampered >> loops/L0-contract-baseline-r5/evidence/baseline_gate.log
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5   # 期望 FAIL：hash mismatch
cp /tmp/bk.log loops/L0-contract-baseline-r5/evidence/baseline_gate.log

echo probe > docs/_qa_probe.md
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5   # 期望 FAIL：仅 traceability_gate
rm docs/_qa_probe.md
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5   # 期望 PASS
```

## 6. 合并前必须同时成立的五个条件（当前满足 1 项）

| # | 条件 | 现状 |
|---|---|---|
| 1 | r5 开发门禁 + `evidence-check` 全通过 | **满足** |
| 2 | 独立 QA 对 r5 冻结候选给出允许合并的结论 | **未满足**（信任根未更新 + 未签名） |
| 3 | 拟合并树与 QA 审阅树一致 | 合并前需最后一次 `git rev-parse HEAD^{tree}` 与 QA 记录中的树比对 |
| 4 | 合并差异已核对，无未审查提交 | 本轮已验证 `main` 是祖先且合并结果树 == 分支树 |
| 5 | 合并符合分支保护规则 | `main` 无保护规则文件，按项目约定执行 `--no-ff`，不强推 |

**结论：在当前状态下不得合并。** TL 不以任何形式代替第 2 项。
