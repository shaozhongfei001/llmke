# 多 KB 图检索静默丢结果（运行态证据）

采集时刻：2026-10-27T11:14:01+08:00

## 1) 图服务直连返回形状
```
kb_9        -> code 200 | result_data 4 | entity_list 3 | identity_violations_count 0
kb_5        -> code 500 | msg 该空间：kb_5不存在... | data 为空（无 result_data 键）
kb_nosuch   -> code 500 | msg 该空间：kb_nosuch不存在... | data 为空（无 result_data 键）
```

## 2) 检索侧日志（platform/r12/logs/alg_retrieval_service.log）
```
2026-10-27 11:13:42.353 | INFO     | operators.client.graph_client:request:60 - 异步请求图检索服务耗时: 0.444s, URL: http://127.0.0.1:19529/query_graph_data, 请求数据: {'space_name': 'kb_9', 'query': '智造贷的授信额度', 'model_info': {}, 'depth': 3, 'top_k': 5}, 图检索结果: {'code': 200, 'msg': '查询成功，共4条文本数据', 'data': {'result
2026-10-27 11:13:42.501 | INFO     | operators.client.graph_client:request:60 - 异步请求图检索服务耗时: 0.010s, URL: http://127.0.0.1:19529/query_graph_data, 请求数据: {'space_name': 'kb_5', 'query': '智造贷的授信额度', 'model_info': {}, 'depth': 3, 'top_k': 5}, 图检索结果: {'code': 500, 'msg': '该空间：kb_5不存在，请检查后再次查询', 'data': 
2026-10-27 11:13:42.501 | ERROR    | multiple_retrieval:retrieval_graph:449 - graph查询报错: 'NoneType' object is not subscriptable, 请求 URL: http://127.0.0.1:19529/, 请求参数 data: {'space_name': 'kb_5', 'query': '智造贷的授信额度', 'model_info': {}, 'depth': 3, 'top_k': 5}, 图检索结果 response: {'code': 500, 'msg': '该空
2026-10-27 11:13:47.068 | INFO     | operators.client.graph_client:request:60 - 异步请求图检索服务耗时: 0.452s, URL: http://127.0.0.1:19529/query_graph_data, 请求数据: {'space_name': 'kb_9', 'query': '智造贷的授信额度', 'model_info': {}, 'depth': 3, 'top_k': 5}, 图检索结果: {'code': 200, 'msg': '查询成功，共4条文本数据', 'data': {'result
```

## 3) 判读
- 11:13:42.353 单独 kb_9：图检索正常返回 4 条
- 11:13:42.501 多 KB（kb_5 在前、kb_9 在后）：只请求了 kb_5，拿回 data=None
- 随即抛 TypeError: 'NoneType' object is not subscriptable → multiple_retrieval.py:449 except 分支 → return graph_documents（提前返回）
- 结果：kb_9 的图检索**根本没被请求**，其图结果被静默丢弃；对外仍返回 code=200（用户与验收都看不到）

## 4) 触发条件
- graph_service.py:788「空间不存在」返回 code=500 且 data=None（无 result_data）；
- multiple_retrieval.py:retrieval_graph 用 milvus_data[""data""][""result_data""] 取键，None 直接抛；except 里 return 而非 continue，导致后续 KB 全部跳过。
