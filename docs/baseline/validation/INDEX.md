# 文档索引（docs/baseline/validation）

> 本目录共 **80** 份文件。没有索引时很容易"拿到作废的当有效的"，交接前先看这里。

## 当前状态（唯一权威数字，2026-10-22）

| 项 | 值 |
|---|---|
| 门禁 | `framework-verify` exit 0 / **252 passed、0 skipped**（需 MySQL 实例在跑） |
| 落地验证 | `schema-verify.sh` PASS：43 表 / 538 列 / 97 模块测试 / 契约一致 / 体检 6 项 |
| 活动候选 | 无（r10 已 `DONE` 并合入 `main`：`b597fcc`） |
| 候选指纹 | `baseline_sha256=f5e07f56…`、`subject=66945f09…`、冻结 `revision=11`、212 文件 |
| 业务闸门 | `p0-gate` **exit 2**（四项 P0 全 OPEN） |
| 签名性质 | r10 为**业主授权自签**（非第三方独立 QA），详见 `R10-QA-HANDOFF.md` §8 |

## 在用（工具/脚本/SQL）（11）

| 文件 | 说明 |
|---|---|
| `consistency-doctor.py` | 一致性体检：找出"单看每张表都对、合起来不对"的数据。 |
| `contract-schema-check.py` | 契约字段 ↔ 数据库列 一致性检查（防"契约改了、库没跟上"）。 |
| `p0-01-route-extract.py` | P0-01 仪器：从 Java 源码提取路由，与「接口总表 CSV」比对。 |
| `p0-02-ddl-diff.py` | P0-02 仪器：把「真实 DDL」与「资产台账」做可判定比对。 |
| `p0-02-ddl-generate.py` | P0-02 仪器：从 ORM 注解生成候选 DDL（MySQL）。 |
| `p0-02-entity-extract.py` | P0-02 仪器（实体侧）：从 Java DO 的 ORM 注解提取「实体模型」，并校验字段明细 CSV。 |
| `p0-02-index-infer.py` | P0-02 / 5.1 仪器：从 Mapper SQL 反推"该建哪些索引"。 |
| `p0-02-table-ownership.py` | P0-02 / D-01 仪器：37 张表分别被哪些服务读写（共库还是分库的判据之一）。 |
| `p0-gate-redteam-audit.py` | P0 关闭闸门红队审计：不改仓库，只在 /tmp 造夹具，验证 check() 是否真能拦住伪造关闭。 |
| `schema-generate.py` | 按 LLMKE 规范 V1 生成目标 schema（旧模型仅作参考）。 |
| `schema-verify.sh` | 一键落地验证：在【本机 MySQL 独立实例】上从零建库、建表、跑模块集成测试。 |

## 参考（54）

| 文件 | 说明 |
|---|---|
| `A2-FIELD-ATTRIBUTION.md` | A2：四张差异表逐列归因（CANDIDATE，需 DDL 裁定） |
| `A2-ORM-COVERAGE.md` | A2 扩展：全 37 表 ORM 映射覆盖率（CANDIDATE） |
| `AI-ADVISORY-POLICY-V1.md` | AI 建议口径 V1（本轮由业主授权） |
| `B1-SQL-REFERENCE-INDEX.md` | B1：源码 SQL 对目标列的引用索引（SOURCE_SQL_REFERENCE） |
| `B3-SCENARIO-INTERFACE-MAP.md` | B3：P0-03 场景 ↔ 506 接口关联索引 |
| `B4-ORM-PARSER-BOUNDARY.md` | B4：ORM 覆盖率的定义、验证样例与解析边界 |
| `BASELINE-REVIEW-PACK-V1.0.md` | 基线现状评审包 V1.0（供外部评审） |
| `DECISION-PACK-V1.1.1.md` | 待批决策包（D-01 P-02 / D-02 requirements.lock） |
| `EXCEPTIONS-DECISION-SHEET.md` | 例外裁决单（6 行） |
| `MERGE-SEQUENCE-V1.1.1.md` | `fix-window/v1.1.1` 合并时序与回退点 |
| `ORM-PARSER-KNOWN-FAILURES.md` | ORM 解析器：保留的失败样例（不删除） |
| `P0-01-ROUTE-EXTRACT.md` | P0-01 仪器：源码路由提取 ↔ 接口清单比对（含实测结论） |
| `P0-02-CREATEBY-SEMANTICS.md` | P0-02 / D-03：`create_by` 到底存什么（源码证据链） |
| `P0-02-DDL-BASELINE-FROM-CODE.md` | P0-02：D-01 定案（共库）与 D-02 基线（从 ORM 生成候选 DDL） |
| `P0-02-DDL-INSTRUMENT.md` | P0-02 仪器：DDL ↔ 字段明细基线差异清单 |
| `P0-02-ENTITY-BASELINE.md` | P0-02 基线换源：用 ORM 注解替掉"二手 CSV" |
| `P0-02-INDEX-INFERENCE.md` | P0-02 / 5.1：从查询反推"该建哪些索引" |
| `P0-02-TABLE-COUPLING.md` | P0-02 / D-01：37 张表的跨服务耦合实测 |
| `P0-04-EXECUTION-CHECKLIST.md` | P0-04 真实执行清单与双代余量采集标准（草案，待 index-owner 认可） |
| `P0-04-READINESS.md` | P0-04 现状核查：双代/切换协议在代码里存在吗 |
| `P0-04-SIMULATION.md` | P0-04 五场景协议模拟结果（SIMULATED） |
| `P0-GATE-REDTEAM-AUDIT.md` | P0 关闭闸门红队审计 |
| `P0-INPUT-INDEX.md` | 四项业务 P0 的外部输入索引（合并后持续工作用） |
| `QA-HANDOFF-V1.0.md` | 独立 QA 交办说明 V1.0 |
| `QA-KEY-HANDOVER-V1.0.md` | QA 主体与密钥交接单 V1.0 |
| `QA-TRUST-CHAIN.md` | r5 独立 QA 信任链调查与决策包 |
| `REUSE-REVIEW-PACK.md` | 批量审阅包（22 组） |
| `ROUND4-PARALLEL-WORK.md` | 第四轮并行工作：P0-01 / P0-02 / P0-03 / PDF 验证 |
| `ROUND5-PLANS.md` | 第五轮计划类交付：A4 迁移草案 / PDF 离线前置 / 外部输入包 |
| `ROUND7-MATERIAL-DRIFT-AUDIT.md` | 第七轮材料漂移复审（第八轮阶段 0） |
| `ROUND7-PROGRESS.md` | 第七轮执行记录（证据工业化与并行交付） |
| `ROUND7-SUMMARY.md` | 第七轮长程任务总结（证据工业化 → 可裁决候选） |
| `SCHEMA-STANDARD-V1.md` | LLMKE 数据库设计规范 V1（新设计，旧模型仅作参考） |
| `SIGNATURE-REQUEST-V1.0.md` | 签署与批准请求清单 V1.0（供外部评审） |
| `T1-VERSION-REGISTER.md` | T1 版本一致性登记（逐文件定性，非批量替换） |
| `TL-长程执行总结-2026-10-21.md` | Tech Lead 长程执行总结（2026-10-21） |
| `TL-长程执行总结-第三轮-2026-10-21.md` | 第三轮长程执行总结（B 策略：L0 基线修复、独立 QA 与受控合并） |
| `TL-长程执行总结-第二轮-2026-10-21.md` | 第二轮长程执行总结 |
| `TL-长程执行总结-第五轮-2026-10-21.md` | 第五轮长程执行总结（保护 r5 前提下推进 P0 证据） |
| `TL-长程执行总结-第六轮-2026-10-21.md` | 第六轮长程执行总结（把静态线索推进到可裁决证据） |
| `TL-长程执行总结-第四轮-2026-10-21.md` | 第四轮长程执行总结与下一步建议 |
| `TL-首次回执-V1.0-20261021.md` | TL 首次回执 V1.0（LLMKE V1.1.0 覆盖补丁施工） |
| `VALIDATION.md` | V1.1.0 实际验证回执 |
| `WINDOW-BUNDLE-VERIFIED.md` | 下一窗口补丁包：已验证（W-05 / W-05b / W-02 / W-04） |
| `WINDOW-RUNBOOK.md` | 下一窗口执行手册（一条命令） |
| `WORKSPACE-MIGRATION-RECORD-V1.0.md` | 工作区迁移执行记录 V1.0 |
| `qa-payload-L0-r2.json` | qa-payload-L0-r2.json |
| `qa-payload-LD-r2.json` | qa-payload-LD-r2.json |
| `qa-payload-l0-r2.json` | qa-payload-l0-r2.json |
| `qa-payload-ld-r2.json` | qa-payload-ld-r2.json |
| `qa-payload-r5.json` | qa-payload-r5.json |
| `qa-payload-r7.json` | qa-payload-r7.json |
| `qa-payload-r9.json` | qa-payload-r9.json |
| `results.json` | results.json |

## 待 owner 裁定（6）

| 文件 | 说明 |
|---|---|
| `FRAMEWORK-DEFECT-PROPOSALS-V1.0.md` | 框架缺陷变更提案 V1.0（R-03 / R-05 / R-06 / R-07 / R-08 / R-09） |
| `NEXT-WINDOW-BACKLOG.md` | 下一窗口待办（Backlog） |
| `P0-03-DESIGN-PROPOSAL.md` | P0-03 设计提案：授权上下文与逐路执行 |
| `P0-04-DESIGN-PROPOSAL.md` | P0-04 设计提案：代次 / 激活指针 / fencing / 租约 |
| `ROUND4-PROPOSALS.md` | 第四轮发现的控制面缺陷提案（P-08 / P-09 / P-10） |
| `W-01-WINDOW-PROPOSAL.md` | W-01 窗口变更方案：把模块测试接入门禁，并补上"证据绑定业务代码" |

## 历史（数字为当时值）（5）

| 文件 | 说明 |
|---|---|
| `FIX-WINDOW-V1.1.1-RESULT.md` | 受控变更窗口 V1.1.1 实施结果 |
| `ROUND-INVENTORY-2026-10-22.md` | 本轮长程任务盘点（2026-10-22 收口） |
| `SCHEMA-V1-RESULT.md` | LLMKE 目标 schema V1：生成结果与核查 |
| `W-01-RESULT.md` | W-01 / W-01b 窗口实施结果 |
| `W-02-W05-RESULT.md` | 窗口结果：弃 r7 → 应用补丁包（W-05 / W-05b / W-02 / W-04） |

## 当前候选交接（2）

| 文件 | 说明 |
|---|---|
| `R10-QA-HANDOFF.md` | r10 交接（`DONE`，签名为**业主授权自签**） |
| `INDEPENDENT-QA-PROMPT.md` | **给独立 QA 的提示词**（真独立背书走这里，需新批次） |

## 已作废/历史（3）

| 文件 | 说明 |
|---|---|
| `R5-QA-HANDOFF.md` | r5 独立 QA 交接包（含硬阻塞） |
| `R7-QA-HANDOFF.md` | r7 独立 QA 交接（W-01 + W-01b） |
| `R9-QA-HANDOFF.md` | r9 独立 QA 交接（W-05 / W-05b / W-02 / W-04） |

## 索引（1）

| 文件 | 说明 |
|---|---|
| `INDEX.md` | 文档索引（docs/baseline/validation） |

## 用法提示

- **复现结论**：只用「在用」组，命令见各文件头部；
- **看当前状态**：本页表格 + `ROUND-INVENTORY-2026-10-22.md`；
- **历史文档的数字不要当现状**：那是当时实测值，故意不改写；
- **作废的 QA 交接包**：仅用于复盘签署流程，不要拿去签名。
