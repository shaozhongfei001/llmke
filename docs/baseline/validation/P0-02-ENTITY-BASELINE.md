# P0-02 基线换源：用 ORM 注解替掉"二手 CSV"

日期：2026-10-22　状态：**已对真实源码跑通并完成端到端验证**
工具：`docs/baseline/validation/p0-02-entity-extract.py`
源码：`RAG-SRC/_src/gien-rag/gien-rag/rag-parent`（43 个 `*DO.java`，其中 38 个带 `@TableName`）
对比物：`docs/upstream/数据库表结构-字段明细.csv`（我们原先的计划基线）
性质：只读分析；不改源码、不改 CSV、不改控制面；r9 候选不受影响。

---

## 1. 为什么要换基线

`字段明细.csv` 是**从 DO 推导出来的二手材料**。用它当基线比对 DDL，会出现两种错误：

- **把对的 DDL 判错**：CSV 写 `VARCHAR(255)`，而实体的 `@Column` 明确写着 `MEDIUMBLOB`；
- **把错的 DDL 判对**：CSV 里某表整列用的是 Java 字段名（驼峰），如果 DDL 也这么建，反而"一致"。

真正的实体模型在源码里：`@TableName` / `@Column(name, type, length, isNull, isKey, isAutoIncrement)`。

---

## 2. 实测结果

```
实体文件=43  实体表=37  实体列=491
CSV 表=37     CSV 行=482        列差异=81
```

差异分三类：

| 类别 | 条数 | 说明 | 例子 |
|---|---|---|---|
| **CSV 用了 Java 字段名而非列名** | 29 | 集中在 `re_embedding_*` 三张表（12+9+8） | CSV `re_embedding_file.fileId` ↔ 实体列 `file_id` |
| **CSV 把非持久化字段当成列** | 7 | 这些字段带 `@TableField(exist = false)`，本就不是列 | `biz_label.bizName`、`interface_info.resourceId/resourceName/resourceType`、`knowledge_base_list.isFolder/permission` |
| **类型/长度不符** | 13 | 见下表 | `answer.reference` CSV `VARCHAR(255)` ↔ 实体 `MEDIUMBLOB` |

类型/长度不符全表：

| 表.列 | CSV | 实体 | 风险 |
|---|---|---|---|
| `answer.log_result` | VARCHAR(255) | **TEXT** | 内容超 255 会被截断 |
| `answer.reference` | VARCHAR(255) | **MEDIUMBLOB** | 参考内容（JSON）可能超长 |
| `question.alg_params` | VARCHAR(255) | **TEXT** | 同上 |
| `question.knowledge_params` | VARCHAR(255) | **TEXT** | 同上 |
| `knowledge_base_list.table_file_paths` | LONGTEXT | **TEXT** | 反向：TEXT 上限 64KB |
| `folder_info.full_path` | VARCHAR(255) | **VARCHAR(2000)** | 路径超长截断 |
| `knowledge_base_list.source_url` | VARCHAR(255) | **VARCHAR(1000)** | URL 超长截断 |
| `knowledge_base_list.uid` | VARCHAR(255) | **VARCHAR(128)** | 反向：CSV 偏大 |
| `syn_log.error_code` | VARCHAR(255) | **VARCHAR(16)** | 反向 |
| `user_info.dept_name` | VARCHAR(255) | **VARCHAR(30)** | 反向 |
| `user_operate.ip` | VARCHAR(20) | **VARCHAR(255)** | 反向 |
| `user_operate.params` | TEXT | **VARCHAR(255)** | 反向 |
| `user_operate.user_name` | VARCHAR(128) | **VARCHAR(255)** | — |

> 注意这里**两个方向都有**：既有"CSV 偏小会截断"，也有"CSV 偏大会浪费/误判"。
> 所以不能简单地认为"按 CSV 建表就安全"。

---

## 3. 端到端验证（关键）

用实体模型生成 DDL，再分别用两套基线比对同一份 DDL：

| 比对 | 结果 |
|---|---|
| **实体基线** ↔ 实体生成的 DDL | **PASS，0 处差异**（`--fields-csv /tmp/entity-model.csv`） |
| **旧 CSV 基线** ↔ 同一份 DDL | **FAIL，85 处差异** |

同一份 DDL，换基线结论从 PASS 变 FAIL —— 说明**基线选择直接决定结论**。
这也正是 P0-02 登记里那条"设计声明 DDL 原样复用，但材料里没有 `SHOW CREATE TABLE` 快照"的实际后果：
中间材料不可信，必须回到源码或真实 DDL。

---

## 4. 降噪过程中修掉的 5 个自身缺陷（都曾制造假差异）

| # | 假象 | 真实原因 |
|---|---|---|
| 1 | 222 → 86 条 `TYPE_DIFF` | 数值型显示宽度（`INT(10)` vs `INT`）在 MySQL 8 已废弃，不该判差异 |
| 2 | 大量 `TYPE_DIFF` | 只有一方给长度时也判差异；改为"双方都已知才比长度" |
| 3 | 大批 `NULL_DIFF` | `@Column` 未写 `isNull` 被当成"可空"；应为"未声明"（三态） |
| 4 | `knowledge_base_list.temp_status` 假"CSV 有实体无" | 字段带初始值 `= Xxx.CODE`，正则要求紧跟 `;` 导致漏解析 |
| 5 | 整表 421 条误报 | `ddl-diff` 把 CSV 里空白可空当成 `NOT NULL`；同样改三态 |

第 5 条出现在另一支工具里，说明**同一个概念（未声明 vs 否）在两个工具里都要一致**，
否则单独看每个工具都"通过"，合起来结果错。

---

## 5. 仍不判定的

| 项 | 原因 |
|---|---|
| 索引 / 约束 / 触发器 / 字符集 | 注解里没有，CSV 也没有 |
| `create_by` 语义（用户 ID / 账号 / 姓名） | 人工裁定（P0-02 的 D-03） |
| 真实 DDL | 本工具只给"实体应有的样子"；DDL 是否存在差异要用 `p0-02-ddl-diff.py` 比 |
| 运行时行为 | 静态分析不覆盖 |

**结论仍然只是"实体侧基线已可信"，不是"P0-02 已关闭"。**

---

## 6. 用法（material 到手后）

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH

# 1) 从源码导出实体基线（建议入库或缓存，替换二手 CSV）
python3 docs/baseline/validation/p0-02-entity-extract.py \
  --src ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent \
  --out /tmp/entity-model.csv

# 2) 用实体基线比对真实 DDL
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl ~/incoming/prod-schema.sql --fields-csv /tmp/entity-model.csv --dump-columns
```

若第 2 步 FAIL，那些行就是 P0-02 的 D01 回答素材（具体到表.列 + 两侧类型 + 源码行号）。
