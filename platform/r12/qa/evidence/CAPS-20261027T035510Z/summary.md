# R13 能力矩阵自检

总计 9/12 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| NORMAL | PASS | http=200 status=2 answer_len=73 refs=3 rt=1 |
| FAQ | FAIL | http=200 status=2 resultType=1 answer='客户访前准备是否是文档的主要内容，取决于文档的类型和目的。如果文档是为了记录和指' refs=0 |
| GLOBAL_POS | FAIL |  http=200 status=2 cost=3.2s refs=0 可解析=0（其中绝对URL=0 相对键=0）社区id=False src示例=None |
| GLOBAL_REFUSE/R1 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='授信额度与票据贴现的关系在提供的事实中未提及，因此无法得出结论。[L0-18625408]' |
| GLOBAL_REFUSE/R2 | PASS | http=200 status=2 拒答=True 编造数值=[] refs=1 answer='事实中未提及 [L0-3c882b30]' |
| GLOBAL_FAITH | PASS | http=200 客户→加点实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] |
| VERSION | PASS | http=200 groups=2 多版本组=2 版本=['V1', 'V0', 'V1', 'V0'] |
| TABLE | FAIL | http=200 status=2 数值=False 单位=True 主体=True 口径='授信/额度'=True refs=2 answer='步核实。目前的信息未能直接提供该企业的授信额度。\n\n若需了解具体额度，建议直接咨询相关金融机构或查阅企业的详细贷款协议。' |
| GRAPH_LOCAL | PASS | http=200 docs=4 含graph标记=4 有正文的图块=4 search_type示例=[['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es', 'graph'], ['milvus', 'es', 'es', 'graph']] |
| GRAPH_IDENTITY | PASS | http=200 code=200 reason=None 键存在=True violations_count=0 |
| GRAPH_UPPERCASE | PASS | 大写(AAA)+开图 http=200 docs=3 graph块=2 | 小写(aaa)+开图 http=200 docs=3 graph块=2 |
| INTERNAL_GUARD | PASS | callback=401 uploadParsedFile=401 |
