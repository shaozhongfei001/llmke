# R13 能力矩阵自检

总计 0/1 PASS（另有 INFO 1 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GRAPH_PROVENANCE | FAIL | http=200 块数=4 exact_chunk=0 provenance分布=['entity_content_recovered'] 抽查引用=4 命中索引={'kb_9': 4} 悬空=[] stale_version=2 最新版本={'R12FIX-product-intro.pptx': 'V1', 'R12FIX-product-loan.docx': 'V1'} ← 数据代次悬空：图 chunk_pk_list 与当前 ES _id 无交集（需重解析+重建图） |
| GRAPH_VERSION_FRESH | INFO | 旧版本块=2 最新版本={'R12FIX-product-intro.pptx': 'V1', 'R12FIX-product-loan.docx': 'V1'} 明细=[{'name': 'R12FIX-product-intro.pptx', 'version': 'V0', 'latest': 'V1', 'source': 'oduct-intro.pptx/V0/R12FIX-product-intro.pptx'}, {'name': 'R12FIX-product-loan.docx', 'version': 'V0', 'latest': 'V1', 'source': 'product-loan.docx/V0/R12FIX-product-loan.docx'}] ← exact_chunk 可能已达标但混入旧版本（语义错，非数字错） |
