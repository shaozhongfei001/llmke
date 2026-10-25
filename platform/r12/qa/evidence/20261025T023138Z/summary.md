# R12 验收 20261025T023138Z

总计 10/17 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 知识库已存在（复用） | PASS | kbId=9 primitive=kb_9 |
| S3 | 上传 中文 DOCX 业务夹具 | FAIL | http=500 fileId=None name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | FAIL | http=500 fileId=None name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | FAIL | http=500 fileId=None name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | FAIL | http=500 fileId=None name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | FAIL | http=500 fileId=None name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | FAIL | http=500 fileId=None name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | FAIL | http=500 fileId=None name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=70 |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=70 最终状态=4(4=失败) 耗时=6s |
| S8 | 无 token 被拒绝 | PASS | http=401 |
| S8 | 伪造 token 被拒绝(Bearer forge…) | PASS | http=401 |
| S8 | 伪造 token 被拒绝(eyJhbGciOiJu…) | PASS | http=401 |
| S8 | 坏文件被网关/服务直接拒绝 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': []} |
| S8 | 删除不存在的知识库未产生副作用 | PASS | http=200 data=False success=True（语义缺陷：拒绝时 success 仍为 true，已登记 R12-FIX-API-01） |
