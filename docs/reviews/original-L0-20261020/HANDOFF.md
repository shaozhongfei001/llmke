# L0-contract-baseline — 交接

## 结果

**dev 自检完成，待独立 QA。** 交付的是「合同 + 门禁 + P0 登记」三件，
不含任何业务实现代码（设计如此）。

## 已交付

- **9 份合同**：`contracts/` 下 api×3、schema×3、semantic、evidence、evaluation，全部登记。
- **生成物**：`generated/sdk/*.types.json`（3）、`generated/schema/*.snapshot.json`（2），无手工编辑。
- **P0 登记**：`docs/registers/P0-CLOSURE.yaml`，4 项全部如实登记为 OPEN。
- **门禁脚本**：`p0_closure_check.py`（双模式）、`mutation_probe.py`（4 探针）、`trace_check.py`。
- **批次骨架**：`L0`（IN_DEV）+ `L1`（BLOCKED，示范 P0 阻断）。

## 门禁结果

| Gate | 结果 | 证据 |
|---|---|---|
| contract_generate_gate | PASS | `evidence/contract_generate_gate.log` |
| contract_check_gate | PASS | `evidence/contract_check_gate.log` |
| mutation_probe_gate | PASS（4/4） | `evidence/mutation_probe_gate.log` |
| traceability_gate | PASS | `evidence/traceability_gate.log` |
| p0_register_gate | PASS | `evidence/p0_register_gate.log` |
| security_scan_gate | PASS | `evidence/security_scan_gate.log` |
| independent_qa_gate | **PENDING** | 未执行 |

## 提交

仓库尚未产生首个 commit（`last_commit` 为空）。首次提交建议：

```bash
git add AI_GUIDE.md README.md Makefile contracts/ generated/ docs/ loops/ scripts/ .codebuddy/ .cursor/ .gitignore .env.example requirements.txt .security-allowlist .framework-manifest.json
git commit -m "feat(l0): 合同基线 + 门禁 + P0 登记"
```

注意：**不要 `git add .`**（红线 7）。`contracts/build/` 属运行产物，按 `.gitignore` 处理。

## 已知事项（交接必须说清）

1. `independent_qa_gate` 未跑：开发身份自签无效，需独立 QA 以 `--role qa` 记录。
2. `make p0-gate` **当前必然 FAIL**（4 项 OPEN）。这是预期状态，不是缺陷。
3. `contracts/build/` 每次 generate/check 都会重写，属产物不是资产。
4. 合同里的默认值（如 `graph.algo=ppr`）来自源码事实，改动需附源码证据。

## 恢复方式

1. 读本文件 → `LOOP.yaml` → `STATE.json` → `EVIDENCE.md` → `FAILURES.md`
2. 复跑：`make contract-all && python3 scripts/mutation_probe.py && make p0-check`
3. 若门禁与记录不一致，以**命令输出**为准，并先修记录。

## 下一个批次

`L1-implementation` 已存在但为 BLOCKED：`make p0-gate` 绿之前不得武装。
解除条件见 `loops/L1-implementation/memory/BLOCKED.md`。
