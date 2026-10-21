# 第三轮任务账本（B 策略）

- 裁决：不合 `fix-window/v1.1.1` 到 `main`；以 `L0-contract-baseline-r5` 为下一目标批次
- 纪律：先改齐控制面 → 一次性冻结 → 再跑门禁 → 独立 QA；不在门禁执行中重冻结

## 1. 任务表

| ID | 目标 | 状态 | 证据 / 说明 |
|---|---|---|---|
| T1 | 修复 T-12 版本一致性 | **DONE** | `docs/baseline/validation/T1-VERSION-REGISTER.md`；逐文件定性，未批量替换 |
| T2-a | P-02 取得 `qa-owner` 语义确认 | **BLOCKED** | 决策包 D-01（`DECISION-PACK-V1.1.1.md`），三选一待选 |
| T2-b | `requirements.lock` 去重 | **BLOCKED** | 决策包 D-02：2 处版本冲突（`pip` 25.0.1/26.2.1、`idna` 3.19/3.20）、14 个无关重型包、105 行/95 唯一包 |
| T3-a | 建立 r5 并一次性冻结 | **DONE** | revision 6、控制面 205 文件、`baseline_sha256=213c6ebc…` |
| T3-b | 跑 7 条开发门禁 + framework-verify + evidence-check | **DONE** | 7/7 pass；exit 0 / 145 passed；evidence-check PASS |
| T3-c | 对抗性检查 3 组 | **DONE** | 控制面变化→7/7 STALE；日志篡改→hash mismatch；文档改动→仅 traceability STALE |
| T3-d | 独立 QA 检查 r5 | **BLOCKED** | `qa-run` 已产出 `QA_PENDING`/`LOCAL_QA_CANDIDATE`；签名未取得，原因见 T4 |
| T4 | 合并到 `main` | **BLOCKED** | 五条件中仅第 1 项满足；第 2 项（QA 允许合并）未满足，故不合并 |

## 2. 合并五条件核对

| # | 条件 | 现状 |
|---|---|---|
| 1 | r5 门禁 + evidence-check 全通过 | **满足** |
| 2 | 独立 QA 对 r5 冻结候选给出允许合并结论 | **未满足** |
| 3 | 拟合并树与 QA 审阅树一致 | 待 QA 签署时锁定树哈希（当前 `HEAD^{tree}` 需在签署后复核） |
| 4 | 合并差异已核对、无未审查提交 | 满足（`main` 是祖先；临时工作树实测合并结果树 == 分支树 `7db46fca…`） |
| 5 | 符合分支保护 | `main` 无保护规则；按约定 `--no-ff`，不强推 |

## 3. 唯一硬阻塞的构成

1. 信任根 `approved_baseline_sha256 = c8a73c37…`（窗口前旧基线），r5 为 `213c6ebc…`
   → 任何签名都会被 `external approved baseline digest mismatch` 拒绝；
2. 由实现者签名或修改信任根 = 自签，独立性失效。

处置与命令：`docs/baseline/validation/R5-QA-HANDOFF.md` §3（由 `qa-owner` 在受保护环境执行）。

## 4. r4 的处置（按裁决保留）

- r4 状态仍为 `IN_DEV`，证据文件**未被删除或覆盖**；
- 因 T-12 改动 + 重冻结，r4 的 `evidence-check` 现在报 STALE —— 这是**正确事实**：
  它的记录绑定 revision 5 的基线，不再代表当前候选；
- 因此 **不得引用 r4 的证据作为 r5 的验收证据**；
- 是否把 r4 显式标为 `SUPERSEDED`（P-06 已支持）留待业主措辞确认，本轮未改其状态。

## 5. 下一条精确命令

```bash
cd ~/data/dev/llmke
~/data/dev/coordination/mk.sh framework-verify                                  # 期望 0
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5     # 期望 PASS
~/data/dev/coordination/mk.sh p0-gate                                           # 期望 2（业务仍阻断）
```

---

## 6. 合并阻塞期间的持续工作（第三轮追加）

| ID | 事项 | 状态 | 证据 |
|---|---|---|---|
| T-10 | 37 表/482 字段 ↔ 源码 DO 实体静态对照 | **部分完成**（静态对照完成；DDL 仍缺，结论只能 CANDIDATE） | `loops/LD-legacy-discovery/evidence/db-entity-check.{md,json}`、工具 `tools/db_entity_check.py` |
| T-11 | 504 条逐端点决议 | BLOCKED（需调用方在用确认） | 静态核验已完成 504/506 |

**T-10 实测结论**

- 37 表全部找到对应实体（源文件缺失 0）；计数一致 **33/37**。
- 4 张表计数不符：`re_embedding_file`(13→14)、`re_embedding_retry_task`(12→13)、
  `re_embedding_task`(13→14)、`user_operate`(13→12)。
- `dialogue` 实体 13 字段：**`create_by` 存在、`user_id` 不存在**、`kb_id` 存在
  → 与设计文档「建 `user_id` 索引」的要求冲突，需 `data-owner` 用 DDL 裁定。
- 边界：实体字段数 ≠ 表结构；未识别继承字段、逻辑删除、JSON 列；不替代 M-04。

---

## 7. 第四轮（QA 等待期间）

| ID | 事项 | 状态 | 产物 |
|---|---|---|---|
| R4-1 | QA 信任链调查与签署决策包 | **DONE** | `docs/baseline/validation/QA-TRUST-CHAIN.md` |
| R4-2 | P0-01 506 条可填决策表 | **DONE** | `evidence/interface-decision-table.csv`（504 OK / 1 行号漂移 / 1 仅注释） |
| R4-3 | P0-02 字段级对照 | **DONE（CANDIDATE）** | `ROUND4-PARALLEL-WORK.md` §2；台账无字段名清单，已登记为 data-owner 输入 |
| R4-4 | P0-03 E1–E8 + 六类负例草案 | **DONE（草案）** | 同文件 §3 |
| R4-5 | PDF 集成验证 | **BLOCKED** | 两臂均不可运行；就绪度证据 + 协议 + 输入清单 |
| R4-6 | 扫描范围 502/503 调查 | **DONE** | `evidence/security-scan-scope.json`；根因=扫描整树、每跑门禁 +1 日志 |
| R4-7 | 控制面缺陷提案 P-08/P-09/P-10 | **DONE（提案）** | `ROUND4-PROPOSALS.md` |
| R4-8 | 修复自引入的绝对路径回归 | **DONE** | `FAIL-4TH-01`；security-check 恢复 PASS |
| R4-9 | P0-04 五场景协议模拟 + 变异对照 | **DONE（SIMULATED）** | `docs/baseline/validation/P0-04-SIMULATION.md`；5/5 场景 PASS，5/5 变异体被拒 |

**r5 候选未受影响**：所有产物位于 `docs/baseline/validation/` 与 `loops/**`（`snapshot()` 排除），
`record.source_sha256 == snapshot(ROOT)` 复核仍为 `True`。

---

## 8. 第五轮（保护 r5 前提下的并行推进）

| ID | 事项 | 状态 | 产物 | 分类 |
|---|---|---|---|---|
| R5-A1 | P0-03 六类负例模拟 + 变异 | **DONE** | `evidence/p0-03-scenarios.json`、`tools/p0_03_scenarios.py` | **SIMULATED** |
| R5-A3 | P0-01 三种输入样例 | **DONE** | `docs/baseline/validation/samples/`（路由导出 / 访问日志 / 调用方确认） | 模板 |
| R5-A2 | 四表逐列归因 | **DONE** | `A2-FIELD-ATTRIBUTION.md`、`evidence/db-mapper-columns.json` | **CANDIDATE** |
| R5-A4 | P-08/P-09/P-10 迁移草案 | **DONE（仅草案）** | `ROUND5-PLANS.md` §1 | 计划 |
| R5-B1 | PDF 离线依赖与前置 | **DONE（清单）** | 同上 §2 | 计划 |
| R5-B2 | 六方外部输入包 | **DONE** | 同上 §3 | 计划 |

**关键结果**：P0-03 **7/7 场景 PASS + 7/7 变异体被拒**；
A2 出现**方向反转**——`user_operate` 12 字段全部有列映射且无继承，说明「台账多一列」比「实体多字段」更可能；
`dialogue.kbId` 未在 resultMap 中映射，第四轮「kbId 存在」的结论据此降级。

**r5 未受影响**：产物全在 `docs/baseline/validation/`、`loops/**`（`snapshot()` 排除）。
| R5-C1 | 全 37 表 ORM 覆盖率（A2 扩展） | **DONE** | `A2-ORM-COVERAGE.md`、`evidence/db-orm-coverage.json`；FULL 14 / PARTIAL 17 / NONE 3 / NO_MAPPER 3 | **CANDIDATE** |

---

## 9. 第六轮（把静态线索推进到可裁决证据）

| ID | 事项 | 状态 | 产物 | 分类 |
|---|---|---|---|---|
| R6-B1 | SQL 列引用索引 | **DONE** | `B1-SQL-REFERENCE-INDEX.md`、`evidence/sql-column-refs.json`（24 条引用） | **SOURCE_SQL_REFERENCE** |
| R6-B2 | 七方一页提交包 | **DONE** | `input-packs/01…07-*.md` | 模板 |
| R6-B3 | 场景↔接口关联 | **DONE** | `B3-SCENARIO-INTERFACE-MAP.md`、`evidence/scenario-interface-map.csv`（1233 条关联） | 关联（非漏洞） |
| R6-B4 | ORM 解析边界与样例 | **DONE** | `B4-ORM-PARSER-BOUNDARY.md`、`tools/orm_parser_selftest.py`（6/6） | 口径 |

**B1 关键结论**：`dialogue.user_id` 在实体/映射/SQL **三层均无引用** → 表述限定为
「已检查源码范围内未发现」，数据库是否存在仍待 DDL；`user_operate.user_id` 有引用。
**B3 缺口**：草案 E7（邻近块/图片回查二次取数）**无对应场景**，已标 GAP，未强行计入。
**B4 风险**：association/collection 内嵌列被计入父表、同名 property 覆盖导致丢列（已实测）。
| R6-D1 | 补 E7 场景（邻近块/图片回查二次取数） | **DONE** | `p0_03_scenarios.py` N8、`p0-03-scenarios.json`；**8/8 场景 + 8/8 变异体被拒** | **SIMULATED** |
| R6-D2 | B3 六类覆盖改为按场景反推（去硬编码） | **DONE** | `B3-SCENARIO-INTERFACE-MAP.md`：**E2–E7 全部有场景，无 GAP** | 关联 |

---

## 10. 第七轮（证据工业化）

| ID | 事项 | 状态 | 产物 | 分类 |
|---|---|---|---|---|
| R7-M1 | 555 项复用候选矩阵 | **DONE** | `evidence/reuse-candidate-matrix.csv`（555 行 / 22 组）、`tools/build_reuse_matrix.py` | 候选，**已批准 0** |
| R7-A2 | ORM 解析器修复（嵌套归属 + 同名 property） | **DONE** | `db_mapper_columns.py`、`orm_parser_selftest.py`（6/6） | 工具 |
| R7-A1 | SQL 引用扩至全 37 表 | **未做** | 前置：台账无字段名清单，列来源只能从 DO 推 | 阻塞自设 |
| R7-B3 | E1–E8 ↔ N1–N8 追溯 | **DONE** | `ROUND7-PROGRESS.md` §4；E2–E7 全覆盖无 GAP | 关联 |

**修复未改变 38%**：真实 34 个 mapper 中嵌套映射 0、同名 property 冲突 0 —— 修复价值在消除潜在风险。
| R7-A1b | 全 37 表列引用索引（带证据等级） | **DONE** | `evidence/sql-refs-all-tables.json`、`tools/sql_refs_all_tables.py`；484 列（MAPPER_FACT 365 / CAMEL_INFERENCE 119），被引用 270 | 只读索引 |
| R7-M2 | 22 组批量审阅包 | **DONE** | `REUSE-REVIEW-PACK.md`、`evidence/reuse-review-pack-summary.json`；555 行、**例外仅 6 行** | 候选 |
| R7-A1c | 零引用表核查（映射方式取证） | **DONE** | `sql-refs-all-tables.json` 增 `mapping_mode`；27 XML_SQL / **10 MP_BASEMAPPER**；5 张零引用表全部为 BaseMapper 实体，零引用已解释 | 事实 |
| R7-M3 | 6 条例外独立裁决单 | **DONE** | `EXCEPTIONS-DECISION-SHEET.md`、`evidence/exceptions-decision-sheet.csv` | 待裁决 |
| R7-A1d | 驼峰约定取证（决定推断列的证据等级） | **DONE** | 无显式运行配置；代码生成器 2 处 `NamingStrategy.underline_to_camel`；10 张 MP 表的推断基座升级为 `MP_CODEGEN_CONVENTION`，其余 27 表仍 `CAMEL_INFERENCE` | 事实+推断 |
| R7-A2b | 重复实体/同名文件显式报告 | **DONE** | `find_report()`；实测命中 **DB-34**（两个 UserOperateDO，字段完全相同），结论不受影响但已记录歧义 | 工具 |
| R7-A1e | 注释剥离分类 | **DONE** | 全表索引增 `columns_comment_only`：8 张表共 36 处仅注释出现 | 证据分级 |
| R7-P04 | P0-04 真实执行清单与余量采集标准 | **DONE（草案）** | `P0-04-EXECUTION-CHECKLIST.md`：五场景判据、五项余量指标、四个验收阈值 | 草案 |
| R7-A3 | 确定性检查 | **DONE** | 同输入两次输出逐字节一致（矩阵/全表索引/审阅包） | 工具 |
