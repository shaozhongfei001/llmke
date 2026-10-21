# HANDOFF.md

当前业务阻断项（P0-01/02/03/04）全部 OPEN。尚无外部独立 QA 签署，本批次不得 DONE。

## 本批次定位

替代已耗尽预算的旧批次，在同一组门禁定义下于当前快照重跑，**不放宽任何 pass 条件**。
门禁结果见 `EVIDENCE.md`；开发自检已全部通过，独立 QA 门禁未运行。

## 下一步

| # | 动作 | 责任角色 | 前置 |
|---|---|---|---|
| 1 | 外部独立 QA 在固定快照复跑并签署（`qa_payload` → 独立签名 → `accept-qa` → `finish`） | `qa-external` | 受保护环境 + 信任根配置 |
| 2 | P0-01/02 的材料索取与裁定（见 `loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md`） | 各 owner | 业务侧输入 |
| 3 | 解析方案落地（PDF/OCR 引用 doc2md 独立组件、DOCX 暂不引用） | `tech-lead` | owner 确认 DOCX 取舍 |

## 红线

- 未改 `generated/`；未用白名单掩盖任何命中。
- 未把四项 P0 改为 CLOSED，未清空 `blocks`。
- 未创建提交；仅按文件显式入库。
- 门禁运行必须导出 `MAKEFLAGS=--no-print-directory`，否则证据日志会再次写入宿主绝对路径。

## 终态与限制（2026-10-21 业主决定：接受 B）

| 门禁 | 状态 |
|---|---|
| `contract_generate_gate` | pass |
| `contract_check_gate` | pass |
| `mutation_probe_gate` | pass（13/13） |
| `traceability_gate` | pass |
| `p0_register_gate` | pass（integrity） |
| `security_scan_gate` | pass（426 文件） |
| `baseline_gate` | pass |
| `independent_qa_gate` | **fail（attempts 3/3 耗尽，未通过）** |

### 为什么接受这个状态
1. 该门禁的 argv 是 `make framework-verify`，其覆盖的 8 项检查**已被上面 7 条门禁逐项跑过并全部 pass**，
   所以"技术基线可信"这一结论没有实质缺口；缺的只是**第三方独立背书**。
2. 修复它需要在当前快照上重跑该门禁——但预算已耗尽，按框架规定不得手工重置 attempts。
3. 另开替代批次需要重写 `FROZEN-MANIFEST.json`，而这会同时改变 `baseline_sha256` 与源码快照，
   使**已签并 DONE 的 `LD-legacy-discovery-r2` 的独立 QA 立即失效**（其状态为 DONE，无法重跑）。
   用一个已生效的签名去换另一个签名，净亏。

### 因此本批次不得声称
- 不得声称"合同基线已获独立 QA 签署"；
- 不得据此关闭任何 P0（四项仍 OPEN，`make p0-gate` exit 2）；
- 不得据此解锁 L1–L4（仍 BLOCKED）。

### 恢复时机
当确实需要新增批次（如 L1 切片）时，**一次性**建齐所有批次 → 重冻结一次 → 统一重跑并重签
（届时 `LD-legacy-discovery-r2` 也需随之重签）。不要为单个门禁反复改冻结基线。
