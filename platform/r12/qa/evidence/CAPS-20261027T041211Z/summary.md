# R13 能力矩阵自检

总计 12/12 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=73 refs=3 rt=1 |
| FAQ | PASS | http=200 status=2 resultType=2 尝试=2/3 answer='是的，文档的结构包含客户访前准备在第一段，日均存款在第二段。' refs=2 |
| GLOBAL_POS | PASS |  http=200 status=2 cost=4.4s refs=3 可解析=3（其中绝对URL=3 相对键=0）社区id=True src示例=product-loan.docx/V0/R12FIX-product-loan.docx |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='授信额度与票据贴现的关系在提供的事实中未提及，因此无法得出结论。[L0-18625408]' |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' |
| GLOBAL_FAITH | PASS | http=200 客户→加点实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=3 含graph标记=2 有正文的图块=2 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 键存在=True violations_count=0 |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=1 | 小写(aaa)+开图 http=200 docs=3 graph块=1 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
