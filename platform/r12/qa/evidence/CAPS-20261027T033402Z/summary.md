# R13 能力矩阵自检

总计 5/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=22 refs=3 rt=1 |
| FAQ | FAIL | http=200 status=2 resultType=1 answer='是的，客户访前准备是文档的主要内容之一。文档还提到了其他信息，如日均存款为 2,' refs=1 |
| GLOBAL | FAIL | http=200 status=2 cost=1.1s refs=1 ref_src示例=ct-loan.docx/V0/R12FIX-product-loan.docx |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=4 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=5 graph_docs=5 有正文的图块=5 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
