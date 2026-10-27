# R13 能力矩阵自检

总计 4/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | FAIL | http=200 status=3 answer_len=16 refs=0 rt=None |
| FAQ | PASS | http=200 status=2 resultType=2 answer='不是，客户访前准备是文档的一部分内容，但不是主要部分。' refs=2 |
| GLOBAL | FAIL | http=200 status=2 cost=3.4s refs=5 ref_src示例=ct-loan.docx/V0/R12FIX-product-loan.docx |
| VERSION | PASS | http=200 groups=1 多版本组=1 版本=['V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | FAIL | http=200 docs=3 graph_docs=0 有正文的图块=0 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
