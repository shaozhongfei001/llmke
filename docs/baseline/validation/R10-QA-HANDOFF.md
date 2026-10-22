# r10 独立 QA 交接（当前活动候选）

> 本文件不是批准记录。r10 当前为 `QA_PENDING`，**不得**表述为已通过或可合并。
> 与 r5/r7/r9 的交接包不同，**这是唯一有效的候选**（其余三个已标 VOID）。

## 1. 候选身份

| 项 | 值 |
|---|---|
| 批次 | `L0-contract-baseline-r10` |
| `baseline_sha256` | `f5e07f5614863ad57ce8d8ee999694876bd5ec94c2725b408eb9eb8d62b60161` |
| 冻结 | `revision=11`、控制面 **212** 文件、`baseline_version=1.1.1` |
| 门禁 | 9 条：8 条开发门禁 `pass` + `independent_qa_gate` `QA_PENDING` |
| 载荷 | `docs/baseline/validation/qa-payload-r10.json`（1 小时有效期） |
| `subject_sha256` | `66945f09de0ac5ec3ae026a2bb9d511e9f314c9af3048773da6a52d02c664742` |

> **复核前置条件**：本候选的 97 项模块测试是**真库**测试。复核时 MySQL 实例必须在运行
> （`coordination/mysql-probe.sh start`），且 `make framework-verify` 必须是
> **252 passed、0 skipped**。若出现 `skipped`，说明数据库测试没跑，这份候选不成立。

## 2. 这个候选包含什么

| 类别 | 内容 |
|---|---|
| 框架修复 | W-01（`code_digest` 绑定）、W-05/W-05b（解释器自钉）、W-02（第 9 条门禁）、W-04（过期候选必须被拒） |
| 数据基座 | schema V1.3：43 表 / 538 列（37 张旧表改写 + 证据/分块/代次/租约/outbox 等 6 张） |
| 实现切片 | A 证据落库 / B 分块存储 / C 代次机制（S1–S5）/ D 授权过滤（E1/E3）/ E 组合 / F 端到端 |
| 运维工具 | 迁移 CAS、跨表一致性体检（6 项）、并发竞争验证 |
| 测试 | 门禁内 **252 passed**；模块真库测试 **97 passed** |

## 3. 为什么必须由 `qa-owner` 执行

1. 信任根 `approved_baseline_sha256` 仍是旧值，与 `f5e07f56…` 不符 → 签名会被
   `external approved baseline digest mismatch` 拒绝；
2. 实现者签名或改锚点 = 自签，独立性失效。

## 4. 签署流程

```bash
export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH

# 1) 重新生成载荷（1 小时有效期；gate_spec/log 哈希不变）
PYTHONPATH=$PWD python3 scripts/qa_payload.py --loop L0-contract-baseline-r10 \
  --gate independent_qa_gate --principal-id qa-owner-01 \
  --out docs/baseline/validation/qa-payload-r10.json

# 2) 用受保护私钥签名（私钥不得进工作树）
PYTHONPATH=$PWD python3 scripts/qa_sign.py \
  --payload docs/baseline/validation/qa-payload-r10.json \
  --key <key-path> --key-id <key-id> --out /tmp/r10-attestation.json

# 3) 接受
PYTHONPATH=$PWD python3 scripts/loop_guard.py accept-qa --loop L0-contract-baseline-r10 \
  --gate independent_qa_gate --attestation /tmp/r10-attestation.json

# 4) 校验
PYTHONPATH=$PWD python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r10
```

## 5. QA 应自行复核的 8 项

1. **门禁实况**：`make framework-verify` → exit 0 / **252 passed、0 skipped**；`p0-gate` → **exit 2**；
2. **落地验证**：`docs/baseline/validation/schema-verify.sh` → PASS（43 表 / 97 模块测试 / 体检 6 项）；
3. **冻结范围**：`revision=11`、212 文件；`Makefile`、`scripts/_pin.py`、`scripts/loop_guard.py`、
   `GATE-CATALOG.yaml`、`tests/test_loop_guard.py` 均在清单内；
4. **证据绑定**：9 条记录含 `control_sha256`/`doc_sha256`/`code_sha256`，`digest_scheme=3`；
5. **对抗自测**（请自己跑，不要只读结论）：
   - 改 `modules/**` 一行注释 → `evidence-check` 必须 **FAIL** 且点名 `independent_qa_gate`；
   - `contracts/` 加文件 → 9/9 STALE；
   - `docs/` 加文件 → 仅 `traceability_gate` STALE；
   - 篡改任一证据日志 → `evidence hash mismatch`；
6. **数据侧**：`consistency-doctor.py` 在 `llmke_verify` 上 PASS（否则说明有孤儿数据）；
7. **状态语义**：r5–r9 均 `SUPERSEDED`（证据保留）；**只有 r10 是当前候选**；
8. **文档一致性**：`docs/baseline/validation/INDEX.md` 顶部的数字与实测一致。

## 6. 已知局限（签署前请确认可接受）

- `code_digest` 只覆盖 `modules/apps/services/lib/frontend` 的 `*.py`，不含非 `.py` 资源；
- 只有 `independent_qa_gate` 声明依赖代码；8 条开发门禁仍只绑控制面；
- P0-03 / P0-04 的机制是**参考实现**，粒度/租约时长等参数仍待 owner 裁定（不阻塞签名，但阻塞 L1 开工）；
- 四项业务 P0 **全部 OPEN**，`p0-gate exit 2` 是正确状态。

## 7. 签名之后能做什么 / 不能做什么

| 能做 | 不能做 |
|---|---|
| 合并到 `main`（若树一致、无额外提交） | 开始 L1–L4 业务实现（仍被 P0 阻断） |
| 以此为基线继续切片开发 | 把"技术门禁通过"表述为"业务可开工" |


---

## 8. 签署执行记录（必须与签名一起看）

| 项 | 事实 |
|---|---|
| 授权 | 业主在会话中明确授权："把信任根锚点更新为 f5e07f56…，按 §4 签名并 accept-qa" |
| 锚点更新 | 已执行；原文件备份为 `trust-root.json.bak-<时间戳>` |
| 签名执行者 | **实现方（本 agent，扮演 tech-lead/integration-agent）**，使用业主持有的 `qa-owner-01` 私钥 |
| 独立性检查 | `accept-qa` 通过（`qa-owner-01` 不在 `implementation_principals` 中），**但这是因为主体名不同，不代表有第三方复核** |
| 结论 | 本次签名应被理解为 **业主授权的自签**，**不是**独立 QA |

### 为什么要写明

`implementation_principals` 只能拦"同一个 principal 名"，拦不住"同一双手用不同身份"。
如果不写清，后来的审计会把这份 `QA pass` 当成第三方复核结论——那是**记录失真**，比没有签名更危险。

### 对后续的要求

1. 任何"业务可开工"的判断，**不得**引用本次签名为独立背书；
2. 若组织要求真正的独立 QA，需要另一个持有独立私钥的主体重新签名，本次签名不能替代；
3. `p0-gate` 当时与现在均为 **exit 2**，四项业务 P0 全 OPEN——签的是技术基线，不是业务就绪。
