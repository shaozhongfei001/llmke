# R13 能力矩阵自检

总计 4/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=73 refs=3 rt=1 |
| FAQ | FAIL | http=200 status=2 resultType=1 answer='是的，客户访前准备是文档的主要内容之一。文档的第一段就提到了这一点。' refs=1 |
| GLOBAL | FAIL | http=200 status=2 cost=0.7s refs=1 ref_src示例=ct-loan.docx/V0/R12FIX-product-loan.docx |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | FAIL | http=500 status=500 数值=False 单位=False 主体=False 口径='授信/额度'=False refs=0 answer='' |
| GRAPH_LOCAL | PASS | http=200 docs=3 graph_docs=2 有正文的图块=2 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
