# L0-contract-baseline — 证据板

## 基线

| 项 | 证据 | 说明 |
|---|---|---|
| 框架底座 | `.framework-manifest.json` | agentic-sdd-framework 2026.08.01-rc1，111 文件受控安装 |
| 合同清单 | `contracts/registry.yaml` | 9 份合同，id/version/layer/depends_on 齐备 |
| 生成报告 | `contracts/build/generate-report.json` | 每份合同的输入哈希 → 产物哈希 |
| 检查报告 | `contracts/build/check-report.json` | 结构/分层/哈希联动逐条判定 |
| 追溯矩阵 | `docs/DESIGN-TRACE.md` | 合同↔设计↔门禁 |

## 门禁证据（dev 自检，executor=integration-agent）

| 门禁 | 结果 | 命令 | 证据 | 备注 |
|---|---|---|---|---|
| contract_generate_gate | PASS | `make generate` | `loops/L0-contract-baseline/evidence/contract_generate_gate.log` | 9/9 合同生成，无 EMPTY_OUTPUT |
| contract_check_gate | PASS | `make check` | `loops/L0-contract-baseline/evidence/contract_check_gate.log` | 无 DRIFT / UNREGISTERED / LAYERING |
| mutation_probe_gate | PASS | `python3 scripts/mutation_probe.py` | `loops/L0-contract-baseline/evidence/mutation_probe_gate.log` | **4/4 探针满足变异必红、恢复必绿** |
| traceability_gate | PASS | `python3 scripts/trace_check.py` | `loops/L0-contract-baseline/evidence/traceability_gate.log` | 9 合同 ↔ 矩阵 ↔ 批次声明一致 |
| p0_register_gate | PASS | `make p0-check` | `loops/L0-contract-baseline/evidence/p0_register_gate.log` | 4 项 P0 登记完整；**全 OPEN 属预期** |
| security_scan_gate | PASS | `make security-check` | `loops/L0-contract-baseline/evidence/security_scan_gate.log` | 无秘密、无敏感产物 |
| independent_qa_gate | **PENDING** | 见 LOOP.yaml | - | 未执行：开发身份不得自签 QA（红线 6） |

## 关键机制证据（不是结论，是可复跑的命令）

| 机制 | 证明方式 | 结果 |
|---|---|---|
| 合同漂移会被抓 | 改 `llmke-graph-api` 不重新生成 → `make check` | FAIL: DRIFT ✅ |
| 未登记文件会被抓 | 放 `contracts/api/orphan-probe.yaml` | FAIL: UNREGISTERED_CONTRACT ✅ |
| 生成器不是 noop | 破坏 `openapi` 键 → `make generate` | FAIL: not an OpenAPI 3.x document ✅ |
| 分层规则真的生效 | application 合同写入 `echarts` → `make check` | FAIL: LAYERING ✅ |
| P0 不能靠改状态关闭 | `status: CLOSED` 且无证据 → `make p0-check` | FAIL: CLOSED requires evidence ✅ |
| 接受风险不能偷跑 | `ACCEPTED_RISK` 但保留 `blocks` | FAIL: must empty blocks ✅ |
| P0 未关闭时实施被拒 | `make p0-gate` | FAIL: 4 OPEN（预期）✅ |

## 产物清单

- `contracts/`：3 份 OpenAPI、3 份 JSON Schema、1 份 semantic、1 份 evidence、1 份 evaluation
- `generated/sdk/`：3 份类型骨架
- `generated/schema/`：2 份规范化快照（含内容哈希）
- `scripts/`：`p0_closure_check.py`、`mutation_probe.py`、`trace_check.py`、`generators/schema_snapshot.py`

## 结论

dev 自检 6/6 绿，且**每一项都做过变异复验**。
未完成：独立 QA（`independent_qa_gate`），因此本批次不得标记为已验收。
