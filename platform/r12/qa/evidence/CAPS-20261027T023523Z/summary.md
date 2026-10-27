# R13 能力矩阵自检

总计 4/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=61 refs=3 rt=1 |
| FAQ | FAIL | http=200 status=2 resultType=1 answer='是的，客户访前准备是文档的主要内容之一。文档的第二段提到了日均存款金额，但第一段' refs=1 |
| GLOBAL | FAIL | http=200 status=2 cost=4.0s refs=0 ref_src示例=None |
| VERSION | PASS | http=200 groups=1 多版本组=1 版本=['V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | FAIL | http=200 docs=3 graph_docs=0 有正文的图块=0 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
