# kb_9 最终代次（FIX-18 生效后）

时间：2026-10-27 13:27；种子：`create_chunk_pk = chunk|index|file_id|seq|sha1(text)`（无 document_id）

## 1. 13 条最终清单（7 个文件 + 台账，共 13 块）

| index | file_id | version | chunk | _id |
|---|---|---|---|---|
| kb_9 | 290 | V0 | 0 | 897762163454970252 |
| kb_9 | 328 | V1 | 0 | 139363536840301567 |
| kb_9 | 330 | V0 | 0 | 1117439109309760356 |
| kb_9 | 331 | V0 | 0 | 409753011178200524 |
| kb_9 | 331 | V0 | 1 | 683665258912140235 |
| kb_9 | 332 | V0 | 0 | 989645615430072466 |
| kb_9 | 333 | V0 | 0 | 984477748032687541 |
| kb_9 | 334 | V0 | 0 | 366245621242201281 |
| kb_9 | 343 | V1 | 0 | 626225001556669433 |
| table_chunks_kb_9 | 329 | V0 | 0 | 1095912197551331871 |
| table_chunks_kb_9 | 333 | V0 | 1 | 177410851220727056 |
| table_summary_kb_9 | 329 | V0 | -1 | 1137902847478273881 |
| table_summary_kb_9 | 333 | V0 | -1 | 885155839145947657 |

## 2. 校验

```
ES==Milvus 逐条：kb_9 9/9、table_chunks 2/2、table_summary 2/2，es_only=[] mv_only=[]  -> ALL_MATCH
version 非空：13/13
table file_id：{329, 333}（台账=329，docx-table=333；台账已从 314 归一）
V0 保留：290、330 均在 ES 与 Milvus 中（未删）
9 条 kb_9 的 _id 与"index+file_id+seq+sha1(内容)"预演值逐条相同 -> 证明 document_id 已不在种子里
```

## 3. 本轮事故（必须记住的教训）

`13:23:59` / `13:24:03` 两个索引服务被**再次重启**，正好落在重解析窗口中间：
```
13:23:49~13:24:00  server.indexing_utils: 请求失败: All connection attempts failed,
                   URL: http://127.0.0.1:19527/insert_fulltext_documents
```
后果：那一轮 9 个文件里 7 个"解析成功但索引失败"，而 `POST /parse_sync` 仍返回
`task_statuses[*].success=true` —— **又一个"HTTP 200 假成功"**，只有翻日志才能发现。
处置：服务恢复后整批重跑（`reparse_kb9_cur_seed18c.json`），本次 9 个文件全部成功、`parse_failed=[]`。

## 4. 兜底打点（B 的观察项）

```
13:27:08  document_version: blocks=5 其中靠 source 路径兜底=5 无版本行=0
```
仍未归 0：`fid=329` 仅 milvus 命中，而 Milvus schema 无 version 列 → 必然兜底。
需 C 在合并处用 ES 的 version 回填（或 Milvus 加列，P2）。
