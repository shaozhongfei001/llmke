# R13 能力矩阵自检

总计 10/10 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GRAPH_LOCAL | PASS | http=200 docs=3 含graph标记=2 有正文的图块=2 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 块数=2 键存在=True violations_count=0 |
| GRAPH_PROVENANCE | PASS | http=200 块数=2 exact_chunk=2 provenance分布=['exact_chunk'] 抽查引用=2 命中索引={'kb_9': 2} 悬空=[] stale_version=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} pq字段=有 pk∩ES_id=0 strict=True 探针='智造贷 授信额度 票据贴现'/top_k=5 |
| GRAPH_VERSION_FRESH | PASS | 旧版本块=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} 明细=[] |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=2 | 小写(aaa)+开图 http=200 docs=3 graph块=2 |
| GLOBAL_POS | PASS |  http=200 status=2 cost=4.3s configId=1 refs=3 可解析=3 覆盖度(去重前缀)=2（绝对URL=0 相对键=3）社区id=True src示例=duct-loan.docx/V1/R12FIX-product-loan(1).docx infra(graph_pid=1461792,es_ok=True,9.2ms) |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='授信额度与票据贴现的关系在提供的事实中未提及，因此无法得出结论。[L0-92b533ae]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='海川电子材料股份有限公司被列为关注类，但事实中未提及需要计提多少比例的贷款损失准备。[L0-3c882b30]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_FAITH | PASS | 多数票=2/2 首次 http=200 首次实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] 各次=[{'江南装备': '30', '华东精密': '60', '北方重工': '60'}, {'江南装备': '30', '华东精密': '60', '北方重工': '60'}] infra(graph_pid=1461792,es_ok=True) |
| PARSE_EFFECTIVE | PASS | http=200 status=3文件=9 抽查=8 取不到块=[] 索引未更新=[] |
