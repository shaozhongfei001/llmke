# 下一窗口待办（Backlog）

日期：2026-10-21　状态：**仅登记，未执行**
当前候选：`L0-contract-baseline-r7`（`QA_PENDING`，冻结 `revision=8`，208 文件）

> 本文件位于 `docs/baseline/validation/`，不参与 `control_digest`/`doc_digest`，
> 新增或修改它**不会**让 r7 候选失效（已实测：写入后 `evidence-check` 仍 PASS）。

---

## 0. 为什么现在不做任何一项

任何一项都要改控制面（`Makefile` / `GATE-CATALOG` / `tests/`），一旦改，r7 的 8 条记录立刻 STALE，
必须"作废候选 → 一次收口冻结 → 新建批次 → 重跑门禁 → 重签 QA"。
在 r7 还没签之前这样做，等于白扔一次候选。

**触发条件**：r7 签名并合并后，或业主明确选择"放弃 r7 直接开新窗口"。

---

## W-05（建议最高优先，**补丁已验证**）R-02 根治：Makefile 不得从 PATH 取解释器

> 2026-10-22 更新：已在隔离工作树试打并验证（193 passed / framework-verify exit 0 / 负向失败响亮）。
> 补丁与验证矩阵见 `W-05-VERIFIED-PATCH.md` 与 `patches/w05-makefile-python.diff`（`git apply --check` 通过）。
> 仍未应用到 r8 —— 应用会让 r7 候选失效。

### 为什么排第一

同一缺陷已经造成 **3 次**事故，每次表现都是"门禁莫名红"，排查成本远高于修复成本：

| 序号 | 场景 | 现象 |
|---|---|---|
| 1 | 直接 `make framework-verify`（conda shell） | `ModuleNotFoundError: openapi_spec_validator` |
| 2 | 同上，第二次 | 同上（已登记 `FAIL-2026-10-21-08`） |
| 3 | `python3 scripts/run_batch.py` 内部 spawn `make` | 同上（`DECISIONS.md` D13） |

现有缓解只是"记得用 `coordination/mk.sh`"——这是**纪律**，不是机制。第 3 次说明纪律挡不住。

### 拟议改动（`Makefile`，1 处新增 + 机械替换）

```diff
+# 解释器唯一来源：优先 LLMKE_PYTHON，其次仓库内 .venv，最后才回退 PATH。
+# 为什么：Makefile 内所有 python3 都取自 PATH，在 conda/系统 shell 下会取到缺依赖的解释器，
+# 表现为"门禁莫名红"。回退 PATH 只为避免无 venv 的环境直接不可用。
+LLMKE_PYTHON ?= $(shell [ -x .venv/bin/python3 ] && echo .venv/bin/python3 || echo python3)
+PY := $(LLMKE_PYTHON)
+
 help:
-	@python3 -c "..."
+	@$(PY) -c "..."
```

并对全部目标把 `python3` 换成 `$(PY)`（约 20 行，纯机械）。

配套：`coordination/mk.sh` 增 `export LLMKE_PYTHON=<绝对路径>`，使 worktree（无 `.venv`）也能固定。

### 验收

| 正向 | 在 conda shell 里 `make framework-test` → 必须 193 passed（不报 ModuleNotFound） |
|---|---|
| 负向 | 故意把 `.venv` 改名 → 必须回退 PATH 并在报错中暴露真实解释器路径，不得静默 |
| 复现性 | `make -n generate` 输出里能直接读到 `LLMKE_PYTHON` 的取值 |

---

## W-02（可选）L3：把模块测试单列为独立门禁

- 现状：模块测试只在 `framework-test` 内跑，证据上依附于 `independent_qa_gate`，看不出"39 条模块测试"这一层。
- 改动：`GATE-CATALOG.yaml` 增 `framework.modules`（`argv: [make, module-test]`），新批次 `LOOP.yaml` 增 `module_test_gate`。
- 代价：控制面 +2 处；门禁数 8 → 9。
- 收益：QA 可单独复核"模块测试是否 pass"，而不必从 `framework-verify` 的合并输出里推断。
- 建议：**与 W-05 同一窗口做**，否则要多付一次冻结与一次 QA。

---

## W-04（小）补一条"签名有效但候选过期"必须被拒的测试

- 现状：`accept_qa` 里 `stale_reasons` 在签名校验**之前**执行，逻辑上一定拦得住；
  但**没有测试**锁定这个顺序。若将来有人调换顺序，"过期候选 + 有效签名"就会被接受。
- 改动：`tests/test_loop_guard.py` 增 1 条：构造 QA 候选 → 改控制面 → 用合法夹具密钥签名 → `accept-qa` 必须失败。
- 代价：1 个测试文件（属控制面，须随窗口一起做）。

---

## W-03（**已降级：当前不需要**）`code_digest` 覆盖非 `.py` 资源

原判断是"`code_digest` 只覆盖 `.py`，能力边界偏窄"。本轮量化后修正：

| 实测项 | 值 |
|---|---|
| `code_digest` 覆盖文件数 | **3** |
| 同目录树内未被覆盖 | **7** |
| 这 7 个是什么 | `modules/apps/services/lib/frontend` 各 1 个 `README.md` + `modules/citation_evidence/tests/` 2 个文件 |

即：**未覆盖的全部是文档与测试，且都是有意排除的**；当前没有任何非 `.py` 的运行时资源（模板/配置/静态资源）。

结论：现在做等于为空想需求改控制面。**改为条件触发**——当出现第一个非 `.py` 运行期资源
（如 `modules/**/*.j2`、`*.yaml` 配置模板）时再启用，届时只需在 `code_files` 里加后缀白名单。

---

## W-06（阻塞于 owner）`requirements.lock` 去重

- 现状：存在 `pip` 25.0.1/26.2.1、`idna` 3.19/3.20 版本冲突，另有 14 个与框架无关的重型包。
- 需要：`baseline-owner` 批准收敛方案；细节见 `DECISION-PACK-V1.1.1.md` D-02。
- 本轮不动。

---

## 建议的窗口打包顺序

1. 等 r7 签名 → 合并（或业主决定放弃 r7）；
2. 同一窗口内做：**W-05 + W-02 + W-04**（三项都要动控制面，合并做只冻结一次）；
3. 冻结后新建 r8 批次，跑 9 条门禁 + 全套对抗；
4. W-03 暂不做；W-06 等 owner。

**教训沿用**：验收实验必须**在冻结之前**跑完（r3 卡死、r6 作废都是这条）。
