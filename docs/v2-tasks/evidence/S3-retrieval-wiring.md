# S3 问答检索接线：Java qa-service → 19532 → 18094

日期：2026-11-02 22:52

## 配置

`platform/r12/conf/rag-qa-service/application-r12.yml`（已备份 `.bak-20261102`）：

```yaml
search-docs-url: http://127.0.0.1:19532/retrieval_documents
retrieve-url:    http://127.0.0.1:19532
```

qa-service 已重启（pid 1453899）。

## 真实链路

请求（经网关，登录后）：

```json
{"userQuestion":"星航贷单户最高授信额度是多少","knowledge":["9"],
 "recallCount":3,"knowledgeGraphEnable":true,"faqPriority":false,
 "rerankerEnabled":false,"useAuth":false,"retrievalType":1,"similarityThreshold":0.0}
```

Java 日志显示上游已切换：

```
检索召回请求参数: {"query":"星航贷单户最高授信额度是多少","top_k":3,...}
knowledge---getBody: {"code":200,"data":{"documents_list":[{"page_content":"“智造贷”...
```

Java 返回（`/qa/ai/retrieveDocs4Plat`，HTTP 200）：

```json
{"data":{"documents_list":[
  {"page_content":"“智造贷”企业流动资金贷款产品说明书...",
   "metadata":{"file_id":"999016","source":"999016","chunk_index":0,
               "search_type":["graph"],
               "position":{"locator":"page=-;offset=[[0, 459]];chunk=0"}}}]}}
```

## 判定

- qa-service 的检索已走 19532（HippoRAG 兼容层），不再调 legacy 19995；
- `search_type=["graph"]` 来自上游 `executed_route=GRAPH`，不是包装层猜的；
- 引用字段落到 Java `RetrieveMetaData` 真正能承载的键：
  `file_id`(Long) / `source` / `chunk_index` / `position{locator}`；
- 直接调检索接口复验（不经 Java）也返回同一文档与 locator。

## 已知限制

- `source` 当前回退为 file_id：快照构建于 title 透传之前，重建后才会是文件名；
- 只接了 `/retrieval_documents`；`/retrieval_documents_global`（global 问答）尚未实现；
- 页面端到端（浏览器点击引用）未验证。

## 安全修正：source 不能填 id/文件名

`rag-common/Document.java:70-72` 对 `metadata.source` 连做三次 `indexOf("/") + substring`；
没有斜杠时 `substring(0,-1)` 抛 `StringIndexOutOfBoundsException`。
本层曾把 file_id 当 source，实测返回 `source="999016"`——在问答组装路径（RetrievedData）会崩。

修正：`source` 恒为 null，不再填 id 或裸文件名；文件路径由 Java 侧
`addConvertedFilePath(file_id)` 补齐。

复验（经 Java，HTTP 200）：

```json
{"file_id":"999016","source":null,"chunk_index":0,
 "search_type":["graph"],
 "position":{"locator":"page=-;offset=[[0, 459]];chunk=0"}}
```

测试 20 passed。
