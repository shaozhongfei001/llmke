# 续跑说明（只写可执行信息）

- 仓库（r5 所在，勿在此写代码）：`~/data/dev/llmke`，分支 `fix-window/v1.1.1`，HEAD `a9c2b43`
- R8 工作树：`~/data/dev/llmke-r8`，分支 `round8/delivery`
- 解释器：`~/data/dev/llmke/.venv/bin/python`（Python 3.12.13）

## 下一条准确命令

```bash
cd ~/data/dev/llmke-r8
PYTHONPATH=$PWD ~/data/dev/llmke/.venv/bin/python -m pytest modules/citation_evidence/tests -q   # 期望 39 passed（模块）
~/data/dev/coordination/verify-all.sh                                    # 期望 3 项通过 / 0 异常
```

## 续跑顺序

1. `R8-T01`/`T06`/`T07`/`T08`/`T09`/`T11`/`T12`/`T13` 已 VERIFIED，勿重做；
2. 已无"纯模块内"可做的 READY 项；下一步要么等外部输入，要么开下一个受控窗口做 `W-01`
   （把 modules 测试纳入 framework-verify）—— 后者需 owner 授权，因 Makefile 属冻结面；
3. `R8-T04` 等 qa-owner（信任根锚点）；`R8-T05` 等四方输入；
4. **W-01/W-01b/W-02/W-04/W-05/W-05b 已实施**：当前候选 `L0-contract-baseline-r9`
   （`QA_PENDING`，9 条门禁），冻结 `revision=10`、211 文件；r5–r8 均 `SUPERSEDED`。
   签署见 `R9-QA-HANDOFF.md`；
5. 注意：任何控制面改动都会让 r7 候选 STALE；要改必须"作废当前候选 + 一次收口冻结 + 新建批次"。
6. 跑门禁前先 `export PATH=~/data/dev/llmke/.venv/bin:$PATH`（run_batch 会 spawn make，见 D13）。

## 说明

本文件遵循项目规则：文档中不写宿主绝对路径（写 `~/`），否则会被 `security-check` 判失败。

## 2026-10-22 收口状态（无人值守轮）

- 候选：**无活动候选**（r9 已 SUPERSEDED；新增实现会作废候选，见 D33）
- 门禁：`framework-verify` exit 0 / **247 passed**；`evidence-check r9` PASS（终态）；`p0-gate` exit 2
- 落地：`schema-v1.3.sql`（43 表）+ `schema-verify.sh`（43 表、92 模块测试、契约↔表列一致）
- 切片：A 证据落库 / B 分块存储 / C 代次机制（S1–S5）/ D 授权过滤下沉 SQL（E1/E3）/ E 组合链路
- 落地：`docs/baseline/validation/artifacts/schema-v1.1.sql`（38 表）+ `schema-verify.sh`（一键真机验证）
- 切片 A：证据接真库端到端（5 条集成测试，模块 44 passed）

### 下一条准确命令（验证现状）

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH
docs/baseline/validation/schema-verify.sh          # 起实例+建表+跑集成测试，期望 PASS
make framework-verify                              # 期望 exit 0 / 199 passed
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r9
```

### 续跑顺序（下次接手直接照做）

1. **等 qa-owner 签 r9**（信任根锚点指向 `cf8a72c8…`）——这是合并与 L1 的前置；
2. 拿到 `index-owner` 对 `P0-04-DESIGN-PROPOSAL.md` 5 条裁定 → 升 schema V1.2 并实现 5 条测试；
3. 拿到 `security-owner` 对 `P0-03-DESIGN-PROPOSAL.md` 5 条裁定 → 实现 E1–E6；
4. 若业主决定迁移旧数据（当前决策为**空库起步**）→ 按 `target-schema-v1-mapping.csv`
   与 11 表逻辑删除值映射（-1→1, 1→0）生成迁移脚本；
5. 后续纵向切片：每片 = 表 + 契约 + 模块 + 集成测试，一片跑通再开下一片。
