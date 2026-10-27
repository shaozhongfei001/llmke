# R14 断言自检 20261026T182704Z

- 结果：45/45 用例与期望一致
- 性质：函数级隔离验证（monkeypatch，不联网）。它只证明**断言有失败能力**，不证明产品通过；产品结论见 R14-BASELINE 证据。

| # | 目标 | 喂入数据 / 说明 | 期望 | 实测 | 判定 | 详情 |
|---|---|---|---|---|---|---|
| VERSION-1 | r13_full_check.cap_version | groups=[]（R13 实测假绿点：空版本列表） | FAIL | FAIL | 一致 | http=200 groups=0 多版本组=0 版本=[] ← 空列表不再算通过 |
| VERSION-2 | r13_full_check.cap_version | data=None（接口无数据） | FAIL | FAIL | 一致 | http=200 groups=0 多版本组=0 版本=[] ← 空列表不再算通过 |
| VERSION-3 | r13_full_check.cap_version | 一组两条但版本号相同 [V0,V0]（同名重复入库，不是两版冲突） | FAIL | FAIL | 一致 | http=200 groups=1 多版本组=0 版本=[] |
| VERSION-4 | r13_full_check.cap_version | 一组只有一条 [V0]（单版本，无冲突可区分） | FAIL | FAIL | 一致 | http=200 groups=1 多版本组=0 版本=[] |
| VERSION-5 | r13_full_check.cap_version | http=500 但 body 合规（故障不得当通过） | FAIL | FAIL | 一致 | http=500 groups=1 多版本组=1 版本=['V0', 'V1'] |
| VERSION-6 | r13_full_check.cap_version | 正例对照：一组含 V0/V1 两版 | PASS | PASS | 一致 | http=200 groups=1 多版本组=1 版本=['V0', 'V1'] |
| S7-1 | acceptance.s7 | data=None（R13 摘要实测：success=true 但无历史） | FAIL | FAIL | 一致 | http=200 data条数=0 含正文=False ← 空历史不算通过 |
| S7-2 | acceptance.s7 | data=[]（空历史） | FAIL | FAIL | 一致 | http=200 data条数=0 含正文=False ← 空历史不算通过 |
| S7-3 | acceptance.s7 | data=[{id:1}]（有记录但无正文） | FAIL | FAIL | 一致 | http=200 data条数=1 含正文=False ← 空历史不算通过 |
| S7-4 | acceptance.s7 | http=500 但 data 含正文（故障不得当通过） | FAIL | FAIL | 一致 | http=500 data条数=1 含正文=True ← 空历史不算通过 |
| S7-5 | acceptance.s7 | 正例对照：data 含真实问答正文 | PASS | PASS | 一致 | http=200 data条数=1 含正文=True |
| S6-1 | acceptance.s6 | records=[{content:""}]（空原文，R13 摘要"首块长度=0"仍 PASS） | FAIL | FAIL | 一致 | http=200 chunk数=1 首块长度=0 ← 空原文不算通过 |
| S6-2 | acceptance.s6 | records=[]（取不到任何块） | FAIL | FAIL | 一致 | http=200 chunk数=0 首块长度=0 ← 空原文不算通过 |
| S6-3 | acceptance.s6 | content/pageContent/page_content 全空 | FAIL | FAIL | 一致 | http=200 chunk数=1 首块长度=0 ← 空原文不算通过 |
| S6-4 | acceptance.s6 | http=500 但含正文 | FAIL | FAIL | 一致 | http=500 chunk数=1 首块长度=10 ← 空原文不算通过 |
| S6-5 | acceptance.s6 | 正例对照：正文在服务真实字段 content | PASS | PASS | 一致 | http=200 chunk数=1 首块长度=15 |
| S6-6 | acceptance.s6 | 引用无 metadata.source（"引用携带文件与定位信息"） | FAIL | FAIL | 一致 | 引用 source 数=0 示例=[] |
| S6-7 | acceptance.s6 | 正例对照：引用带 source | PASS | PASS | 一致 | 引用 source 数=1 示例=['kb_9/R12FIX-product-loan.docx'] |
| TABLE-1 | r13_full_check.cap_table | 答案含 3000 但主体错（"本季度市场预算是3000元"） | FAIL | FAIL | 一致 | http=200 status=2 数值=True 单位=False 主体=False 口径='授信/额度'=True refs=1 answer='本季度市场预算是3000元，与授信无关。' |
| TABLE-2 | r13_full_check.cap_table | 答案含 3000/万元/主体，但口径错（营收而非授信额度） | FAIL | FAIL | 一致 | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=False refs=1 answer='华东精密制造有限公司2025年营业收入为3000万元。' |
| TABLE-3 | r13_full_check.cap_table | 答案对但无引用（不可回填的结论不算证据） | FAIL | FAIL | 一致 | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=0 answer='华东精密制造有限公司的授信额度为3000万元。' |
| TABLE-4 | r13_full_check.cap_table | 答案无主体（"授信额度3000万元" 不知是谁的） | FAIL | FAIL | 一致 | http=200 status=2 数值=True 单位=True 主体=False 口径='授信/额度'=True refs=1 answer='授信额度3000万元。' |
| TABLE-5 | r13_full_check.cap_table | http=500 但答案文本对 | FAIL | FAIL | 一致 | http=500 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=1 answer='华东精密制造有限公司的授信额度为3000万元。' |
| TABLE-6 | r13_full_check.cap_table | 正例对照：数值+单位+主体+口径+引用齐备（= 02:24 真实答案） | PASS | PASS | 一致 | http=200 status=2 数值=True 单位=True 主体=True 口径='授信/额度'=True refs=1 answer='华东精密制造有限公司的授信额度为3000万元。' |
| GLOBAL-1 | r13_full_check.cap_global | 拒答话术「没有直接…的信息」+ 2 条干净 source（R13 实测即此形态） | FAIL | FAIL | 一致 | http=200 status=2 cost=0.0s refs=2 ref_src示例=kb_9/a.docx/0 |
| GLOBAL-2 | r13_full_check.cap_global | source 是重复拼接的 host（http://127.0.0.1:19000/http://…，浏览器无法解析） | FAIL | FAIL | 一致 | http=200 status=2 cost=0.0s refs=2 ref_src示例=/http://127.0.0.1:19000/r12-rag/a.docx/0 |
| GLOBAL-3 | r13_full_check.cap_global | 只有 1 条 source（单篇文档不足以支撑跨文档归纳） | FAIL | FAIL | 一致 | http=200 status=2 cost=0.0s refs=1 ref_src示例=kb_9/a.docx/0 |
| GLOBAL-4 | r13_full_check.cap_global | 答案过短且是拒答（"没有相关信息"） | FAIL | FAIL | 一致 | http=200 status=2 cost=0.0s refs=2 ref_src示例=kb_9/a.docx/0 |
| GLOBAL-5 | r13_full_check.cap_global | 正例对照：长答案 + 2 条可解析 source | PASS | PASS | 一致 | http=200 status=2 cost=0.0s refs=2 ref_src示例=kb_9/a.docx/0 |
| GRAPH_LOCAL-1 | r13_full_check.cap_graph_local | 图块 metadata 含 graph 但正文为空（无法回填原文） | FAIL | FAIL | 一致 | http=200 docs=1 graph_docs=1 有正文的图块=0 |
| GRAPH_LOCAL-2 | r13_full_check.cap_graph_local | http=500 但文档列表非空 | FAIL | FAIL | 一致 | http=500 docs=1 graph_docs=1 有正文的图块=1 |
| GRAPH_LOCAL-3 | r13_full_check.cap_graph_local | 正例对照：图块带非空正文 | PASS | PASS | 一致 | http=200 docs=1 graph_docs=1 有正文的图块=1 |
| INTERNAL_GUARD-1 | r13_full_check.cap_internal_guard | 内部回写入口返回 200（未鉴权放行） | FAIL | FAIL | 一致 | callback=200 uploadParsedFile=403 |
| INTERNAL_GUARD-2 | r13_full_check.cap_internal_guard | 内部回写入口返回 500（故障不得当"已拒绝"） | FAIL | FAIL | 一致 | callback=500 uploadParsedFile=403 |
| INTERNAL_GUARD-3 | r13_full_check.cap_internal_guard | 正例对照：两个入口均 403 | PASS | PASS | 一致 | callback=403 uploadParsedFile=403 |
| DENIED-1 | security_acceptance.denied | denied(500, {"success": false})（R13 实测返回 True，一般故障被当拒绝） | FAIL | FAIL | 一致 | denied(...) = False |
| DENIED-2 | security_acceptance.denied | denied(0, {"success": false})（连接中断/超时） | FAIL | FAIL | 一致 | denied(...) = False |
| DENIED-3 | security_acceptance.denied | denied(None, {"success": false})（取不到状态码） | FAIL | FAIL | 一致 | denied(...) = False |
| DENIED-4 | security_acceptance.denied | denied(200, {"success": false, "errorCode": "99999"})（业务报错≠鉴权拒绝） | FAIL | FAIL | 一致 | denied(...) = False |
| DENIED-5 | security_acceptance.denied | denied(200, {"success": false})（无明确鉴权错误码） | FAIL | FAIL | 一致 | denied(...) = False |
| DENIED-6 | security_acceptance.denied | 正例对照：denied(403, …) | PASS | PASS | 一致 | denied(...) = True |
| DENIED-7 | security_acceptance.denied | 正例对照：denied(200, {"errorCode": "30016"})（网关明确鉴权错误码） | PASS | PASS | 一致 | denied(...) = True |
| DENIED-8 | security_acceptance.denied | 正例对照：denied(200, {"errorCode": 30017})（整型错误码） | PASS | PASS | 一致 | denied(...) = True |
| SQL-1 | security_acceptance.sql | mysql 退出码 1（口令检查容器/查询失败）-> 必须抛错而不是返回空串 | FAIL | FAIL | 一致 | 抛出 RuntimeError: sql failed rc=1: ERROR 2003 (HY000): Can't connect（期望如此） |
| SQL-2 | security_acceptance.sql | 正例对照：退出码 0 -> 原样返回 | PASS | PASS | 一致 | 返回 'admin\t$2a$' |
