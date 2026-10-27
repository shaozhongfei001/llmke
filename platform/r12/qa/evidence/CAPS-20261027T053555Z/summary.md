# R13 能力矩阵自检

总计 2/2 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GRAPH_PROVENANCE | PASS | http=200 块数=2 exact_chunk=2 provenance分布=['None'] 抽查引用=2 命中索引={'kb_9': 2} 悬空=[] stale_version=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} pq字段=缺失 pk∩ES_id=2 strict=True 探针='智造贷 授信额度 票据贴现'/top_k=5 |
| GRAPH_VERSION_FRESH | PASS | 旧版本块=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} 明细=[] |
