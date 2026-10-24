# 四项 P0 的输入表（第九轮）

> 判定口径：`p0-gate` 仍 rc=2，四项**全部 OPEN**。本表只回答"缺什么、谁给、给了之后怎么验"，
> 不构成任何关闭建议。`VERIFIED_INPUT` 列写"是"的，必须是仓库内可复算的产物。

## 汇总

| P0 | 判据（关闭需要什么） | 已验证输入（仓内可复算） | 缺失输入 | 责任人 | 当前判定 |
|---|---|---|---|---|---|
| P0-01 接口 | 506 条候选逐条给出"运行时注册 + 调用方确认" | 清单自洽性、状态分布、证据覆盖（`R9-T17`：506 全未验证，三项证据均 0） | `route export` 结果、调用方确认、逐条 `IN_USE/UNKNOWN` 裁决 | interface-owner | **OPEN** |
| P0-02 数据库 | 真实生产 DDL + 恢复副本 + 迁移 dry-run | 三产物对账（`R9-T05`：37/478 → 43/538，差 6 表 60 列） | 生产 DDL 快照、恢复副本、37 表遗留库实测、迁移脚本 | data-owner | **OPEN** |
| P0-03 权限 | security-owner 批准的 E1 规范 + 全链路过滤验证 | 授权上下文校验、SQL 谓词过滤、越权拒绝且不回显文件名（`modules/authz` + `answer_api` 真库用例） | E1 规范批准件、真实网关签名校验、跨 KB 撤权实测 | security-owner | **OPEN**（实现为候选） |
| P0-04 索引代次 | 四后端真实测试 + 双代余量 + 迟到重试实测 | 状态机/CAS/fencing/outbox 语义（`R9-T08`、`R9-T11` 真库）；代次守卫只取 ACTIVE | `document_chunk.generation_id`（缺列）、`index_outbox.claimed_at`（缺列）、四后端联调 | index-owner | **OPEN** |

## 逐项：给了输入后怎么验（可直接执行）

### P0-01
1. 拿到 `route export`（注册清单）后：与本清单按 `(service, method, path)` 对齐，产出差集；
2. 差分结果**只证明注册**；`IN_USE` 仍需调用方确认或访问日志；
3. 复算命令：`python3 coordination/p0-01-inventory-audit.py --out ...`（本表数字即由它产出）。

### P0-02
1. 拿到生产 DDL（`SHOW CREATE TABLE` 全量）后：与 `target-schema-v1.sql` 做同构比对；
2. 迁移脚本必须在**恢复副本**上执行，禁止直接对生产库跑；
3. 复算命令：`python3 coordination/p0-02-diff.py --old <生产DDL> --new artifacts/schema-v1.3.sql`。

### P0-03
1. E1 规范批准后，把 `policy_state` 从 `CANDIDATE_NOT_RELEASEABLE` 改为批准版本号；
2. 负例必须覆盖：跨 KB、非授权文件、FAQ 来源、邻近块/图回查、撤权后旧会话；
3. 现有可复用负例：`modules/answer_api/tests/test_answer_unit.py` 与 `test_answer_db.py`。

### P0-04
1. 先解决两处缺列（`generation_id`、`claimed_at`），否则"块属于哪一代"无法证明；
2. 四后端各自注入失败（部分成功 / 全失败 / 中断）后验证：旧代仍可读、新代不半可用；
3. 迟到重试：旧 `lease_token` 写入必须 0 行（已有 `insert_guarded_sql` 可复用）。

## 关于 `P0-CLOSURE.yaml` 的过期数据（保留原因，不擅自改）

- 现状：`baseline_version: 1.1.0`，而 `VERSION` 为 `1.1.1`。
- **未修订的原因**：该字段表示"这份 P0 登记适用于哪版基线"，属 owner 语义；实现方改成 1.1.1
  等于替 owner 宣称"新版基线下 P0 判据不变"，这是**替他人下结论**。
- 处置：保留原值，在此登记；由 baseline-owner 在下一次登记更新时一并处理。
- 副作用（如实）：该文件在 `doc_digest` 内，改动会让 `traceability_gate` STALE，
  因此即使要改也应与"建新批次 + 一次冻结"同批进行。
