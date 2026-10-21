# W-01 窗口变更方案：把模块测试接入门禁，并补上"证据绑定业务代码"

状态：**方案（PROPOSED）**，未执行任何控制面修改。
作者：tech-lead／r8 工作树。批准人：`baseline-owner`（冻结面变更）；排序需 `qa-owner` 协同。
日期：2026-10-21

---

## 0. 一句话结论

`modules/` 下的 39 条测试**完全不在门禁内**；更要紧的是，**P-03 之后没有任何门禁证据绑定业务代码**——
改 `modules/**` 不会让任何门禁记录失效。两件事必须在同一次冻结里修，否则第二层永远是假绿通道。

---

## 1. 实测事实（不含推测）

| 事实 | 实测值 | 来源 |
|---|---|---|
| `Makefile:15` `framework-test` | `python3 -m pytest tests/ -q` | `cat -n Makefile` |
| `framework-verify` 是否包含它 | 是（`Makefile:22`） | 同上 |
| 门禁内测试数 | **145 passed** | `make framework-verify` |
| 模块测试数 | **39 passed** | `pytest modules/citation_evidence/tests -q` |
| 合并跑 | **184 passed** | `python -m pytest tests/ modules/ -q`（本轮实测） |
| `Makefile` 是否控制面 | **是** | `freeze_baseline.controls()` |
| 控制面文件数 | **205** | 同上 |
| `tests/` 控制面文件数 | 15 | 同上 |
| `modules/` 控制面文件数 | **0** | 同上 |
| `source_files` 是否含 modules | 含（217 个中 6 个） | `baseline_support.source_files()` |
| 门禁目录条目 | 31 条，pytest 类仅 `framework.regressions`（跑单文件） | `GATE-CATALOG.yaml` |
| 直接 `pytest modules/`（不加 `-m`） | **收集失败**：`ModuleNotFoundError: No module named 'modules'` | 本轮实测 |

最后一条要特别注意：**只把 `modules/` 加进 `pytest tests/ modules/` 而不带 `python3 -m`** 会直接红。
现有写法是 `python3 -m pytest`，所以 `PLAYPATH=cwd` 天然在 `sys.path`，加路径即可，无需 `PYTHONPATH=`。

---

## 2. 问题分两层（这是本方案的核心判断）

### L1 收集缺口：39 条测试从不执行

`framework-test` 只收集 `tests/`，`modules/` 一行没跑。所以"145 passed"从不代表模块可用。

### L2 绑定缺口：**没有任何门禁证据绑定业务代码**（比 L1 严重）

P-03 把摘要拆成 `control_digest`（205 个控制文件）与 `doc_digest`（17 个说明文档）。
`modules/**` **两个都不在**：

- 在 `source_files`（217）里 —— 旧 `digest_scheme=1` 会因此判 STALE；
- 不在 `control_digest`、也不在 `doc_digest` —— 新 `digest_scheme=2` **不会**判 STALE。

结论：**改 `assembler.py` 一行代码，r5 的 7 条门禁与 QA 候选记录仍全部 PASS。**

这既是 P-03 的设计意图（开发期改业务代码不该反复作废控制面证据），也是一个必须显式封口的洞：
一旦把模块测试接进门禁，这条门禁**跑完就腐**——它证明"当时那版代码过了"，但证据不绑那版代码。

> 换句话说：只做 L1，等于新增一条**看起来有证据、实际不绑定**的门禁。这种门禁比没有更危险。

---

## 3. 拟议变更（精确到行）

### 3.1 变更 1：`Makefile`（L1，1 行）

```diff
 framework-test:
-	@python3 -m pytest tests/ -q
+	@python3 -m pytest tests/ modules/ -q
```

预期结果：`184 passed`（145 + 39），已在内存验证过命令本身可行。

### 3.2 变更 2：`scripts/baseline_support.py`（L2，新增第三个摘要）

```diff
 DIGEST_SCHEME=2
+DIGEST_SCHEME=3
 DOC_EXCLUDED=(...)
 DOC_DEPENDENT_GATES=frozenset({'traceability_gate'})
+# 业务代码摘要：modules/** 的实现代码。只被"声明依赖代码"的门禁比较。
+# 不放进 control_digest —— 否则每次改业务代码都会作废全部门禁，等于重演 P-03 前的返工。
+CODE_DEPENDENT_GATES=frozenset({'independent_qa_gate','module_test_gate'})
+
+def code_files(root): ...
+def code_digest(root): return digest({r:filehash(...) for r in code_files(root)})
```

`code_files` 口径：`modules/**/*.py`（不含 `tests/`、不含 `__pycache__`）。
不含测试文件是有意的：测试改动属"验证强度变化"，应由 `tests/` 的既有控制面绑定覆盖，不必让业务摘要跟着动。

### 3.3 变更 3：`scripts/loop_guard.py`（L2，记录与比较）

- `run_gate` 记录新增 `code_sha256`（执行前计算），`digest_scheme=3`；
- `stale_reasons` 新增：`if g['id'] in CODE_DEPENDENT_GATES and rec.get('code_sha256')!=code_digest(root)` → STALE；
- 兼容：`digest_scheme=2` 的旧记录**不回溯改写**，仍按 control/doc 判定；`=1` 按整树。

### 3.4 变更 4（可选 L3）：独立门禁条目

若希望"39 条模块测试"在证据里有独立记录（便于 QA 单独复核），需再动两处**控制面**：

- `docs/policies/GATE-CATALOG.yaml` 增 `framework.modules`（`argv: [make, module-test]`，`required_checks: [module_tests]`）；
- 新批次 `LOOP.yaml` 增 `module_test_gate`（`catalog_id: framework.modules`，`depends_on: [contract_check_gate]`）。

代价：控制面 +2 处；收益：证据粒度可单列。**建议本轮不做**（先封 L1+L2 的洞，粒度以后再说）。

---

## 4. 影响面

### 4.1 摘要（内存预测，未写盘）

| 项 | 当前 | 变更后（预测） |
|---|---|---|
| `control_digest` | `60bae549f5d5c43e…` | **`31c696a3eca9eebf…`** |
| 变化文件数 | — | **1**（仅 `Makefile`） |
| `digest_scheme` | 2 | **3** |
| `code_digest` | 无 | 新增（6 个 modules 文件） |

预测方法：取 `controls()` 的 205 个文件，仅把 `Makefile` 的哈希替换为"改后内容"的哈希后重算。可复现：

```bash
PYTHONPATH=scripts python3 - <<'PY'
from pathlib import Path
from baseline_support import control_digest
from freeze_baseline import controls
print(len(list(controls(Path('.')))), control_digest(Path('.')))
PY
```

### 4.2 证据与批次

| 对象 | 影响 |
|---|---|
| **r5（当前候选）** | `control_digest` 变化 → **7 条开发门禁记录 + QA 候选立即 STALE**。r5 无法再用于合并 |
| r4 / r3 | 早已 STALE／终态，不受新增影响 |
| `main` | 不动 |
| L1–L4 | 仍 BLOCKED，不受影响 |
| `p0-gate` | 仍 `exit 2`，本方案不触碰 P0 |

> **这是本方案最大的代价，必须由业主先选排序（见 §5）。**

### 4.3 不改变的边界

- 不放宽任何既有门禁：`tests/` 15 个文件仍在控制面；凭据/私钥/连接串判定不动；
- 不把业务代码塞进 `control_digest`（否则重演"改一行就全废"）；
- 不用"测试数量"替代业务完成度：184 passed 仍只是框架测试。

---

## 5. 与 r5 的排序（三选一，代价已量化）

| 方案 | 步骤 | QA 轮次 | main 变绿时间 | r5 结局 |
|---|---|---|---|---|
| **甲** | 先签 r5 → 合并 → 再开 W-01 → r6 → 签 r6 | **2 次** | 早（一次 QA 后） | 合并进 main，随后被 r6 取代 |
| **乙（推荐）** | 放弃 r5 → 现在做 W-01 → 一次冻结 → r6 → 签 r6 | **1 次** | 晚（r6 签完） | 置 `SUPERSEDED`，证据保留 |
| **丙** | 挂起 W-01，等 L1 开工前再做 | 0 次（暂） | — | r5 可用 |

**推荐乙**，理由：

1. r5 **目前没有签名**，不存在"已投入的 QA 成本被浪费"；选甲等于为一个中间态多买一次 QA；
2. QA 预算是本项目最稀缺资源（L0-r2 就是耗尽作废的）；
3. W-01 的变更与"建 r6 批次"本来就要在同一次冻结里完成，选乙天然合并，边际成本≈0；
4. 选丙的风险是把"门禁不绑业务代码"带进业务期——到那时 `modules/**` 文件数远多于 6 个，
   洞更大、改动面更广。

**选甲的条件**：业主明确需要 `main` 尽快恢复"可复核全绿"，且能立刻拿到 r5 签名。

---

## 6. 执行顺序（若选乙）

```bash
# 0) 前置：确认已无人在跑门禁（r5 的证据要保留，不要边跑边改）
cd ~/data/dev/llmke-r8 && git status --short          # 必须干净

# 1) 第一刀：L1（只改 Makefile 一行）
#    改后立刻验证 184 passed，暂不冻结
~/data/dev/coordination/mk.sh framework-test          # 期望 184 passed

# 2) 第二刀：L2（baseline_support + loop_guard + 新增测试）
PYTHONPATH=$PWD python3 -m pytest tests/ modules/ -q  # 期望 ≥184 passed
PYTHONPATH=$PWD python3 -m pytest tests/test_digest_scope.py -q

# 3) 三刀做完再一次收口冻结（禁止中途冻结，否则重演 r3 卡死）
python3 scripts/freeze_baseline.py --write
python3 scripts/freeze_baseline.py                    # 期望 baseline: PASS

# 4) 建 r6（与"建批次"合并到同一次冻结）
python3 scripts/new_loop.py L0-contract-baseline-r6
# 继承 r5 的 8 条门禁定义，不放宽 pass 条件
python3 scripts/loop_guard.py arm --loop L0-contract-baseline-r6 --to integration-agent \
        --executor tech-lead --expected-revision 1
python3 scripts/run_batch.py --loop L0-contract-baseline-r6 --executor integration-agent

# 5) 全量核验
~/data/dev/coordination/verify-all.sh                 # 期望 3 项通过 / 0 异常
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r6   # 期望 PASS
~/data/dev/coordination/mk.sh p0-gate                 # 期望 2（不变）

# 6) r5 置终态（保留证据，不改写）
#    STATE.json: status=SUPERSEDED, replaced_by=L0-contract-baseline-r6, terminal_reason=...

# 7) 生成 QA 载荷，交 qa-owner 签 r6（信任根锚点需先更新到 r6 的 baseline_sha256）
```

---

## 7. 回退点

| 点 | 触发条件 | 回退动作 |
|---|---|---|
| R1 | 步骤 1 后 `framework-test` 不足 184 | `git checkout -- Makefile`；结论：收集口径有问题，先查再改 |
| R2 | 步骤 2 后既有 145 条出现回归 | 回退 L2 三处改动，只保留 L1 或全回退 |
| R3 | 冻结后才发现要再改控制面 | **不要**就地重改：按 P-06 把该候选置 `SUPERSEDED`，另建 r7 |
| R4 | r6 门禁有红 | 不改 pass 条件凑绿；定位后重跑受影响门禁，必要时弃批重建 |

---

## 8. 正反向验收（缺一不可）

### 正向
1. `framework-test` → **184 passed**；
2. `framework-verify` → `exit 0`；
3. `evidence-check --loop r6` → `PASS`，记录中含 `code_sha256`；
4. `p0-gate` → **exit 2**（证明没顺手放宽 P0）。

### 反向（证明新门禁不是装饰）
| 反例 | 期望 |
|---|---|
| 把 `assembler.py` 里 `text_hash` 改成返回常量 | `184` 里对应测试红 → `framework-test` 非 0 |
| **只改一行注释**（语义不变） | `module_test_gate`/`independent_qa_gate` 记录 **STALE**（证明 `code_digest` 真的绑代码） |
| 改 `tests/` 下任一测试文件 | 仍须红/STALE（证明没把控制面绑定挪走） |
| 删掉 `modules/citation_evidence/tests/test_assembler.py` | 收集数下降；`framework-test` 计数与预期不符必须被察觉 |
| `contracts/` 加一个文件 | 7/7 STALE（不变） |

第 2 条是本方案**唯一能证明 L2 生效**的实验。不做它，就无法区分"真绑定"和"看起来绑定"。

---

## 9. 显式不做（避免被误读为已覆盖）

- 不把 `modules/**` 加进 `control_digest`；
- 不新增 `framework.modules` 门禁条目（L3，建议下一窗口）；
- 不改 `p0-gate` 的任何口径；
- 不为凑数字补测试；39 条已是当前边界覆盖的合理上限（单条 8 类 + 集合 4 类 + 契约 + 审计 + CLI）；
- 不动 r5 已有日志与状态（置终态 ≠ 改写）。

---

## 10. 需要谁做什么

| 事项 | 责任方 | 形式 |
|---|---|---|
| 批准冻结面变更（Makefile + 两个脚本） | `baseline-owner` | 在 `BASELINE-AUTHORITY.yaml` 的 `change_list` 增 W-01 条目 |
| 选定 §5 的甲/乙/丙 | 业主 | 一句话即可 |
| r5 若选乙：确认其作废不影响已有验收叙事 | `qa-owner` | 书面确认 |
| r6 签名 + 信任根锚点更新 | `qa-owner` | 按 `R5-QA-HANDOFF.md` §3 流程 |

---

## 附：复现本文所有数字

```bash
cd ~/data/dev/llmke-r8
~/data/dev/llmke/.venv/bin/python -m pytest tests/ modules/ -q  # 184 passed
PYTHONPATH=scripts python3 -c "
from pathlib import Path
from baseline_support import source_files, control_digest
from freeze_baseline import controls
c=list(controls(Path('.')))
print('control=',len(c),'source=',len(source_files(Path('.'))))
print('modules_in_control=',sum(1 for x in c if x.startswith('modules/')))
print('control_digest=',control_digest(Path('.')))"
```
