# R13 撤权验收 20261026T154143Z

主体：`r13_reader`（biz_type=1 / target_id=9 / permission=1）；撤权动作：删除该行；finally 中已恢复。

总计 21/21 PASS

> 采样时刻：20261026T154143Z（UTC）。R15–R18 的端口监听结论是**该时刻的运行态快照**，不代表源码/配置仓当前内容——源码已改但运行态未重载时，两者会不一致，这本身就是本报告要暴露的"静默抵消"情形。

| 用例 | 结果 | 详情 |
|---|---|---|
| R1 授权时知识库详情可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 kbName=R12验收主链 |
| R2 授权时普通问答返回完整回答 | PASS | POST /qa/ai/question http=200 status=2 resultType=1 内容长度=121 引用数=3 帧数=74 |
| R3 授权时 global 问答返回完整回答 | PASS | POST /qa/ai/question(globalMode=true) http=200 status=2 内容长度=115 引用数=1 帧数=62 |
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
| R15 撤权后经非回环地址无法无凭据取回 kb_9 内容 | PASS | POST http://192.168.71.16:19995/retrieval_documents 不可达（ConnectionError） |
| R16 撤权后经非回环地址无法无凭据取回原文 | PASS | POST http://192.168.71.16:18095/stream 不可达（ConnectionError） |
| R17 内部服务端口仅监听回环地址（含写入面 12340/19526/19527） | PASS | 全部仅监听回环 |
| R18 撤权后经非回环地址无法取回图谱检索结果 | PASS | POST http://192.168.71.16:19529/query_graph_data 不可达（ConnectionError） |
| R19 恢复授权后知识库详情恢复可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 |
| R20 恢复授权后问答恢复可用 | PASS | POST /qa/ai/question http=200 status=2 内容长度=127 引用数=3 |
| R21 全过程知识库本体未被改动 | PASS | before=1/15 after=1/15 撤权期间授权表=3	1	1	1;3	3	1	1 |

## 事实记录（INFO，不计入 PASS/FAIL）

- 回环内无凭据可读（既定边界，不计分）：POST 127.0.0.1:19995/retrieval_documents → documents=1；POST 127.0.0.1:18095/stream → http=200 字节=100329。含义：内部服务不做对象级授权，安全性完全依赖'只绑回环 + 仅 Java 调用'；本机任意进程/用户仍可绕过 user_privilege 取数据，若该边界不被接受需另行立项。

## 夹具前置（不是被撤权对象）

- r13_reader user_id=5
- 助手配置 fixture configId=10（create_by=r13_reader, is_default=1, is_del=1, kb_9）
- 阶段A 起：已授予 biz_type=1 target_id=9 permission=1
- 阶段B 起：已撤权（删除 user_privilege biz_type=1 target_id=9 行）
- 阶段D 起：已恢复授权（重新写入 biz_type=1 target_id=9 permission=1）

## 修复归属清单（R17 端口 0.0.0.0 的处置路由；本脚本只取证不改）

- Nacos 配置内容（配置/算法侧 owner）：6 处 server.host=0.0.0.0 —— alg_doc_config_py L3→12340(doc-parse,写入面)、index_data_config_py L7→19526(写入面)、index_data_config_py L37→19527(写入面)、alg_retrieval_config_py L7→19995(读)、alg_llm_config_py L6→19996(推理)、index_graph_config_py L4→19529(读)。注意：改代码或改 conf/ 均无效，只有配置中心 dataId 内容有效。
- 预览服务 owner：源码侧已被他人改为 PREVIEW_HOST 方案（R13-SEC-NET-01：preview/app.py 的 host=os.getenv("PREVIEW_HOST","127.0.0.1")、preview/run.sh:32 传 -e），但**运行态未生效**——容器为 host 网络、无端口映射，18095 仍监听 0.0.0.0，必须重建/重启容器（改 PortBindings 无从改起，本脚本早期建议已撤回）。
- 部署 owner：systemd/r12-graphsvc.service:14 源码侧已被改为 --host 127.0.0.1，但实跑进程仍绑 0.0.0.0（需 daemon-reload + 重启服务才生效），19529 本采样时刻仍是外露状态。
- index-service owner：services/rag-java/.../interfaces/KnowledgeBaseFileController.java:442 的注释（假设预览服务仅在 127.0.0.1:18095、本接口为唯一收口）前提已失效；:55 为其默认 URL。这是注释/前提问题，不是本次泄漏的成因，不要当修复点。
- 离线包风险（TL 决策）：随包复制的是 7 个端口的暴露面，拆成两条来源，只改一条无效。注意路径约定：凡写 payload/... 均指 platform/r12/dist/offline/payload/... （platform/r12/offline/ 是安装报告目录，不含 payload，别去那里找）。复现路径与自测值：①配置侧 6 处：platform/r12/dist/offline/payload/nacos/configs.json，`grep -o '0\.0\.0\.0' | wc -l`=6（`grep -c` 只得 5，因 index_data_config_py 的 L7/L37 两处落在 JSON 同一行内容里）；②源码硬编码 1 处：platform/r12/dist/offline/payload/preview/app.py:399 host 写死 + payload/preview/run.sh:31 --network host。ops-offline 已在 offline-kit.sh verify 第 9 段做提示性盘点（不计失败）并记入 platform/r12/offline/INSTALL-FINDINGS.md §七；pack/init-nacos 的收紧与否由 TL 决策。
- 收紧后的验收门（ops-offline 提供、qa-authz 已只读试跑）：platform/r12/bin/check-bind.sh --expect-loopback，退出 0 才算通过；它同时比对“配置声明 vs 实际监听”，能识别快照未同步导致的“静默抵消”。本机现状：qa-authz 实测该命令退出 1，提示“仍有 7 个端口对外可达”，与本脚本 R17 的 7 端口枚举一致。
- 加固有效性限定（否则可能空转）：只改配置中心/包内 configs.json 不足以保证生效——5 个 Python 服务存在 Nacos 本地快照回退：nacos client 的 SNAPSHOT_BASE 默认是相对路径 `nacos-data/snapshot`（platform/r12/venvs/alg/.../nacos/client.py:65，按服务 CWD 解析），只有 doc-parse 显式传了 no_snapshot=True（services/rag-alg/alg_doc_parse_service/server/nacos_utils.py:39,61）；检索/推理/向量/全文/图谱在配置中心不可达时会按本地快照启动。源码树实测有 7 份快照含 host: 0.0.0.0（alg_llm_config_py、alg_doc_config_py、alg_retrieval_config_py、index_data_config_py×3、index_graph_config_py），故加固须同步处理 `services/rag-alg/**/nacos-data/snapshot/*`，否则改动可能被静默抵消。（本节事实由 qa-authz 独立复现：client.py:65、nacos_utils.py:39/61、7 份快照文件清单；写入面的绑定盘点限定同样适用于本节。）
