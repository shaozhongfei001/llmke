# 下一窗口执行手册（一条命令）

日期：2026-10-22　状态：**脚本已在隔离工作树实测通过**
脚本：`~/data/dev/coordination/window-apply.sh`（仓外，不参与控制面与摘要）
补丁：`docs/baseline/validation/patches/window-bundle-v1.diff`

> 仍未对 r8 执行。执行前需要业主就 **r7 签或弃** 给出结论——因为补丁会改控制面，
> r7 必然作废，这一步不能由实现方代替决定。

---

## 1. 一条命令

```bash
# 先看计划（不改任何文件）
~/data/dev/coordination/window-apply.sh \
  --root ~/data/dev/llmke-r8 --dry-run \
  --supersede L0-contract-baseline-r7 --batch L0-contract-baseline-r8

# 确认后真跑
~/data/dev/coordination/window-apply.sh \
  --root ~/data/dev/llmke-r8 \
  --supersede L0-contract-baseline-r7 --batch L0-contract-baseline-r8
```

参数含义：

| 参数 | 作用 |
|---|---|
| `--root` | 目标工作树（默认当前目录） |
| `--supersede <批次>` | 把旧候选置 `SUPERSEDED` 并写 `replaced_by` + `terminal_reason`；**不删除、不改写证据** |
| `--batch <名字>` | 新批次名；不允许已存在 |
| `--dry-run` | 只打印将要执行的命令 |

---

## 2. 脚本做什么（顺序即纪律）

1. **前置检查**：工作树干净（忽略 `.runner.lock` 与 `docs/baseline/validation/` 未跟踪文件）、补丁可 `git apply --check`、目标批次不存在；
2. **处置旧候选**：`SUPERSEDED` + `replaced_by` + `terminal_reason`；
3. **应用补丁**（W-05 / W-05b / W-02 / W-04 整包）；
4. **建批次**：沿用最近批次的门禁定义，追加 `module_test_gate`（9 条），登记 `PROJECT-PLAN`，补齐 `EVIDENCE/FAILURES/HANDOFF/SHARED_MEMORY/memory/BLOCKED`；
5. **冻结前自查**：`trace_check` + `sync_rules`；
6. **一次性收口冻结**（`--write` 后立刻只读复核）；
7. **武装** + **在坏 PATH 下跑门禁**（`env -i PATH=/usr/bin:/bin` + 只给 `LLMKE_PYTHON`）——这一步同时验证 W-05b 是否真的生效；
8. **复验**：`make framework-verify`、`evidence-check`、`p0-gate` 必须为 2；
9. 失败即停，不做"部分成功"的假象。

---

## 3. 防护（已实测）

| 场景 | 行为 |
|---|---|
| 工作区脏 | **拒绝执行**并列出脏文件（干跑只警告） |
| 批次已存在 | 拒绝执行 |
| 补丁已应用过 / 树已变化 | 拒绝执行（干跑只警告） |
| `p0-gate` 返回 0 或 1 | **立刻中止**并提示人工核查（正常必须是 2） |

---

## 4. 隔离实测结果（`/tmp/win-probe`，验证后已删除）

```
[window] 处置旧候选 r7 -> SUPERSEDED (replaced_by=r8)
[window] 应用补丁 window-bundle-v1.diff
[window] 建批次 r8：gates=9
[window] trace-check: PASS / rule-mirror: PASS
[window] 一次性收口冻结：baseline: PASS（两次）
[window] 武装：baton committed
[window] 坏 PATH 下跑门禁：
         pass × 8（contract_generate / contract_check / mutation_probe / traceability /
                   p0_register / security_scan / baseline / module_test）
[window] 复验：framework-verify exit 0 / 194 passed / baseline PASS
         evidence-check r8: PASS
         p0-gate exit=2（正确阻断）
```

即：**9 条门禁批次、R-02 根治、W-04 回归测试、坏 PATH 下的可复现性**四项一次验证完毕。

---

## 5. 回退

脚本**不创建任何提交**，因此窗口内回退很简单：

```bash
cd ~/data/dev/llmke-r8
git checkout -- .                       # 撤销补丁对已跟踪文件的修改
rm -rf loops/<新批次>                    # 删除未跟踪的新批次目录
git status --short                      # 应只剩 .runner.lock
```

若已提交：`git revert <commit>` 后必须**再冻结一次**并把受影响批次置终态
（`run_batch` 会拒绝在 STALE 批次上重跑，见 §6）。

---

## 6. 执行后必须知道的约束

1. **任何控制面改动后必须新建批次**——`run_batch` 会对已失效批次报
   `FAIL: prior evidence invalid`，不能就地重跑；
2. **目录条目 `allowed_kinds` 必须含批次 `kind`**（`L0-*` 是 `contract`），否则 `arm` 报
   `gate differs from approved command catalog` 且不指出哪一条；
3. **验收实验必须在冻结之前跑完**（r3 卡死、r6 作废都是这条）。
