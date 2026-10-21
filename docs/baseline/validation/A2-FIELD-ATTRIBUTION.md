# A2：四张差异表逐列归因（CANDIDATE，需 DDL 裁定）

- 方法升级：第四轮只能用 DO 字段名 + 驼峰猜列名；本轮改用 **MyBatis Mapper XML** 的
  `resultMap` 与手写 SQL，拿到**源码级的列名证据**
- 结论分类：`SOURCE_FACT`（mapper 明确映射）/ `WEAK`（仅在手写 SQL 中出现）/ `PENDING_DDL`
- 工具：`loops/LD-legacy-discovery/tools/db_mapper_columns.py`
- 证据：`loops/LD-legacy-discovery/evidence/db-mapper-columns.json`
- **仍不等于 DDL**：索引、约束、触发器、引擎、字符集、默认值都看不到；**不关闭 P0-02**

---

## 0. 先说方法本身的局限（否则结论会被高估）

| 局限 | 影响 |
|---|---|
| 34 个 mapper 中**多数没有 `resultMap`**，只有手写 SQL | 无法得到完整列清单，只能得到「SQL 里出现过哪些列」 |
| 手写 SQL 里的标识符可能是**其他表**的列 | `WEAK` 级证据必须标注，不能当 schema |
| `resultMap` 可能只映射查询需要的子集 | 「未映射」≠「不存在该列」 |
| 未识别继承 | 四张表实测均**无 `extends`**，故继承因素在本轮可排除 |

> **自纠记录**：首版解析只处理 `<result>` 未处理 `<id>`，导致 `re_embedding_task.id` 被误判为「未映射」。
> 已修正（`10/14` 而非 `9/14`）。这类解析缺陷会直接改变归因方向，必须在报告里留痕。

---

## 1. `user_operate`（DB-34）：台账 13 vs 实体 12 —— **方向反转**

| 事实 | 值 |
|---|---|
| 实体字段 | **12** |
| `resultMap` 映射 | **12/12（全部）** |
| 实体是否继承 | **否** |
| 台账申报 | **13** |

**归因**：既然 12 个字段全部有明确列映射、且无继承，那么「台账 13」更可能是
**数据库里有一列，而 DO 没有映射**（而不是 DO 多出一个非持久化字段）。

→ 这与第四轮的直觉**相反**。第四轮只能说「差 −1」，本轮能把方向锁定为「台账侧多一列」。
→ 具体是哪一列，**必须靠 DDL**（`待 DDL 裁定`）。

## 2. `re_embedding_file`（DB-18）：台账 13 vs 实体 14

| 事实 | 值 |
|---|---|
| 实体字段 | 14 |
| `resultMap` | **无**（该 mapper 只有手写 SQL） |
| SQL 中出现过的列 | `id`、`task_id`、`kb_id`、`is_del`、`status`（5 个） |
| 其余字段 | `kbName`、`fileId`、`gmtCreate`、`gmtModified`、`totalChunkNum`、`processedChunkNum`、`errorChunkNum`、`isMigrate`、`lastError` —— **无源码级列证据** |

**归因**：无法判定多出的 1 个字段是持久化列还是查询辅助属性。
`待 DDL 裁定`。**不得**据此认定「实体多写了一个字段」。

## 3. `re_embedding_retry_task`（DB-19）：台账 12 vs 实体 13

| 事实 | 值 |
|---|---|
| 实体字段 | 13 |
| `resultMap` | **无** |
| SQL 中出现过的列 | `file_id`、`id`、`is_del`、`task_id`、`type`（5 个） |
| 无列证据 | `uid`、`payload`、`lastError`、`gmtCreate`、`gmtModified`、`retryTimes`、`status`、`kbId` |

**归因**：同 DB-18，`待 DDL 裁定`。

## 4. `re_embedding_task`（DB-20）：台账 13 vs 实体 14

| 事实 | 值 |
|---|---|
| 实体字段 | 14 |
| `resultMap` 映射 | **10/14** |
| **未映射字段** | `totalFileNum`、`uid`、`createBy`、`modifiedBy` |
| 已映射 | `id`、`kbId`、`kbName`、`embeddingModelName`、`status`、`isDel`、`logSummary`、`gmtCreate`、`gmtModified`、`msgKey` |

**归因**：4 个未映射字段里，`createBy`/`modifiedBy` 强烈提示「ORM 只映射了查询所需列」，
而**不是**这些列不存在（业务上几乎必然有创建人）。因此这张表最可能的解释是
**resultMap 不完整**，而非实体多字段。

→ 这条恰好说明：**不能用 resultMap 的缺失倒推列不存在**。

## 5. `dialogue`（重点，语义问题单列）

| 事实 | 值 |
|---|---|
| 实体字段 | 13（与台账 13 **计数一致**） |
| `resultMap` 映射 | **12/13** |
| **未映射** | `kbId` |
| `createBy` | **已映射**（`create_by`） |
| `user_id` | **实体中不存在** |

**必须单列的两个问题**：

1. **`user_id` 缺失 vs 设计文档要求**
   设计文档要求为 `dialogue` 建 `user_id` 索引，而实体里没有该属性、resultMap 里没有该列。
   这可能是：(a) 设计超前于实现；(b) 列存在但 DO 未映射；(c) 索引建在别的表上。
   **三种可能都只能靠 DDL 裁定**，不能用「字段数一致」覆盖这个冲突。

2. **`kbId` 未在 resultMap 中**
   第四轮据 DO 属性判定「`kbId` 存在」；本轮发现它**没有列映射**。
   因此第四轮那句结论应降级为「实体有该属性，但 ORM 是否读写该列未证实」。
   → **计数一致 ≠ 语义对齐**，再次被实证。

---

## 6. 汇总表

| 表 | 台账 | 实体 | resultMap | 未映射字段 | 归因方向 | 结论级别 |
|---|---|---|---|---|---|---|
| `user_operate` | 13 | 12 | **12/12** | 无 | **台账侧可能多一列** | CANDIDATE（方向已定，列名待 DDL） |
| `re_embedding_file` | 13 | 14 | 0（无 resultMap） | 14 | 无法判定 | PENDING_DDL |
| `re_embedding_retry_task` | 12 | 13 | 0（无 resultMap） | 13 | 无法判定 | PENDING_DDL |
| `re_embedding_task` | 13 | 14 | 10/14 | `totalFileNum`/`uid`/`createBy`/`modifiedBy` | **可能是 resultMap 不完整** | CANDIDATE |
| `dialogue` | 13 | 13 | 12/13 | `kbId` | 计数一致但语义冲突 | CANDIDATE（冲突单列） |

## 7. 边界与不做的事

- **不关闭 P0-02**，不改 `DATABASE-ASSETS.yaml` 的计数去「对齐」源码；
- **不反向修改实体**去迎合台账；
- 不把 `resultMap` 当 schema；
- 需要 `data-owner` 提供：真实 DDL（逐表 `SHOW CREATE TABLE`）、索引/约束/触发器/引擎/字符集、
  以及**字段名清单**（当前台账只有计数，没有字段名）。
