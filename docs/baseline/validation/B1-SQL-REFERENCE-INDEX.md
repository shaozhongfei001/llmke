# B1：源码 SQL 对目标列的引用索引（SOURCE_SQL_REFERENCE）

- 工具：`loops/LD-legacy-discovery/tools/sql_column_refs.py`（只读）
- 证据：`loops/LD-legacy-discovery/evidence/sql-column-refs.json`
- 扫描：39 个含 SQL 的 XML/Java/SQL 文件，命中 **24 条**列引用
- **能证明**：源码里哪些语句/映射引用了这个列名
- **不能证明**：数据库里存在该列（只有 DDL 能证明）；也不能证明「没搜到 = 不存在」

---

## 1. 引用矩阵

| 表 | 有引用的列 | **无任何引用**的列 |
|---|---|---|
| `re_embedding_file` | `is_del`、`kb_id`、`task_id` | `gmt_create`、`gmt_modified`、`create_by`、`update_by` |
| `re_embedding_retry_task` | `is_del`、`kb_id`、`file_id` | `gmt_create`、`gmt_modified`、`create_by`、`update_by` |
| `re_embedding_task` | `is_del`、`gmt_create`、`gmt_modified`、`kb_id` | `create_by`、`update_by`、`total_file_num`、`uid` |
| `user_operate` | `gmt_created`、`gmt_modified`、`user_id` | `is_del`、`create_by`、`update_by` |
| `dialogue` | `gmt_create`、`gmt_modified`、`create_by`、`update_by`、`session_id` | **`user_id`**、`kb_id`、`is_del` |

引用类型分三类，**不可混用**：
`SELECT` / `INSERT` / `UPDATE` / `DELETE`（手写 SQL）与 `RESULT_MAP_MAPPING`（ORM 映射声明）。

## 2. 对 `dialogue.user_id` 的专项结论

已检查范围：
- DO 实体属性（`DialogueDO.java`，13 字段）；
- Mapper `resultMap`（12 条映射）；
- Mapper 手写 SQL 语句；
- Java 注解 SQL；
- 继承（该类**无 `extends`**）、`association`/`collection`（该 mapper **未使用**）；
- `SELECT *`（本次扫描 **0 处**命中目标表）。

**结论表述（严格限定）**：
> **在当前已检查的源码范围内，未发现 `dialogue.user_id` 的任何属性、映射或 SQL 引用。**
> 数据库是否真无此列，仍须 DDL 核验。源码缺失 ≠ 列不存在。

设计文档要求为 `dialogue` 建 `user_id` 索引，而源码三层（实体/映射/SQL）均无该列 →
这构成一个**必须由 `data-owner` 用 DDL 裁定的冲突**，不能用「字段数一致」掩盖。

## 3. 「无引用」不等于「不存在」——三种必须区分的解释

| 解释 | 例子 | 如何区分 |
|---|---|---|
| **列不存在** | 设计未落地 | DDL 才能确认 |
| **列存在但由框架自动填充** | `create_by`/`gmt_create` 常由 MyBatis-Plus 自动填充，手写 SQL 不显式写 | 查 `MetaObjectHandler` / `@TableField(fill=...)` |
| **列存在但该模块不写** | `re_embedding_*` 可能由其他服务写入 | 查是否有其他服务的 DAO 引用该表 |

本轮观察到：`re_embedding_file`/`retry_task` 的四个审计列**全部无引用**，
而 `re_embedding_task` 的 `gmt_create`/`gmt_modified` **有引用**。
同模块内不一致，更可能是「部分表由别的路径写入」，而非「部分表没有审计列」。

→ 因此这三张表的审计列差异**必须**由 DDL 裁定，不得推测。

## 4. 与第五轮 ORM 覆盖率结论的关系

| 第五轮结论 | 本轮补充 |
|---|---|
| 未映射字段多为 `isDel`/审计列 | 本轮证明：其中一部分**连 SQL 也不引用**（如 `re_embedding_file.create_by`） |
| 「未映射 ≠ 不存在」 | 仍成立，但证据变弱：不能再用「SQL 里出现过」来反证 |
| ORM 覆盖率 38% | 这是**下界**，因为本轮才发现「无语句的 mapper」此前被整文件跳过 |

## 5. 自纠记录

| # | 问题 | 后果 | 修正 |
|---|---|---|---|
| 1 | 首版只扫 SQL 语句，未把 `resultMap` 当引用来源 | `dialogue.create_by` 等被误判为「无引用」（17 条 vs 24 条） | 增加 `RESULT_MAP_MAPPING` 类型 |
| 2 | `if not stmts: continue` 会整文件跳过「只有 resultMap 的 MyBatis-Plus 映射」 | `user_operate`、`re_embedding_task` 全部显示无引用 | 改为按文件名回推表名后继续处理 |
| 3 | 未处理「语句里出现的是别名/其他表」 | 文件名与语句推导可能不一致 | 改为**并集**，并记录推导来源 |

## 6. 边界与不做的事

- 不把本索引写入 `DATABASE-ASSETS.yaml`（控制面，且证据级别不够）；
- 不据此关闭 P0-02；
- 不声称任何表结构已确认；
- 动态 SQL 的 `<if>` 分支未逐分支判定（按语句整体计）。
