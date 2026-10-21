# L0-contract-baseline-r2 证据

本批次为原 `L0-contract-baseline` 的替代批次：原批次 6 条门禁预算耗尽（3/3）且
`security_scan_gate` 因证据日志含宿主绝对路径而失败，无法在原批次内恢复。

## 1. 前置治理动作（已获授权）

**业主于 2026-10-21 明确授权重写冻结基线**。变更面（授权前已精确测量并报备）：

| 类型 | 数量 | 明细 |
|---|---|---|
| 新增控制文件 | 2 | `loops/L0-contract-baseline-r2/LOOP.yaml`、`loops/LD-legacy-discovery-r2/LOOP.yaml` |
| 内容变化 | 1 | `docs/PROJECT-PLAN.yaml`（登记两个 r2 批次） |
| 删除 | 0 | — |

执行：`python3 scripts/freeze_baseline.py --write` → `FROZEN-MANIFEST.json` 文件数 196 → 198，
`make baseline-check` PASS。
备注：manifest 的 `authority` 文本仍为补丁原文（生成器硬编码），本次重冻结的授权依据记录在本文件与
`FAILURES.md`，不修改生成器。

## 2. 根因修复（环境级，未改任何冻结脚本）

原失败链：父 `make` 把 `w`（print-directory）传给子 make → 子 make 输出
`make[1]: 进入目录“<项目绝对路径>”` → 写入 `loops/*/evidence/*.log` →
`security_scan.py --all-files` 扫描这些日志 → 命中 `PERSONAL_ABSOLUTE_PATH` → 失败输出写回同一日志。

处置：
1. 4 份被污染的**旧批次**日志移出仓库（备份区 `superseded-L0-evidence-20261021/`），并在
   `loops/L0-contract-baseline/FAILURES.md` / `memory/BLOCKED.md` 留痕；
2. 门禁运行时导出 `MAKEFLAGS=--no-print-directory`，使新日志不再含宿主路径（本次全部新日志已复验干净）。

## 3. 门禁结果（同一快照 `d0530bee…`）

| 门禁 | 结果 |
|---|---|
| `contract_generate_gate` | pass |
| `contract_check_gate` | pass |
| `mutation_probe_gate` | pass（13/13 回归） |
| `traceability_gate` | pass |
| `p0_register_gate` | pass（integrity） |
| `security_scan_gate` | pass（**415 file(s) scanned**） |
| `baseline_gate` | pass |
| `independent_qa_gate` | **NOT_RUN / QA_PENDING**（需受保护环境外部签署） |

端到端复核：`make framework-verify` → **exit 0**，`127 passed`；
`make p0-gate` → **exit 2**（四项 P0 仍 OPEN，正确阻断）。

## 4. 本批次不证明

- 不证明业务可交付；P0-01/02/03/04 仍全部 OPEN，L1–L4 仍 BLOCKED。
- 不构成独立 QA 签署（开发身份不得自签）。
- 旧批次 `L0-contract-baseline` 的证据仍为红（已 superseded，不修复、不删除其失败记录）。
