# 检索层 order_num 每请求随机（跨请求不可对账）

采集：2026-10-27T11:20:04+08:00；同一 query 连续两次 POST 19995/retrieval_documents（kb_9, enabled_graph=true, rerank/faq=false, top_k=5）

## 实测
```
请求1  pk 1689901252393637717  order_num 2731322325943537746  st [milvus, es, es, graph]
请求1  pk 2107837105731089944  order_num 2170415455900260032  st [milvus, graph]
请求2  pk 1689901252393637717  order_num 3184086112846778709  st [milvus, es, es, graph]
请求2  pk 2107837105731089944  order_num 1179646822323273520  st [milvus, graph]
```

## 判读
- **同一批 chunk（pk 完全相同、顺序相同）**，但 `order_num` 两次完全不同 → 它由 `retrieval_fun_tool.py:491 order_num = str(create_uuid())` 每次请求现造，不是存储身份。
- 因此：任何以 `order_num` / `[retrive-tag id=…]` 为键做**跨请求**比较（例如开图/关图引用交集）的度量，**结构上恒为 0**，与图是否生效无关。
- 可用的稳定对账键：文档顶层 `pk`（ES `_id`/Milvus pk，实测稳定）或 `(metadata.id=document_id, metadata.chunk_index)`。
- 注意 metadata 内 `pk` 字段被检索层白名单丢弃，pk 只在**文档顶层**返回；`title`/`search` 同样被丢（见 retrieval_metadata_whitelist_before.md）。
