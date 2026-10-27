# R13 能力矩阵自检

总计 1/3 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| PARSE_EFFECTIVE | FAIL | http=200 status=3文件=9 抽查=8 取不到块=[] 索引未更新=[{'fileId': '328', 'name': 'R12FIX-product-loan(1).docx', 'latest_create_time': '2026-10-27 13:25:55.428683', 'since': '2026-10-27T13:20:00'}, {'fileId': '290', 'name': 'R12FIX-product-loan.docx', 'latest_create_time': '2026-10-27 13:25:49.049291', 'since': '2026-10-27T13:20:00'}] ← 解析成功但 ES create_time 未更新（索引未生效） |
| GRAPH_PROVENANCE | FAIL | http=200 块数=2 exact_chunk=0 provenance分布=['None'] 抽查引用=2 命中索引={'kb_9': 2} 悬空=[] stale_version=0 最新版本={} strict=False 探针='智造贷 授信额度 票据贴现'/top_k=5 ← 数据代次悬空：图 chunk_pk_list 与当前 ES _id 无交集（需重解析+重建图） |
| GRAPH_VERSION_FRESH | PASS | 旧版本块=0 最新版本={} 明细=[] |
