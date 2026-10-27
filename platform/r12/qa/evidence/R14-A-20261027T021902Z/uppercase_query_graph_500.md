# 开图检索 HTTP 500：查询含大写 ASCII 时 documents[query] KeyError

采集：2026-10-27T11:40:25+08:00；发现路径=B-graph 的 /qa 开图 refs=0 → A 在 19995 层隔离

## A/B 对照（唯一变量：查询里的 AAA 大小写；其余参数相同）
```
POST 19995/retrieval_documents  kb_9 top_k=10 enabled_graph=true enabled_rerank=false enabled_faq=false
  信用评级为AAA的公司执行利率需要加多少个基点  -> HTTP 500  Internal Server Error
  信用评级为aaa的公司执行利率需要加多少个基点  -> HTTP 200
  智造贷的授信额度                              -> HTTP 200
```
enabled_graph=false 时同一大写查询 -> HTTP 200（说明与图无关，是"图分支取键"这一步）。

## 堆栈（platform/r12/logs/alg_retrieval_service.log）
```
app/view/api/retrieval_documents_view.py:17 in post
app/retrieval_service.py:478 in multiple_retrieval_documents
KeyError: '信用评级为AAA的公司执行利率需要加多少个基点'
```

## 代码级根因（app/retrieval_service.py）
```
355  query = qa_model.query
372  def _add_query_to_queries(query_str, target_list):
375      normalized_query = query_str.lower()      # ← 只把小写形式加进 queries
376      target_list.append(normalized_query)
379  _add_query_to_queries(query, queries)          # documents 的键 = 小写查询
...
478          documents[query].extend(graph_documents)   # ← 用原始大小写取键 → KeyError
```
注：`366-370` 原本有一段"含大写时同时加入原串与小写串"的逻辑，但已被注释掉，改由 `_add_query_to_queries` 统一小写 → 原串不再进 `queries`，`documents` 里就没有原串键。

## 影响
- 任何含大写 ASCII 的查询（产品编号 `PRD-CORP-LOAN-2026-01`、`T-CORE-001`、评级 `AAA/AA`、英文缩写）→ 开图检索直接 500；
- Java 侧拿不到 documents_list → 引用为空（B 观测到的"开图 refs=0"，答案仍可能由模型自身知识给出 → **答案对但零出处**）；
- 与"多 KB 静默丢结果""FAQ offset break"是不同缺陷，但同属"一个异常吃掉整批结果"。
