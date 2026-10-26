# R13 能力矩阵自检

总计 6/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=71 refs=3 rt=1 |
| FAQ | PASS | http=200 status=2 resultType=2 answer='不是，客户访前准备是文档的一部分内容，但不是主要部分。' refs=2 |
| GLOBAL | FAIL | http=200 status=2 cost=2.8s refs=5 ref_src示例= |
| VERSION | PASS | http=200 groups=0 |
| TABLE | PASS | http=200 status=2 命中3000=True answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | PASS | http=200 docs=3 graph_docs=1 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
