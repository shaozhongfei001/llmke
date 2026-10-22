# HANDOFF — L0-contract-baseline-r5

## 定位

B 策略下的 **V1.1.1 收口候选**：T-12 版本一致性修复后、一次性冻结、重跑 L0 全部开发门禁。
与 r4 使用**同一组 8 条门禁**（7 开发 + 1 QA），**未放宽任何 pass 条件**。

## 当前状态

| 项 | 值 |
|---|---|
| 批次状态 | `QA_PENDING`（rev 12） |
| baton | `qa-external` |
| 冻结基线 | `VERSION=1.1.1`、`FROZEN-MANIFEST` revision 6、控制面 205 文件 |
| `baseline_sha256` | `213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52` |
| `source_snapshot_sha256` | `f4f6ee2d9d5280dead4cbd748d159e4d1a05392a7cf7e6e8ce332fcc30c0078c` |

| 门禁 | 状态 |
|---|---|
| `contract_generate_gate` | pass |
| `contract_check_gate` | pass |
| `mutation_probe_gate` | pass |
| `traceability_gate` | pass |
| `p0_register_gate` | pass（integrity） |
| `security_scan_gate` | pass |
| `baseline_gate` | pass |
| `independent_qa_gate` | **QA_PENDING（`LOCAL_QA_CANDIDATE`，非通过）** |

## 阻塞（唯一）

**独立 QA 签名**，原因有两层：

1. 信任根 `approved_baseline_sha256` 仍为 `c8a73c37…`（窗口前旧基线），当前为 `213c6ebc…`
   → `verify_envelope` 必然以 `external approved baseline digest mismatch` 拒绝；
2. 由实现者签名或改信任根 = 自签，违反独立性。

处置与精确命令见 `docs/baseline/validation/R5-QA-HANDOFF.md`（由 `qa-owner` 执行）。

## 红线

- 未改 `generated/`；未放宽任何门禁 pass 条件；未改 `P0-CLOSURE.yaml`。
- 未改动 r4 的证据与状态（`IN_DEV`，历史候选原样保留）；未删除任何 `evidence/**`。
- 未合并到 `main`；未强推；未创建任何伪造签名。

## 下一条精确命令

```bash
cd ~/data/dev/llmke
~/data/dev/coordination/mk.sh framework-verify                                  # 期望 0
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5     # 期望 PASS
```

签署与合并见 `docs/baseline/validation/R5-QA-HANDOFF.md` §3–§6。
