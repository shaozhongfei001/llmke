# `fix-window/v1.1.1` 合并时序与回退点

- 适用分支：`fix-window/v1.1.1`（`75e7267` → `a83f875` → `cd79c9e`）
- 前提事实：分支上 `framework-verify` exit 0 / 145 passed、`p0-gate` exit 2、`r4` 七门禁 pass
- 本文件在 `docs/baseline/validation/`，不参与源码快照，写入不影响任何证据

---

## 0. 先明确一条容易误判的事实

**合并动作本身不会使 `L0-contract-baseline-r4` 的证据失效。**

证据绑定的是**文件内容**（`control_digest` / `baseline_sha256` / 证据日志哈希），不是 git 提交号。
`git merge` 只新增提交对象，不改变工作树内容 → 合并后 `evidence-check --loop r4` 仍应 PASS。

**会使 r4 失效的只有一件事：合并后再改控制面**（`scripts/**`、`docs/policies/**`、`tests/**`、
`docs/PROJECT-PLAN.yaml`、`loops/*/LOOP.yaml`、`VERSION` 等），因为那会改变 `control_digest`。

由此得到两种策略，二选一：

| 策略 | 做什么 | r4 结局 | 代价 |
|---|---|---|---|
| **A（推荐先做）** | 现在就把分支合并进 `main`，T-12 与 LD 批次留到下一个窗口 | **保住**，`main` 立刻回到全绿 | 0 |
| **B** | 合并前先把 T-12 修完、把 LD 替代批次建齐，再合并 | **作废**，需 r5 重跑 | 一次完整重跑 + 重签 |

> 不要把 A 和 B 混着做：先合并、再改控制面，等于让 `main` 上的 r4 立刻变 STALE，却又没准备好替代批次。

---

## 1. 策略 A：立即合并（推荐）

### A-1 合并前确认（只读，不消耗预算）

```bash
cd ~/data/dev/llmke
git checkout fix-window/v1.1.1
git status --short                      # 期望：仅交付 zip 与 .runner.lock 未跟踪
~/data/dev/coordination/mk.sh framework-verify    # 期望 exit 0
~/data/dev/coordination/mk.sh p0-gate             # 期望 exit 2
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r4   # 期望 PASS
```

**回退点 R0**：不合并即无损，`main` 不受影响。

### A-2 合并

```bash
git checkout main
git merge --no-ff fix-window/v1.1.1 -m "merge: V1.1.1 受控变更窗口（P-01/P-03/P-04/P-05/P-06）"
```

**回退点 R1**：`git reset --hard 4b1fca8`（合并尚未推送时）。

### A-3 合并后复验（关键：证明证据没被合并动作破坏）

```bash
~/data/dev/coordination/mk.sh framework-verify                     # 期望 exit 0
~/data/dev/coordination/mk.sh p0-gate                              # 期望 exit 2
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r4   # 期望仍 PASS
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r3   # 期望 PASS（终态）
```

**回退点 R2**：若 A-3 出现 r4 STALE，说明合并引入了内容差异（不应发生），
执行 `git reset --hard 4b1fca8` 并保留分支待查，**不要**就地重跑门禁（会消耗预算且留下失败记录）。

### A-4 合并后必须同步的两条口径

1. `main` 上 `LD-legacy-discovery-r2` 的 QA 签名绑定旧 `baseline_sha256`，**已自动失效**；
   该批次按业主口径**作为历史记录保留**，不得在报告中称为「当前候选的有效 QA」。
2. `main` 的「当前候选」是 `L0-contract-baseline-r4`（7 条开发门禁），独立 QA 仍 **NOT_RUN**。
   若要用 L0 证明技术基线，只能引用 r4 的 7 条 pass + 明确注明「无第三方独立背书」。

---

## 2. 策略 B：先修完再合并（下一个窗口）

顺序不可颠倒，**核心纪律：所有控制面改动一次性做完，最后只冻结一次，然后才开始跑门禁**。

| 步 | 动作 | 是否改控制面 | 回退点 |
|---|---|---|---|
| B-1 | 修 T-12：`AI_GUIDE.md` 版本表述、`loops/*/LOOP.yaml` 的 `baseline_version` 统一 1.1.1、`BLOCKED.md` 口径 | 是 | 丢弃工作树即回退 |
| B-2 | 建 LD 替代批次（`LD-legacy-discovery-r3`），登记 `docs/PROJECT-PLAN.yaml` | 是 | 删批次目录 + 还原 plan |
| B-3 | 建 L0 替代批次（`L0-contract-baseline-r5`），登记 plan | 是 | 同上 |
| B-4 | **唯一一次** `python3 scripts/freeze_baseline.py --write`（revision → 3） | 是 | `git checkout -- docs/baseline/FROZEN-MANIFEST.json` |
| B-5 | 按批次顺序 arm → `run_batch`（r5 先，LD-r3 后） | 否 | 失败只消耗该门禁 attempt，不重冻结 |
| B-6 | 外部独立 QA 在固定快照复跑并签名（`qa_payload` → 独立签名 → `accept-qa`） | 否 | 签名不入库则无副作用 |
| B-7 | 旧批次置 `SUPERSEDED`（含 r4、LD-r2），写明 `replaced_by` 与 `terminal_reason` | 否（STATE 非控制面） | 改回 status 即可 |
| B-8 | 合并 | — | R1 |

**为什么必须先 B-4 再 B-5**：本窗口实测——在批次门禁执行中间重冻结，
会让该批次已通过的记录全部绑定旧基线，而 `run_gate` 拒绝在有失效记录时重跑，
批次就此卡死（`r3` 的成因，见 `FIX-WINDOW-V1.1.1-RESULT.md` §3.2）。

---

## 3. 无论选哪种策略，都不要做的事

| 禁止 | 后果 |
|---|---|
| 手工改 `STATE.json` 的 `attempts` | 等于伪造预算，框架无此语义 |
| 删除 `loops/*/evidence/**` 或 `FAILURES.md` | 违反 append-only，历史不可追溯 |
| 在 `main` 上就地重跑已 STALE 的门禁 | 被 `prior evidence invalid` 拒绝，并留下失败记录 |
| 把 `LD-legacy-discovery-r2` 的签名当作当前候选证据 | 业主已明确：历史验收不得冒充当前 QA |
| 为让 `p0-gate` 变绿而改 `P0-CLOSURE.yaml` | 需要真实证据 + owner 双签，改状态即造假 |

---

## 4. 需要业主决定的一件事

**选 A 还是 B。** TL 建议 **A**：当前分支已是可复核的完整切片（145 passed / exit 0 / 对抗验证通过），
先合并让 `main` 回到全绿，把 T-12 与批次建齐留到下一个有明确目标的窗口（例如启动 LD 复核或 L1 切片时），
避免为「文档版本号统一」这类低风险改动提前作废 r4 的 7 条证据。

若选 B，请同时给出下一个窗口的**目标批次**（LD 复核 / L1 切片 / 仅文档一致性），
因为 B-2/B-3 要按那批目标一次建齐，建多了同样是浪费预算。
