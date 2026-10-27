# R13 能力矩阵自检

总计 2/3 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| FAQ | PASS | http=200 status=2 resultType=2 answer='是的，文档的结构包含客户访前准备在第一段，日均存款在第二段。' refs=2 |
| GLOBAL | FAIL | http=200 status=2 cost=1.4s refs=1 ref_src示例=ct-loan.docx/V0/R12FIX-product-loan.docx |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=2 | 小写(aaa)+开图 http=200 docs=3 graph块=2 |
