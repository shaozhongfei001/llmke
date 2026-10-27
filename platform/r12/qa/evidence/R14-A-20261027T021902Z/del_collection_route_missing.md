# 19526 缺少 /del_collection 路由（社区摘要 Milvus 侧从未被删除过的直接原因）

采集：2026-10-27T11:34:24+08:00

## 事实
```
GET 19526/openapi.json 的 paths（改造前）：
  /create_milvus_collection /create_milvus_db /create_milvus_index /del_doc_by_col
  /del_doc_entity /get_doc_by_col /get_doc_page /insert_vector_documents_custom
  /migrate_milvus_collection /milvus_vector_search /static_count /update_by_id
  /update_by_id_batch /update_doc
  → 没有 /del_collection
```
`graph_summary.del_community()` 一直 POST `/del_collection`（ES del_index + Milvus del_collection 双写）：
- ES 侧命中（/del_index 存在）→ 索引被删；
- Milvus 侧 404 → 被调用方当"已执行"记进明细 → **集合从未被删**；
- 这正是 R13 观测到的「ES 7 条 / Milvus 65 条」的一个直接原因（另一原因是每次重建都用随机 pk 追加）。

## 处置（R14-A 补齐，我的域 index_vector_service）
- `milvus_kb_service.del_collection()`：名称经 `generate_collection_name_uuid()` 归一（与写入口径一致）、不存在时幂等返回 `dropped=false`；
- `view/api/del_collection_view.py` + `view/urls.py` 注册 `/del_collection`；
- 实测：
```
insert r12a_del_probe            -> code 200, insert_count 1
POST /del_collection  第 1 次     -> code 200, {"collection_name":"_r12a_del_probe","dropped":true}
POST /del_collection  第 2 次     -> code 200, dropped=false（幂等）
utility.has_collection("_r12a_del_probe") -> False
```
