# r9 独立 QA 交接（W-05 / W-05b / W-02 / W-04）

> **本文件已作废（r9 已被 SUPERSEDED）。**
> 保留原因：记录当时的候选指纹与签署步骤，供复盘。
> **不要**用它去签当前批次；当前无活动候选，需先建新批次（见 `NEXT-SESSION.md`）。


> 本文件不是批准记录。r9 当前为 `QA_PENDING`，**不得**表述为已通过或可合并。

## 1. 候选身份

| 项 | 值 |
|---|---|
| 批次 | `L0-contract-baseline-r9` |
| `baseline_sha256` | `cf8a72c845ad7fd9052b3e4919688da714aeb990bbbf65280b50e196d719d972` |
| 冻结 | `revision=10`、控制面 211 文件、`baseline_version=1.1.1` |
| 门禁 | 9 条：8 条开发门禁 `pass` + `independent_qa_gate` `QA_PENDING` |
| 载荷 | `docs/baseline/validation/qa-payload-r9.json` |

## 2. 为什么必须由 `qa-owner` 执行

1. 信任根 `approved_baseline_sha256` 仍指旧基线 `c8a73c37…`，与 `ba3bcb8b…` 不符，
   任何签名都会被 `external approved baseline digest mismatch` 拒绝；
2. 实现者签名或实现者改锚点 = 自签，独立性失效。

## 3. 签署流程

```bash
export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
cd ~/data/dev/llmke-r9
export PATH=~/data/dev/llmke/.venv/bin:$PATH

# 1) 重新生成载荷（有效期 1 小时；gate_spec/log 哈希不变）
PYTHONPATH=$PWD python3 scripts/qa_payload.py --loop L0-contract-baseline-r9 \
  --gate independent_qa_gate --principal-id qa-owner-01 \
  --out docs/baseline/validation/qa-payload-r9.json

# 2) 用受保护私钥签名（私钥不得进入工作树）
PYTHONPATH=$PWD python3 scripts/qa_sign.py \
  --payload docs/baseline/validation/qa-payload-r9.json \
  --key <key-path> --key-id <key-id> --out /tmp/r9-attestation.json

# 3) 接受
PYTHONPATH=$PWD python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r9 \
  --gate independent_qa_gate --attestation /tmp/r9-attestation.json

# 4) 校验
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r9
```

## 4. QA 应自行复核的 9 项

1. **版本与权限**：`VERSION=1.1.1`；`BASELINE-AUTHORITY.yaml` 的 `change_list` 含 `P-01/P-03/P-04/P-05/P-06/W-01`；
   **注意：W-05/W-05b/W-02/W-04 尚未写入 `change_list`**（见 §5 第 1 条，需业主补授权留痕后再签）；
2. **冻结范围**：`revision=9`、210 文件；`Makefile`、`scripts/_pin.py`、`scripts/run_batch.py`、
   `scripts/loop_guard.py`、`GATE-CATALOG.yaml`、`tests/test_loop_guard.py` 均在冻结清单内；
3. **证据摘要**：9 条记录均含 `control_sha256`/`doc_sha256`/`code_sha256`，`digest_scheme=3`；
4. **门禁结果**：`run_batch` 8 条 pass；`framework-verify` exit 0 / **194 passed**；
5. **解释器可复现性**（本窗口核心）：
   ```bash
   env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME \
     LLMKE_PYTHON=$HOME/data/dev/llmke/.venv/bin/python3 \
     bash -c 'cd ~/data/dev/llmke-r9 && python3 scripts/run_batch.py --loop <新批次> --executor qa'
   ```
   应在无 venv 的 PATH 下仍全部通过（证明入口自钉生效）；
6. **对抗测试**（自行跑一遍）：
   - 先 `qa-run` 已有候选 → 改 `modules/**` 一行注释 → `evidence-check` 必须 FAIL 且点名 `independent_qa_gate`；
     候选生成前改代码不会 FAIL，这是预期（无记录绑定）；
   - `contracts/` 加文件 → 9/9 STALE；
   - `docs/` 加文件 → 仅 `traceability_gate` STALE；
   - 篡改任一证据日志 → `evidence hash mismatch`；
7. **状态语义**：r5/r6/r7 均 `SUPERSEDED`（证据保留）；r9 `QA_PENDING`；
8. **文档一致性**：`W-02-W05-RESULT.md` 的实测结果与本机复跑一致；
9. **拟合并差异**：r9 工作树与 `main` 的差异只含本窗口提交，无未审查改动。

## 5. 签署前必须先解决的两件事（诚实提示）

1. ~~授权留痕缺失~~ **已解决**：r8 因 `change_list` 缺本次条目被作废；r9 的
   `BASELINE-AUTHORITY.yaml` 已含 `W-02-W05` 条目（`approved_by: project-owner, 2026-10-22`），
   冻结 `revision=10` 已包含该变更。QA 只需核对 `FROZEN-MANIFEST.change_list` 是否含 `W-02-W05`。
2. **已知局限**：
   - `code_digest` 覆盖 `modules/apps/services/lib/frontend` 的 `*.py`（排除 `tests`/`__pycache__`），
     不含非 `.py` 资源；
   - 只有 `independent_qa_gate` 声明依赖代码；8 条开发门禁仍只绑控制面；
   - `_pin.py` 在既无 `LLMKE_PYTHON` 又无 `.venv` 时保持原行为（不报错）。
