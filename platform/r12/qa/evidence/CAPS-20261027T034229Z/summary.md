# R13 能力矩阵自检

总计 6/9 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=63 refs=3 rt=1 |
| FAQ | FAIL | http=200 status=2 resultType=1 answer='是的，客户访前准备是文档的主要内容之一。文档的第二部分提到了日均存款金额，但客户' refs=1 |
| GLOBAL | FAIL | http=200 status=2 cost=1.0s refs=1 ref_src示例=ct-loan.docx/V0/R12FIX-product-loan.docx |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=3 graph_docs=3 有正文的图块=3 |
| GRAPH_IDENTITY | PASS | http=200 code=200 键存在=True violations_count=0 |
| GRAPH_UPPERCASE | FAIL | 大写(AAA)+开图 http=500 小写(aaa)+开图 http=200（成对：两者都必须 200） ← 仅大写失败：开图检索对大写 ASCII 抛异常（检索层缺陷，非图算法无效） |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
