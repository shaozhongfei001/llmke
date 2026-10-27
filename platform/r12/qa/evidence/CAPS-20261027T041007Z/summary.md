# R13 能力矩阵自检

总计 4/12 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | FAIL | http=200 status=2 answer_len=68 refs=0 rt=1 |
| FAQ | FAIL | http=403 status=None resultType=None 尝试=3/3 answer='' refs=0 |
| GLOBAL_POS | FAIL |  http=403 status=None cost=0.0s refs=0 可解析=0（其中绝对URL=0 相对键=0）社区id=False src示例=None |
| GLOBAL_REFUSE/R1 | FAIL | http=403 status=None 拒答=False 编造数值=[] refs=0 answer='' |
| GLOBAL_REFUSE/R2 | FAIL | http=403 status=None 拒答=False 编造数值=[] refs=0 answer='' |
| GLOBAL_FAITH | FAIL | http=403 客户→加点实测={'江南装备': None, '华东精密': None, '北方重工': None} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={'江南装备': (None, '30'), '华东精密': (None, '60'), '北方重工': (None, '60')} 缺失数值=['30', '60'] |
| VERSION | FAIL | http=500 groups=0 多版本组=0 版本=[] ← 空列表不再算通过 |
| TABLE | FAIL | http=403 status=None 数值=False 单位=False 主体=False 口径='授信/额度'=False refs=0 answer='' |
| GRAPH_LOCAL | PASS | http=200 docs=3 含graph标记=2 有正文的图块=2 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 键存在=True violations_count=0 |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=1 | 小写(aaa)+开图 http=200 docs=3 graph块=1 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
