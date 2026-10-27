# R13 能力矩阵自检

总计 10/13 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=61 refs=3 rt=1 |
| FAQ | PASS | http=200 status=2 resultType=2 尝试=1/3 answer='不是，客户访前准备是文档的一部分内容，但不是主要部分。' refs=2 |
| GLOBAL_POS | FAIL |  http=200 status=2 cost=3.9s configId=1 refs=1 可解析=1（绝对URL=0 相对键=1）社区id=True src示例=product-loan.docx/V0/R12FIX-product-loan.docx |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-18625408]' |
| GLOBAL_REFUSE/R2 | FAIL | http=500 status=None 拒答=False 编造数值=[] refs=0 answer='' |
| GLOBAL_FAITH | PASS | 多数票=2/2 首次 http=200 首次实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] 各次=[{'江南装备': '30', '华东精密': '60', '北方重工': '60'}, {'江南装备': '30', '华东精密': '60', '北方重工': '60'}] |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=3 含graph标记=2 有正文的图块=2 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 块数=4 键存在=True violations_count=0 |
| GRAPH_PROVENANCE | FAIL | http=200 块数=4 exact_chunk=0 provenance分布=['entity_content_recovered'] 抽查引用=4 悬空=[] ← 数据代次悬空：图 chunk_pk_list 与当前 ES _id 无交集（需重解析+重建图） |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=2 | 小写(aaa)+开图 http=200 docs=3 graph块=2 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
