# 门禁执行规则（GATE EXECUTION RULES）

本文件是**规则载体**，不是建议。凡是判定"门禁是否通过"的命令，必须遵守下列条款。

## R1 判定只认退出码，不认屏幕文字

门禁是否通过 = 进程退出码。任何形如 `make xxx | tail -n`、`cmd | grep PASS`
的写法都**不得**用于判定，因为管道返回的是最后一个命令的退出码。

```bash
# 错误：FAIL 会被打印出来，但退出码是 tail 的 0
python3 scripts/loop_guard.py evidence-check --loop L0-...-r10 | tail -2

# 正确：保留退出码
python3 scripts/loop_guard.py evidence-check --loop L0-...-r10 > /tmp/ec.log 2>&1
rc=$?; cat /tmp/ec.log; echo "rc=$rc"
```

**实例（2026-10-22，本项目真实发生）**：上述错误写法打印了
`FAIL: independent_qa_gate: invalid approval validity window`，而 `exit=0`。
若据此判定"通过"，就会把失效签名当成有效证据。

## R2 必须管道时，脚本内先 `set -o pipefail`

```bash
set -euo pipefail
```

只对自己的脚本有效；对交互式一行命令无效，因此 R1 优先。

## R3 需要断言时，先落日志再判

```bash
cmd > "$LOG" 2>&1; rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL($rc)"; tail -20 "$LOG"; exit 1; }
```

## R4 批量判定用 `PIPESTATUS[0]`

```bash
cmd | tee /tmp/out.log
rc=${PIPESTATUS[0]}
```

## 适用对象

`make *-gate`、`make framework-verify`、`loop_guard.py evidence-check|qa-run|accept-qa`、
`run_batch.py`、`freeze_baseline.py`、`qa_payload.py`，以及任何以退出码作为放行依据的命令。
