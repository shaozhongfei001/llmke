# W-05 已验证补丁：Makefile 不再从 PATH 取解释器（R-02 根治）

日期：2026-10-22　状态：**已在隔离工作树验证通过，未应用到 r8**
补丁：`docs/baseline/validation/patches/w05-makefile-python.diff`（98 行，仅动 `Makefile`）

> 未应用的原因：r7 是 `QA_PENDING` 候选，改 `Makefile` 会让它立即 STALE。
> 应用时机 = 下一个窗口（与 W-02/W-04 一起，一次冻结）。

---

## 1. 补丁做了什么

| 项 | 内容 |
|---|---|
| 新增 2 个变量 | `LLMKE_PYTHON ?= $(shell [ -x .venv/bin/python3 ] && echo .venv/bin/python3 \|\| echo python3)`、`PY := $(LLMKE_PYTHON)` |
| 机械替换 | `@python3 ` → `@$(PY) `，**共 24 处** |
| 新增诊断目标 | `python-info`：打印 `make sees: <真实解释器路径>` |
| 未改 | 任何目标的命令语义、pass 条件、门禁集合 |

为什么这样设计：

1. **优先级明确**：显式变量 > 仓库内 `.venv` > PATH。worktree 没有 `.venv` 时由 `mk.sh` 注入绝对路径；
2. **回退不静默**：没有 venv 也没有变量时仍回退 PATH，但 `python-info` 与失败栈都会暴露真实路径；
3. **不动 pass 条件**：这是环境修复，不是放宽门禁。

---

## 2. 验证矩阵（隔离工作树 `/tmp/w05-probe`，detached at `a800fe6`）

| # | 场景 | 命令要点 | 结果 |
|---|---|---|---|
| 1 | PATH 里**没有** venv（模拟 conda），只给 `LLMKE_PYTHON` | `env -i PATH=/usr/local/bin:/usr/bin:/bin LLMKE_PYTHON=…/venv/bin/python3 make framework-test` | **193 passed** |
| 2 | 既无变量也无 venv | `env -i PATH=/usr/local/bin:/usr/bin:/bin make python-info` | `make sees: /usr/bin/python3`（可见） |
| 2b | 同上跑测试 | `make framework-test` | **exit 2**，`ModuleNotFoundError: openapi_spec_validator`（**响亮失败，不静默**） |
| 3 | 仓库内存在 `.venv`（符号链接） | `env -i … make python-info` | `make sees: /tmp/w05-probe/.venv/bin/python3`，`framework-test` → **193 passed**（自动优先，无需变量） |
| 4 | 补丁后重冻结再全量核验 | `freeze_baseline.py --write` → `make framework-verify` | **exit 0 / 193 passed / baseline PASS** |
| 5 | 其他目标是否被 24 处替换破坏 | `p0-check` / `trace-check` / `security-check` | 均 **exit 0**；`security-check: PASS (596 files)` |
| 6 | 补丁能否应用到 r8 当前树 | `git apply --check` | **OK**（可干净应用） |

补充事实：补丁后未重冻结时 `framework-verify` 会在 `baseline-check` 报
`FAIL: frozen control changed: Makefile` —— 这是**正确行为**（控制面变了就必须重冻结），
不是补丁缺陷。

---

## 3. 应用步骤（下一窗口）

```bash
cd ~/data/dev/llmke-r8
git apply docs/baseline/validation/patches/w05-makefile-python.diff

# mk.sh 注入绝对路径（worktree 无 .venv 时必须）
#   在 coordination/mk.sh 增加：export LLMKE_PYTHON="$HOME/data/dev/llmke/.venv/bin/python3"

# 验收（注意：先在 conda 式 PATH 下验证，否则等于没测）
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME \
  LLMKE_PYTHON=$HOME/data/dev/llmke/.venv/bin/python3 \
  bash -c 'cd ~/data/dev/llmke-r8 && make framework-test'     # 期望 193 passed

# 一次性收口冻结（所有控制面改动做完之后）
python3 scripts/freeze_baseline.py --write
python3 scripts/freeze_baseline.py                            # 期望 baseline: PASS
```

---

## 4. 已知局限（不隐瞒）

- `$(shell ...)` 在**每次** make 调用时求值，检查的是 `$(CURDIR)/.venv`；若用 `make -C <dir>`，
  求值目录随 `-C` 变化。当前所有入口（`mk.sh`/`verify-all.sh`/`run_batch`）都是先 `cd` 再 `make`，不受影响；
- 只固定 `python3`。若将来引入 `pip`/`node` 等其他工具链命令，需各自处理；
- 不改变 `p0-gate` 的 `exit 2`，也不改变任何业务就绪结论。

---

## 5. 与前次事故的对应

| 事故 | 触发方式 | 本补丁是否覆盖 |
|---|---|---|
| 直接 `make framework-verify`（conda） | 人工命令 | 覆盖（`LLMKE_PYTHON` 或 `.venv`） |
| 同上的第二次复发 | 人工命令 | 覆盖 |
| `run_batch` 内部 spawn `make` | 脚本链 | 覆盖（子进程继承 `LLMKE_PYTHON`） |
| `mk.sh` 跑错工作树 | 入口脚本 | 已由 mk.sh 自动识别 root 处理（D6） |
