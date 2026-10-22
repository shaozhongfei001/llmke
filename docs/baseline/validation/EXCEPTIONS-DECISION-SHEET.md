# 例外裁决单（6 行）

> 这 6 行**不得**被组内批量处理吞掉：每行都需要一个单独决定。
> 其余 549 行可按组「默认建议 + 例外项」批量审阅。

| row_id | 类型 | 名称 | 异常 | 需要什么决定 | 责任方 | 影响 |
|---|---|---|---|---|---|---|
| DB-18 | TABLE | re_embedding_file | count_mismatch | 需要真实 DDL 与字段名清单：确定是多一列还是少一列，并指出具体列名 | data-owner | P0-02、该表复用决议 |
| DB-19 | TABLE | re_embedding_retry_task | count_mismatch | 需要真实 DDL 与字段名清单：确定是多一列还是少一列，并指出具体列名 | data-owner | P0-02、该表复用决议 |
| DB-20 | TABLE | re_embedding_task | count_mismatch | 需要真实 DDL 与字段名清单：确定是多一列还是少一列，并指出具体列名 | data-owner | P0-02、该表复用决议 |
| DB-34 | TABLE | user_operate | count_mismatch | 需要真实 DDL 与字段名清单：确定是多一列还是少一列，并指出具体列名 | data-owner | P0-02、该表复用决议 |
| API-0345 | INTERFACE | GET /ai/getRerankModelInfos | static_status=PATH_ONLY_COMMENTED | 给出书面决议：该接口是否曾上线、是否迁移（不得默认废弃） | interface-owner | P0-01、该接口决议 |
| API-0425 | INTERFACE | GET /database/dataTable/queryTableFileData/{ | static_status=LINE_DRIFT | 确认 handler 归属与当前行号，避免把漂移当成缺失 | interface-owner | P0-01 清单准确性 |

## 为什么这 6 行特殊

- 4 张表：台账计数与实体不一致，方向未定；静态证据到此为止，必须 DDL；
- `API-0345`：路径仅存在于注释，历史上是否上线源码无法回答；
- `API-0425`：行号漂移 11 行，路径与 handler 都在，但清单定位不准会影响逐端点核对。
