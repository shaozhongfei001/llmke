# 第七轮长程任务总结（证据工业化 → 可裁决候选）

- 分支 `fix-window/v1.1.1`，HEAD `250cab8`；`main` 仍 `4b1fca8`（**全程未合并**）
- 累计提交 30 个；`VERSION=1.1.1`；冻结 revision 6（205 文件）
- `control_digest=60bae549f5d5`、`doc_digest=4a5ccba1843e`、`snapshot=f4f6ee2d9d52`（均未变）
- r5：`QA_PENDING`，7 条开发门禁 pass；四项 P0 全 OPEN
- 本文件不参与源码快照与冻结控制面

---

## 1. 交付清单（7 项要求 → 7 项完成）

| # | 要求 | 产物 | 状态 |
|---|---|---|---|
| 1 | 555 项候选裁决矩阵 | `evidence/reuse-candidate-matrix.csv`（555 行 / 22 组） | ✅ |
| 2 | 全 37 表 SQL 引用索引 | `evidence/sql-refs-all-tables.json` | ✅ |
| 3 | ORM 分析器修复 | `tools/db_mapper_columns.py` + `orm_parser_selftest.py` 8/8 | ✅ |
| 4 | E7 场景 | `p0-03-scenarios.json` N8 | ✅ |
| 5 | P0 输入审阅包 | `input-packs/01…07`、`REUSE-REVIEW-PACK.md`、`EXCEPTIONS-DECISION-SHEET.md` | ✅ |
| 6 | r5 QA 可执行交接 | `QA-TRUST-CHAIN.md`、`R5-QA-HANDOFF.md` | ✅（待 owner 执行） |
| 7 | 可运行工具/可复算产物 | 6 个工具 + 5 份可复算 JSON/CSV | ✅ |

---

## 2. 核心数据

### 2.1 555 项候选矩阵

| 维度 | 值 |
|---|---|
| 总行数 | **555**（源码 12 / 表 37 / 接口 506） |
| 有证据或明确未知原因 | **555 / 555** |
| **已批准** | **0** |
| `DECISION_PENDING` | 555 |
| 批量审阅组 | 22 |
| 必须逐行裁决的例外 | **6** |

**6 条例外**：4 张计数不符的表（`re_embedding_file/retry_task/task`、`user_operate`）
+ 2 条静态异常接口（`API-0345` 仅注释、`API-0425` 行号漂移）。

### 2.2 全 37 表列索引

| 指标 | 值 |
|---|---|
| 列总数 | **484** |
| `MAPPER_FACT`（resultMap 显式） | **365** |
| `CAMEL_INFERENCE`（推断） | **119** |
| SQL/映射中被引用 | **270** |
| 仅出现在注释中 | 36（8 张表） |
| 映射模式 | `XML_SQL` 27 / `MP_BASEMAPPER` **10** |

**零引用表 5 张已解释**：全部是 MyBatis-Plus `BaseMapper` 实体（无 XML SQL，框架运行时生成）。

### 2.3 ORM 覆盖率与修复

| 指标 | 值 |
|---|---|
| FULL / PARTIAL / NONE / NO_MAPPER | **14 / 17 / 3 / 3** |
| 已知歧义 | **DB-34**（两个同名 `UserOperateDO`，字段均 12 个且相同） |
| 修复缺陷 | 嵌套列污染父表、同名 property 静默丢列、同名文件静默取首个 |
| 对数字的影响 | **无**（真实 34 个 mapper 中嵌套 0、冲突 0）——修复价值是消除潜在失真 |

### 2.4 模拟验证（全部 SIMULATED）

| 对象 | 场景 | 变异体 | 说明 |
|---|---|---|---|
| P0-03 六类负例 | **8/8 通过** | **8/8 被拒** | E2–E7 全覆盖，N3/N4/N7 为扩展 |
| P0-04 五场景 | **5/5 通过** | **5/5 被拒** | 纯内存模型 |

---

## 3. 自纠记录（本轮 5 条，全部保留）

| # | 问题 | 后果 | 修正 |
|---|---|---|---|
| 1 | B1 未把 `resultMap` 当引用来源 | 引用数 17 → 24 | 增加 `RESULT_MAP_MAPPING` |
| 2 | 整文件跳过「只有 resultMap 的 mapper」 | `user_operate` 全显示无引用 | 按文件名回推表名 |
| 3 | 未处理别名/他表 | 表名推导不一致 | 改为并集并记录来源 |
| 4 | B4 按 property 比对而非 column | 6 样例全误判 FAIL | 改判 `result_map` 的值 |
| 5 | 审阅包例外规则过窄 | 例外 1 行（漏掉 5 行真异常） | 带异常备注即为例外 → 6 行 |

---

## 4. 门禁实测

| 命令 | 结果 |
|---|---|
| `framework-verify` | **exit 0 / 145 passed** |
| `security-check` | **PASS（560 文件）** |
| `evidence-check --loop r5` | **PASS（未 STALE）** |
| `p0-gate` | **exit 2**（四项 P0 全 OPEN） |
| `verify-all.sh` | 3 项通过、0 异常 |

---

## 5. 进度（按可核对计数，不用未定义百分比）

| 项 | 分子/分母 |
|---|---|
| 复用决议 | **已批准 0 / 555** |
| 候选覆盖 | 有证据 555 / 555 |
| 四项 P0 关闭 | **0 / 4** |
| L1–L4 解锁 | **0 / 4** |
| L 系业务切片实现 | **0** |
| 独立 QA 签署 | **0 / 1（r5）** |
| 合并 | **未执行** |
| 业务可用性 | **0%** |

---

## 6. 结论

第七轮把「证据碎片」装配成了**可裁决的形式**（555 行矩阵、6 行例外、484 列索引、8 场景模拟），
但**没有任何一项被批准、没有任何 P0 关闭、没有任何业务切片实现**。

继续推进只剩外部输入，静态分析已到顶。
签署需求与证据清单见 `SIGNATURE-REQUEST-V1.0.md`。
