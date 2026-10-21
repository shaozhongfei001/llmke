# FAILURES.md

Append-only run failures; actual failures are never deleted to obtain PASS.

### 2026-10-20T17:11:09.292991+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; contract_generate_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:48.708948+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:48.995833+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:49.246077+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:49.508615+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:49.768172+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:50.034852+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:50.282497+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:50.549790+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:50.796988+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:55:51.043591+00:00 contract_generate_gate

prior evidence invalid: baseline_gate: source/baseline changed; evidence STALE; contract_check_gate: source/baseline changed; evidence STALE; mutation_probe_gate: source/baseline changed; evidence STALE; p0_register_gate: source/baseline changed; evidence STALE; security_scan_gate: source/baseline changed; evidence STALE; traceability_gate: source/baseline changed; evidence STALE

### 2026-10-21T04:56:00.595947+00:00 contract_check_gate

gate prerequisite not passed: contract_generate_gate

### 2026-10-21T04:56:00.746457+00:00 mutation_probe_gate

gate prerequisite not passed: contract_check_gate

### 2026-10-21T04:56:00.899378+00:00 traceability_gate

gate prerequisite not passed: mutation_probe_gate

### 2026-10-21T04:56:01.053671+00:00 p0_register_gate

gate prerequisite not passed: traceability_gate

### 2026-10-21T04:56:01.196446+00:00 security_scan_gate

gate prerequisite not passed: p0_register_gate

### 2026-10-21T04:56:01.345993+00:00 baseline_gate

gate prerequisite not passed: security_scan_gate

### 2026-10-21T04:56:07.788957+00:00 security_scan_gate

command exited 2; evidence loops/L0-contract-baseline/evidence/security_scan_gate.log

## FAIL-2026-10-21-04 L0 门禁预算耗尽 + security_scan_gate 自污染（阻断）

### 现象
新增 `docs/integration/DOC2MD-WORKSPACE-DECISION.md` 后源码快照变化
（`488ea2a5…` → `69da69fc…`），既有 7 条门禁记录判为 STALE。按框架重跑后：
- 5 条恢复为 pass（`contract_generate/contract_check/mutation_probe/p0_register/traceability` @ 69da69fc）
- `security_scan_gate` **fail**
- 6 条门禁 attempts 已达 3/3（`baseline_gate` 2/3），**修复预算耗尽**
- `LD-legacy-discovery` 的 `inventory_gate` 同样 STALE，attempts 3/3

### 根因（两条叠加）
1. **快照绑定**：`docs/integration/` 不在快照排除前缀内，任何 `docs/**` 新增都会使既有证据 STALE
   （这是设计如此，不是缺陷）。
2. **安全门禁自污染（环境缺陷）**：`make run-dev` 的父 make 会把 `w`（print-directory）传给子 make，
   子 make 输出 `make[1]: 进入目录“<项目绝对路径>”`，该行被写进 `loops/*/evidence/*.log`；
   而 `security_scan.py --all-files` **会扫描这些证据日志**，命中 `PERSONAL_ABSOLUTE_PATH` 规则 → 失败 →
   失败的输出又写回同一日志 → 下一轮继续命中。项目位于 `/home/<user>/` 下时**必然复发**。
   （参考环境未复现，是因为其项目根不在 `/home/<user>/` 下。）

### 已验证的修复方向（环境级，不改冻结文件）
- `MAKEFLAGS=--no-print-directory` 可阻止子 make 打印绝对目录；
- 但**已写入的 4 份脏日志无法清洗**：证据日志按哈希绑定记录，重写即失效，而重跑受预算限制。

### 状态
**BLOCKED**。按框架 `on_exhausted` 规定：STOP，保留失败，由 TL 批准新修订/新批次，**不得手工重置 attempts**。
可选处置见 `memory/BLOCKED.md`。
