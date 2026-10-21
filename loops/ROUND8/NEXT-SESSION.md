# 续跑说明（只写可执行信息）

- 仓库（r5 所在，勿在此写代码）：`~/data/dev/llmke`，分支 `fix-window/v1.1.1`，HEAD `a9c2b43`
- R8 工作树：`~/data/dev/llmke-r8`，分支 `round8/delivery`
- 解释器：`~/data/dev/llmke/.venv/bin/python`（Python 3.12.13）

## 下一条准确命令

```bash
cd ~/data/dev/llmke-r8
PYTHONPATH=$PWD ~/data/dev/llmke/.venv/bin/python -m pytest modules/citation_evidence/tests -q   # 期望 39 passed
~/data/dev/coordination/verify-all.sh                                    # 期望 3 项通过 / 0 异常
```

## 续跑顺序

1. `R8-T01`/`T06`/`T07`/`T08`/`T09`/`T11`/`T12`/`T13` 已 VERIFIED，勿重做；
2. 已无"纯模块内"可做的 READY 项；下一步要么等外部输入，要么开下一个受控窗口做 `W-01`
   （把 modules 测试纳入 framework-verify）—— 后者需 owner 授权，因 Makefile 属冻结面；
3. `R8-T04` 等 qa-owner（信任根锚点）；`R8-T05` 等四方输入；`W-01` 等窗口授权；
4. 注意：在 r8 里改 `Makefile` 会让 r5 候选整体 STALE，不要顺手加 target。

## 说明

本文件遵循项目规则：文档中不写宿主绝对路径（写 `~/`），否则会被 `security-check` 判失败。
