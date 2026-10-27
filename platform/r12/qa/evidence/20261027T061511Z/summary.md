# R12 验收 20261027T061511Z

计划场景：['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8']（未知：[]）
总计 34/34 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 删除上一轮验收库（保证基线独立可重复） | PASS | kbId=24 kbName=R14-BASELINE-KB http=200 |
| S2 | 创建独立验收库 | PASS | http=200 kbId=27 kbName=R14-BASELINE-KB primitive=kb_27 旧库清理=1 |
| PREP | 独立库助手配置就绪 | PASS | kbName=kb_27 configId=12（R14-BASELINE-CFG） |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=420 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=421 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=422 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=423 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=424 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=425 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=426 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=427 |
| S4 | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=420 最终状态=3 耗时=18s |
| S4 | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=421 最终状态=3 耗时=0s |
| S4 | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=422 最终状态=3 耗时=0s |
| S4 | 解析完成 PDF 数字版 | PASS | fileId=423 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 纯文本 | PASS | fileId=424 最终状态=3 耗时=15s |
| S4 | 解析完成 DOCX 含表格 | PASS | fileId=425 最终状态=3 耗时=24s |
| S4 | 解析完成 PDF 扫描件(OCR) | PASS | fileId=426 最终状态=3 耗时=0s |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=427 最终状态=4(4=失败) 耗时=21s |
| S5 | 真实模型回答（29字问题） | PASS | http=200 帧数=80 答案长度=296 |
| S5 | 回答带引用 | PASS | 引用条数=2 |
| S6 | 服务端可独立取回原文（不随请求传正文） | PASS | http=200 chunk数=1 首块长度=459 |
| S6 | 引用携带文件与定位信息 | PASS | 引用 source 数=2 示例=['r12-rag/kb_27/R12FIX-product-loan.docx/V0/R12FIX-product-loan.docx', 'r12-rag/kb_27/R12FIX-product-intro.pptx/V0/R12FIX-product-intro.pptx'] |
| S6 | 答案要点可在引用原文中找到支撑 | PASS | 答案命中要点=['5000', '1000', '三年', '授信额度'] 其中被原文支撑=['5000', '1000', '三年', '授信额度'] 引用块数=2 |
| S7 | 历史对话可恢复 | PASS | http=200 session=kb_27 问答对数=1 问与答均有正文=True 本轮queryId=q-1793081791802 命中=True |
| S7 | 会话列表可查 | PASS | http=200 |
| S8 | 无 token 被拒绝 | PASS | http=401 |
| S8 | 伪造 token 被拒绝(Bearer forge…) | PASS | http=401 |
| S8 | 伪造 token 被拒绝(eyJhbGciOiJu…) | PASS | http=401 |
| S8 | 坏文件被网关/服务直接拒绝 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': []} |
| S8 | 删除不存在的知识库被明确拒绝且无副作用 | PASS | http=404 errorCode=10001 data=None |
| COVERAGE | 选中的场景均已真实执行 | PASS | 选中=['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'] 实际执行=['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'] 未执行=[] 未知场景=[] |
