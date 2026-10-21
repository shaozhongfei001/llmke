# L0-contract-baseline — 失败记录

> 规则：先记录再修复；每条必须有根因与重跑结果。没有失败也要写「本次无失败」。

## F-001 未先 generate 就 check，误判为合同损坏

- Gate: contract_check_gate
- Time: 2026-10-20
- Command: `make check`（在首次 `make generate` 之前）
- Symptom: `FAIL: example-api: LINKAGE: generated output missing/empty`
- Root cause: 顺序颠倒。check 校验的是「生成报告 ↔ 磁盘产物 ↔ 合同哈希」三方一致，
  首次运行尚无生成报告与产物，必然 LINKAGE 失败。**不是合同写错了。**
- Owner: integration-agent
- Fix: 先 `make generate` 再 `make check`；Makefile 增 `contract-all` 目标把顺序固化，
  避免下次再靠记忆。
- Rerun command: `make contract-all`
- Rerun result: PASS (9 contracts)
- Status: fixed

## F-002 追溯矩阵以路径为键，注册表以 id 为键，导致追溯检查失败

- Gate: traceability_gate
- Time: 2026-10-20
- Command: `python3 scripts/trace_check.py`
- Symptom: `FAIL: 合同 llmke-retrieval-api 未出现在 DESIGN-TRACE.md`（3 条）
- Root cause: 设计追溯表只写了文件路径（`api/llmke-retrieval.openapi.yaml`），
  没写注册表主键 id。两个标识体系并行，人读没问题，机器比对断链。
- Owner: integration-agent
- Fix: 表格改为「`id`（`path`）」双写。
- Rerun command: `python3 scripts/trace_check.py`
- Rerun result: PASS
- Status: fixed

## F-003 沿用他项目的状态词，被状态机拒绝

- Gate: memory-check
- Time: 2026-10-20
- Command: `make memory-check LOOP=L0-contract-baseline`
- Symptom: `FAIL: LOOP.yaml unknown status: 'READY_FOR_DEV'`
- Root cause: 写作时沿用上游项目的 `ready_for_dev`，本框架枚举是
  `DRAFT / ARMED / IN_DEV / QA_PENDING / BLOCKED / DONE`。**状态词是门禁契约的一部分，
  不是自由文本。**
- Owner: tech-lead
- Fix: LOOP.yaml 与 STATE.json 同步改为 `IN_DEV`。
- Rerun command: `make memory-check LOOP=L0-contract-baseline`
- Rerun result: PASS
- Status: fixed

## F-004 证据单元格用批次相对路径，evidence-check 以仓库根为基准

- Gate: independent_qa_gate 前置（evidence-check）
- Time: 2026-10-20
- Command: `make evidence-check LOOP=L0-contract-baseline`
- Symptom: `EVIDENCE.md references missing/empty evidence: evidence/p0_register_gate.log`（6 条）
- Root cause: EVIDENCE.md 的「证据」列写成 `evidence/xxx.log`（相对批次目录），
  而 evidence-check 用 `root / ev_cell` 解析，基准是仓库根。两个基准并存。
- Owner: integration-agent
- Fix: 证据列统一改为仓库相对路径 `loops/L0-contract-baseline/evidence/xxx.log`，
  与 `evidence/manifest.json` 里的 `evidence` 字段保持同一写法。
- Rerun command: `make evidence-check LOOP=L0-contract-baseline`
- Rerun result: PASS
- Status: fixed

## F-005 security_scan_gate 首轮是空转；连带发现底座框架两个缺陷

- Gate: security_scan_gate
- Time: 2026-10-20
- Command: `make security-check`
- Symptom: 首次运行输出 `PASS (0 file(s) scanned)` —— **通过，但什么都没扫**。
- Root cause（三层，逐层挖出来的）：
  1. 扫描器用 `git ls-files` 取文件；新仓库尚未提交，清单为空 → 0 文件 → 恒 PASS。
  2. `.security-allowlist` 文档写「格式为 `file:substring`」，但 `is_allowlisted`
     实现是 `f"{rel}:{a}" in f"{rel}:{line}"`，对带文件名前缀的条目永远为假
     （拼出来是 `tests/x.py:tests/x.py:secret`）→ 白名单形同虚设。
  3. 改成扫工作树后暴露：底座框架自身测试夹具里的假的密码/主机/私钥
     （`tests/test_security_scan.py`）会命中；底座仓之所以「PASS」，
     是因为它的 `tests/`、`scripts/` 根本没被 git 跟踪，从来没被扫过。
- Owner: integration-agent
- Fix（三处，均为收紧而非放宽）：
  1. 新增 `--all-files`（扫工作树），`make security-check` 改用之；
     扫描范围为空时**直接 FAIL**，不再以 0 文件通过。
  2. `is_allowlisted` 按文档语义重写为 `file:substring` 精确匹配。
  3. 逐行阅读后新增 4 条白名单，每条都写明「为什么是误报」；
     不是屏蔽规则，是登记已审阅的例外。
- Rerun command: `make security-check`
- Rerun result: PASS (178 file(s) scanned) —— 从 0 到 178，这次是真扫
- Status: fixed
- 遗留：底座框架的这两处缺陷未回馈上游仓（本仓只改自己的一份），
  建议在评审后同步给 `agentic-sdd-framework` 维护方。

## 本次无其他失败

`independent_qa_gate` 未执行属流程安排（待独立 QA），不计为失败。
