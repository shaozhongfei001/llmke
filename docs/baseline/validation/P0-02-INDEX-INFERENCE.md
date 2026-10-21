# P0-02 / 5.1：从查询反推"该建哪些索引"

日期：2026-10-22　性质：只读分析；不改源码、不改控制面
工具：`docs/baseline/validation/p0-02-index-infer.py`
结论：得到 **116 组候选**；文档 5.1 写的三条索引**没有一条被现有查询使用**（与文档"支撑新查询"的措辞一致），
其中一条还因缺列建不出来（已另行证实）。

---

## 1. 为什么要反推

代码里 `@Index` 出现 **0 次**，`*.sql` 迁移脚本 **0 个**，所以"已建了哪些索引"读不出来。
但"查询需要哪些索引"是可以从 SQL 与 Java 查询链里读出来的——这是 5.1 那三条索引的唯一可验证替代。

**必须区分两件事**：

| | 来源 | 用途 |
|---|---|---|
| 建议索引 | 本工具（查询模式） | 判断"该不该建" |
| 已有索引 | `SHOW CREATE TABLE` | 判断"已经建了什么" |

本工具只产出前者。

---

## 2. 方法与覆盖

| 来源 | 提取内容 | 覆盖量 |
|---|---|---|
| `*.xml` 单表语句 | `WHERE` 等值/范围列、`ORDER BY`、`GROUP BY` | **64 条**（另有 40 条多表语句无法归属单表，已跳过） |
| Java `LambdaQueryWrapper` 链 | `.eq/.ne/.gt/.ge/.lt/.le/.like/.in` + `.orderByAsc/Desc` + `.groupBy` | 37 个 DO 类 |
| 合并 | 以 `(表, 等值列, 范围列, 排序列, 分组列)` 为键计数 | **116 组候选** |

字段名到列名的映射复用 `p0-02-entity-extract.py` 的结果（(DO 类, Java 字段) → 列），
保证与 DDL 基线同口径——这是第三次强调：**同一概念在多个工具里必须共享定义**。

---

## 3. 文档 5.1 的三条索引与现有查询的关系

| 索引 | 列是否都存在 | 现有查询是否使用 |
|---|---|---|
| `dialogue(user_id, gmt_create)` | **否**（dialogue 13 列无 user_id） | — 建不出来 |
| `file_parse_task(status, gmt_create)` | 是 | **否** |
| `answer(dialogue_id, type)` | 是 | **否** |

文档原文是"仅补充三类索引**以支撑新查询**"，所以"现有查询未使用"是**预期**，不是工具失败。
（我最初把"能否重新发现这三条"当成工具的通过标准，跑出来两条 MISSING 时以为工具坏了；
读到原文后才确认是判据错了。这个纠错过程保留在此，避免后来者重复误判。）

---

## 4. 现有查询真正要求的高频索引（出现 ≥2 次）

| 表 | 列组合 | 次数 |
|---|---|---|
| `re_embedding_file` | 等值 `(id)` | 9 |
| `re_embedding_file` | 等值 `(kb_id, task_id, file_id, is_del)` | 2 |
| `re_embedding_retry_task` | 等值 `(status)` | 3 |
| `re_embedding_retry_task` | 等值 `(type)` | 3 |
| `re_embedding_retry_task` | 等值 `(status)` + 排序 `(gmt_create)` | 2 |
| `knowledge_base_list` | 等值 `(status)` | 4 |
| `folder_info` | 等值 `(kb_id, type, status)` | 2 |
| `knowledge_base` | 等值 `(status)` | 3 |

### 一条值得注意的偏差

P0-04 的任务领取实际发生在 **`re_embedding_retry_task`** 上，条件是

```
is_del=0 AND status=2 AND type=? AND retry_times<max  ORDER BY gmt_create LIMIT 1
```

对应**建议索引**：`(status, type, gmt_create)` 或 `(type, status, gmt_create)`
（`is_del` 基数极低、`retry_times` 为范围，放在排序键之后）。

而文档 5.1 把队列扫描索引写在 **`file_parse_task(status, gmt_create)`** 上——
**表都对不上**。要么是文档笔误，要么是设计时以为队列在 `file_parse_task`。
这一点需要 `index-owner` 确认，不能靠猜。

---

## 5. 不能由本工具回答的

| 项 | 原因 |
|---|---|
| 是否已有索引、索引名与列序 | 只能 `SHOW CREATE TABLE` |
| 索引是否会被真正使用 | 需要 `EXPLAIN` + 真实数据分布；`status` 这类低基数列很可能被优化器放弃 |
| 多表 JOIN 的执行计划 | 40 条多表语句未归属（本工具跳过） |
| 写放大与维护成本 | 需要写入频率数据 |

特别是 `status` 这类列：**单列索引常常无效**（区分度太低）。本工具给出的是"查询模式"，
不是"建了就会快"。这一条必须写进给 owner 的结论里，否则会误导成"照着建一堆单列索引"。

---

## 6. 建议的下一步（需 owner 输入）

1. 由 `index-owner` 确认队列到底在 `re_embedding_retry_task` 还是 `file_parse_task`；
2. 把 116 组候选里出现 ≥2 次的，用真实数据跑 `EXPLAIN`，剔除低区分度项；
3. 与 `SHOW CREATE TABLE` 的现有索引取差集，得到"确实缺的索引"；
4. 5.1 的 `dialogue(user_id, gmt_create)` 改为 `dialogue(create_by, gmt_create)` 需业务确认口径
   （账号分页 ≠ 用户 ID 分页）。

在此之前，任何"索引已补齐"的结论都不成立。
