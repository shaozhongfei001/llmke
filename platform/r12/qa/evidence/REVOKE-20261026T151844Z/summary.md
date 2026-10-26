# R13 撤权验收 20261026T151844Z

主体：`r13_reader`（biz_type=1 / target_id=9 / permission=1）；撤权动作：删除该行；finally 中已恢复。

总计 17/21 PASS

| 用例 | 结果 | 详情 |
|---|---|---|
| R1 授权时知识库详情可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 kbName=R12验收主链 |
| R2 授权时普通问答返回完整回答 | PASS | POST /qa/ai/question http=200 status=2 resultType=1 内容长度=122 引用数=3 帧数=76 |
| R3 授权时 global 问答返回完整回答 | PASS | POST /qa/ai/question(globalMode=true) http=200 status=2 内容长度=148 引用数=1 帧数=84 |
| R4 授权时 FAQ 直答命中（resultType=2） | PASS | POST /qa/ai/question(FAQ) http=200 status=2 resultType=2 内容长度=27 |
| R5 引用可构造出可访问的对象键 | PASS | 对象键=r12-rag/kb_9/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx |
| R6 授权时可取回引用原文流 | PASS | POST /index/knowledgeBase/file/stream http=200 ctype=application/octet-stream 字节=37544 head=b'PK\x03\x04' |
| R7 授权时可预览（返回真实 PDF） | PASS | POST /index/knowledgeBase/file/previewStream http=200 ctype=application/pdf 字节=100329 head=b'%PDF-1.7' |
| R8 撤权后知识库详情被拒 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=403 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R9 撤权后问答被拒且未返回知识库内容 | PASS | POST /qa/ai/question http=403 status=None 内容长度=0 引用数=0 errorCode=30016 body={"success":false,"errorMsg":"没有足够权限","errorCode":"30016","data":null} |
| R10 撤权后 global 问答被拒且未返回内容 | PASS | POST /qa/ai/question(globalMode=true) http=403 status=None 内容长度=0 引用数=0 |
| R11 撤权后 FAQ 直答被拒且未返回内容 | PASS | POST /qa/ai/question(FAQ) http=403 status=None resultType=None 内容长度=0 引用数=0 |
| R12 撤权后按已知对象键取原文被拒 | PASS | POST /index/knowledgeBase/file/stream http=403 ctype=application/json resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R13 撤权后预览被拒 | PASS | POST /index/knowledgeBase/file/previewStream http=403 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R14 撤权后连续两次问答均被拒（无缓存旁路） | PASS | 复用旧会话 http=403 status=None 内容=0 引用=0; 新会话 http=403 status=None 内容=0 引用=0 |
| R15 撤权后内部检索服务无凭据不可取回 kb_9 内容 | FAIL | POST http://127.0.0.1:19995/retrieval_documents（无 Authorization） http=200 documents=1 首块='“智造贷”企业流动资金贷款产品说明书文件编号：PRD-CORP-LOAN-2026-01（R12 验收测试夹具，非真实业务文件）一、适用对象面向制造业中小微企业' |
| R16 撤权后内部预览服务无凭据不可取回原文 | FAIL | POST http://127.0.0.1:18095/stream（无 Authorization） http=200 ctype=application/pdf 字节=100329 head=b'%PDF-1.7' |
| R17 内部服务端口仅监听回环地址（含写入面 12340/19526/19527） | FAIL | 以下内部端口监听 0.0.0.0（局域网可直达）: 19995(算法检索 alg_retrieval_service(读/召回))=['0.0.0.0']; 18095(Office 预览 r12-preview(读))=['0.0.0.0']; 12340(文档解析 doc-parse(写入面))=['0.0.0.0']; 19526(向量检索 index_vector_service(写面))=['0.0.0.0']; 19527(全文检索 index_fulltext_service(写面))=['0.0.0.0']; 19529(图谱检索 graph(读))=['0.0.0.0']; 19996(模型推理 llm_open_chat(读/推理))=['0.0.0.0']；12340/19526/19527 属写入面，本脚本只做绑定盘点、未发写入请求（避免副作用） |
| R18 内网其他主机无法绕过网关取原文 | FAIL | POST http://192.168.71.16:18095/stream（无 Authorization） http=200 字节=100329 |
| R19 恢复授权后知识库详情恢复可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 |
| R20 恢复授权后问答恢复可用 | PASS | POST /qa/ai/question http=200 status=2 内容长度=152 引用数=3 |
| R21 全过程知识库本体未被改动 | PASS | before=1/15 after=1/15 撤权期间授权表=3	1	1	1;3	3	1	1 |

## 夹具前置（不是被撤权对象）

- r13_reader user_id=5
- 助手配置 fixture configId=10（create_by=r13_reader, is_default=1, is_del=1, kb_9）
- 阶段A 起：已授予 biz_type=1 target_id=9 permission=1
- 阶段B 起：已撤权（删除 user_privilege biz_type=1 target_id=9 行）
- 阶段D 起：已恢复授权（重新写入 biz_type=1 target_id=9 permission=1）

## 修复归属清单（R17 端口 0.0.0.0 的处置路由；本脚本只取证不改）

- Nacos 配置内容（配置/算法侧 owner）：6 处 server.host=0.0.0.0 —— alg_doc_config_py L3→12340(doc-parse,写入面)、index_data_config_py L7→19526(写入面)、index_data_config_py L37→19527(写入面)、alg_retrieval_config_py L7→19995(读)、alg_llm_config_py L6→19996(推理)、index_graph_config_py L4→19529(读)。注意：改代码或改 conf/ 均无效，只有配置中心 dataId 内容有效。
- 预览服务 owner：platform/r12/preview/app.py:399 host 硬编码 0.0.0.0 + preview/run.sh:31 --network host；最小改法 app.py 的 host 改读 PREVIEW_HOST（默认 127.0.0.1）+ run.sh 传 -e（容器为 host 网络、无端口映射，改 PortBindings 无从改起，本脚本上一轮建议已撤回）。
- 部署 owner：platform/r12/systemd/r12-graphsvc.service:14 带 --host 0.0.0.0（19529 的第二条绑定路径）。
- index-service owner：services/rag-java/.../interfaces/KnowledgeBaseFileController.java:442 的注释（假设预览服务仅在 127.0.0.1:18095、本接口为唯一收口）前提已失效；:55 为其默认 URL。这是注释/前提问题，不是本次泄漏的成因，不要当修复点。
- 离线包风险（TL 决策）：随包复制的是 7 个端口的暴露面，拆成两条来源，只改一条无效。注意路径约定：凡写 payload/... 均指 platform/r12/dist/offline/payload/... （platform/r12/offline/ 是安装报告目录，不含 payload，别去那里找）。复现路径与自测值：①配置侧 6 处：platform/r12/dist/offline/payload/nacos/configs.json，`grep -o '0\.0\.0\.0' | wc -l`=6（`grep -c` 只得 5，因 index_data_config_py 的 L7/L37 两处落在 JSON 同一行内容里）；②源码硬编码 1 处：platform/r12/dist/offline/payload/preview/app.py:399 host 写死 + payload/preview/run.sh:31 --network host。ops-offline 已在 offline-kit.sh verify 第 9 段做提示性盘点（不计失败）并记入 platform/r12/offline/INSTALL-FINDINGS.md §七；pack/init-nacos 的收紧与否由 TL 决策。
