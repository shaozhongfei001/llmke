# R13 能力矩阵自检

总计 5/7 PASS

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=73 refs=3 rt=1 |
| FAQ | PASS | http=200 status=2 resultType=2 answer='不是，客户访前准备是文档的一部分内容，但不是主要部分。' refs=2 |
| GLOBAL | FAIL | http=200 status=2 cost=3.6s refs=5 ref_src示例= |
| VERSION | PASS | http=200 groups=1 版本示例=['V0', 'V0'] |
| TABLE | PASS | http=200 status=2 命中3000=True answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | FAIL | http=200 docs=3 graph_docs=0 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
