# r7 独立 QA 交接（W-01 + W-01b）

> **本文件已作废（r7 已被 SUPERSEDED）。**
> 保留原因：记录当时的候选指纹与签署步骤，供复盘。
> **不要**用它去签当前批次；当前无活动候选，需先建新批次（见 `NEXT-SESSION.md`）。


> 本文件不是批准记录。r7 当前为 `QA_PENDING`，**不得**表述为已通过或可合并。

## 1. 候选身份

| 项 | 值 |
|---|---|
| 批次 | `L0-contract-baseline-r7` |
| `baseline_sha256` | `59ab8258b3633271c794ad8a15923f8c879248715ba7f069b933801ff4100618` |
| `FROZEN-MANIFEST` | `revision=8`、控制面 208 文件、`baseline_version=1.1.1` |
| 开发门禁 | 7/7 pass（`digest_scheme=3`） |
| QA 门禁 | `independent_qa_gate`：`QA_PENDING` / `LOCAL_QA_CANDIDATE` |
| 载荷 | `docs/baseline/validation/qa-payload-r7.json` |

## 2. 为什么必须由 `qa-owner` 执行

1. 信任根里 `approved_baseline_sha256` 仍指向窗口前的旧基线，
   与 `59ab8258…` 不符 → 任何签名都会被 `external approved baseline digest mismatch` 拒绝；
2. 由实现者签名、或由实现者改信任根锚点 = **自签**，独立性当场失效。

## 3. 签署流程（供 qa-owner 使用）

```bash
# 0) 先在受保护环境把信任根 approved_baseline_sha256 更新为 r7 的值（这是 owner 的动作）
export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json

# 1) 重新生成载荷（有效期 1 小时；gate_spec_sha256 与 log_sha256 不会变）
cd ~/data/dev/llmke-r8
PATH=~/data/dev/llmke/.venv/bin:$PATH PYTHONPATH=$PWD \
  python3 scripts/qa_payload.py --loop L0-contract-baseline-r7 --gate independent_qa_gate \
  --principal-id qa-owner-01 --out docs/baseline/validation/qa-payload-r7.json

# 2) 用受保护私钥签名（私钥不得进入工作树）
PATH=~/data/dev/llmke/.venv/bin:$PATH PYTHONPATH=$PWD \
  python3 scripts/qa_sign.py --payload docs/baseline/validation/qa-payload-r7.json \
  --key <key-path> --key-id <key-id> --out /tmp/r7-attestation.json

# 3) 接受
PATH=~/data/dev/llmke/.venv/bin:$PATH PYTHONPATH=$PWD \
  python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r7 \
  --gate independent_qa_gate --attestation /tmp/r7-attestation.json

# 4) 校验
PATH=~/data/dev/llmke/.venv/bin:$PATH PYTHONPATH=$PWD \
  python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r7   # 期望 PASS 且不再报 QA_PENDING
```

## 4. QA 应自行复核的 8 项

1. **版本与权限**：`VERSION=1.1.1`；`BASELINE-AUTHORITY.yaml` 含 `W-01` 且 `approved_by` 记录本次业主批准；
2. **冻结范围**：`revision=8`、208 文件；`Makefile`、`baseline_support.py`、`loop_guard.py` 均在其中；
3. **证据摘要**：7 条开发门禁记录含 `control_sha256`/`doc_sha256`/`code_sha256`、`digest_scheme=3`；
4. **门禁结果**：`run_batch` 输出 7 条 pass；`framework-verify` exit 0 / 193 passed；
5. **对抗测试**（务必自己跑一遍，勿只读结论）：
   - 改 `modules/**` 一行注释 → `evidence-check` 必须 **FAIL** 且点名 `independent_qa_gate`；
   - `contracts/` 加文件 → 8/8 STALE；
   - `docs/` 加文件 → 仅 `traceability_gate` STALE；
   - 篡改任一证据日志 → `evidence hash mismatch`；
6. **状态语义**：r5/r6 为 `SUPERSEDED`（证据保留、不再参与当前候选）；r7 为 `QA_PENDING`；
7. **文档一致性**：`W-01-RESULT.md` §3.1 的实验与本机复跑结果一致；
8. **拟合并差异**：r7 所在工作树与 `main` 的差异仅含本窗口提交，无未审查改动。

## 5. 已知局限（签署前请确认可接受）

- `code_digest` 覆盖 `modules/apps/services/lib/frontend` 的 `*.py`（排除 `tests`/`__pycache__`），
  **不覆盖**非 `.py` 资源（模板、配置、静态资源）；
- 只有 `independent_qa_gate` 声明依赖代码；7 条开发门禁仍只绑控制面；
- 模块测试已进门禁，但未单列为独立门禁条目（L3 未做，见方案 §3.4）。
