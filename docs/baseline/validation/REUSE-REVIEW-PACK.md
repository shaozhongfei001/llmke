# 批量审阅包（22 组）

> 默认建议恒为 `UNDECIDED`：静态证据不足以裁定 KEEP/REWRITE。
> **例外项** = 证据类型 UNKNOWN/FACT 或 置信 HIGH 的行，必须逐行裁决。
> 每行仍可单独拒绝/修改；批准字段由 owner 填写。

## GRP-DB-任务/同步

- 行数：**5**　例外项：**3**　责任角色：index-owner
- 证据分布：{'SOURCE_OBSERVATION': 5}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

| row_id | 名称 | 证据 | 证据类型 | 备注 |
|---|---|---|---|---|
| DB-18 | re_embedding_file | 实体 14 vs 台账 13（不一致，方向待 DDL）；ORM 覆盖 NONE；SQL 引用列 3 个 | SOURCE_OBSERVATION | count_mismatch |
| DB-19 | re_embedding_retry_task | 实体 13 vs 台账 12（不一致，方向待 DDL）；ORM 覆盖 NONE；SQL 引用列 3 个 | SOURCE_OBSERVATION | count_mismatch |
| DB-20 | re_embedding_task | 实体 14 vs 台账 13（不一致，方向待 DDL）；ORM 覆盖 PARTIAL；SQL 引用列 4 个 | SOURCE_OBSERVATION | count_mismatch |

## GRP-DB-公共业务配置

- 行数：**2**　例外项：**0**　责任角色：tech-lead
- 证据分布：{'SOURCE_OBSERVATION': 2}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-DB-知识库/目录/文件

- 行数：**4**　例外项：**0**　责任角色：data-owner
- 证据分布：{'SOURCE_OBSERVATION': 4}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-DB-结构化查询元数据

- 行数：**4**　例外项：**0**　责任角色：data-owner
- 证据分布：{'SOURCE_OBSERVATION': 4}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-DB-身份/组织/功能或数据授权

- 行数：**16**　例外项：**1**　责任角色：security-owner
- 证据分布：{'SOURCE_OBSERVATION': 16}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

| row_id | 名称 | 证据 | 证据类型 | 备注 |
|---|---|---|---|---|
| DB-34 | user_operate | 实体 12 vs 台账 13（不一致，方向待 DDL）；ORM 覆盖 FULL；SQL 引用列 3 个 | SOURCE_OBSERVATION | count_mismatch |

## GRP-DB-问答/配置

- 行数：**6**　例外项：**0**　责任角色：qa-domain-owner
- 证据分布：{'SOURCE_OBSERVATION': 6}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-alg_doc_parse_service

- 行数：**11**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 11}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-alg_llm_inference_service

- 行数：**14**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 14}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-alg_retrieval_service

- 行数：**4**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 4}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-index_fulltext_service

- 行数：**10**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 10}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-index_graph_service

- 行数：**7**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 7}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-index_structure_service

- 行数：**5**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 5}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-index_vector_service

- 行数：**14**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 14}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-rag-auth-service

- 行数：**138**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 138}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-rag-graph-service

- 行数：**17**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 17}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-rag-index-service

- 行数：**182**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 182}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-rag-qa-service

- 行数：**68**　例外项：**1**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 67, 'FACT': 1}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

| row_id | 名称 | 证据 | 证据类型 | 备注 |
|---|---|---|---|---|
| API-0345 | GET /ai/getRerankModelInfos | 路径仅存在于注释，方法已注释 | FACT | static_status=PATH_ONLY_COMMENTED |

## GRP-ITF-sensitive-words-service

- 行数：**12**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 12}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-ITF-tools/tools-database

- 行数：**23**　例外项：**1**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 23}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

| row_id | 名称 | 证据 | 证据类型 | 备注 |
|---|---|---|---|---|
| API-0425 | GET /database/dataTable/queryTableFileData/{databaseId}/{tab | 源码存在，清单行号漂移 | SOURCE_OBSERVATION | static_status=LINE_DRIFT |

## GRP-ITF-version_service

- 行数：**1**　例外项：**0**　责任角色：interface-owner
- 证据分布：{'SOURCE_OBSERVATION': 1}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-SRC-JAVA

- 行数：**8**　例外项：**0**　责任角色：algorithm-owner, data-owner, integration-agent, qa-domain-owner, security-owner
- 证据分布：{'SOURCE_OBSERVATION': 8}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

## GRP-SRC-PY

- 行数：**4**　例外项：**0**　责任角色：algorithm-owner, index-owner
- 证据分布：{'SOURCE_OBSERVATION': 4}
- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）

（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）

