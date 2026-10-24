# 摘要缺口实测（第九轮 R9-T13）

> **status: FINDING_NOT_FIXED · 未修改任何控制面 · 不构成通过或验收**
> 实验工具：`coordination/r9-digest-gap-probe.py`（仓外，只读 + 一次可控改动后立即还原）
> 原始输出：`loops/round9/evidence/T13-digest-gap.json`

## 为什么做这个实验

外部评审第 2 题指出：之前的四组对抗只证明"**已纳入摘要的改动**会触发失效"，
**不证明摘要没有漏项**。本实验直接找漏项。

## 结果

| 探针 | 动作 | control_digest | code_digest | doc_digest | 旧证据是否仍判定有效 |
|---|---|---|---|---|---|
| B1 | 在 `docs/baseline/validation/schema-verify.sh` 末尾追加一行注释 | **不变** | **不变** | **不变** | **是** |
| C1 | 在仓库根新建未跟踪文件 `_r9_untracked_probe.txt` | 不变 | 不变 | 不变 | 是 |
| A1 | 运行环境（Python 3.12.13 / MySQL 8.0.41） | 无对应输入 | 无对应输入 | 无对应输入 | 是 |

实验后已 `git checkout` / 删除探针文件，`restored_ok = true`，工作区干净。

## 这说明什么（以及不说明什么）

**说明**：`schema-verify.sh` 是**被当成验证命令执行**的脚本，但它位于
`docs/baseline/validation/`（冻结排除前缀）。把它改成"直接 exit 0"，三个摘要都不变，
`evidence-check` 仍会 PASS —— 也就是说：

> 证据能证明"树没变"，**不能证明"当初拿来做验证的那个脚本"没变**。

同理，解释器版本、MySQL 版本、已安装包集合都不在任何摘要内；同一棵树在不同环境上
可以得到不同结论，而记录看起来完全一致。

**不说明**：本实验没有证明 `p0-gate` / `framework-verify` 可以被绕过——这两个入口的命令
（`Makefile`、`scripts/*`）都在控制面内，改它们会让 `control_digest` 变化。

## 可行的修法（未实施，需窗口）

| 方案 | 代价 | 效果 |
|---|---|---|
| A. 把被当门禁执行的脚本移入 `scripts/` | 改控制面 + 重冻结 + 新批次 | 一次到位，脚本进入 `control_digest` |
| B. 每条门禁记录增加 `command_digest`（被执行命令及其脚本内容的哈希），复核时比较 | 改 `loop_guard`/`baseline_support`，属控制面 | 精确：只绑定"实际执行的命令"，不依赖路径约定 |
| C. 仅把命令 sha256 写进证据日志并在复核时断言 | 改日志格式，影响面小 | 弱：日志本身在排除前缀，需与 B 同时做才闭环 |

**建议 B 为主、A 为辅**：B 直接回答"谁跑的、跑的是什么"，A 让脚本无法藏在排除前缀里。
两者都需在受控窗口内一次完成，且会使当前候选失效；本轮只登记不动手。

## 复现

```bash
python3 coordination/r9-digest-gap-probe.py | head -40
```
