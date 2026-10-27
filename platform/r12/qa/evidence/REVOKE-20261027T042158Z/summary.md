# R13 撤权验收 20261027T042158Z

主体：`r13_reader`（biz_type=1 / target_id=9 / permission=1）；撤权动作：删除该行；finally 中已恢复。

总计 21/21 PASS

> 采样时刻：20261027T042158Z（UTC）。R15–R18 的端口监听结论是**该时刻的运行态快照**，不代表源码/配置仓当前内容——源码已改但运行态未重载时，两者会不一致，这本身就是本报告要暴露的"静默抵消"情形。

| 用例 | 结果 | 详情 |
|---|---|---|
| R1 授权时知识库详情可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 kbName=R12验收主链 |
| R2 授权时普通问答返回完整回答 | PASS | POST /qa/ai/question http=200 status=2 resultType=1 内容长度=96 引用数=3 帧数=59 尝试=1 |
| R3 授权时 global 问答返回完整回答 | PASS | POST /qa/ai/question(globalMode=true) http=200 status=2 内容长度=19 引用数=1 帧数=1 尝试=3 |
| R4 授权时 FAQ 直答命中（resultType=2） | PASS | POST /qa/ai/question(FAQ) http=200 status=2 resultType=2 内容长度=30 尝试=2 |
| R5 引用可构造出可访问的对象键 | PASS | 对象键=r12-rag/kb_9/R12FIX-product-loan.docx/V1/R12FIX-product-loan(1).docx |
| R6 授权时可取回引用原文流 | PASS | POST /index/knowledgeBase/file/stream http=200 ctype=application/octet-stream 字节=37543 head=b'PK\x03\x04' |
| R7 授权时可预览（返回真实 PDF） | PASS | POST /index/knowledgeBase/file/previewStream http=200 ctype=application/pdf 字节=100300 head=b'%PDF-1.7' |
| R8 撤权后知识库详情被拒 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=403 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R9 撤权后问答被拒且未返回知识库内容 | PASS | POST /qa/ai/question http=403 status=None 内容长度=0 引用数=0 errorCode=30016 body={"success":false,"errorMsg":"没有足够权限","errorCode":"30016","data":null} |
| R10 撤权后 global 问答被拒且未返回内容 | PASS | POST /qa/ai/question(globalMode=true) http=403 status=None 内容长度=0 引用数=0 |
| R11 撤权后 FAQ 直答被拒且未返回内容 | PASS | POST /qa/ai/question(FAQ) http=403 status=None resultType=None 内容长度=0 引用数=0 |
| R12 撤权后按已知对象键取原文被拒 | PASS | POST /index/knowledgeBase/file/stream http=403 ctype=application/json;charset=UTF-8 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R13 撤权后预览被拒 | PASS | POST /index/knowledgeBase/file/previewStream http=403 resp={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| R14 撤权后连续两次问答均被拒（无缓存旁路） | PASS | 复用旧会话 http=403 status=None 内容=0 引用=0; 新会话 http=403 status=None 内容=0 引用=0 |
| R15 撤权后经非回环地址无法无凭据取回 kb_9 内容 | PASS | POST http://192.168.71.16:19995/retrieval_documents 不可达（ConnectionError） |
| R16 撤权后经非回环地址无法无凭据取回原文 | PASS | POST http://192.168.71.16:18095/stream 不可达（ConnectionError） |
| R17 内部服务端口仅监听回环地址（含写入面 12340/19526/19527） | PASS | 全部仅监听回环 |
| R18 撤权后经非回环地址无法取回图谱检索结果 | PASS | POST http://192.168.71.16:19529/query_graph_data 不可达（ConnectionError） |
| R19 恢复授权后知识库详情恢复可读 | PASS | GET /index/knowledgeBase/getKbById?id=9 http=200 |
| R20 恢复授权后问答恢复可用 | PASS | POST /qa/ai/question http=200 status=2 内容长度=145 引用数=3 尝试=1 |
| R21 全过程知识库本体未被改动 | PASS | before=1/15 after=1/15 撤权期间授权表=3	1	1	1;3	3	1	1 |

## 事实记录（INFO，不计入 PASS/FAIL）

- 回环内无凭据可读（既定边界，不计分）：POST 127.0.0.1:19995/retrieval_documents → documents=1；POST 127.0.0.1:18095/stream → http=200 字节=100300。含义：内部服务不做对象级授权，安全性完全依赖'只绑回环 + 仅 Java 调用'；本机任意进程/用户仍可绕过 user_privilege 取数据，若该边界不被接受需另行立项。

## 夹具前置（不是被撤权对象）

- r13_reader user_id=5
- 助手配置 fixture configId=10（create_by=r13_reader, is_default=0, is_del=1, kb_9）
- 阶段A 起：已授予 biz_type=1 target_id=9 permission=1
- 阶段B 起：已撤权（删除 user_privilege biz_type=1 target_id=9 行）
- 阶段D 起：已恢复授权（重新写入 biz_type=1 target_id=9 permission=1）

## 修复归属清单（R17 端口 0.0.0.0 的处置路由；本脚本只取证不改）

- Nacos 配置内容（配置/算法侧 owner）：6 处 server.host=0.0.0.0 —— alg_doc_config_py L3→12340(doc-parse,写入面)、index_data_config_py L7→19526(写入面)、index_data_config_py L37→19527(写入面)、alg_retrieval_config_py L7→19995(读)、alg_llm_config_py L6→19996(推理)、index_graph_config_py L4→19529(读)。注意：改代码或改 conf/ 均无效，只有配置中心 dataId 内容有效。
- 预览 18095（已修复，留三条经验）：① app.py 里 host=os.getenv("PREVIEW_HOST","127.0.0.1") 位于 `if __name__ == "__main__":` 内，而容器是 `python -m uvicorn app:app` **模块方式**启动 → 该行是死代码；真正生效点是 Dockerfile:54 的 CMD，现为 `--host ${PREVIEW_HOST:-127.0.0.1}` + 容器 env PREVIEW_HOST=127.0.0.1 + 重建镜像。② 期间曾因缩进被改坏（uvicorn.run 顶到第 0 列 → NameError）导致容器 crash-loop 12 次，且 **py_compile 能通过**，只有起进程才暴露。③ 容器是 host 网络、无端口映射，改 PortBindings 无从改起（本脚本最早的建议已撤回）。
- 部署 19529（已修复）：unit 文件改成 --host 127.0.0.1 必须配 `systemctl --user daemon-reload` + restart 才生效；此前未 reload 时 ExecStart 实参仍是 0.0.0.0，且 Restart=always 会用旧参数 5s 后自动起回，表现为「一会儿有、一会儿没有」的抖动（会造成不同人采样结论不一致）。
- index-service：services/rag-java/.../interfaces/KnowledgeBaseFileController.java:442 的注释（「预览服务在 127.0.0.1:18095 内部端口不做鉴权，这里是唯一收口点」）在 18095 收回回环后**重新成立**；:55 为默认 URL。它只是注释，不是修复点。
- 离线包风险（TL 决策，当前**未同步**）：运行态 7 个端口都已只绑回环，但包内配置仍是 0.0.0.0 —— check-bind 的判定为「已收紧但配置未同步」（12340/19526/19527/19529/19995/19996），即按现状重打包会把已收紧的端口重新放开。拆成两条来源，只改一条无效。注意路径约定：凡写 payload/... 均指 platform/r12/dist/offline/payload/... （platform/r12/offline/ 是安装报告目录，不含 payload，别去那里找）。复现路径与自测值：①配置侧 6 处：platform/r12/dist/offline/payload/nacos/configs.json，`grep -o '0\.0\.0\.0' | wc -l`=6（`grep -c` 只得 5，因 index_data_config_py 的 L7/L37 两处落在 JSON 同一行内容里）；②源码硬编码 1 处：真正生效点是 platform/r12/dist/offline/payload/preview/Dockerfile:52 的镜像 CMD，现仍为 `--host 0.0.0.0`（源码侧 Dockerfile:54 已改为 `${PREVIEW_HOST:-127.0.0.1}`，两者不一致）；包内 payload/preview/app.py 仍是 host="0.0.0.0" 且 run.sh 用 --network host。注意 app.py 里的 host 只在 `__main__` 生效，模块方式启动不执行，改它不解决问题。ops-offline 已在 offline-kit.sh verify 第 9 段做提示性盘点（不计失败）并记入 platform/r12/offline/INSTALL-FINDINGS.md §七；pack/init-nacos 的收紧与否由 TL 决策。
- 收紧后的验收门（ops-offline 提供、qa-authz 已只读试跑）：platform/r12/bin/check-bind.sh --expect-loopback，退出 0 才算通过；它同时比对“配置声明 vs 实际监听”，能识别快照未同步导致的“静默抵消”。本脚本终版采样时 qa-authz 实测该命令**退出 0**（7 个端口全部只绑回环，18095 判「一致」，其余 6 个判「已收紧但配置未同步」）；早期采样曾退出 1，可作对照。
- 加固有效性限定（否则可能空转）：只改配置中心/包内 configs.json 不足以保证生效——5 个 Python 服务存在 Nacos 本地快照回退：nacos client 的 SNAPSHOT_BASE 默认是相对路径 `nacos-data/snapshot`（platform/r12/venvs/alg/.../nacos/client.py:65，按服务 CWD 解析），只有 doc-parse 显式传了 no_snapshot=True（services/rag-alg/alg_doc_parse_service/server/nacos_utils.py:39,61）；检索/推理/向量/全文/图谱在配置中心不可达时会按本地快照启动。源码树实测有 7 份快照含 host: 0.0.0.0（alg_llm_config_py、alg_doc_config_py、alg_retrieval_config_py、index_data_config_py×3、index_graph_config_py），故加固须同步处理 `services/rag-alg/**/nacos-data/snapshot/*`，否则改动可能被静默抵消。（口径补充：**当前磁盘上的离线包内不含 `payload/src/`、快照副本 0 份**，即该风险目前只存在于源码树；一旦重打包把 `services/rag-alg` 纳入 `payload/src/`，它才会随包复制到目标机。）（本节事实由 qa-authz 独立复现：client.py:65、nacos_utils.py:39/61、7 份快照文件清单；写入面的绑定盘点限定同样适用于本节。）
