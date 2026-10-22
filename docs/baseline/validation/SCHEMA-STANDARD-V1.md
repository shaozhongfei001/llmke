# LLMKE 数据库设计规范 V1（新设计，旧模型仅作参考）

日期：2026-10-22　状态：**提案（PROPOSED）**，未应用到任何数据库
依据：业主裁决——"源项目/源码/详细设计无法追溯的，按 LLMKE 全新设计生成；旧 DDL 仅作参考"

> 本文与 `docs/baseline/validation/target-schema-v1.sql` 一起，构成 LLMKE 自己的 schema 基线。
> **它不关闭 P0-02**：P0-02 的核心是"按文施工会失败"的确定性错误，本规范正是为了消除这些错误，
> 但关闭仍需 `data-owner` 确认迁移可执行、可回滚。

---

## 1. 为什么可以"不复刻旧库"

旧库的问题不是"名字不好看"，而是**同一语义有多种表示**，导致按文施工必然出错：

| 维度 | 旧库实测 | 后果 |
|---|---|---|
| 创建人列宽 | `create_by` 有 30 / 50 / 128 / 255 四种 | 按 30 建则截断，按 255 建则各服务校验不一致 |
| 更新人列名 | `update_by`(23 表) vs `modify_by`(7 表) | 统一即 schema 变更，不是改名 |
| 逻辑删除列名 | `is_del`(14 表) vs `is_dtl`(6 表) | 同上；且 `@TableLogic` 只标注了 1 处 |
| 索引 | 文档写 `dialogue(user_id, gmt_create)`，实际无 `user_id` 列 | **建表语句直接报错** |
| 时间类型 | `DATETIME` 无精度 | 同秒并发排序不稳定 |

这些都不是"业务语义"问题，而是**表示层不统一**。既然旧 DDL 本身不可得且不自洽，复刻它没有收益。

---

## 2. 规范正文

### 2.1 通用

| 项 | 规定 | 理由 |
|---|---|---|
| 引擎 | `InnoDB` | 事务与行锁 |
| 字符集 | `utf8mb4` / `utf8mb4_0900_ai_ci` | 支持 emoji；排序规则显式声明，不依赖库默认 |
| 表名 / 列名 | 小写 `snake_case`，单词间单下划线 | 避免大小写敏感差异（旧库有 `retrieve_recall_Param` 这种混合写法） |
| 主键 | 每表必须有，单列 `BIGINT AUTO_INCREMENT`，列名 `id` | 无主键表无法做主从与幂等；**不用 UNSIGNED**——旧库所有 `*_id` 引用列都是有符号 `BIGINT`，只把主键改无符号会造成隐式转换、索引失效（生成器与本条保持一致） |
| 时间 | `DATETIME(3)` | 毫秒精度，避免同秒并列 |
| 审计列约束 | `NOT NULL` 且**不带默认值** | 由 ORM 显式填充；迁移时需回填历史数据，否则 `INSERT` 会失败（见 `SCHEMA-V1-RESULT.md` §4） |
| 布尔 | `TINYINT(1) NOT NULL DEFAULT 0` | 不用 `CHAR(1)`/字符串 `'0'` |

### 2.2 审计列（四件套，全表统一）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `created_by` | `VARCHAR(64) NOT NULL` | — | 登录账号（**不是用户 ID**，见 `P0-02-CREATEBY-SEMANTICS.md` 的证据链） |
| `created_at` | `DATETIME(3) NOT NULL` | — | 创建时间 |
| `updated_by` | `VARCHAR(64) NOT NULL` | — | 最后修改人（账号） |
| `updated_at` | `DATETIME(3) NOT NULL` | — | 最后修改时间 |

取代旧的：`create_by`(4 种宽度) / `update_by` / `modify_by` / `gmt_create` / `gmt_modified`。

- 宽度统一 **64**：旧库最大 255（`department_info`），但 255 是"没想过"的默认值；
  账号语义下 64 足够（`user_info.user_name` 本身是 128，如确需对齐可整体调到 128——这是**待确认项**，见 §4）。
- 全部 `NOT NULL`：旧库允许为空，导致"谁创建的"在数据里缺失，无法追责。

### 2.3 逻辑删除

统一 `is_deleted TINYINT(1) NOT NULL DEFAULT 0`，并在所有查询中显式过滤。

- 取代 `is_del` / `is_dtl` 两种写法；
- **不采用 `deleted_at` 时间戳方案**：现有 ORM 配置（MyBatis-Plus `@TableLogic`）按 0/1 工作，
  换成时间戳需要改所有查询与框架配置，收益不足；
- 建议为 `(is_deleted, <常用过滤列>)` 建联合索引，避免全表扫描。

### 2.4 命名与语义

| 类别 | 规定 | 示例 |
|---|---|---|
| 外键列 | `<被引用表单数>_id` | `kb_id`、`file_id` |
| 状态列 | `<对象>_status`，取值必须有枚举定义 | `task_status` |
| 计数列 | `<对象>_count` | `retry_count` |
| JSON 列 | `<对象>_json`，类型 `JSON` | `detail_json` |
| 不加无意义前缀 | 不写 `t_`/`tbl_` | `dialogue` 而非 `t_dialogue` |

### 2.5 索引规范

1. 主键索引自动；
2. 唯一约束用 `uniq_<列>`，普通索引用 `idx_<列1>_<列2>`；
3. **联合索引列序**：等值列在前、范围列其次、排序列最后；
4. 低基数列（如 `is_deleted`、`status` 少取值）**不单独建索引**，只作为联合索引前缀的补充；
5. 每个索引必须在文档里写明"支撑哪个查询"，无查询支撑的索引不建。

---

## 3. 与旧模型的映射（自动生成）

由 `schema-generate.py` 从旧实体模型自动改写，规则：

| 旧列 | 新列 | 处理 |
|---|---|---|
| `create_by` | `created_by` | 重命名 + 宽度统一 64 + `NOT NULL` |
| `update_by` / `modify_by` | `updated_by` | 两个名字合并 |
| `gmt_create` | `created_at` | 重命名 + 精度 `(3)` |
| `gmt_modified` | `updated_at` | 重命名 + 精度 `(3)` |
| `is_del` / `is_dtl` | `is_deleted` | 两个名字合并 |
| 其余列 | 原样 | 保留旧名与类型（仅当类型属于规范集合时） |

生成物：
- `target-schema-v1.sql`：LLMKE 目标 DDL
- `target-schema-v1-mapping.csv`：旧列 → 新列的逐列映射（迁移脚本的输入）

---

## 4. 待确认项（不能由实现方单方面定）

| # | 问题 | 影响 |
|---|---|---|
| 1 | `created_by` 宽度取 64 还是 128（对齐 `user_info.user_name`） | 决定是否需要改 `user_info` |
| 2 | 账号是否可能改名；改名后历史 `created_by` 如何处理 | 影响是否要额外存 `created_by_id` |
| 3 | 是否保留旧表名（`dialogue`/`knowledge_base_list`） | 影响迁移脚本与接口兼容 |
| 4 | 时间是否统一为 UTC 存储 | 旧库按本地时间存，改 UTC 需数据换算 |
| 5 | 是否引入 `row_version` 乐观锁列 | 与现有并发控制方式相关 |

这五条由 `data-owner` + `baseline-owner` 裁定后才可冻结本规范。

---

## 5. 本规范不做什么

- **不生成业务逻辑**，只定义结构；
- **不替代迁移**：目标 DDL 只是"应该长什么样"，从旧库迁过去仍需脚本与回滚方案；
- **不关闭 P0-02**：P0-02 要求的是"实际 DDL 与实体模型差异清单 + 迁移执行记录"；
  本规范让"应该长什么样"不再有歧义，但仍需在真实库上验证。
