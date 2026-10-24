# P0-02 差异报告（DRY RUN）

> **status: DRY_RUN · P0-02 仍 OPEN · 未执行任何迁移 · 不得作为数据库兼容结论**

生成方式：`coordination/p0-02-diff.py`（仓外工具，只读已入库产物）

## 输入

- `docs/baseline/validation/artifacts/target-schema-v1.sql`
- `docs/baseline/validation/artifacts/schema-v1.3.sql`
- `docs/baseline/validation/artifacts/target-schema-v1-mapping.csv`

## 规模

| 对象 | 表 | 列 |
|---|---|---|
| 旧目标 schema | 37 | 478 |
| 当前目标 schema (v1.3) | 43 | 538 |
| 列级映射行 | — | 480（覆盖 37 表） |

## 表级变化（旧目标 → v1.3）

- 新增表 6：document_chunk, document_evidence, index_generation, index_generation_activation, index_outbox, index_write_lease
- 删除表 0：无

### 映射中的非列条目（说明文字被写进了列字段）

| 表 | 字段内容 |
|---|---|
| department_info | `seq（去掉 AUTO_INCREMENT）` |
| knowledge_base_list | `(merged into table_file_paths)` |

因此映射行 480 中，真正的列是 **478** 个。

## 映射覆盖缺口

- 目标 schema 中**无列级映射**的表 6：document_chunk, document_evidence, index_generation, index_generation_activation, index_outbox, index_write_lease
- 映射里存在但 schema 中已无的表 0：无

### 有映射但 schema 中缺失映射列的表

无

### 目标表里未被映射覆盖的列（前 20 表）

无

## 本报告**没有**回答的问题（P0-02 未关闭的原因）

1. 真实生产 DDL 是否与 `target-schema-v1.sql` 一致——仓库里没有生产快照；
2. 37 表遗留库的逐表结构是否与 ORM 推导一致——生成器需仓外 Java 源码，未重跑；
3. 迁移脚本能否在生产数据上执行——无恢复副本，未验证；
4. 新增对象是否有业务需求或 owner 决策支撑——属 data-owner 裁定。

## 复现

```bash
python3 coordination/p0-02-diff.py --out /tmp/p002.json --md /tmp/p002.md
```
