# A2 扩展：全 37 表 ORM 映射覆盖率（CANDIDATE）

- 目的：回答一个具体问题——**能不能用 ORM 层替代 DDL 来确认列？**
- 工具：`loops/LD-legacy-discovery/tools/db_orm_coverage.py`
- 证据：`loops/LD-legacy-discovery/evidence/db-orm-coverage.json`
- 口径：`FULL`=resultMap 覆盖全部实体字段；`PARTIAL`=有 resultMap 但未覆盖全部；
  `NONE`=有 mapper 但无 resultMap（纯手写 SQL）；`NO_MAPPER`=找不到 mapper
- **结论一律 CANDIDATE**：即使 FULL 也看不到索引/约束/引擎/字符集

---

## 1. 总量：只有 38% 的表 ORM 完整

| 覆盖度 | 表数 | 占比 |
|---|---|---|
| **FULL** | **14** | **38%** |
| PARTIAL | 17 | 46% |
| NONE（有 mapper 无 resultMap） | 3 | 8% |
| NO_MAPPER（无 mapper 文件） | 3 | 8% |
| 合计 | 37 | 100% |

**直接答案：不能。** 62% 的表在 ORM 层拿不到完整列清单，
用 ORM 替代 DDL 会得到「部分表可信、其余靠猜」的结论。

## 2. 缺口分布：多数只差 1 个字段

| 缺口 | 表数 |
|---|---|
| 差 **1** 个字段 | **13** |
| 差 3 | 1 |
| 差 4 | 1 |
| 差 6 | 1 |
| 差 7 | 1 |

13/17 的 PARTIAL 表只差 1 个字段——这说明差异**不是随机遗漏**，而是有规律的。

## 3. 最常未映射的字段（关键推论）

| 字段 | 出现次数 | 性质 |
|---|---|---|
| `isDel` | **10** | 逻辑删除 |
| `id` | 6 | 主键（部分 mapper 用 `<id>` 或 `SELECT *`） |
| `gmtCreate` | 6 | 审计列 |
| `gmtModified` | 6 | 审计列 |
| `createBy` | 5 | 审计列 |
| `updateBy` | 4 | 审计列 |
| `kbId` / `status` / `description` / `databaseId` | 各 3 | 业务列 |

**推论（强）**：
未映射的字段集中在**逻辑删除与审计列**，这几乎必然是「resultMap 只列了查询需要列」，
**不是这些列不存在**。业务上 `create_by`/`gmt_create` 不可能没有。

→ 因此上一轮的判断需要修正方向：**「实体比台账多 1」的最可能解释是
台账计入了 `isDel`/审计列，而 resultMap 没映射它**，而不是「实体多写了个非持久化字段」。

## 4. 对四张差异表的具体含义

| 表 | 上一轮结论 | 本轮修正 |
|---|---|---|
| `user_operate` | 台账 13 / 实体 12，方向不明 | 12/12 全映射且无继承 → **台账侧多一列**（很可能是审计或逻辑删除列） |
| `re_embedding_file` | 实体 14 / 台账 13 | mapper **无 resultMap**（NONE），无法用 ORM 判定；`待 DDL` |
| `re_embedding_retry_task` | 实体 13 / 台账 12 | 同上（NONE）；`待 DDL` |
| `re_embedding_task` | 实体 14 / 台账 13 | PARTIAL 10/14，未映射 `totalFileNum`/`uid`/`createBy`/`modifiedBy` —— 典型「resultMap 不完整」；`待 DDL` |
| `dialogue` | 实体 13 = 台账 13，但缺 `user_id` | 12/13，未映射 `kbId`；**`user_id` 在实体与 resultMap 中均不存在** |

## 5. 三条方法论结论

1. **未映射 ≠ 不存在**：把「resultMap 没有」当成「列不存在」，方向就错了。
2. **计数一致 ≠ 语义对齐**：`dialogue` 13=13，但 `user_id` 缺失、`kbId` 未映射。
3. **ORM 不能替代 DDL**：38% 完整率不足以支撑「结构已确认」的结论。

## 6. 边界

- 本轮只做只读静态分析，未连接任何数据库；
- 未解析 `<association>`/`<collection>` 嵌套映射，可能低估覆盖度；
- 未识别 mapper 中 `SELECT *` 的表（这类表的列完全不在 resultMap 里）；
- `NO_MAPPER` 的 3 张表（`tools_table`、`tools_table_column`、`tools_table_file`）
  可能是 MyBatis-Plus 直接按注解工作，需二次确认。

## 7. 对 P0-02 的意义

P0-02 关闭必须依赖 `data-owner` 的真实 DDL，**没有任何静态替代路径**：
- DO 字段数：只反映 Java 类；
- resultMap：只反映查询所需列（62% 不完整）；
- 手写 SQL：只反映被查询到的列（弱证据）。

三者叠加仍不等于 schema。**继续标 `CANDIDATE`，不关闭 P0-02。**
