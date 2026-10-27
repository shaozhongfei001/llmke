# R13 能力矩阵自检

总计 4/9 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=61 refs=3 rt=1 |
| FAQ | FAIL | http=200 status=2 resultType=1 answer='是的，客户访前准备是文档的主要内容之一。文档的第二段提到了日均存款金额，但客户访' refs=1 |
| GLOBAL | FAIL | http=200 status=2 cost=3.9s refs=0 ref_src示例=None |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | PASS | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=3 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GRAPH_LOCAL | FAIL | http=200 docs=3 含graph标记=0 有正文的图块=0 search_type示例=[['milvus', 'es', 'es'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es']] |
| GRAPH_IDENTITY | FAIL | 异常: ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=19529): Max retries exceeded with url: /query_graph_data (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x72c73abd3fa0>: Failed to establish a new connection: [Errno 111] Connection refused')) |
| GRAPH_UPPERCASE | FAIL | 大写(AAA)+开图 http=500 docs=0 graph块=0 | 小写(aaa)+开图 http=200 docs=3 graph块=2 ← 仅大写失败：开图检索对大写 ASCII 抛异常（检索层缺陷，非图算法无效） |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
