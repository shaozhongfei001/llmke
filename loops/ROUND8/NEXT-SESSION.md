# 续跑说明（只写可执行信息）

- 仓库（r5 所在，勿在此写代码）：`~/data/dev/llmke`，分支 `fix-window/v1.1.1`，HEAD `a9c2b43`
- R8 工作树：`~/data/dev/llmke-r8`，分支 `round8/delivery`
- 解释器：`~/data/dev/llmke/.venv/bin/python`（Python 3.12.13）

## 下一条准确命令

```bash
cd ~/data/dev/llmke-r8
PYTHONPATH=$PWD ~/data/dev/llmke/.venv/bin/python -m pytest modules/citation_evidence/tests -q
```

## 续跑顺序

1. `R8-T01` 已 VERIFIED，勿重做；
2. 下一个 READY：给切片加「不支持声明的 block 策略」（`unsupported_policy: block`），仍不依赖 P0；
3. `R8-T03` 需 owner 给建议口径后再动；
4. `R8-T04` 等 qa-owner；`R8-T05` 等四方输入。

## 说明

本文件遵循项目规则：文档中不写宿主绝对路径（写 `~/`），否则会被 `security-check` 判失败。
