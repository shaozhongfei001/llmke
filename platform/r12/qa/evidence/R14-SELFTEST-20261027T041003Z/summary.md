# R14 断言自检 20261027T041003Z

- 结果：87/87 用例与期望一致
- 性质：函数级隔离验证（monkeypatch，不联网）。它只证明**断言有失败能力**，不证明产品通过；产品结论见 R14-BASELINE 证据。

| # | 目标 | 喂入数据 / 说明 | 期望 | 实测 | 判定 | 详情 |
|---|---|---|---|---|---|---|
| VERSION-1 | r13_full_check.cap_version | groups=[]（R13 实测假绿点：空版本列表） | FAIL | FAIL | 一致 | http=200 groups=0 多版本组=0 版本=[] ← 空列表不再算通过 |
| VERSION-2 | r13_full_check.cap_version | data=None（接口无数据） | FAIL | FAIL | 一致 | http=200 groups=0 多版本组=0 版本=[] ← 空列表不再算通过 |
| VERSION-3 | r13_full_check.cap_version | 一组两条但版本号相同 [V0,V0]（同名重复入库，不是两版冲突） | FAIL | FAIL | 一致 | http=200 groups=1 多版本组=0 版本=[] |
| VERSION-4 | r13_full_check.cap_version | 一组只有一条 [V0]（单版本，无冲突可区分） | FAIL | FAIL | 一致 | http=200 groups=1 多版本组=0 版本=[] |
| VERSION-5 | r13_full_check.cap_version | http=500 但 body 合规（故障不得当通过） | FAIL | FAIL | 一致 | http=500 groups=1 多版本组=1 版本=['V0', 'V1'] |
| VERSION-6 | r13_full_check.cap_version | 正例对照：一组含 V0/V1 两版 | PASS | PASS | 一致 | http=200 groups=1 多版本组=1 版本=['V0', 'V1'] |
| S7-1 | acceptance.s7 | data=None（R13 摘要实测：success=true 但无历史） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=0 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-2 | acceptance.s7 | data=[]（空历史） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=0 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-3 | acceptance.s7 | data=[{id:1}]（有记录但无正文） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=1 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-4 | acceptance.s7 | http=500 但 data 含正文（故障不得当通过） | FAIL | FAIL | 一致 | http=500 session=kb_9 问答对数=1 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-5 | acceptance.s7 | 正例对照：服务真实结构 data={queryReplyPairList:[{query,reply}]} 且问答均有正文 | PASS | PASS | 一致 | http=200 session=kb_9 问答对数=1 问与答均有正文=True 本轮queryId=None 命中=False |
| S7-6 | acceptance.s7 | data={queryReplyPairList: []}（会话存在但没有任何问答对） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=0 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-7 | acceptance.s7 | 问答对里 reply 正文为空（只存了问题没存答案，R14-F01b 收紧点） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=1 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-8 | acceptance.s7 | 问答对里 query 正文为空（只有答案没有提问，无法证明是同一轮问答） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=1 问与答均有正文=False 本轮queryId=None 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7-9 | acceptance.s7 | 正例对照：历史里存在本轮 queryId 的问答对且回答非空 | PASS | PASS | 一致 | http=200 session=kb_9 问答对数=1 问与答均有正文=True 本轮queryId=q-THIS-ROUND 命中=True |
| S7-10 | acceptance.s7 | 只有旧 queryId 的历史（本轮提问未落库，历史再多也不算通过） | FAIL | FAIL | 一致 | http=200 session=kb_9 问答对数=2 问与答均有正文=True 本轮queryId=q-THIS-ROUND 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
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
| FAQ-1 | r13_full_check.cap_faq | 正例对照：首次即 resultType=2（FAQ 直答） | PASS | PASS | 一致 | http=200 status=2 resultType=2 尝试=1/3 answer='是的，客户访前准备在第一段。' refs=1 |
| FAQ-2 | r13_full_check.cap_faq | 前两次 resultType=1、第三次=2（LLM 选择器抖动）→ 有重试就应 PASS | PASS | PASS | 一致 | http=200 status=2 resultType=2 尝试=3/3 answer='是的，客户访前准备在第一段。' refs=0 |
| FAQ-3 | r13_full_check.cap_faq | 3 次都 resultType=1（从未走 FAQ 直答）→ 必须 FAIL，重试不得变假绿 | FAIL | FAIL | 一致 | http=200 status=2 resultType=1 尝试=3/3 answer='普通回答' refs=0 |
| FAQ-4 | r13_full_check.cap_faq | 3 次都 http=500 → 必须 FAIL（故障不得当通过） | FAIL | FAIL | 一致 | http=500 status=None resultType=None 尝试=3/3 answer='' refs=0 |
| GLOBAL-1 | r13_full_check.cap_global | 正例题却答成拒答（没有 [L0- 社区 id）→ 不得当通过 | FAIL | FAIL | 一致 |  http=200 status=2 cost=0.0s refs=2 可解析=2（其中绝对URL=0 相对键=2）社区id=False src示例=r12-rag/kb_9/a.docx/V0/a.docx |
| GLOBAL-2 | r13_full_check.cap_global | source 重复拼接 host（http://h/http://h/…）→ 不可解析 | FAIL | FAIL | 一致 |  http=200 status=2 cost=0.0s refs=2 可解析=1（其中绝对URL=0 相对键=1）社区id=True src示例=r12-rag/kb_9/b.docx/V0/b.docx |
| GLOBAL-3 | r13_full_check.cap_global | 只有 1 条 source（跨文档归纳至少 2 条） | FAIL | FAIL | 一致 |  http=200 status=2 cost=0.0s refs=1 可解析=1（其中绝对URL=0 相对键=1）社区id=True src示例=r12-rag/kb_9/a.docx/V0/a.docx |
| GLOBAL-4 | r13_full_check.cap_global | 两条 source 都是重复拼接 host → 全部不可解析 | FAIL | FAIL | 一致 |  http=200 status=2 cost=0.0s refs=2 可解析=0（其中绝对URL=0 相对键=0）社区id=True src示例=None |
| GLOBAL-6 | r13_full_check.cap_global | 正例对照：单 host 绝对 URL（合法形态，R14-F01j 实测修正，不得判不可解析） | PASS | PASS | 一致 |  http=200 status=2 cost=0.0s refs=2 可解析=2（其中绝对URL=2 相对键=0）社区id=True src示例=127.0.0.1:19000/r12-rag/kb_9/a.docx/V0/a.docx |
| GLOBAL-5 | r13_full_check.cap_global | 正例对照：≥2 条可解析 source + 出现社区 id（不判措辞/行数） | PASS | PASS | 一致 |  http=200 status=2 cost=0.0s refs=2 可解析=2（其中绝对URL=0 相对键=2）社区id=True src示例=r12-rag/kb_9/a.docx/V0/a.docx |
| GREFUSE-1 | r13_full_check.cap_global_refuse | 正例对照：拒答且未出现任何具体数值（引用数不设下限） | PASS | PASS | 一致 | http=200 status=2 拒答=True 编造数值=[] refs=0 answer='提供的资料中未提及票据贴现与授信额度的关系，无法确定。' |
| GREFUSE-2 | r13_full_check.cap_global_refuse | 拒答话术里夹带编造数值（"AAA 加 15 个基点"）→ 必须 FAIL（B 实测过的回归） | FAIL | FAIL | 一致 | http=200 status=2 拒答=True 编造数值=['15 个基点'] refs=0 answer='资料未提及，但按行业惯例 AAA 加 15 个基点。' |
| GREFUSE-3 | r13_full_check.cap_global_refuse | 不拒答且直接给数值（R2 计提比例被编造）→ 必须 FAIL | FAIL | FAIL | 一致 | http=200 status=2 拒答=False 编造数值=['2%'] refs=0 answer='关注类需要计提 2% 的贷款损失准备。' |
| GFAITH-1 | r13_full_check.cap_global_faith | 正例对照：答案与原文一致（AAA→30 个基点、AA→60 个基点） | PASS | PASS | 一致 | http=200 客户→加点实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] |
| GFAITH-2 | r13_full_check.cap_global_faith | 答案与上下文矛盾（AAA→100 个基点）→ 忠实度 FAIL（A 实测过 100/60 形态） | FAIL | FAIL | 一致 | http=200 客户→加点实测={'江南装备': '100', '华东精密': '60', '北方重工': None} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={'江南装备': ('100', '30'), '北方重工': (None, '60')} 缺失数值 |
| GFAITH-3 | r13_full_check.cap_global_faith | 正例对照：评级句与加点句分开表述（实测真实形态），映射 30/60/60 正确即 PASS | PASS | PASS | 一致 | http=200 客户→加点实测={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 期望={'江南装备': '30', '华东精密': '60', '北方重工': '60'} 不符={} 缺失数值=[] |
| GRAPH_LOCAL-1 | r13_full_check.cap_graph_local | search_type 含 graph 但正文为空（无法回填原文） | FAIL | FAIL | 一致 | http=200 docs=1 含graph标记=1 有正文的图块=0 search_type示例=[['milvus', 'graph']] |
| GRAPH_LOCAL-2 | r13_full_check.cap_graph_local | http=500 但文档列表非空 | FAIL | FAIL | 一致 | http=500 docs=1 含graph标记=1 有正文的图块=1 search_type示例=[['milvus', 'graph']] |
| GRAPH_LOCAL-3 | r13_full_check.cap_graph_local | 正例对照：search_type 含 graph 且正文非空 | PASS | PASS | 一致 | http=200 docs=1 含graph标记=1 有正文的图块=1 search_type示例=[['milvus', 'es', 'graph']] |
| GRAPH_LOCAL-4 | r13_full_check.cap_graph_local | 正文非空但 search_type 不含 graph（只是普通向量/全文命中，不得当"图参与"） | FAIL | FAIL | 一致 | http=200 docs=1 含graph标记=0 有正文的图块=0 search_type示例=[['milvus', 'es']] |
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
| ONLY-1 | acceptance.plan | --only S6,S7 必须解析为"要执行 S6/S7"（旧实现两者都会落空 → 0 用例） | PASS | PASS | 一致 | plan('S6,S7')=(['S6', 'S7'], []) |
| ONLY-2 | acceptance.plan | --only S99 必须被识别为未知场景（不得静默当成全量/空跑） | PASS | PASS | 一致 | plan('S99')=([], ['S99']) |
| ONLY-3 | acceptance.plan | 空 --only = 全量场景（顺序固定） | PASS | PASS | 一致 | plan('')=(['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'], []) |
| COVERAGE-1 | acceptance.check_coverage | 选中 S6/S7 但只执行了 S6 → 必须判"未覆盖"（选中未执行=失败） | FAIL | FAIL | 一致 | 选中=['S6', 'S7'] 实际执行=['S6'] 未执行=['S7'] 未知场景=[] |
| COVERAGE-2 | acceptance.check_coverage | 正例对照：选中的场景全部执行（多余的前置 PREP 不影响判定） | PASS | PASS | 一致 | 选中=['S6', 'S7'] 实际执行=['PREP', 'S6', 'S7'] 未执行=[] 未知场景=[] |
| COVERAGE-3 | acceptance.check_coverage | --only 里有不存在的场景（S99）时覆盖判定也必须 FAIL（不能"选中=[] 就已覆盖"） | FAIL | FAIL | 一致 | 选中=[] 实际执行=[] 未执行=[] 未知场景=['S99'] |
| GID-1 | r13_full_check.cap_graph_identity | 正例对照：200 且含 identity_violations*/count=0 | PASS | PASS | 一致 | http=200 code=200 reason=None 键存在=True violations_count=0 |
| GID-2 | r13_full_check.cap_graph_identity | 200 但缺 identity 键（不得用默认 0 当通过） | FAIL | FAIL | 一致 | http=200 code=200 reason=None 键存在=False violations_count=None ← 200 缺键不得当 0 |
| GID-3 | r13_full_check.cap_graph_identity | 200 但 identity_violations_count=2（chunk_pk_list 与社区摘要混用） | FAIL | FAIL | 一致 | http=200 code=200 reason=None 键存在=True violations_count=2 |
| GID-4 | r13_full_check.cap_graph_identity | http=500（非 200 不得当通过，identity 无法验证） | FAIL | FAIL | 一致 | http=500 code=500 reason=None 键存在=False violations_count=None ← 非 200/非 code=200 且无 reason：identity 无法验证，不计入图算法结论 |
| GUP-1 | r13_full_check.cap_graph_uppercase | 大写查询 500 / 小写 200（开图对大写 ASCII 抛异常） | FAIL | FAIL | 一致 | 大写(AAA)+开图 http=500 docs=1 graph块=1 | 小写(aaa)+开图 http=200 docs=1 graph块=1 ← 仅大写失败：开图检索对大写 ASCII 抛异常（检索层缺陷，非图算法无效） |
| GID-5 | r13_full_check.cap_graph_identity | http=200 + body code=500 + reason（图业务空结果）→ 归 INFO/EMPTY_LEGIT，既不算 PASS 也不算 FAIL | PASS | PASS | 一致 | neutral=True ok=False detail=http=200 code=500 reason='no_vertex_matched' 键存在=False violations_count=None ← EMPTY_LEGIT |
| GUP-2 | r13_full_check.cap_graph_uppercase | 正例对照：大写与小写都 200，且两边都含 graph 块 | PASS | PASS | 一致 | 大写(AAA)+开图 http=200 docs=1 graph块=1 | 小写(aaa)+开图 http=200 docs=1 graph块=1 |
| GUP-3 | r13_full_check.cap_graph_uppercase | 两边都 200 但检索结果里没有 graph 块（只证明"不 500"，没证明图参与 → 仍判 FAIL） | FAIL | FAIL | 一致 | 大写(AAA)+开图 http=200 docs=1 graph块=0 | 小写(aaa)+开图 http=200 docs=1 graph块=0 ← 大写真 200 但无文档/无 graph 块：只证明不 500，未证明图参与 |
| F05-OOD-1 | permission_domain_scope.out_of_domain | kb_10 的引用被判为域外（跨域引用=泄露） | PASS | PASS | 一致 | out_of_domain(kb_10)=['http://x/r12-rag/kb_10/a.docx'] |
| F05-OOD-2 | permission_domain_scope.out_of_domain | kb_9 引用 + 空 source（FAQ 直答命中）均不算域外 | PASS | PASS | 一致 | out_of_domain(kb_9,空)=[] |
| F05-5XX-1 | permission_domain_scope.classify_5xx | 500 必须被判为 5xx（错误页炸掉不能算"已拒绝"） | PASS | PASS | 一致 | classify_5xx(500)=True |
| F05-5XX-2 | permission_domain_scope.classify_5xx | 403 不得被判为 5xx（真拒绝不能被当成故障） | PASS | PASS | 一致 | classify_5xx(403)=False |
| REVOKE-DENIED-1 | revoke_acceptance.denied_http | denied_http(500, {"success": false})（撤权验收把一般故障当"撤权生效"） | FAIL | FAIL | 一致 | denied_http(...) = False |
| REVOKE-DENIED-2 | revoke_acceptance.denied_http | denied_http(200, {"success": false})（无鉴权错误码） | FAIL | FAIL | 一致 | denied_http(...) = False |
| REVOKE-DENIED-3 | revoke_acceptance.denied_http | denied_http(0, …)（连接中断，不得当撤权生效） | FAIL | FAIL | 一致 | denied_http(...) = False |
| REVOKE-DENIED-4 | revoke_acceptance.denied_http | 正例对照：denied_http(403, …) | PASS | PASS | 一致 | denied_http(...) = True |
| REVOKE-DENIED-5 | revoke_acceptance.denied_http | 正例对照：denied_http(200, {"errorCode": "30016"}) | PASS | PASS | 一致 | denied_http(...) = True |
| REVOKE-SQL-1 | revoke_acceptance.sql | mysql 退出码 1（撤权 SQL 失败）-> 必须抛错而不是空串 | FAIL | FAIL | 一致 | 抛出 RuntimeError: sql failed rc=1: （期望如此） |
| S7-11 | acceptance.s7 | 不传 session（旧默认 r12-sess-1 不存在）必须判 FAIL，不得静默查一个不存在的会话 | FAIL | FAIL | 一致 | 未指定会话 id：禁止用默认值（旧默认 r12-sess-1 不存在，会掩盖真实问题） |
