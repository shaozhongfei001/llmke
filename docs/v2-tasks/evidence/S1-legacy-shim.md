# S1 legacy 兼容层（19529 → 18094）证据

任务：T-S1A。交付：`services/rag-alg/index_data_service/graph_engine_adapter/legacy_shim.py`（301 行，md5 `5be0f9bd8856f65862d4dec709f3a7f4`）、
`tests/test_legacy_shim.py`（235 行，md5 `1b9534e0c8e4e3d279ca72c88b687f6f`）与本文件。
未修改任何既有文件（`git status` 中我名下只有这两个 `??` 新文件）。

## 1. 真实契约（读代码得出，不是猜）

### 1.1 legacy 19529 注册的路由

`services/rag-alg/index_data_service/index_graph_service/graph_api_start.py`

| 行 | 路径 | 处理函数 |
|---|---|---|
| 97 | `POST /del_space` | `del_space_data` |
| 103 | `POST /generate_triple_data` | `_safe_entry(generate_triple_data)` |
| 130 | `POST /generate_community` | `generate_community` |

实测 `GET http://127.0.0.1:19529/openapi.json` 的实际路由表：

```
['/batch_insert_vertex', '/create_attribute', '/create_space', '/create_space_attribute',
 '/del_community', '/del_space', '/generate_community', '/generate_triple_data',
 '/query_community', '/query_graph_data']
```

**发现的既有缺陷（不是本层引入）**：`application-r12.yml:91-92` 把
`remote.del-graph-entity.url` 配成 `http://127.0.0.1:19529/del_doc_entity`，
但 19529 上**没有**这个路由（`/del_doc_entity` 属于 19526 向量服务，
`index_vector_service/src/index_vector_service_pactera/view/urls.py:33`）。
实测 `POST http://127.0.0.1:19529/del_doc_entity` → **HTTP 404**。
即 Java `GraphDomainServiceImpl.delGraphEntity`（`:50-70`）今天必然走
`RemoteGraphUtils.doExchange` 的非 200 分支抛 `FILE_PARSE_ERROR`，原因丢失。

### 1.2 请求模型（`index_graph_service/base.py`）

`QueryDocChunk`（`:64`，继承 `GraphModel`）——`/generate_triple_data` 的 body：

```python
space_name: str            # 必填，ES 索引名（Java 传 primitiveName，如 kb_9）
partition_num: int = 10
replica_factor: int = 1
generation: str = ""
col_name: str = ''         # 条件查询列
col_values: List[str] = [] # 条件查询值
model_info: dict           # 必填
embed_model_name: str = "bge-large-zh-v1.5"
top_k: int = 30
system_prompt: Optional[str] = None
entity_types: Optional[List[str]] = None
```

`DelModel`（`:93`）——`/del_space` 的 body：`space_name`、`generation`、`condition_json: dict = {}`。

`BaseResponse`（`:16`）：`{code:int=200, msg:str, data:Any}`。

### 1.3 返回形状（`graph_service.py`）

- `/generate_triple_data` 成功（`:762-769`）：
  `code=200, msg="添加成功，新增和更新N条图数据,新增M条实体",
   data={error_edge_data_list, error_tag_data_list, triples_total, edges_total, edges_failed, ...}`
- `/del_space` 成功（`:208`）：`code=200, msg="删除成功"`。
- 错误约定：`graph_api_start.py:25 _safe_entry` 把异常折成 `BaseResponse(code=500, msg=...)`，
  **HTTP 仍是 200**。

### 1.4 Java 侧实际发出的 body（`rag-index-service`）

`application/service/impl/FileAppServiceImpl.java:634-657`：

```java
graphReq.put("space_name", spaceName);              // kb.getPrimitiveName() 原始名
graphReq.put("embedding_model_name", ...);          // 注意：legacy 模型字段叫 embed_model_name
graphReq.put("model_info", modelInfo);
graphReq.put("col_name", "title");
graphReq.put("col_values", Arrays.asList(matchTitle));
graphReq.put("generation", knowledgeBaseFile.getVersion());
graphReq.put("entity_types", ...);                  // 仅当 kb.graphPrompt 非空
```

`domain/service/impl/GraphDomainServiceImpl.java:29-47`（del_space）：
`{space_name, condition_json:{file_id}}`；`:50-70`（del_doc_entity）：
`{db_name, index_name="graph_entity_<space>", update_condition_json:{file_id[],title[]}}`。

`application-r12.yml:89-97`：
`del-graph-space→19529/del_space`、`del-graph-entity→19529/del_doc_entity`、
`generate-graph→19529/generate_triple_data`、`generate-community→19529/generate_community`。

### 1.5 V2 目标契约（18094，`graph_engine_adapter/api.py`）

`BuildRequest`（`:44-46`）= `{docs:[{file_id:str, text:str, locator:Optional[str]}], root:Optional[str]}`，
`docs` 至少 1 条；`POST /v2/graph/build`（`:163-183`）成功返回
`{schema:"llmke.graph-api.v1", status:"BUILT", snapshot, generation, documents, chunks, sources}`，
内部异常 → HTTP 500 + `detail`。

## 2. 关键落差：legacy 请求里没有正文

`/generate_triple_data` 的请求**只有 `space_name` + `col_name`/`col_values`**，
正文是 legacy 自己按标题去 ES 捞的（`graph_fun_tool.py:908 get_document_chunk`
→ `search_by_custom_param`），然后 `llm_generate_triple` 抽三元组。
V2 `/v2/graph/build` 相反：**必须由调用方带 `docs`**。

因此本兼容层的取舍是（已写进模块 docstring 与 400 响应文案）：

- 请求带 `docs` → 归一成 `{file_id, text, locator}` 转发；
- 请求不带 `docs`（= 今天 Java 真实发的报文）→ **`code=400` + 说明**，
  不复刻 ES 查询、不凭空生成正文、不静默回 200。

**结论（需要产品侧决策）**：仅靠本层无法让 Java 现有抓图链路真正建成图，
必须二选一：①Java 请求里带上 `docs`；②另立"V2 侧读 ParseArtifact 取正文"的通道
（与 T-S1B artifact 绑定天然相关）。本层已按①预留字段，①落地时 Java 只需加一个 `docs` 字段。

## 3. 实现要点

- `create_app(http_post=None)`：注入 `http_post(url, payload, timeout)`，
  返回值需带 `status_code` 与 `.json()`；直接返回 dict 视为已解析的 200 体（便于测试）。
- 环境变量：`LLMKE_V2_GRAPH_API`（默认 `http://127.0.0.1:18094`）、
  `LLMKE_V2_ROOT`（默认 `.artifacts/api-root`，请求里 `root` 优先）、
  `LLMKE_V2_GRAPH_TIMEOUT`（默认 600s）。
- 错误语义：**HTTP 200 + body.code**，与 legacy `_safe_entry` 一致；
  这样 Java `RemoteGraphUtils.doExchange:70-75`（HTTP≠200 直接抛错丢 body）仍能读到 `msg`。

| 场景 | code | 说明 |
|---|---|---|
| 正常转发且上游 `status=BUILT` 且有 snapshot | 200 | data 透传 chunks/sources/snapshot/generation + `upstream` 原文 |
| 上游 HTTP 非 200 | 502 | `msg` 带上游 `detail`/`msg`，`data.upstream_status` |
| 上游超时/连接异常 | 502 | `msg` 形如 `上游图服务不可达 TimeoutError: read timed out`，**不产生 HTML 500** |
| 上游 200 但 `status≠BUILT` 或无 snapshot | 502 | fail-closed，不回成功 |
| `/generate_community` | 501 | `msg="community not wired yet"`，不调用上游 |
| `/del_space`、`/del_doc_entity` | 501 | `msg="delete not wired yet"`，不调用上游 |
| 缺 `docs` / `docs=[]` / 某条 `text` 为空 | 400 | 带原因，不调用上游 |

- `file_id` 兜底顺序：`doc.file_id` → `body.col_values[0]` → `body.space_name`，
  每次兜底计入 `data.file_id_fallbacks`（不做无声替换）。
- `locator` 缺失 → 传 `None`（符合 BuildDoc 定义）；兼容 `page_num`/`page`。
- **不伪造边统计**：HippoRAG build 不返回边写入数，故 `triples_total/edges_total/
  edges_written/edges_failed` 显式置 `null` + `legacy_edge_metrics="UNAVAILABLE_V2_GRAPH_API"`，
  绝不拿 `chunks` 冒充 `edges_total`。

## 4. 测试

命令：

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m pytest tests/test_legacy_shim.py -q
```

真实输出：

```
..............                                                           [100%]
14 passed in 0.43s
```

（复跑一次：`14 passed in 0.48s`）

14 项覆盖：正常转发字段（file_id/text/locator、尾斜杠不叠 `//`、默认与覆盖 root）、
上游 500→非 200 code 带原因、上游超时→JSON 不抛 HTML、上游 200 但未 BUILT、
上游非 JSON 体、community 501 且零上游调用、del_space/del_doc_entity 501 且零上游调用、
缺 docs/空 docs→400、某条 text 空→400、file_id 从 col_values 兜底并留痕、
边统计不伪造、JSON 字符串 body、health 自述接线且不访问上游。

## 5. 真实建图验证（打到真实 18094）

19530 已被别的进程占用（`ss -ltn` 有监听，`GET /health` 回 404，非本任务实例），
故改用 **19531**；用完已 kill（`ss` 确认端口关闭）。

启动：

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service nohup \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m uvicorn \
  graph_engine_adapter.legacy_shim:app --host 127.0.0.1 --port 19531 \
  > /tmp/s1-legacy-shim-20261102/uvicorn-19531.log 2>&1 &
```

真实请求（Java 真实字段 + `docs`，`root` 指向 /tmp 避免动共享 `.artifacts`）：

```
curl -s -X POST http://127.0.0.1:19531/generate_triple_data -H 'Content-Type: application/json' -d '{
 "space_name":"kb_9","col_name":"title","col_values":["授信审批指引.docx"],
 "embedding_model_name":"text-embedding-bge-m3",
 "model_info":{"modelName":"qwen2.5-7b-instruct"},"generation":"V0",
 "root":"/tmp/s1-legacy-shim-20261102/root",
 "docs":[{"file_id":"343","text":"单笔授信金额超过五亿元须提交分行信贷审查委员会审批。","locator":"p12"},
         {"file_id":"343","text":"贷后检查每季度开展一次，重点核查借款人经营现金流与担保物状态。"}]}'
```

真实响应（`[HTTP 200 in 11.472775s]`）：

```json
{"code":200,"msg":"V2 建图完成 docs=2 chunks=2 sources=2",
 "data":{"docs":2,"documents":2,"chunks":2,"sources":2,
  "snapshot":"/tmp/s1-legacy-shim-20261102/root/snapshot-20261102215354-365190-g0",
  "generation":0,"error_edge_data_list":[],"error_tag_data_list":[],
  "triples_total":null,"edges_total":null,"edges_written":null,"edges_failed":null,
  "legacy_edge_metrics":"UNAVAILABLE_V2_GRAPH_API","file_id_fallbacks":0,
  "legacy_fields_seen":["col_name","col_values","embedding_model_name","generation","model_info","space_name"],
  "graph_api":"http://127.0.0.1:18094/v2/graph/build",
  "upstream_schema":"llmke.graph-api.v1",
  "upstream":{"schema":"llmke.graph-api.v1","status":"BUILT",
   "snapshot":"/tmp/s1-legacy-shim-20261102/root/snapshot-20261102215354-365190-g0",
   "generation":0,"documents":2,"chunks":2,"sources":2}}}
```

**图是真的建了**（不是我说的，是 18094 自己报的）：

```
GET http://127.0.0.1:18094/health
{"schema":"llmke.graph-api.v1","status":"ok",
 "snapshot":"/tmp/s1-legacy-shim-20261102/root/snapshot-20261102215354-365190-g0",
 "nodes":3,"edges":2,"facts":7}
```

落盘目录：`openie_results_ner_qwen2.5-7b-instruct.json`、`sources.json`、
`qwen2.5-7b-instruct_text-embedding-bge-m3/`、`llm_cache`。
`sources.json` 证明 legacy 字段到来源映射确实贯通（第一条带 `locator=p12`，第二条无 locator 就不写）：

```json
{"chunk-a86887f7bb126d95771f0f129947c4ed":[{"file_id":"343","locator":"p12"}],
 "chunk-f58f4822e4252ccaf36b97c78da29cec":[{"file_id":"343"}]}
```

三个未接线端点的真实响应（均 HTTP 200 + code 501 + `upstream_called:false`）：

```json
{"code":501,"msg":"community not wired yet","data":{"endpoint":"/generate_community","wired":false,"upstream_called":false,...}}
{"code":501,"msg":"delete not wired yet","data":{"endpoint":"/del_space","wired":false,"upstream_called":false,...}}
{"code":501,"msg":"delete not wired yet","data":{"endpoint":"/del_doc_entity","wired":false,"upstream_called":false,...}}
```

收尾：`kill 1167416` → `19531 closed`；18094 与 19529 未被停（仍在监听）。

## 6. 已知落差（未解决，需决策，不在本任务范围）

1. **Java 请求没有 `docs`** → 真实链路今天会拿到 `code=400`（见 §2）。
2. **Java 零产出闸门会判失败**：`FileAppServiceImpl.java:661-673` 要求
   `data.edges_total>0 && data.edges_written>0`，而 V2 build 不返回边统计 →
   本层只能给 `null`（不伪造），故**即使带上 docs，Java 侧仍会把这次建图记成失败**。
   要闭环需二选一：V2 `/v2/graph/build` 返真实的图规模（从快照读 nodes/edges），
   或改 Java 闸门读 `chunks/sources`。
3. `generate_community` / `del_space` / `del_doc_entity` 一律 501：
   Java 侧 `delGraphSpace`/`delGraphEntity` 会把 501 当错误抛 `DELETE_GRAPH_ERROR`；
   `generateCommunity` 的失败仅告警不影响图状态（`FileAppServiceImpl.java:692-694`），
   行为可接受。V2 侧要真支持删除/社区，需先在 18094 开对应端点。
4. legacy 的 `model_info` / `entity_types` / `generation` 本层只记录（`legacy_fields_seen`）
   不消费：HippoRAG 的 LLM 由 18094 进程环境决定，代次由 rebuild 自己维护。

## 7. 我没做的部分

- 没改 `api.py`、没改任何 Java/yml（含 `application-r12.yml`）、没改 `TASKS.yaml`；
- 没实现社区检测/删除端点，没在 18094 上加接口；
- 没启动/停止 18094、19529（只 kill 了自己起的 19531）；
- 没 git add/commit（两个新文件仍是 `??`）；
- 没动共享 `.artifacts/api-root`：真实 curl 用 `root=/tmp/s1-legacy-shim-20261102/root`。
