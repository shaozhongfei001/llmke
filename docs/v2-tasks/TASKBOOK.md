# LLMKE V2 后续任务书（bb32876）

- 日期：2026-11-02
- 基线提交：bb32876
- 分支：design/v2-input-engine-adoption-20261030-2101

## 入口

- 使用说明：`docs/v2-tasks/PROMPT-TL-USAGE.md`（先读本说明，再选入口）

- 当前主任务（新会话开工，长程任务书）：`docs/v2-tasks/PROMPT-TL-START.md`（VL0–VL7 + D01–D10 验收）
- 续跑/接手（中断后继续）：`docs/v2-tasks/PROMPT-TL-RESUME.md`（接续指令 + CHECKPOINT 模板）

## 切换条件

- 新会话、冷开工、尚未建立分支或工作树：先读 PROMPT-TL-START.md。
- 会话中断后恢复、分支已建、有活作业或未提交改动：先读 PROMPT-TL-RESUME.md + `docs/v2-tasks/CHECKPOINT.md`（若存在）+ TASKS.yaml + 三工作树 `git status`。
- 两种情况下都要求：先读 TASKS.yaml 的 meta/base_commit，核对当前 HEAD 是否与 bb32876 一致。

## 连续执行机制

- 确认 CodeBuddy `/goal`（或实际生效的 Stop hook）已激活；Goal 条件在 PROMPT-TL-START.md 第 10 节。
- 阶段汇报后继续执行，不询问“是否继续”。

## 检查点

- 写入 `docs/v2-tasks/CHECKPOINT.md`（模板见 PROMPT-TL-RESUME.md）。

## 纪律

- 每条结论必须能指向脚本/测试/报告（文件:行号 或 命令+输出）；找不到证据记为 UNVERIFIED。
- 不复制两份提示词全文；本文件只做入口与差异说明。
