# S1 产品建图契约（TL 核对）

来源（真实代码，非推测）：
`services/rag-java/rag-parent/rag-index-service/src/main/java/com/gientech/ragindexservice/application/service/impl/FileAppServiceImpl.java:610-670`

## 请求

`POST {generate-graph.url}`，当前配置指向 `http://127.0.0.1:19529/generate_triple_data`
（`rag-index-service/src/main/resources/config/application-r12.yml:94`）。

字段：

| 字段 | 值/来源 |
|---|---|
| `space_name` | KB 的 `primitiveName`（如 `kb_9`），不能用中文展示名 |
| `embedding_model_name` | 任务参数 |
| `model_info` | 模型信息对象，可空 |
| `col_name` | 固定 `"title"` |
| `col_values` | `[原始文件名]`（不是转换后的 `.md` 名） |
| `generation` | 文件版本号，可空 |
| `entity_types` | KB 图提示词逗号分隔，可空 |

## 响应判定（严格）

Java 侧只看两件事：

1. `code == 200`；
2. `data.edges_total > 0` 且 `data.edges_written > 0`。

任一不满足 → `GRAPH_PARSE_ERROR`，该文件解析状态记为失败（原文注释：曾出现
“gps=3 成功但 0 条边”的假成功，所以这里加了闸门）。

含义：兼容层不能返回固定计数，也不允许“建图成功但 0 边”时报 200。

## 文本来源

legacy Python 图服务按 `space_name` 查 ES：
`index_name = [space_name, "table_chunks_" + space_name]`，再用 `col_values`（title）过滤。
兼容层可以复用同一读法取 chunks（这是输入层），再调用 HippoRAG 图服务
`POST http://127.0.0.1:18094/v2/graph/build`。

## 结论

- 兼容层必须实现：读 chunks → 调 18094 → 用真实边数回填 `edges_total/edges_written`；
- 其他端点（community/删除）未接时返回 501，不能返回 200 假成功；
- D0 的“页面走 HippoRAG”由此路径证明，而不是只看 18094 单测。
