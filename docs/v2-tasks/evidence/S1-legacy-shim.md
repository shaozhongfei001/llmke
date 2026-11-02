# S1 legacy 兼容层（19529 → 18094）证据

任务 T-S1A。本次迭代按 TL 要求改为**复用 `legacy_es.fetch_docs`**，本文件不再自带 ES 查询。

交付（只改这三个文件）：
- `services/rag-alg/index_data_service/graph_engine_adapter/legacy_shim.py`
- `tests/test_legacy_shim.py`
- 本文件

未改动 `legacy_es.py`、`api.py`、任何 Java / yml；未执行 `git add`/`commit`。

## 1. 真实契约（读代码 + 实测）

### 1.1 legacy 19529 注册的路由

`index_graph_service/graph_api_start.py`：`:97 /del_space`、`:103 /generate_triple_data`、
`:130 /generate_community`。实测 `GET 19529/openapi.json` 路径表：
`['/batch_insert_vertex','/create_attribute','/create_space','/create_space_attribute',
'/del_community','/del_space','/generate_community','/generate_triple_data',
'/query_community','/query_graph_data']`。

**既有缺陷（非本层引入）**：`application-r12.yml:91-92` 配的
`del-graph-entity → http://127.0.0.1:19529/del_doc_entity` 在 19529 上并不存在
（`/del_doc_entity` 属 19526，`index_vector_service/.../view/urls.py:33`）。
实测 `POST 19529/del_doc_entity` → **HTTP 404**。

### 1.2 请求 / 响应模型（`index_graph_service/base.py`）

`QueryDocChunk`（`:64`）：`space_name, partition_num, replica_factor, generation,
col_name, col_values, model_info, embed_model_name, top_k, system_prompt, entity_types`
—— **请求里没有正文**。`DelModel`（`:93`）：`space_name, generation, condition_json`。
`BaseResponse`（`:16`）：`{code:int=200, msg:str, data:Any}`。

### 1.3 Java 发送与判定

`FileAppServiceImpl.java:634-657`：`{space_name(kb.getPrimitiveName()), embedding_model_name,
model_info, col_name:"title", col_values:[原始文件名], generation, entity_types?}`。
`:659-673`：`code==200` 且 `data.edges_total>0` 且 `data.edges_written>0`，否则
`GRAPH_PARSE_ERROR`（文件记失败）。`GraphDomainServiceImpl.java:29-70`：删除请求。
`RemoteGraphUtils.doExchange:65-77`：HTTP≠200 直接抛错且丢 body —— 故本层沿用
legacy 的「HTTP 200 + body.code」。

### 1.4 正文来源

`legacy_es.fetch_docs(space_name, col_name, col_values, post=None)`，与 legacy
`graph_fun_tool.py:908-957` 同一读法：`/search_by_custom_param`，
`index_name=["{space}", "table_chunks_{space}"]`，`col_name`/`col_values` 过滤。

## 2. 必须记录的实测落差：19527 返回的是**扁平 hit**

`fetch_docs` 的文档注释与测试里的 fixture 都是**折形** `{chunk_id: source}`
（legacy 在 `graph_fun_tool.py:956` 做的转换），但**代理 19527 直接返回的原始响应是扁平 hit**。
实测（2026-11-02，只读查询）：

```
$ curl -X POST 19527/search_by_custom_param \
   -d '{"index_name":["kb_9","table_chunks_kb_9"],"col_name":"title","col_values":["丙-额度分项.docx"]}'
{"code":200,"msg":"查询成功","data":{"total_count":1,"result_data":[
  {"_index":"kb_9","_id":"144729756366911329","_score":1.0,
   "_source":{"page_content":"星航贷额度分项说明星航贷单户最高授信额度为8000万元。…",
              "metadata":{"file_id":999010,"title":"丙-额度分项.docx",
                          "page_number":[0,0,0,0],"chunk_index":0,"offset":[[0,66]],…}}}]}}
```

把这份真实响应喂给 `fetch_docs`（未改其代码），得到的实际产出：

```
$ PYTHONPATH=services/rag-alg/index_data_service python -c \
  "from graph_engine_adapter.legacy_es import fetch_docs; print(fetch_docs('kb_9','title',['丙-额度分项.docx']))"
err= None
n= 1
{"file_id": "999010", "text": "星航贷额度分项说明星航贷单户最高授信额度为8000万元。…",
 "locator": "page=[0, 0, 0, 0];offset=[[0, 66]];chunk=0", "es_id": "_source"}
```

即：正文与 `file_id` 正确，但 `es_id` 变成字符串 `"_source"`（遍历时命中 `_source` 这个键），
`locator` 里出现 `page=[0, 0, 0, 0]`。`es_id="_source"` 若写进快照的 `sources.json`，
检索引用会指向一个不存在的块。

**本层的处置（`_to_build_docs`，带计数，不静默）**：BuildDoc 只需要
`{file_id,text,locator}`，`es_id` 一律丢弃；当 `es_id == "_source"`（或 locator 恰为
`es:_source`）时判定为"拿不到真实 chunk id"，locator 降级为 `file:<file_id>`
（文件级可回溯），并在响应 `data.es.locator_degraded` 计数。其余 locator 原样透传
（`page=[0, 0];offset=…;chunk=0` 这类含真实 offset/chunk 的串不改写）。

**给 TL 的修法建议（我没改 `legacy_es.py`）**：遍历时若 `row` 里存在 `_source` 就用
`row.get("_id")` 当 chunk id、`row["_source"]` 当 source，否则再退回折形分支；
`page_number` 全 0 时不要拼进 locator。两行改动即可，改完本层的降级分支自然不再触发。

## 3. legacy_shim 行为

- 文档来源：请求带 `docs` → 直接用（仅做结构校验，text 空 → 400）；
  没有 → `fetch_docs(space_name, col_name, col_values, post=适配器)`。
  `fetch_docs` 的 post 是两参 `(url, payload)`，本层用 `_es_post` 适配到统一的
  `http_post(url, payload, timeout)` 注入口，测试用一个假客户端覆盖"ES + 建图"两条链路。
- `error` 非空 → `code=500` + 原因（**不再返回 400**；`space_name` 为空也由
  `fetch_docs` 给出可读 error，实测回 `space_name 为空，无法定位 ES 索引`）。
- 计数回填：`triples_total = edges_total = 上游 facts`、`edges_written = 上游 edges`，
  并写 `data.edges_semantics` 注明语义；`facts`/`edges` 任一为 0/缺失/bool → `code=500`。
- 上游异常：HTTP 非 200 → 502；超时/连接异常 → 502 + 异常类型；未 BUILT 或无 snapshot → 502。
- 未接线端点：`/generate_community`、`/del_space`、`/del_doc_entity` → `code=501`，
  `data.upstream_called=false`，绝不调上游。
- 环境变量：`LLMKE_V2_GRAPH_API`(18094) / `LLMKE_V2_ES_PROXY`(19527，由 legacy_es 读取) /
  `LLMKE_V2_ROOT`(.artifacts/api-root) / `LLMKE_V2_GRAPH_TIMEOUT`(600s)。

## 4. 测试

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m pytest tests/test_legacy_shim.py tests/test_legacy_es.py -q
```

真实输出：`28 passed in 0.44s`（我的 22 项 + TL 的 `test_legacy_es.py` 6 项，后者未改动）。

TL 指定的四项：
1. 无 docs + ES 2 块 → 转发成功；断言 ES payload 逐字段
   `{"index_name":["kb_9","table_chunks_kb_9"],"col_name":"title","col_values":["丙-额度分项.docx"]}`，
   转发 docs 的 `text`/`file_id`(metadata.file_id=999010)/`locator`
   (`page=[0, 0];offset=[[0, 66]];chunk=0`)，第二条无 file_id → 兜底 `丙-额度分项.docx`、
   locator `es:chunk-b`；并断言 BuildDoc 只有三个键（`es_id` 不进）。
2. ES 失败（连接异常 / HTTP 503）→ `code=500` 且 `build_calls == []`。
3. 上游 `facts=3, edges=5` → `edges_total=3`、`edges_written=5`、`triples_total=3`。
4. 原"无 docs → 400"已改为"ES 也查不到才 500"，断言 `build_calls == []`。

补充：`test_flat_es_hit_degrades_locator_instead_of_writing_fake_id` 用真实扁平 hit fixture
锁住 §2 的降级行为（locator `file:999010` + `locator_degraded=1`），防止将来有人
"顺手"把 `es:_source` 放回产物。另有 facts/edges 零或缺失的 5 例参数化、501 零调用、
未 BUILT、非 JSON、JSON 字符串 body、health 自述等。

## 5. 真实端到端（真实 ES 19527 + 真实 18094，legacy 形状请求）

**19531 被一个跑旧代码的实例占用**（pid 1188940，`LLMKE_V2_ROOT=/tmp/v2-shim-root`，
探针返回旧版 `data.es_url` 结构），我不杀别人的进程，改在 **19533** 起新版本实例，
验证完已 kill（`ss` 确认无监听）。19527 / 18094 / 19529 全程未启停。

请求（只有 space_name/col_name/col_values，与 Java 实际报文同形）：

```
curl -X POST http://127.0.0.1:19533/generate_triple_data -H 'Content-Type: application/json' -d '{
 "space_name":"kb_9","embedding_model_name":"text-embedding-bge-m3",
 "model_info":{"modelName":"qwen2.5-7b-instruct"},
 "col_name":"title","col_values":["丙-额度分项.docx"],"generation":"V0"}'
```

真实响应 `[HTTP 200 5.339825s]`：

```
code            = 200
msg             = V2 建图完成 docs=1 chunks=1 facts=3 edges=12
docs/chunks/sources = 1 / 1 / 1
triples_total   = 3
edges_total     = 3        ← 上游 facts
edges_written   = 12       ← 上游 edges
snapshot        = /tmp/s1-legacy-shim-20261102/root-es2/snapshot-20261102220217-185597-g0
generation      = 0
es              = {"es_proxy":"http://127.0.0.1:19527",
                   "es_query":{"space_name":"kb_9","col_name":"title",
                               "col_values":["丙-额度分项.docx"]},
                   "es_docs_used":1,"locator_degraded":1}
```

落盘证明降级生效（`sources.json` 里不是 `es:_source`）：

```json
{"chunk-5789841d879302e41a7eaf65ae020f81":[{"file_id":"999010","locator":"file:999010"}]}
```

失败面（同实例、真实 ES）：

```
不存在的文件名 → {"code":500,"msg":"知识库 kb_9 未查询到可建图文本（ES total=0）", …}
```

**语义提醒**：`edges_written(12) > edges_total(3)` —— `facts` 是 LLM 抽的三元组数，
`edges` 是 HippoRAG 图里的边数（含 passage↔entity 结构边），两者不是同一集合。
Java 闸门只要求 >0 所以可用；若要做质量闸门需重新定义语义。

## 6. 我没做的部分

- 没改 `legacy_es.py`（含 §2 的缺陷，只在本层降级 + 建议）、没改 `api.py`、Java、yml；
- 没实现社区检测 / 删除端点；
- 没启停 19527 / 18094 / 19529；只起停自己用的 19533（已关）；
- 没 `git add`/`commit`；没动共享 `.artifacts/api-root`（真实 build 用 `/tmp/...` 下的独立 root）。
