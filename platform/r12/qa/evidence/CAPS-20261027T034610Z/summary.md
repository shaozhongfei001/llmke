# R13 能力矩阵自检

总计 2/3 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| GRAPH_LOCAL | PASS | http=200 docs=4 含graph标记=4 有正文的图块=4 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 键存在=True violations_count=0 |
| GRAPH_UPPERCASE | FAIL | 大写(AAA)+开图 http=500 docs=0 graph块=0 | 小写(aaa)+开图 http=200 docs=3 graph块=2 ← 仅大写失败：开图检索对大写 ASCII 抛异常（检索层缺陷，非图算法无效） |
