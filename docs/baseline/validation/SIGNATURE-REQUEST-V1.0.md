# 签署与批准请求清单 V1.0（供外部评审）

- 候选：`L0-contract-baseline-r5`（`QA_PENDING`，rev 12）
- 冻结：`VERSION=1.1.1`、`FROZEN-MANIFEST` revision 6、205 文件
- `baseline_sha256 = 213c6ebc203ef846c3edf5397a9640310a683391878ddb5af4c12b8da25cbc52`
- `control_digest = 60bae549f5d5…`、`snapshot = f4f6ee2d9d52…`
- **当前：0 项已签署、0 项 P0 关闭、未合并**

> 每一项都要求：**签署人 + 日期 + 明确结论 + 依据的文件**。
> 只写「同意」不算；必须写清同意的是哪条结论、基于哪份证据。

---

## 1. `qa-owner`（4 项，其中 2 项为合并前置）

### 1.1 批准 r5 的基线锚点（治理动作）

| 项 | 内容 |
|---|---|
| 要做 | 把信任根 `approved_baseline_sha256` 从 `c8a73c37…` 更新为 `213c6ebc…` |
| 证据 | `QA-TRUST-CHAIN.md` §2–§3（含「锚点在仓外、不在冻结清单内」的查证） |
| 解锁 | 后续签名可被 `verify_envelope` 接受 |
| 风险 | 不做则任何签名都会被 `external approved baseline digest mismatch` 拒绝 |

### 1.2 签署 r5 独立 QA（**合并唯一拦路条件**）

| 项 | 内容 |
|---|---|
| 要做 | 用 `qa-ed25519-2026-10` 签署 `independent_qa_gate` 的载荷 |
| 证据 | `R5-QA-HANDOFF.md` §3（命令）、§4（8 项自查清单）、§5（对抗复跑） |
| 签名绑定 | `subject_sha256=732f729a…`，含 loop/gate/source/baseline/log 哈希 |
| 解锁 | 合并五条件中的第 2 项；合并后我再复验树指纹一致 |
| 禁止 | 实现者代签；载荷过期可重生成（被签内容不变） |

### 1.3 P-02 语义三选一

| 项 | 内容 |
|---|---|
| 选项 | A 接受时校验有效期/复核只看签名与撤销（建议）｜B 维持现状｜C 延长有效期 |
| 证据 | `DECISION-PACK-V1.1.1.md` D-01（含三选项影响面与正反例） |
| 解锁 | QA 历史证据能否长期复核 |

### 1.4 P-10 审计语义

| 项 | 内容 |
|---|---|
| 要做 | 是否同意信任根增加 `baseline_approvals` 追加列表（含批准人/时间/撤销） |
| 证据 | `ROUND4-PROPOSALS.md` P-10 |
| 解锁 | 基线批准可追溯（当前是单标量，覆盖即丢失） |

**签署记录模板**

```
我（principal_id）于 <日期> 确认：
[ ] 1.1 批准基线锚点 213c6ebc…（依据 QA-TRUST-CHAIN.md）
[ ] 1.2 批准 r5 合并（依据 R5-QA-HANDOFF.md，树指纹 f4f6ee2d…）
[ ] 1.3 P-02 选择：A / B / C
[ ] 1.4 P-10：同意 / 不同意
签名文件：<envelope 路径>    签名指纹：<sha256>
```

---

## 2. `data-owner`（提供 + 2 项裁决）

| 项 | 内容 | 证据 |
|---|---|---|
| 提供 | 37 表 `SHOW CREATE TABLE` + 索引/约束/触发器/引擎/字符集/版本 | `input-packs/02-data-owner.md` |
| 提供 | **字段名清单**（台账当前只有计数，无字段名） | 同上 |
| 裁决 | `user_operate` 台账 13 / 实体 12：**多出的那一列是什么** | `A2-FIELD-ATTRIBUTION.md` §1、`EXCEPTIONS-DECISION-SHEET.md` |
| 裁决 | `dialogue.user_id` 是否存在 | `B1-SQL-REFERENCE-INDEX.md` §2（三层均未发现） |
| 解锁 | P0-02 进入关闭评估；37 表复用决议可裁 | |

**关键证据**：`db-entity-check.json`（33/37 计数一致）、`db-orm-coverage.json`（FULL 14/37）、
`sql-refs-all-tables.json`（484 列、引用 270）。

---

## 3. `interface-owner`（2 项裁决 + 506 条填报）

| 项 | 内容 | 证据 |
|---|---|---|
| 填报 | 506 条运行时在用状态（路由导出/访问日志/调用方确认 三选一） | `samples/` 三份样例、`interface-decision-table.csv` |
| 裁决 | `API-0345`（`/ai/getRerankModelInfos`）是否曾上线、是否迁移 | `interface-inventory-check.json` |
| 裁决 | `API-0425` 行号漂移 11 行，确认 handler 归属 | 同上 |
| 解锁 | P0-01 进入关闭评估 | |

**注意**：静态核验 504/506 只证明「代码里有」，**不构成在用**。

---

## 4. `security-owner`（2 项批准）

| 项 | 内容 | 证据 |
|---|---|---|
| 批准 | E1 授权上下文正式规范（字段、签名、失效语义） | 草案见 `ROUND4-PARALLEL-WORK.md` §3.1 |
| 批准 | E2–E7 六类负例策略是否采纳（deny 优先/撤权即时/FAQ 按来源复核/图路仅整 KB） | `ROUND7-SUMMARY.md` §2.4、`p0-03-scenarios.json`（8 场景 8 变异） |
| 裁定 | 侧信道（N3）与错误元数据（N7）是否纳入六类，还是另立 | `B3-SCENARIO-INTERFACE-MAP.md` |
| 解锁 | P0-03 从 SIMULATED 进入真实验证 |

---

## 5. `index-owner`（1 项确认）

| 项 | 内容 | 证据 |
|---|---|---|
| 确认 | P0-04 五个验收阈值：存储峰值 ≤70%、内存 ≤80%、切换 P95 ≤5min、回滚 P95 ≤2min、四者同批次达标 | `P0-04-EXECUTION-CHECKLIST.md` §3 |
| 确认 | 数据规模（50 文件 / 1 万块）是否足够代表 | 同上 §1 |
| 提供 | S1–S5 真实执行结果 + 双代余量实测 | 同上 §2、§5 |
| 解锁 | P0-04 关闭、L1–L4 全部 | |

---

## 6. `baseline-owner`（2 项批准）

| 项 | 内容 | 证据 |
|---|---|---|
| 批准 | `requirements.lock` 收敛方案（2 处版本冲突 + 14 个无关重型包） | `DECISION-PACK-V1.1.1.md` D-02 |
| 批准 | P-08（扫描范围固定、源码/产物分轮）与 P-09（QA 载荷改用 control_digest） | `ROUND4-PROPOSALS.md` |
| 注意 | 任一实施都会改控制面 → 重冻结 → **r5 候选作废**，需与批次建齐合并为一次窗口 | |

---

## 7. `algorithm-owner`（提供，二选一）

| 项 | 内容 | 证据 |
|---|---|---|
| 路线 A | `magic_pdf` 离线包 + 模型清单（含 sha256） | `input-packs/07-algorithm-owner.md` |
| 路线 B | 旧系统对 6 份样本的参考输出（块数/文本/页码/offset） | 同上 |
| 现状 | 两臂均不可运行；PDF 等价性**未验证**；未切 pdfplumber | `pdf-verification-readiness.json` |

---

## 8. 签署后的影响总表

| 签署项 | 立即解锁 | 仍需 |
|---|---|---|
| 1.1 + 1.2 | **合并 r5** | 合并后复验 + 树指纹比对 |
| 1.3 | 历史 QA 可长期复核 | 实施 P-02（改控制面） |
| 2 | P0-02 关闭评估 | 迁移/回退记录 |
| 3 | P0-01 关闭评估 | `/retrieval_qa` 书面决议 |
| 4 | P0-03 真实验证 | 真实检索链环境 |
| 5 | P0-04 真实执行 | 四套存储 |
| 6 | 环境可复现性 | 干净容器实测 |
| 7 | PDF 等价性验证 | 另一臂 |

---

## 9. 声明

1. 本文是**请求**，不是批准记录；仓库中不存在任何对应的已签署内容。
2. 所有模拟结果标 `SIMULATED`；所有静态结论标 `CANDIDATE` 或 `SOURCE_OBSERVATION`。
3. 四项业务 P0 **全部 OPEN**，`p0-gate exit 2`，L1–L4 **BLOCKED**，业务可用性 **0%**。
