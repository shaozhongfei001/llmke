# 解析服务 Nacos 配置交付清单（供 TL 权威发布）

生成：parse-ops 2026-10-25　目标 Nacos：`http://127.0.0.1:18848/nacos`，namespace=**public**（tenant 传空串）

> 说明：TL 已决定"Nacos 只保留服务发现 + Python 配置，Java 侧改配置版本化"。下面 4 个 data_id 全部属于 **Python 解析服务私有**，不含任何跨服务共享配置。我已发布过一份使服务可运行；TL 做权威发布时**直接覆盖同 data_id 即可**，无需改代码。

## 1. data_id 一览

| # | data_id | group | 文件 | 被谁读取 |
|---|---|---|---|---|
| 1 | `alg_doc_config_py` | DEFAULT_GROUP | `alg_doc_config_py.yaml` | `server/nacos_utils.py`（`DocParseConfig().config`） |
| 2 | `alg_doc_parse_java_common` | DEFAULT_GROUP | `alg_doc_parse_java_common.yaml` | `configs['java-common']`（`process_reporter` / `minio_utils` / `indexing_utils`） |
| 3 | `alg_doc_parse_java_gateway` | DEFAULT_GROUP | `alg_doc_parse_java_gateway.yaml` | `configs['java-gateway']`（`save_to_minio` / `parse_task` 异步回调） |
| 4 | `alg_doc_parse_index` | DEFAULT_GROUP | `alg_doc_parse_index.yaml` | `configs['index']`（`/parse` 带索引写 ES/Milvus） |

`alg_doc_config_py.other-nacos` 把 2/3/4 挂进来；**这三个 data_id 必须同时存在**，否则服务 import 期就会因 `yaml.load(None)` 崩溃（`nacos_utils.create_client` 对缺失配置不兜底）。

## 2. TL 指定需要的键 → 落点（全部已补齐）

| 要求的键 | 所在 data_id | 取值（按 R12-ENV-CONTRACT） | 备注 |
|---|---|---|---|
| `java-common.server.host-ip` | #2 | `127.0.0.1` | `MinioFile` / `index_es` / `index_milvus` 都用它拼 URL |
| `java-common.minio.uri` | #2 | `http://${server.host-ip}:19000` | 支持 `${server.host-ip}` 占位替换 |
| `java-common.minio.access-key` | #2 | `r12minio` | 与 `platform/r12/.env` 的 `R12_MINIO_ACCESS_KEY` 一致 |
| `java-common.minio.secret-key` | #2 | `${R12_MINIO_SECRET_KEY}` | 与 `.env` 的 `R12_MINIO_SECRET_KEY` 一致（**生产请改密管注入**） |
| `java-gateway.server.port` | #3 | `8088` | |
| `index.es_server.port` | #4 | `19200` | 见 §4 疑点 |
| `index.milvus_server.port` | #4 | `19630` | 见 §4 疑点 |
| `index.milvus_conn_config.milvus_database` | #4 | `rag_knowledge_base` | 作为 `db_name` 传给 milvus 插入接口 |

补充事实：
- **bucket 不在任何配置键里**。`server/minio_utils.py:52` 用 `file_path` 的**第一段**做 bucket 名，例如 `r12-rag/fixtures/a.pdf` → bucket=`r12-rag`、object=`fixtures/a.pdf`。所以"bucket=r12-rag"是**调用约定**，需要告知所有往 MinIO 放文件的角色。
- `alg_doc_config_py.mysql: {}` 必须保留为**空 map**：`process_reporter.py:48` 会 `mysql_config = config['mysql']` 再 `.update(java_common['mysql'])`，缺失即 KeyError。
- 我发布的 `alg_doc_parse_java_common.mysql.schema` 是**按代码实际用到的列反推的最小 DDL**（`parse_task` + 三张财报表），不是原厂 schema；TL 若有正式 schema 请直接覆盖 content。

## 3. 服务侧固定键（不可删）

`server.port=12340`、`log_path`、`layout_garbage_path`（`pdf_parser.py:50` 必读）、`chunk_size`、`overlap_size`、`use_ali/use_fudan/use_text_in/use-mineru/bypass`、`other-nacos`。
可选键（有代码默认值）：`image_boxes_batch_size`(4)、`table_split_max_worker`(4)、`excel_parse_max_worker`(1)、`garbage_filter`(False)、`use_multi_modal`(False)、`es_insert_*`/`milvus_insert_*`（批量与重试参数）。

## 4. 尚未确定、**我没有编造**的两个键（阻塞 /parse 带索引）

`server/indexing_utils.py` 里两个 URL 模板只做 `.format(ip=..., port=...)`：

- `config['es-insert']` → `port` 取 `index.es_server.port`
- `config['milvus-insert']` → `port` 取 `index.milvus_server.port`

请求体（上游协议，已按代码逐字段核对）：
```
POST <es-insert>
{"index_name": "<index_name>", "document_list": [chunk...], "duplicate_flag": true|false}
期望响应 {"code": 200, ...}
```
```
POST <milvus-insert>
{"index_name": "...", "embed_model": "<embedding model id>", "db_name": "rag_knowledge_base",
 "document_list": [chunk...], "duplicate_flag": true|false}
期望响应 {"code": 200, ...}
```

**需要 TL 确认两件事**（我按契约推理存在矛盾，故不填）：
1. 这两个 URL 该指向 **ES/Milvus 本体** 还是 **代理服务**？契约 §1 里 ES=19200、Milvus=19630 是本体；但同一张表里 `index_fulltext_service`=19527（ES 代理）、`index_vector_service`=19526（Milvus 代理）才是接收 `{index_name,document_list}` 这种业务 JSON 的一方。若走代理，`index.es_server.port` 应填 19527、`index.milvus_server.port` 填 19526（此时与"es 19200 / milvus 19630"的字面要求不同）。
2. 两个接口的**路径**（如 `/es/v1/insert`、`/milvus/v1/insert`）——代码里只有 `{ip}:{port}` 变量，路径必须写死在模板里，猜错就会 404。

TL 给出"URL 模板 + 端口口径"后，我 5 分钟内补进 `alg_doc_config_py` 并跑 B 项验收（真实文件 → ES + Milvus 落库 + 计数核对）。

## 5. 发布命令（TL 侧可直接用）

```bash
NACOS=http://127.0.0.1:18848/nacos
D=/home/szf/data/dev/llmke-r12/platform/r12/nacos
for id in alg_doc_config_py alg_doc_parse_java_common alg_doc_parse_java_gateway alg_doc_parse_index; do
  curl -s -X POST "$NACOS/v1/cs/configs" \
    --data-urlencode "dataId=$id" --data-urlencode "group=DEFAULT_GROUP" \
    --data-urlencode "tenant=" --data-urlencode "content@$D/$id.yaml"; echo " <- $id"
done
# 校验
curl -s "$NACOS/v1/cs/configs?dataId=alg_doc_config_py&group=DEFAULT_GROUP&tenant=" | head -20
```

改完需**重启**解析服务（`other-nacos` 的增删只在启动期生效；单个 data_id 的 content 变更由 watcher 热生效）。
