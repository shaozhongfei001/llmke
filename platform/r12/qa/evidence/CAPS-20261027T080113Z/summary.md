# R13 能力矩阵自检

总计 9/9 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GLOBAL_POS | PASS |  http=200 status=2 cost=3.8s configId=1 refs=2 可解析=2 覆盖度(去重前缀)=2（绝对URL=0 相对键=2）社区id=True src示例=duct-loan.docx/V1/R12FIX-product-loan(1).docx infra(graph_pid=1461792,es_ok=True,7.8ms) |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-18625408]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_FAITH | PASS | 多数票=2/2 首次 http=200 首次实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] 各次=[{'江南装备': '30', '华东精密': '60', '北方重工': '60'}, {'江南装备': '30', '华东精密': '60', '北方重工': '60'}] infra(graph_pid=1461792,es_ok=True) |
| GRAPH_LOCAL | PASS | http=200 docs=3 含graph标记=2 有正文的图块=2 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 块数=2 键存在=True violations_count=0 |
| GRAPH_PROVENANCE | PASS | http=200 块数=2 exact_chunk=2 provenance分布=['exact_chunk'] 抽查引用=2 命中索引={'kb_9': 2} 悬空=[] stale_version=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} pq字段=有 pk∩ES_id=0 strict=True 探针='智造贷 授信额度 票据贴现'/top_k=5 |
| GRAPH_VERSION_FRESH | PASS | 旧版本块=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} 明细=[] |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=2 | 小写(aaa)+开图 http=200 docs=3 graph块=2 |
