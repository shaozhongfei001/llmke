# R12 验收 20261024T220225Z

总计 32/36 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 知识库已存在（复用） | PASS | kbId=9 primitive=kb_9 |
| S5 | 真实模型回答（29字问题） | PASS | http=200 帧数=89 答案长度=152 |
| S5 | 回答带引用 | FAIL | 引用条数=0 |
| S6 | 服务端取回原文 | FAIL | 引用中无 file_id，无法核对原文 |
| S7 | 历史对话可恢复 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': None} |
| S7 | 会话列表可查 | PASS | http=200 |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=35 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=36 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=37 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=38 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=39 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=40 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=41 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=42 |
| S4 | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=35 最终状态=3 耗时=30s |
| S4 | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=36 最终状态=3 耗时=0s |
| S4 | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=37 最终状态=3 耗时=12s |
| S4 | 解析完成 PDF 数字版 | PASS | fileId=38 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 纯文本 | PASS | fileId=39 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 含表格 | PASS | fileId=40 最终状态=3 耗时=18s |
| S4 | 解析完成 PDF 扫描件(OCR) | PASS | fileId=41 最终状态=3 耗时=0s |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=42 最终状态=4(4=失败) 耗时=601s |
| S5 | 真实模型回答（29字问题） | PASS | http=200 帧数=79 答案长度=213 |
| S5 | 回答带引用 | PASS | 引用条数=1 |
| S6 | 服务端可独立取回原文（不随请求传正文） | PASS | http=200 chunk数=1 首块长度=0 |
| S6 | 引用携带文件与定位信息 | PASS | 引用 source 数=1 示例=['r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx'] |
| S6 | 答案要点可在引用原文中找到支撑 | PASS | 答案命中要点=['5000', '1000', '三年', '授信额度'] 其中被原文支撑=['5000', '授信额度'] 引用块数=1 |
| S7 | 历史对话可恢复 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': None} |
| S7 | 会话列表可查 | PASS | http=200 |
| S8 | 无 token 被拒绝 | PASS | http=401 |
| S8 | 伪造 token 被拒绝(Bearer forge…) | FAIL | http=500 |
| S8 | 伪造 token 被拒绝(eyJhbGciOiJu…) | PASS | http=401 |
| S8 | 坏文件被网关/服务直接拒绝 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': []} |
| S8 | 删除不存在的知识库返回业务错误 | FAIL | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': False} |
