# R13 能力矩阵自检

总计 15/16 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| PARSE_QUEUE_STALL | PASS | 队列分布={'PENDING(1)':0,'DEAL_ING(2)':0,'RETRY_ING(3)':0,'成功(4)':376,'失败(5)':51} status=99合计=0 其中超5分钟未推进=0 最老PENDING=None分钟 判定=队列健康 |
| NORMAL | PASS | http=200 status=2 answer_len=73 refs=3 rt=1 |
| FAQ | PASS | http=200 status=2 resultType=2 尝试=1/3 answer='不是，客户访前准备是文档的一部分内容，但不是主要部分。' refs=2 |
| GLOBAL_POS | PASS |  http=200 status=2 cost=3.9s configId=1 refs=3 可解析=3 覆盖度(去重前缀)=2（绝对URL=0 相对键=3）社区id=True src示例=duct-loan.docx/V1/R12FIX-product-loan(1).docx infra(graph_pid=1461792,es_ok=True,29.9ms) |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='授信额度与票据贴现的关系在提供的事实中未提及，因此无法得出具体关系。[L0-92b533ae]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' infra(graph_pid=1461792,es_ok=True) |
| GLOBAL_FAITH | PASS | 多数票=2/2 首次 http=200 首次实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] 各次=[{'江南装备': '30', '华东精密': '60', '北方重工': '60'}, {'江南装备': '30', '华东精密': '60', '北方重工': '60'}] infra(graph_pid=1461792,es_ok=True) |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] parent一致前置=有 |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=3 含graph标记=2 有正文的图块=2 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 块数=2 键存在=True violations_count=0 |
| GRAPH_PROVENANCE | PASS | http=200 块数=2 exact_chunk=2 provenance分布=['exact_chunk'] 抽查引用=2 命中索引={'kb_9': 2} 悬空=[] stale_version=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} pq字段=有 pk∩ES_id=0 strict=True 探针='智造贷 授信额度 票据贴现'/top_k=5 |
| GRAPH_VERSION_FRESH | PASS | 旧版本块=0 最新版本={'R12FIX-product-loan.docx': 'V1', 'R12FIX-product-intro.pptx': 'V1'} 明细=[] |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=2 | 小写(aaa)+开图 http=200 docs=3 graph块=2 |
| PARSE_EFFECTIVE | FAIL | http=500 status=3文件=0 抽查=0 取不到块=[] 索引未更新=[] |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
