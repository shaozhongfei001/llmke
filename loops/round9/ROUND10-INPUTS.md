# 第十轮依赖 DAG 与 owner 输入清单

> 用途：第九轮不把"下一轮怎么开始"留给记忆。每条都带**可执行命令**与**缺谁的什么输入**。
> 原则：外部输入未到时，只阻塞其下游节点，其余并行推进。

## 1. DAG

```
[O1] 业主授权新批次窗口 ──┐
                          ├─> A1 建 r12（先落 LOOP/计划/规则 → 一次冻结 → 跑 9 条门禁）
[O2] index-owner 裁定缺列 ─┤        │
                          │        ├─> A2 command_digest 落地（R9-T14）──> A6 变异测试（改脚本必须失效）
                          │        └─> A3 代码/证据冻结口径刷新
[O3] data-owner 生产 DDL ──┼─> B1 生产 DDL × 目标 schema 对账 ──> B2 恢复副本迁移 dry-run
[O4] interface-owner route export ─┼─> C1 清单 × 注册 差集 ──> C2 调用方确认 ──> C3 P0-01 关闭评估
[O5] security-owner E1 批准 ──────┼─> D1 规则接入 ──> D2 撤权/跨 KB/FAQ 负例 ──> D3 P0-03 关闭评估
[O6] index-owner 加 generation_id / claimed_at ─┼─> E1 块级代次绑定 ──> E2 四后端故障注入 ──> E3 P0-04 关闭评估
[O7] 第三方持新密钥 ──────────────┴─> F1 载荷（1h）→ 签名 → accept-qa → finish → 合并
```

关键约束：`A1` 之后任何控制面改动都会让 A1 的候选失效，所以 A2/B1/C1/D1/E1 **必须在 A1 之前**全部落盘。

## 2. 可执行命令（按节点）

### A1 建批次（需 O1）
```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH
~/data/dev/coordination/mysql-probe.sh start
# 先落 LOOP.yaml / PROJECT-PLAN / docs/policies 改动，再：
PYTHONPATH=$PWD python3 scripts/freeze_baseline.py --write      # 唯一一次冻结
PYTHONPATH=$PWD python3 scripts/trace_check.py
PYTHONPATH=$PWD python3 scripts/loop_guard.py arm --loop L0-contract-baseline-r12 --to integration-agent --executor tech-lead --expected-revision 1
PYTHONPATH=$PWD python3 scripts/run_batch.py --loop L0-contract-baseline-r12 --executor integration-agent
```

### A2 `command_digest` 落地（需 O1）
1. 复用已验证的探针：`python3 coordination/command-digest-probe.py`（`VERIFIED_DRYRUN`）；
2. 在 `loop_guard.run_gate` 记录 `command_digest`，`baseline_support` 增加计算函数；
3. 验收：改 `docs/baseline/validation/schema-verify.sh` 一个字节 → `evidence-check` 必须 FAIL。

### B1/B2 P0-02（需 O3）
```bash
python3 coordination/p0-02-diff.py --old <生产DDL.sql> --new docs/baseline/validation/artifacts/schema-v1.3.sql \
  --out /tmp/p002.json --md /tmp/p002.md
```

### C1 P0-01（需 O4）
```bash
python3 coordination/p0-01-inventory-audit.py --out /tmp/p001.json --md /tmp/p001.md
# 拿到 route export 后，按 (service,method,path) 与 items 做差集（工具待加 --routes 参数）
```

### E1 块级代次绑定（需 O2）
- 给 `document_chunk` 加 `generation_id`（或建 `chunk_generation` 映射）后，
  `fetch_chunks_active` 改为直接按 `generation_id = 激活指针` 过滤，删除"按版本对齐"的近似；
- 回归：`python -m pytest modules/answer_api/tests -q`（现有 4 条代次守卫必须仍绿）。

### F1 独立签署（需 O7）
```bash
python3 scripts/qa_payload.py --loop <新批次> --gate independent_qa_gate --principal-id <第三方主体> --out /tmp/payload.json
# 第三方签：
python3 scripts/qa_sign.py --key-file <其私钥> --key-id <其 key_id> --payload /tmp/payload.json --out /tmp/env.json
# 本机收口（先跑前置检查）：
~/data/dev/coordination/close-batch.py --loop <新批次> --envelope /tmp/env.json --execute
```

## 3. Owner 输入清单（逐项可勾）

| # | 谁 | 需要给什么 | 给了之后可解锁 |
|---|---|---|---|
| O1 | project-owner | 授权"新建批次并重冻结"（会使 r11 失效） | A1/A2 及全部下游 |
| O2 | index-owner | 裁定：`document_chunk.generation_id` vs `chunk_generation` 映射；`index_outbox.claimed_at` | P0-04 的可证明性 |
| O3 | data-owner | 生产库 `SHOW CREATE TABLE` 全量 + 一份恢复副本 | P0-02 关闭评估 |
| O4 | interface-owner | `route export` 结果 + 各接口调用方确认 | P0-01 关闭评估 |
| O5 | security-owner | E1 规范批准件（含撤权语义） | P0-03 关闭评估 |
| O6 | index-owner | 四后端联调环境与故障注入授权 | P0-04 实测 |
| O7 | 第三方 | **新生成**密钥并持有；业主登记公钥 | 独立签署 |
| O8 | baseline-owner | 批准 `P0-CLOSURE.yaml` 的 `baseline_version` 更新 | 台账一致性 |

## 4. 不要做的事（上一轮踩过）

1. 不要复用 r11：`independent_qa_gate` 的 attempts 已 2/3，且签名窗口只有 1 小时；
2. 不要在冻结之后再改控制面（r6/r8 因此作废）；
3. 不要把 `route export` 当成 `IN_USE` 证据；
4. 不要在没有 `generation_id` 的情况下宣称"块级代次已绑定"——现在只是按版本对齐的近似。
