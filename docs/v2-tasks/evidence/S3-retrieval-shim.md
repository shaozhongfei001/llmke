# S3 问答检索接线（19995 `/retrieval_documents` → 18094 `/v2/graph/query`）证据

## 0. 当前状态（TL 裁决后：我是唯一写者）

TL 裁决：保留「我的实现 + TL 叠加的 Java 字段映射」的合并版本，已落库
`f1a54ad`（检索兼容层接管 qa-service）、`7281f8b`（`source` 不再填 id/文件名）。
之后我在同一文件上追加了 global 端点的接线（见 §4.3），仍是唯一写者。

本轮快照（2026-11-02 22:54:39 取，工作区未提交）：

| 文件 | 行数 | md5 |
|---|---|---|
| `services/rag-alg/index_data_service/graph_engine_adapter/retrieval_shim.py` | 421 | `7bf7b047d577f4d8ee52aff45bedbbf3` |
| `tests/test_retrieval_shim.py` | 306 | `9a0e063372004d5c27c3e36958acd6bf` |

测试：`23 passed`（原 20 项 + global 3 项）。
19532 已重启为新代码（pid 1488099），18094 / 19995 / 19531 / 19527 未启停。

历史（供追溯，别再据此判断现状）：22:45–22:50 期间同一路径与同一端口曾被另一个 agent 会话
并发改写（它先起 19532、我落盘覆盖了它那份源码、随后它两次改实现并改过我的测试文件）。
那段过程由 TL 裁决收口为上面的合并版本，`import re` 的重复引入已在追加 global 时顺手去掉。

**遗留提醒**：同一目录下另有 `docs/v2-tasks/evidence/S3-retrieval-wiring.md`
（另一会话建的同类证据），本文件是 TL 指定我维护的那一份（`S3-retrieval-shim.md`）。

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

当前：`23 passed in 0.38s`（原 20 项 + global 3 项；Python 3.11.15 / fastapi 0.162.0 / httpx 0.28.1）。
上一轮（未加 global 时）：`20 passed`；连跑邻近接线测试
（`test_legacy_shim.py test_graph_api.py test_retrieval_shim.py`，后两者未改）：`52 passed`。

global 追加的 3 项：

- `test_global_returns_501_and_never_calls_upstream`：`code=501`、msg 逐字等于
  `global not ready: community report not wired`、`data is None`、**出站 0 次**（既没调上游，
  也没把普通 chunk 塞进 data 冒充摘要）；
- `test_global_with_graph_disabled_is_400_not_501`：`enabled_graph=false` → `code=400` 且出站 0 次
  （请求侧问题比能力缺失先说清，不用 501 掩盖）；
- `test_health_reports_global_as_not_wired`：`/health.global` 可见
  `endpoint/wired=false/reason/why`。

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

### 4.2 7281f8b 修复前的中间版本（实例 19536，仅留档）

> 下面是 `7281f8b` **修复 source 之前**抓到的那一版，`"source": "999016"` 已在修复中去掉
> （现在恒为 `null`）。留在这里是为了对上 §5.1 的记录，不代表现状。

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

### 4.3 global 端点：501（19532 重启后真实调用）

契约依据：legacy `alg_retrieval_service/app/view/urls.py:24 RetrievalGlobalView(path="/retrieval_documents_global")`
是"GraphRAG 社区摘要 map-reduce"入口；Java `NacosConfig.java:27` 默认
`http://127.0.0.1:19995/retrieval_documents_global`，由 `AiServiceImpl.java:2259/2366/2498`
在 `query_mode=global` 时调用，答案取 `RetrievedData.getGlobalAnswer:62-63`（`data.global_answer`）。
实测上游能力：`GET 18094/openapi.json` 只有 `/health`、`/v2/graph/build`、`/v2/graph/query`
（`api.py:156/174/212`），`community.py` 未暴露 HTTP → **社区报告不存在**。

重启 19532（pid 1488099，新代码）后真实调用：

```
$ curl -X POST http://127.0.0.1:19532/retrieval_documents_global -H 'Content-Type: application/json' \
   -d '{"query":"单笔授信超过五亿元由谁审议通过","query_mode":"global","knowledge_base_name":["kb_9"],
        "top_k":3,"summary_top_k":5}'
[HTTP 200, 0.001195s]
{"code":501,"msg":"global not ready: community report not wired","data":null}
```

`enabled_graph=false` 时同路径（单元测试覆盖，见 §3）→ `code=400`，原因写"global 建立在图社区摘要之上"。
`/health` 自述（同实例真实响应）：

```json
{"endpoint": "/retrieval_documents_global", "wired": false,
 "reason": "global not ready: community report not wired",
 "why": "18094 无社区报告端点（只有 /health、/v2/graph/build、/v2/graph/query），community.py 未暴露 HTTP；拿普通检索结果顶替 global 等于造假"}
```

### 4.4 上游 500 故障与修复后的复验（故障不是本层引入的）

故障：22:54:22 有人在 `/tmp/v2-shim-root` 下重建了图快照（health 显示 `nodes=5, edges=12, facts=3`），
此后 `POST 18094/v2/graph/query` 对**任何**问句都 500（实测 `单笔授信…` 3.9s/500、`a` 0.99s/500）。
本层当时如实回 502（这就是它该做的）：

```
{"code":502,"msg":"上游图服务 http://127.0.0.1:18094/v2/graph/query 返回 HTTP 500: Internal Server Error","data":null}
```

TL 定位上游根因并修复（提交 `04bce3d`）：`HippoRAG.get_top_k_weights` 的自检
`count_nonzero(weights)==len(map)` 在小语料/CJK 下失败（选中短语权重为 0）；适配器现在只跳过这条
自检、仍按上游规则截断 map，并记 `trace.weights_assert_skipped`。

修复后复验（同一实例 19532、同一快照，无重启本层）：

```
$ curl -X POST 127.0.0.1:18094/v2/graph/query -d '{"query":"单笔授信超过五亿元由谁审议通过","top_k":3}'
[HTTP 200, 0.003051s] route=GRAPH reason=GRAPH_CALLED hit=1
  idx=chunk-5789841d879302e41a7eaf65ae020f81
  sources=[{"file_id":"999010","locator":"page=-;offset=[[0, 66]];chunk=0","title":"丙-额度分项.docx"}]

$ curl -X POST 127.0.0.1:19532/retrieval_documents -d '{"query":"单笔授信超过五亿元由谁审议通过","knowledge_base_name":["kb_9"],"top_k":3}'
[HTTP 200, 0.005919s] code=200 msg=查询成功
  {"file_id": 999010, "source": null,
   "position": {"locator": "page=-;offset=[[0, 66]];chunk=0",
                "sources": [{"file_id":"999010","locator":"page=-;offset=[[0, 66]];chunk=0","title":"丙-额度分项.docx"}]},
   "chunk_index": 0, "title": "丙-额度分项.docx",
   "locator": "page=-;offset=[[0, 66]];chunk=0",
   "search_type": ["graph"], "score": null,
   "idx": "chunk-5789841d879302e41a7eaf65ae020f81",
   "sources": [{"file_id":"999010","locator":"page=-;offset=[[0, 66]];chunk=0","title":"丙-额度分项.docx"}]}
```

要点：`search_type=["graph"]` 与上游 `executed_route=GRAPH` 一致（仍只透传不猜）；`source=null`
（`7281f8b` 的修复生效）；`file_id` 为 int；**`title` 已能端到端给出真实文件名**（见 §5.2 更新）。
注意这是**新快照**（1 条命中、`chunk-5789…`），与 §4.1 旧快照（`chunk-ca1d8268…`）不是同一份语料。

## 5. 实测落差与审计意见（别当成已解决）

### 5.1 已修：`source` 恒为 `null`（原风险：拿 `file_id`/裸文件名顶 `source` 会踩 Java 解析缺陷）

**状态：已修并复验通过**（TL 在 `7281f8b` 中把 `source` 固定为 `null`）：
Java 侧不再有任何非路径串进入 `source`，`buildParsedFilePath` 的 `substring` 分支不会被触发；
同时 `file_id=999016`（Long）与 `position.locator` 保留，引用所需信息不丢。
下面保留原始风险推导，作为"为什么不能把 id 填进 source"的依据。

历史：中间版本曾写 `"source": primary.get("title") or str(raw_file_id)`，实测在这份快照上取到
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
→ 结论（已执行）：`source` 恒为 `null`，不给 `file_id`、也不给裸文件名。
（`RetrieveDoc.RetrieveMetaData` 确实有 `source/position/chunk_index/file_id/search_type` 这些
驼峰映射字段，`RetrieveDoc.java:36-96` 可证；问题在 `source` 的**取值语义**，不在键名。）

`file_id` 的 int 转换经 TL 裁决保留（Jackson 能收 `Long`），非数字时置 `null` 的原因已在代码里
注释说明——这是有意为之的取舍，不是遗漏。

### 5.2 `title`：旧快照为 `null`，新快照已端到端给出真实文件名（已解决）

18094 的 `sources.json` 在 build 时按 `BuildDoc{file_id,text,locator,title?}` 写，`api.py:119-122`
只写非空字段。**旧**快照 build 未传 `title`，所以 §4.1/§4.2 里 `title` 都是 `null`（`file_id=999016` 有）。
`1088280`（兼容层透传文件标题）落地后，重建的新快照 `sources.json` 已带 `title`：

```json
{"chunk-5789841d879302e41a7eaf65ae020f81":[{"file_id":"999010",
  "locator":"page=-;offset=[[0, 66]];chunk=0","title":"丙-额度分项.docx"}]}
```

本层映射（`title` 取 `sources[0].title`）无需改动即生效，上游 500 修复后已端到端复验
（§4.4）：`metadata.title = "丙-额度分项.docx"`、`position.sources[0].title` 同值。

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
- **没实现 global**：只接了一个如实 501 的端点，没有社区检测/摘要（18094 无该能力），
  也没有"用普通检索凑一个答案"的降级；
- 没启停 18094 / 19995 / 19527 / 19531；19532 按 TL 指令重启到新代码后**保持运行**
  （pid 1488099，供 TL 复验；需要关请说一声）；我自己的 19534/19535/19536 已关；
- 没 `git add` / `commit`（`f1a54ad`、`7281f8b`、`1088280` 都是 TL 那边提交的；
  本轮 global 改动还在工作区未提交）；
- 没去修 18094 重建后 `/v2/graph/query` 的 500（属建图/上游侧，我只如实回 502 并记录）。
