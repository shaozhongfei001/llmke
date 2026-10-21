# LLMKE 目标 schema V1：生成结果与核查

日期：2026-10-22　状态：**提案产物（未应用）**
依据：业主裁决"无法追溯的按 LLMKE 全新设计生成，旧 DDL 仅作参考"
产物：`docs/baseline/validation/artifacts/` 下三个文件 + `SCHEMA-STANDARD-V1.md`

---

## 1. 生成了什么

| 文件 | 内容 |
|---|---|
| `target-schema-v1.sql` | **37 张表 / 478 列** 的目标 DDL（含审计列改写、主键、注释、`utf8mb4_0900_ai_ci`） |
| `target-schema-v1-mapping.csv` | **479 行** 旧列→新列映射（迁移脚本输入） |
| `target-model.csv` | 目标模型（供回环校验） |

审计列改写共 **154 处**：`create_by→created_by`、`update_by/modify_by→updated_by`、
`gmt_create→created_at`、`gmt_modified→updated_at`、`is_del/is_dtl→is_deleted`。

---

## 2. 验证

| 检查 | 结果 |
|---|---|
| 目标 DDL ↔ 目标模型（`p0-02-ddl-diff.py` 回环） | **PASS，0 差异** |
| 每表有主键 | **37/37** |
| 重复列 | **无** |
| `VARCHAR` 缺长度 | **无** |
| 含审计列的表 | 36/37（旧表本来就不都有创建人概念） |

---

## 3. 过程中发现的**源码真实缺陷**（不是设计问题）

`knowledge_base_list` 有**两个 Java 字段映射到同一列** `table_file_paths`：

```java
// KnowledgeBaseListDO.java:122
@Column(name = "table_file_paths", comment = "表格解析后的文件路径", type = MySqlTypeConstant.LONGTEXT)
private String tableFilePaths;

// KnowledgeBaseListDO.java:125
@Column(name = "table_file_paths", type = MySqlTypeConstant.TEXT, comment = "表格解析后的文件路径")
private Long sourceId;        // ← 字段名是 sourceId，列名却是 table_file_paths
```

两处类型还冲突（`LONGTEXT` vs `TEXT`）。影响：

1. MyBatis-Plus 拼 `INSERT` 时会把两列都写进去 → `INSERT INTO ... (table_file_paths, table_file_paths)`，
   运行期直接报语法错误（或按实现去重后**静默丢掉 `source_id` 的写入**）；
2. 无论哪种，`source_id` 这个业务字段**根本没落到库里**——这是一条会静默丢数据的路径；
3. 也说明"实体注解可以直接当 DDL"是不成立的：**注解本身可能写错**。

处理：生成器检测到重名列时**只保留第一个**，并在映射表里标 `(merged into …)`，
不静默丢弃——这一条必须由 `data-owner` 确认 `sourceId` 到底对应哪一列。

---

## 4. 显式偏差与待办（不隐瞒）

| 项 | 情况 | 需谁定 |
|---|---|---|
| 主键 `BIGINT` 而非 `UNSIGNED` | 旧库所有 `*_id` 都是无符号？否——都是有符号 `BIGINT`；只改主键会隐式转换 | `data-owner` |
| 审计列 `NOT NULL` 无默认值 | 迁移必须回填历史数据，否则 `INSERT` 失败 | `data-owner` |
| 二级索引一个没建 | 没有"已有索引"基线，按规范 §2.5"无查询支撑不建"；查询候选见 `P0-02-INDEX-INFERENCE.md` | `index-owner` |
| `created_by` 宽 64 vs 128 | 与 `user_info.user_name`(128) 不一致 | `baseline-owner` |
| 表名是否沿用旧名 | 当前沿用（降低迁移与接口兼容成本） | `baseline-owner` |
| 时间是否 UTC | 当前沿用本地时间语义 | `data-owner` |

规范 §4 的五条待确认项仍然有效，本文件不代替裁定。

---

## 5. 这份产物的定位

- **是**：LLMKE 自己的 schema 基线提案 —— 从此"应该长什么样"有唯一答案，不再依赖不可得的旧 DDL；
- **是**：迁移脚本的输入（`target-schema-v1-mapping.csv` 逐列给出改什么）；
- **不是**：已应用的变更。没有连任何数据库，没有执行任何 DDL；
- **不是**：P0-02 的关闭。P0-02 仍需"实际库结构核对 + 迁移执行记录 + 回滚验证 + 双签"。

**`p0-gate` 仍应 `exit 2`。**

---

## 6. 复现

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH

# 1) 从旧源码导出实体模型（仅作参考）
python3 docs/baseline/validation/p0-02-entity-extract.py \
  --src ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent --out /tmp/entity-model.csv

# 2) 按 LLMKE 规范生成目标 schema
python3 docs/baseline/validation/schema-generate.py \
  --model /tmp/entity-model.csv --out-dir docs/baseline/validation/artifacts

# 3) 回环校验
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl docs/baseline/validation/artifacts/target-schema-v1.sql \
  --fields-csv docs/baseline/validation/artifacts/target-model.csv
```
