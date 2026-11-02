# S3 问答检索接线（19995 `/retrieval_documents` → 18094 `/v2/graph/query`）证据

交付（只新建这三个文件，未改任何既有文件，未 `git add`/`commit`）：

| 文件 | 行数 | md5 |
|---|---|---|
| `services/rag-alg/index_data_service/graph_engine_adapter/retrieval_shim.py` | 353 | `9dce9706dcd568c738b1cf861b93d985` |
| `tests/test_retrieval_shim.py` | 269 | `6990c8e25a720051bd6f4bf85dfd7b86` |
| 本文件 | — | — |

## 0. 先说一个必须由 TL 裁定的现场冲突

我按要求在 **19532** 起实例时端口已被占用，占用者是**另一个 agent 会话**起的同名模块：

```
$ ps -o pid,lstart,cmd -p 1443204
1443204  Mon Nov  2 22:45:49 2026  .../python -m uvicorn graph_engine_adapter.retrieval_shim:app --host 127.0.0.1 --port 19532
$ ss -ltnp | grep 19532
LISTEN ... 127.0.0.1:19532 ... users:(("python",pid=1443204...))
$ curl -s 127.0.0.1:19532/health
{"schema":"llmke.retrieval-shim.v1","graph_api":"http://127.0.0.1:18094","wired":["POST /retrieval_documents"]}
```

要点：
- 该进程 cwd=`/home/szf/data/dev/llmke-v2`、`PYTHONPATH=services/rag-alg/index_data_service`，即它 import 的
  就是本任务指定的**同一路径** `graph_engine_adapter/retrieval_shim.py`；但它的 health schema 是
  `llmke.retrieval-shim.v1`、只有 `{schema, graph_api, wired}` 三个键，**不是本文件的实现**
  （本文件 schema=`llmke.graph-api.retrieval-shim.v1`，health 自述 8 个键）。
- 它启动于 22:45:49，早于我的首次落盘，说明在我开始写之前该路径上**已存在另一份实现**；
  我的 `write_to_file` 覆盖了磁盘上的那一份（我开工时的文件名搜索结果是 0 命中，无法提前察觉）。
  那个会话的源码我这边已无法取回（字节码也被我的测试 import 覆盖），只能由它自己重写。
- 因此：**现在磁盘上是我的实现，而 19532 上跑的是旧内存里的另一份实现**。若 TL 直接 curl 19532，
  看到的不是本证据里的行为。我没有 kill 它（不是我的进程），也没有再占用 19532。
- 我的真实验证改在 **19534**（正常路径）与 **19535**（指向死上游验 502），验证完均已 kill，
  18094 / 19995 / 19531 / 19532 全程未启停。请 TL 决定保留哪一份实现。

## 1. 真实契约（读代码 + 实测）

### 1.1 Java 侧调用链

- `application/remote/RetrieveClient.java:14-18` 声明了 Feign `POST /retrieval_documents`，
  但**调用点已注释**：`application/service/impl/AiServiceImpl.java:3119`，
  实际走 `:3122-3123` `RestTemplate.postForObject(nacosConfig.getSearchDocsUrl(), HttpEntity<String>)`。
- URL 来自 `config/application-r12.yml:39`：`spring.ai.gt.search-docs-url:
  http://127.0.0.1:19995/retrieval_documents`（`infrastructure/NacosConfig.java:20-21`）。
  → 切到本层是**改这一行配置**，属配置变更，我没有改。
- 判定：`:3129-3134` 只有 `code==200` 才取 `data`，否则用 `msg` 抛 `RETRIEVE_DOC_ERROR`；
  `:3137` 再兜一层只记日志。→ 沿用 legacy 的「HTTP 200 + body.code」是对的。

### 1.2 请求

- `alg_retrieval_service/app/base.py:83 QARetrieveConfig`：`query`、`rewritten_query=""`、
  `knowledge_base_name[]`、`top_k=10`、`top_n=10`、`enabled_graph=False`、`condition_json`、
  `search_policy=1`、`enabled_faq=True`、`enabled_rerank=True` …
- Java 当前**实际发的报文**是 `interfaces/req/app/RetrieveDocReq.java:20-64`
  （`enabled_graph / search_policy / top_k / top_n / query / knowledge_base_name / condition_json` …），
  **不含 `rewritten_query`**；`rewritten_query` 只经 `domain/entity/ExtendedConfig.java:123-127`
  出现在另一条 `/qa/ai/question` 路径上。本层两者都接受，`rewritten_query` 非空优先。

### 1.3 响应

`alg_retrieval_service/app/retrieval_service.py:577-582`：

```
{"code":200,"msg":"查询成功","data":{
  "faq_result_list":[], "database_documents":[],
  "documents_list":[...], "web_documents_list":[], "log_list":[]}}
```

`documents_list` 每项按 `rag-common/.../qa/dto/Document.java:26-32` 反序列化
（`@JSONField("page_content")` + `metadata` 是 JSONObject；`SimpleDocumentFilter.java:12-17`
只保留 `page_content/order_num`，多余 metadata 键不报错）。

**legacy 自身的不一致**：空结果早退分支 `retrieval_service.py:535-538` **漏了 `web_documents_list`**
（实测 19995 同问句即走该分支，`data` 只有 4 个键）。本层始终给全五键——
Java `RetrievedData.existDocs:73-85` 对 null 也判空，给全更稳。

### 1.4 上游 18094

`graph_engine_adapter/api.py:212-234`：`POST /v2/graph/query`，`QueryRequest:33-35` 是
`query: str(min_length=1)` + `top_k: int(ge=1, le=20)`（**越界 422**）。

```
{"schema","query","executed_route","reason","trace","hit_count",
 "docs":[{"rank","text","idx","sources":[{"file_id","locator","title"?}]}],"sources_available"}
```

`sources` 来自 build 时写的快照 `sources.json`（`api.py:111-124`）：**没有映射时 `[]`**，
`title` 只有 build 时传过才有；`reason` 是**顶层字段**（不在 `trace` 里）。

## 2. 本层行为

映射（`_to_document`）：

| 上游 | documents_list |
|---|---|
| `docs[i].text` | `page_content`（原样） |
| `sources[0]` | `metadata.file_id / title / locator`（缺就是 `null`） |
| `sources[*]` | `metadata.sources`（逐条原样保留） |
| `docs[i].idx` | `metadata.idx` |
| `executed_route=GRAPH` | `metadata.search_type=["graph"]` |
| `executed_route=DENSE_FALLBACK` | `metadata.search_type=["dense_fallback"]` + `metadata.graph_reason=上游 reason` |
| — | `metadata.score` 恒 `null`（18094 不给分数，不编） |

错误语义（HTTP 恒 200 + body.code）：

| 场景 | code | 备注 |
|---|---|---|
| 转发成功（含 0 命中） | 200 | 0 命中时 `msg` 写明「graph 未召回任何文档」 |
| 请求体空/非 JSON/`query` 与 `rewritten_query` 都空 | 400 | 不调上游 |
| `enabled_graph` **显式** `false` | 400 | 本层只有图路径，不替调用方把 dense 结果说成图检索 |
| 上游 HTTP≠200 / 超时 / 连不上 / 非 JSON / `executed_route` 不在 {GRAPH,DENSE_FALLBACK} | 502 | `data=null`，原因在 `msg` |

两个"不静默"的处理：
- `top_k` 被夹到 18094 的 `[1,20]`，被夹时 `msg` 里写「top_k 已按上游上限截断为 N」；
- 请求给多个 `knowledge_base_name` 时 `msg` 里写「多知识库未分区（18094 单快照）」。

环境变量：`LLMKE_V2_GRAPH_API`（默认 `http://127.0.0.1:18094`）、`LLMKE_V2_GRAPH_TIMEOUT`（默认 120）。

## 3. 测试

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m pytest tests/test_retrieval_shim.py -q
```

真实输出：`20 passed in 0.38s`（venv Python 3.11.15 / fastapi 0.162.0 / httpx 0.28.1）。
连同邻近接线测试一起跑：`tests/test_legacy_shim.py tests/test_graph_api.py tests/test_retrieval_shim.py`
→ `52 passed in 0.55s`（未改那两份文件）。

覆盖 TL 指定的 6 项 + 补充：

1. 正常 GRAPH：五键齐全、`documents_list` 长度、`page_content`、`file_id/locator/title`、
   `search_type=["graph"]`、`score=None`、`idx`、出站报文 `{query,top_k}` 与 URL 逐字段断言；
2. `DENSE_FALLBACK`：`search_type=["dense_fallback"]` 且带 `graph_reason=GRAPH_NOT_CALLED`，
   并断言 `"graph" not in search_type`（防回退被说成图检索）；
3. 多来源：`metadata.sources` 两条全留，第一条进顶层 `file_id/title/locator`；
4. 无 sources：`file_id/title/locator/idx` 全 `null`、`sources==[]`，不伪造；
5. 上游失败：HTTP 500 / HTTP 503 / `TimeoutError` / `ConnectionRefusedError` 四例参数化
   → `code=502`、`data is None`、`msg` 有原因；另有 `200 + HTML` → 502 且提示不是 JSON；
6. 空 query：`""`/空白/只有空 `rewritten_query`/`{}` 四例 → `code=400` 且**出站调用为 0**。

补充：`rewritten_query` 优先并被写入 msg；`top_k` 默认 10 / 50→20 且 msg 标注截断 / 0→1；
未知 `executed_route`（如 `None`）→ 502 fail-closed；无正文命中被丢弃并计数；
0 命中 → 200 + 空列表 + 诚实 msg；`enabled_graph=false` → 400 且不调上游；`/health` 自述。

## 4. 真实端到端（真实 18094，实例 19534）

请求（与 `RetrieveDocReq` 同形，只保留交集字段）：

```
curl -X POST http://127.0.0.1:19534/retrieval_documents -H 'Content-Type: application/json' \
  -d '{"query":"单笔授信超过五亿元由谁审议通过","knowledge_base_name":["kb_9"],"top_k":3}'
```

真实响应 `[HTTP 200, 0.031265s]`：

```
code = 200     msg = 查询成功
data.faq_result_list / database_documents / web_documents_list / log_list = [] / [] / [] / []
data.documents_list = [
 {"page_content": "“智造贷”企业流动资金贷款产品说明书 文件编号：PRD-CORP-LOAN-2026-01（R12 验收测试夹具，
                    非真实业务文件）一、适用对象…二、授信额度单户最高授信额度为人民币5000万元。…（全文 459 字）",
  "metadata": {"file_id": "999016",
               "title": null,                                    ← 上游快照 sources.json 无 title，不编
               "locator": "page=-;offset=[[0, 459]];chunk=0",
               "search_type": ["graph"],
               "score": null,
               "idx": "chunk-ca1d8268933dd200d88189cca497d46c",
               "sources": [{"file_id": "999016", "locator": "page=-;offset=[[0, 459]];chunk=0"}]}}]
```

同一问句直查上游，确认**确实是图检索**、本层是透传而非自造：

```
$ curl -X POST 127.0.0.1:18094/v2/graph/query -d '{"query":"单笔授信超过五亿元由谁审议通过","top_k":3}'
executed_route= GRAPH   reason= GRAPH_CALLED   hit_count= 1
```

失败面（同为真实调用）：

```
# 指向死上游（LLMKE_V2_GRAPH_API=http://127.0.0.1:1，实例 19535）
{"code":502,"msg":"上游图服务 http://127.0.0.1:1/v2/graph/query 不可达 ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=1): Max retries exceeded ...","data":null}
# 空 query（19534）
{"code":400,"msg":"query 为空（rewritten_query 与 query 都没有可用文本）","data":null}
```

两个实例验证完已 kill（`ss` 确认 19534/19535 无监听）；18094/19995/19531/19532 未启停。

## 5. 实测落差（必须写在证据里，别当成已解决）

1. **`title` 实测恒为 `null`**：18094 的 `sources.json` 是 build 时按 `BuildDoc{file_id,text,locator,title?}`
   写出的，`api.py:119-122` 只写非空字段。当前快照 build 时没传 `title`，所以检索侧拿不到文件名
   （`file_id=999016` 是有的）。要出文件名只有两条路：build 时把 `title` 带上，或本层拿 `file_id`
   反查文件服务（本层不做，属跨服务依赖）。
2. **`locator` 里的 `page=-`**：上游给的定位串是 ES 侧的 `page=-;offset=[[0, 459]];chunk=0`，
   `page=-` 表示页码取不到。本层原样透传（不猜页码），下游若要用页码需另行补。
3. **`DENSE_FALLBACK` 只能靠夹具验，真实 18094 复现不出来**：实测连 `{"query":"qzxvbnm"}` 这种
   乱串也返回 `executed_route=GRAPH, reason=GRAPH_CALLED, hit_count=1`。也就是说当前快照下
   「路由=GRAPH」**不等于**「图上真找对了」，它只说明引擎的图检索入口被调用过。本层只负责不歪曲透传，
   路由真伪的判定属引擎侧（`engine_hipporag.py:113-194` 的 trace 语义）。
4. **同问句 legacy 19995 返回 0 条**（实测 `HTTP 200 6.39s`，走的是阈值未命中的早退分支，
   `data` 只有 4 个键、`documents_list=[]`），而图检索给出 1 条：这是图路径与 dense+rerank 阈值路径的
   真实差异，不是本层造的数据。
5. **最大的语义缺口：不做知识库分区**。`knowledge_base_name` 在本层不参与过滤——18094 服务单个快照，
   所以任何 KB 的请求拿到的都是同一份图的命中，多个 KB 时只在 `msg` 里声明"未分区"。
   要真正分区，需要在 18094 侧支持按 KB 选快照（属建图/快照层，不在本层）。
6. `search_policy`(1/2/3)、`enabled_rerank`、`enabled_faq`、`condition_json`、`top_n` 本层都不实现，
   也不拿别的检索结果去顶替。

## 6. 我没做的部分

- 没改任何既有文件（含 `api.py`、`legacy_shim.py`、`assertions.py`、Java、`application-r12.yml`）；
- **没切 19995**（那是 `application-r12.yml:39` 的配置变更），本层只在自己的端口上验证；
- 没实现 dense / FAQ / 表格 / 联网检索，也没有把它们的空结果包装成"查询成功且有内容"；
- 没启停 18094 / 19995 / 19527 / 19531 / 19532；只起停了自己的 19534、19535（已关）；
- 没 `git add` / `commit`；
- 没动 §0 里另一会话的进程，也没尝试恢复它被覆盖的源码。
