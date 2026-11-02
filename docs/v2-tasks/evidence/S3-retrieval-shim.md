# S3 问答检索接线（19995 `/retrieval_documents` → 18094 `/v2/graph/query`）证据

## 0. 先看这条：同一路径被两个会话同时在写

我按任务在 `services/rag-alg/index_data_service/graph_engine_adapter/retrieval_shim.py`
落盘后，**另一个 agent 会话持续在同一路径/同一端口上改写**（父进程都是
`/bin/bash -c eval "$(cat)"`，即 agent 执行 shell）。时间线（均为本机 2026-11-02）：

| 时刻 | 事实 |
|---|---|
| 22:45:49 | 他人会话起 uvicorn 19532，加载的是**另一份**同路径实现（health schema `llmke.retrieval-shim.v1`，只有 3 个键） |
| ~22:46:3x | 我的 `write_to_file` 覆盖了那份源码（我开工时该文件名搜索 0 命中，无法提前察觉；那份源码/字节码已不可取回） |
| 22:48 | 我交付版本：353 行、md5 `9dce9706dcd568c738b1cf861b93d985`，测试 `20 passed` |
| 22:49:15 | 他人会话改写实现（15347 B） |
| 22:49:21 | 他人会话重启 19532，此时跑的是「我的实现 + 它的改写」 |
| 22:49:57 | 再次改写实现（16189 B、371 行） |
| 22:50:15 | 同时改写了我的 `tests/test_retrieval_shim.py`（如把 `file_id` 断言改成接受 int） |

现在磁盘上的快照（22:51:10 取）：
`retrieval_shim.py` 371 行 / md5 `4bc1f9019fedd06bd08e2c82f4f400a8`；
`tests/test_retrieval_shim.py` / md5 `d9571597769b6e94a0a54cb3f64385a5`；`20 passed in 0.35s`。
内容 = 我的实现 + 他人叠加的 Java 字段映射（见 §5.1 的审计意见）。

**我没有继续写这两个文件**（避免和对方互相覆盖），也没 kill 19532 上别人的进程。
真实验证全部在我自己的端口上做（19534 验我的版本，19536 验当前版本），验完已 kill；
18094 / 19995 / 19531 / 19532 全程未启停。**§5.1 的 Java 风险请 TL 裁决后再定稿。**

## 1. 真实契约（读代码 + 实测）

### 1.1 Java 调用链

- `application/remote/RetrieveClient.java:14-18` 有 Feign `POST /retrieval_documents`，但
  **调用点已注释**（`application/service/impl/AiServiceImpl.java:3119`）；实际走 `:3122-3123`
  `RestTemplate.postForObject(nacosConfig.getSearchDocsUrl(), HttpEntity<String>)`。
- 地址来自 `config/application-r12.yml:39`：`spring.ai.gt.search-docs-url:
  http://127.0.0.1:19995/retrieval_documents`（`infrastructure/NacosConfig.java:20-21`）。
  切到本层 = 改这一行配置，属配置变更，**我没改**。
- 判定：`AiServiceImpl.java:3129-3134` 只认 `code==200`，否则拿 `msg` 抛
  `RETRIEVE_DOC_ERROR`；`:3137` 再兜一层只记日志 → 沿用 legacy「HTTP 200 + body.code」是对的。

### 1.2 请求

- `alg_retrieval_service/app/base.py:83 QARetrieveConfig`：`query`、`rewritten_query=""`、
  `knowledge_base_name[]`、`top_k=10`、`top_n=10`、`enabled_graph=False`、`condition_json`、
  `search_policy=1`、`enabled_faq`、`enabled_rerank` …
- Java 当前**实际发**的是 `interfaces/req/app/RetrieveDocReq.java:20-64`（`enabled_graph`、
  `search_policy`、`top_k`、`top_n`、`query`、`knowledge_base_name`、`condition_json` …），
  **不含 `rewritten_query`**——该字段只经 `domain/entity/ExtendedConfig.java:123-127`
  出现在另一条 `/qa/ai/question` 路径。本层两者都收，`rewritten_query` 非空优先。

### 1.3 响应

`alg_retrieval_service/app/retrieval_service.py:577-582`：

```
{"code":200,"msg":"查询成功","data":{
  "faq_result_list":[], "database_documents":[],
  "documents_list":[...], "web_documents_list":[], "log_list":[]}}
```

`documents_list` 每项按 `rag-common/.../qa/dto/Document.java:26-32` 反序列化
（`@JSONField("page_content")` + `metadata` 是 JSONObject；`SimpleDocumentFilter.java:12-17`
只保留 `page_content/order_num`，多余 metadata 键不致命）。
**legacy 自身不一致**：空结果早退分支 `retrieval_service.py:535-538` 漏了 `web_documents_list`
（实测 19995 同问句即走该分支，`data` 只有 4 键）。本层始终给全五键。

### 1.4 上游 18094

`graph_engine_adapter/api.py:212-234`：`POST /v2/graph/query`，`QueryRequest:33-35` 是
`query:str(min_length=1)` + `top_k:int(ge=1, le=20)`（**越界 422**）。返回
`{executed_route, reason, trace, hit_count, docs:[{rank,text,idx,sources:[{file_id,locator,title?}]}], sources_available}`。
`sources` 来自 build 时写的快照 `sources.json`（`api.py:111-124`），**无映射时 `[]`**，
`title` 只有 build 传过才有；`reason` 是**顶层字段**（不在 `trace` 里）。

## 2. 本层行为

| 上游 | documents_list |
|---|---|
| `docs[i].text` | `page_content`（原样） |
| `sources[0]` | `file_id / title / locator`（缺就是 `null`） |
| `sources[*]` | `metadata.sources`（逐条原样保留） |
| `docs[i].idx` | `metadata.idx` |
| `executed_route=GRAPH` | `metadata.search_type=["graph"]` |
| `executed_route=DENSE_FALLBACK` | `search_type=["dense_fallback"]` + `metadata.graph_reason=上游 reason` |
| — | `metadata.score` 恒 `null`（18094 不给分数，不编） |

错误语义（HTTP 恒 200 + body.code）：

| 场景 | code |
|---|---|
| 转发成功（含 0 命中，msg 写明「未召回」） | 200 |
| 请求体空/非 JSON / `query` 与 `rewritten_query` 都空 | 400（不调上游） |
| `enabled_graph` 显式 `false` | 400（本层无 dense 路径，不替调用方改语义） |
| 上游 HTTP≠200 / 超时 / 连不上 / 非 JSON / `executed_route` 不在 {GRAPH,DENSE_FALLBACK} | 502（`data=null`，原因在 `msg`） |

不静默的两处：`top_k` 夹到 18094 的 `[1,20]` 并在 msg 写「已按上游上限截断为 N」；
请求给多个 `knowledge_base_name` 时 msg 写「多知识库未分区（18094 单快照）」。
环境变量：`LLMKE_V2_GRAPH_API`、`LLMKE_V2_GRAPH_TIMEOUT`（默认 18094 / 120s）。

## 3. 测试

```
cd /home/szf/data/dev/llmke-v2
PYTHONPATH=services/rag-alg/index_data_service \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m pytest tests/test_retrieval_shim.py -q
```

我交付时：`20 passed in 0.38s`（Python 3.11.15 / fastapi 0.162.0 / httpx 0.28.1）；
当前磁盘版本：`20 passed in 0.35s`。连跑邻近接线测试
（`test_legacy_shim.py test_graph_api.py test_retrieval_shim.py`，后两者未改）：`52 passed`。

TL 指定 6 项 + 补充，逐项对应：

1. 正常 GRAPH：五键齐全、列表长度、`page_content`、`file_id/title/locator`、
   `search_type=["graph"]`、`score=None`、`idx`，并逐字段断言出站报文
   `{"query": ..., "top_k": ...}` 与 URL `/v2/graph/query`；
2. `DENSE_FALLBACK`：`search_type=["dense_fallback"]` + `graph_reason=GRAPH_NOT_CALLED`，
   并断言 `"graph" not in search_type`（防回退被说成图检索）；
3. 多来源：`metadata.sources` 全留，第一条进顶层三字段；
4. 无 sources：`file_id/title/locator/idx` 全 `null`、`sources==[]`，不伪造；
5. 上游失败：HTTP 500 / HTTP 503 / `TimeoutError` / `ConnectionRefusedError` 四例 →
   `code=502`、`data is None`、msg 有原因；另 `200 + HTML` → 502 且说明不是 JSON；
6. 空 query：`""` / 空白 / 只有空 `rewritten_query` / `{}` 四例 → `code=400` 且**出站 0 次**。

补充：`rewritten_query` 优先并写进 msg；`top_k` 默认 10、50→20 且 msg 标注截断、0→1；
未知 `executed_route`（如 `None`）→ 502 fail-closed；无正文命中被丢弃并计数；
0 命中 → 200 + 空列表 + 诚实 msg；`enabled_graph=false` → 400 且不调上游；`/health` 自述。

## 4. 真实端到端

### 4.1 我的版本（实例 19534，我的实现 md5 `9dce9706`）

请求与 `RetrieveDocReq` 同形：

```
curl -X POST http://127.0.0.1:19534/retrieval_documents -H 'Content-Type: application/json' \
  -d '{"query":"单笔授信超过五亿元由谁审议通过","knowledge_base_name":["kb_9"],"top_k":3}'
```

响应 `[HTTP 200, 0.031265s]`：

```
code=200 msg=查询成功
faq_result_list=[] database_documents=[] web_documents_list=[] log_list=[]
documents_list=[{"page_content": "“智造贷”企业流动资金贷款产品说明书 文件编号：PRD-CORP-LOAN-2026-01
                                （R12 验收测试夹具，非真实业务文件）…单户最高授信额度为人民币5000万元…（459 字）",
                 "metadata": {"file_id": "999016", "title": null,
                              "locator": "page=-;offset=[[0, 459]];chunk=0",
                              "search_type": ["graph"], "score": null,
                              "idx": "chunk-ca1d8268933dd200d88189cca497d46c",
                              "sources": [{"file_id": "999016",
                                           "locator": "page=-;offset=[[0, 459]];chunk=0"}]}}]
```

同一问句直查上游，确认**确实是图检索**、本层只透传：

```
$ curl -X POST 127.0.0.1:18094/v2/graph/query -d '{"query":"单笔授信超过五亿元由谁审议通过","top_k":3}'
executed_route= GRAPH   reason= GRAPH_CALLED   hit_count= 1
```

失败面（同实例真实调用）：

```
# 上游不可达（LLMKE_V2_GRAPH_API=http://127.0.0.1:1，实例 19535）
{"code":502,"msg":"上游图服务 http://127.0.0.1:1/v2/graph/query 不可达 ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=1): Max retries exceeded ...","data":null}
# 空 query
{"code":400,"msg":"query 为空（rewritten_query 与 query 都没有可用文本）","data":null}
```

### 4.2 当前磁盘版本（实例 19536，改写后的实现）

同一请求 `[HTTP 200, 0.038538s]`，`code=200`，`documents_list[0].metadata`：

```json
{"file_id": 999016, "source": "999016",
 "position": {"locator": "page=-;offset=[[0, 459]];chunk=0",
              "sources": [{"file_id": "999016", "locator": "page=-;offset=[[0, 459]];chunk=0"}]},
 "chunk_index": 0, "title": null, "locator": "page=-;offset=[[0, 459]];chunk=0",
 "search_type": ["graph"], "score": null,
 "idx": "chunk-ca1d8268933dd200d88189cca497d46c",
 "sources": [{"file_id": "999016", "locator": "page=-;offset=[[0, 459]];chunk=0"}]}
```

两个实例验完均 kill（`ss` 确认 19534/19535/19536 无监听）。

## 5. 实测落差与审计意见（别当成已解决）

### 5.1 【需 TL 裁决】当前版本把 `file_id` 塞进 `metadata.source`，会踩 Java 的解析缺陷

当前改写加入 `"source": primary.get("title") or str(raw_file_id)`，实测在这份快照上取到
`"source": "999016"`。而 `Document.buildParsedFilePath`（`rag-common/.../dto/Document.java:62-93`）
假设 `source` 是 minio 对象路径，直接做三次 `substring`：

```java
String objectName = source.substring(source.indexOf("/") + 1);            // "999016".indexOf("/")=-1 → substring(0)
String substring  = objectName.substring(objectName.indexOf("/") + 1);    // 同样 -1 → substring(0)
sourceFileName    = substring.substring(0, substring.indexOf("/"));       // indexOf=-1 → substring(0,-1)
```

第三步会抛 `StringIndexOutOfBoundsException`（代码级推导，我没有跑 Java 验证）。
该方法的调用链是真实存在的：
`RetrievedData.getSimpleDocuments(minioUrl)` → `getDocumentsByStr`（`RetrievedData.java:108-116`
对每篇 `forEach(d -> d.buildParsedFilePath(minioUrl))`，**无 try/catch**），
上游调用点在 `AiServiceImpl.java:2902` 与 `:3010`。
→ 建议：`source` 只在**有真实路径**时给；拿不到路径时宁可留空，别用 `file_id` 顶。
（`RetrieveDoc.RetrieveMetaData` 确实有 `source/position/chunk_index/file_id/search_type` 这些
驼峰映射字段，`RetrieveDoc.java:36-96` 可证；问题在 `source` 的**取值语义**，不在键名。）

顺带一个数据保真问题：`file_id = int(str(raw_file_id))` 失败时被置 `None`
（当前实现 `:209-212`）。上游 `file_id` 若出现非数字（如 `file-xxx`），标识会**静默丢失**；
而 Jackson/fastjson 对数字字符串转 `Long` 本来就会自行转换，无需本层提前转。

### 5.2 `title` 实测恒为 `null`

18094 的 `sources.json` 在 build 时按 `BuildDoc{file_id,text,locator,title?}` 写，`api.py:119-122`
只写非空字段；当前快照 build 未传 `title`，检索侧就拿不到文件名（`file_id=999016` 是有的）。
要出文件名只能：build 时带上 `title`，或本层按 `file_id` 反查文件服务（本层不做）。

### 5.3 `locator` 里的 `page=-`

上游定位串是 ES 侧的 `page=-;offset=[[0, 459]];chunk=0`，`page=-` 表示页码取不到。
本层原样透传，不猜页码。

### 5.4 `DENSE_FALLBACK` 真实 18094 复现不出来

实测连 `{"query":"qzxvbnm"}` 也返回 `executed_route=GRAPH, reason=GRAPH_CALLED, hit_count=1`。
即当前快照下「路由=GRAPH」**只说明引擎的图检索入口被调用过**，不代表图真找对了
（trace 语义见 `engine_hipporag.py:113-194`）。回退分支只能用注入夹具验（本层已覆盖）。

### 5.5 同问句 legacy 19995 返回 0 条

实测 `HTTP 200 6.39s`，走阈值未命中的早退分支，`data` 只有 4 个键、`documents_list=[]`；
而图检索给 1 条。这是「dense+rerank 阈值」与图路径的真实差异，不是本层造的数据。

### 5.6 最大的语义缺口：不做知识库分区

`knowledge_base_name` 在本层**不参与过滤**（18094 服务单个快照），任何 KB 拿到的都是同一份图的
命中；多 KB 时只在 msg 里声明「未分区」。真要分区得在 18094 侧支持按 KB 选快照。
另有 `search_policy`(1/2/3)、`enabled_rerank`、`enabled_faq`、`condition_json`、`top_n`
本层不实现，也不拿别的检索结果顶替。

## 6. 我没做的部分

- 没改任何既有文件（`api.py`、`legacy_shim.py`、`assertions.py`、Java、`application-r12.yml` 均未动）；
- **没切 19995**（那是配置变更），只在自己的端口验证；
- 没实现 dense / FAQ / 表格 / 联网检索，也没把它们的空结果包装成"成功且有内容"；
- 没启停 18094 / 19995 / 19527 / 19531 / 19532；只起停自己的 19534、19535、19536（已关）；
- 没 `git add` / `commit`；
- 发现同一路径有第二个会话在改写后，**停止继续写实现与测试文件**（避免互相覆盖），
  也没去动 19532 上别人的进程；§0 与 §5.1 留给 TL 裁决。
