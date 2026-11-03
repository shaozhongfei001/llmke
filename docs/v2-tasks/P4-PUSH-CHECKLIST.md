# P4 推送与合并确认清单（推送/合并前必须用户确认）

> 本会话接管期在 llmke-v2 的提交（git log 权威清单），推送目标 `git@github.com:shaozhongfei001/llmke.git`。
> **未经用户明确同意，不执行任何 push/merge。**

## 1. 推送前核对

1. 工作树干净：`git status --short` 为空（或仅剩声明过的在途文件）；
2. 全套回归绿：图引擎 10 文件 + 前端 tsc 0 新增错误 + dist 构建成功；
3. 用户抽 3 条证据复现通过；
4. M4 盲审（11 条 claim）全部有非空 verdict+note，无 overstated 未修正项；
5. 用户明确说“可以推送”。

## 2. 推送命令（届时按序执行）

```bash
cd /home/szf/data/dev/llmke-v2
git push origin design/v2-input-engine-adoption-20261030-2101
```

- 分支未在远端时用 `-u` 建立跟踪；推送失败（rejected）不 force push，先 fetch 对齐。

## 3. 合并 main

- 首选：GitHub 上开 PR → 用户/评审审阅后合并（可留评审链接）；
- 或本地：`git fetch origin main && git merge origin/main`（在 feature 分支先合入 main 的增量，
  解决冲突后）再让用户合并 PR；**本会话不自行在 main 上提交/推送**。

## 4. 回滚

- 回滚代码：`git revert <commit>` 或重推旧 commit 的分支；
- 回滚数据：快照目录均在（/tmp/r20-root、/tmp/tl-a2-root、/tmp/s4-root-c），
  指向旧快照重启 18094 即可；
- Nebula 存量：未动（T-B2 未执行）。

## 5. 推送后待办

- 更新评审包 README/PR 链接；把 T-B2（清库授权）、D10 全量问句、语义评审列为下一批。
