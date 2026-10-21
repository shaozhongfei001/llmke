# DRAFT

先完成切片目标、依赖、角色和门禁，再由 TL 武装。

### 2026-10-21T05:09:13.415354+00:00 contract_generate_gate

frozen control file set changed; frozen control changed: docs/PROJECT-PLAN.yaml

### 2026-10-21T08:09:28.613112+00:00 independent_qa_gate

command exited 2; evidence loops/L0-contract-baseline-r2/evidence/independent_qa_gate.log

### 2026-10-21T08:10:10.138125+00:00 independent_qa_gate

command exited 2; evidence loops/L0-contract-baseline-r2/evidence/independent_qa_gate.log

## FAIL-2026-10-21-06 QA 门禁因「日志自引用」连续失败，预算耗尽

### 现象
`independent_qa_gate` 三次运行全部 fail（attempts 3/3，预算耗尽）：
1. 第 1 次：调用方 shell 用的是 conda base 的 python3，`make generate` 抛
   `ModuleNotFoundError: No module named 'openapi_spec_validator'` → exit 2；
2. 第 2 次：换用 venv 解释器后，`security_scan` 仍失败，命中的是**上一次失败日志**里
   残留的 traceback 绝对路径（`.../scripts/contract_generate.py`）；
3. 第 3 次：同一次失败把「扫描命中」写入自身日志，形成**自引用**：
   `FAIL: .../independent_qa_gate.log:8: PERSONAL_ABSOLUTE_PATH`。

### 根因（两条叠加，均与环境有关，与代码无关）
- **解释器未固定**：门禁 argv 是 `make framework-verify`，其内部 `python3` 取自 PATH；
  调用方未激活 venv 时用的是系统/conda 解释器，缺 `openapi_spec_validator` 等依赖。
- **证据日志自引用**：`run_gate` 在**运行结束后**才重写日志，因此运行期间磁盘上是**上一次**的内容；
  若上次内容是失败 traceback（含宿主绝对路径），`security_scan --all-files` 会把它当命中，
  本次失败又把命中文本写回同一文件 → 下一轮继续命中。

### 处置
- 第 1 次失败的日志移出仓库（备份区 `superseded-L0r2-qa-log-20261021/`），
  失败事实保留在本文件与 `evidence/events.jsonl`（fail 记录不参与哈希校验，移动不影响 evidence-check）。
- 永久修复方向：门禁一律通过 `coordination/qa-run.sh` 调用（固定 venv PATH + `MAKEFLAGS`），
  并保证新批次目录初始无日志（首轮扫描不会读到历史失败内容）。

### 状态
`independent_qa_gate` **BLOCKED（预算耗尽）**。L0-r2 的 7 条开发门禁仍为 pass；
按 `on_exhausted` 规定不得手工重置 attempts，需另开批次或由 owner 裁定。
