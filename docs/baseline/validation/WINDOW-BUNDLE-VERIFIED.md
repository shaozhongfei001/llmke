# 下一窗口补丁包：已验证（W-05 / W-05b / W-02 / W-04）

日期：2026-10-22　状态：**已在隔离工作树端到端验证，未应用到 r8**
补丁：`docs/baseline/validation/patches/window-bundle-v1.diff`（212 行，6 个文件，`git apply --check` 通过）

> 未应用原因：r7 是 `QA_PENDING` 候选，改任何控制面文件都会让它立即 STALE。
> 使用时**整包应用**（4 项改动互相依赖，分开应用会冲突或漏改）。

---

## 1. 包里有什么

| 文件 | 改动 | 对应项 |
|---|---|---|
| `Makefile` | 新增 `LLMKE_PYTHON`/`PY`，`@python3` → `@$(PY)`（25 处）；新增 `module-test`、`python-info` 目标 | W-05 / W-02 |
| `scripts/_pin.py`（新） | 仅标准库的入口自钉：`LLMKE_PYTHON` → `.venv/bin/python3` → 保持现状；`os.execve` 重入一次 | W-05b |
| `scripts/run_batch.py` | 首个导入 `_pin` | W-05b |
| `scripts/loop_guard.py` | 首个导入 `_pin` | W-05b |
| `docs/policies/GATE-CATALOG.yaml` | 新增 `framework.modules`（`make module-test`） | W-02 |
| `tests/test_loop_guard.py` | 新增 1 条：签名有效但候选过期必须被拒 | W-04 |

---

## 2. 为什么需要 W-05b（本轮新发现）

W-05 只改 `Makefile`，**不够**。实测链条：

1. `loop_guard` 已把门禁 argv 里的 `python3` 换成 `sys.executable`；
2. 但如果**入口**自己就是被 `python3 scripts/run_batch.py`（conda）启动的，
   那么 `sys.executable` 就是 conda 解释器，后续每个门禁子进程都继承它；
3. 实测表现：`mutation_probe_gate` 失败（缺依赖），而不是全部失败——**更难排查**。

所以真正的修复点是入口：`_pin.py` 在任何重型导入之前把进程换成正确解释器。
放在 `baseline_support` 里太晚（它自己要先被导入），因此必须独立成仅标准库的薄模块。

---

## 3. 验证矩阵（隔离工作树，detached，验证后已删除）

| # | 场景 | 结果 |
|---|---|---|
| 1 | `PATH` 无 venv + `LLMKE_PYTHON` → `make framework-test` | **193 passed**（当时尚未加 W-04 测试） |
| 2 | 无变量、无 venv → `make python-info` | `make sees: /usr/bin/python3`（可见，不静默） |
| 3 | 仓库内 `.venv` 存在 → `make python-info` | `make sees: <repo>/.venv/bin/python3`；测试 193 passed |
| 4 | **用系统 `python3` 启动 `run_batch`**（模拟 conda），仅给 `LLMKE_PYTHON` | **8/8 开发门禁 pass**（含 `module_test_gate`） |
| 5 | 同上但**不装** `_pin`（对照） | `mutation_probe_gate` **FAIL**（缺依赖） |
| 6 | W-02 全链路：9 条门禁批次 | 8 pass + QA `PENDING`；`evidence-check: PASS` |
| 7 | W-04 变异测试：删掉 `accept_qa` 的 stale 检查 | 新增用例 **失败**（证明测试有效）；恢复后 15 passed |
| 8 | 合并包后重冻结 → `make framework-verify` | **exit 0 / 194 passed / baseline PASS** |
| 9 | `git apply --check`（对 r8 当前树） | **OK** |

---

## 4. 本轮发现的 3 条硬约束（都会影响窗口执行顺序）

### 4.1 `run_batch` 拒绝在"证据已失效"的批次上重跑

```
FAIL: prior evidence invalid: … evidence STALE
```

含义：任何控制面改动之后，**旧批次不能重跑**，必须新建批次。
这正是 r3 卡死、r6 作废的机制化表述——现在有明确报错，不再需要靠经验。

### 4.2 目录条目的 `allowed_kinds` 必须包含批次 `kind`

`L0-contract-baseline-*` 的 `kind=contract`。新增门禁若只写 `allowed_kinds: [implementation]`，
`arm` 会报 `gate differs from approved command catalog`，且**不指出是哪一条**。已在 §1 的补丁里写成三值齐全。

### 4.3 门禁 argv 的 `python3` 由 `sys.executable` 决定，不是由 `make` 决定

即：`Makefile` 的 `PY` 只影响 make 目标内部；门禁 argv 走的是另一条路。
两条路必须都被钉住（W-05 + W-05b）。

---

## 5. 应用步骤（下一窗口，顺序不可换）

```bash
cd ~/data/dev/llmke-r8
git apply docs/baseline/validation/patches/window-bundle-v1.diff

# 0) 确认没人在跑门禁；确认当前候选已处理（r7 要么已签并合并，要么已置终态）

# 1) 先在"坏 PATH"下验收，否则等于没测
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME \
  LLMKE_PYTHON=$HOME/data/dev/llmke/.venv/bin/python3 \
  bash -c 'cd ~/data/dev/llmke-r8 && make framework-test'        # 期望 194 passed

# 2) 一次性收口冻结
python3 scripts/freeze_baseline.py --write
python3 scripts/freeze_baseline.py                               # 期望 baseline: PASS

# 3) 必须新建批次（4.1）；沿用 9 条门禁定义，不放宽 pass 条件
python3 scripts/trace_check.py                                   # 先确认计划一致
#   建 L0-contract-baseline-rN + 登记 PROJECT-PLAN + 补齐 EVIDENCE/FAILURES/HANDOFF/SHARED_MEMORY
python3 scripts/loop_guard.py arm --loop L0-contract-baseline-rN --to integration-agent \
        --executor tech-lead --expected-revision 1
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME \
  LLMKE_PYTHON=$HOME/data/dev/llmke/.venv/bin/python3 \
  bash -c 'cd ~/data/dev/llmke-r8 && python3 scripts/run_batch.py --loop L0-contract-baseline-rN --executor integration-agent'

# 4) 全量核验 + 对抗（同 r7 那 4 条）+ 生成 QA 载荷
```

---

## 6. 已知局限

- `_pin.py` 只在 `LLMKE_PYTHON` 或 `<repo>/.venv` 存在时生效；两者都没有时**保持原行为**（不报错），
  这一点在 §3 第 2 行已实测为"可见但不阻断"；
- 只钉 `python3`，不钉 `pip`/`node` 等其他工具链；
- 新增第 9 条门禁属控制面，会让门禁数 8 → 9，QA 交接与 README 类说明需同步更新；
- 补丁包内 4 项互相依赖：**分拆应用会冲突**（`Makefile` 同一区域被两处修改）。

---

## 7. 与事故的对应

| 事故 | 本包是否覆盖 |
|---|---|
| 直接 `make`（conda）两次 | 覆盖（W-05） |
| `run_batch` 内部 spawn `make` | 覆盖（W-05 + W-05b） |
| 用系统 `python3` 直接起 `run_batch` | 覆盖（W-05b） |
| 候选过期仍显示 PASS（W-01b 修复） | 已修，本包再加回归测试（W-04） |
| 批次中途改控制面导致卡死 | 未"修复"（这是正确行为），但 §4.1 的报错已使其可诊断 |
