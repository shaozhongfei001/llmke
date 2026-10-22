# 37 表/482 字段 ↔ 源码 DO 实体 静态对照

> 只读源码，未连接数据库。**结论一律 CANDIDATE**：实体字段数 ≠ 实际表结构。
> 不替代 M-04 的真实 DDL；不得据此关闭 P0-02。

## 总量

| 指标 | 值 |
|---|---|
| 台账表数 | 37 |
| 台账申报字段数 | 482 |
| 源码实体字段数 | 484 |
| 计数一致的表 | 33 |
| 计数不一致的表 | 4 |
| 源文件缺失的表 | 0 |

## 计数不一致明细

| 台账ID | 表 | 申报 | 实体 | 差 |
|---|---|---|---|---|
| DB-18 | re_embedding_file | 13 | 14 | +1 |
| DB-19 | re_embedding_retry_task | 12 | 13 | +1 |
| DB-20 | re_embedding_task | 13 | 14 | +1 |
| DB-34 | user_operate | 13 | 12 | -1 |

## dialogue 表身份字段（P0-02 关注点）

| 实体 | 字段数 | create_by | user_id | kb_id |
|---|---|---|---|---|
| gien-rag/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/domain/model/DialogueDO.java | 13 | True | False | True |

## 源文件缺失

（无）

## 可用于 P0-02 的结论（仍须 DDL 裁定）

- `dialogue` 实体共 13 个字段：`create_by` **存在**、`user_id` **不存在**、`kb_id` True。
  → 与设计文档「为 `dialogue` 建 `user_id` 索引」的要求**冲突**：源码中没有该列。
  → 需 `data-owner` 用真实 DDL 裁定：是设计超前、还是实体未映射该列。
- 台账 482 字段 vs 实体 484 字段，差 +2；差异集中在 4 张表，需逐表裁定是否为「实体多映射/台账少记」。

## 边界

- 未校验列名映射是否正确（`@TableField` 缺失时按驼峰转下划线猜测）；
- 未识别继承自基类的字段、逻辑删除字段、JSON 列；
- 实际索引/约束/触发器/引擎/字符集仍需 M-04。
