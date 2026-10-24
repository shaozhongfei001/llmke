# R12 验收 20261024T212048Z

总计 6/8 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S1 | 登录并取菜单 | PASS | http=200 menus=7 |
| S1 | 取当前用户信息 | PASS | http=200 user=admin |
| S2 | 知识库已存在（复用） | PASS | kbId=4 primitive=kb_4 |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=1 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=2 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=3 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | FAIL | http=413 fileId=None name=pdf-scanned.pdf |
| S3 | 加密 PDF 明确失败（负例） | FAIL | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': [{'id': '4', 'kbId': '4', 'fileName': 'pdf-encrypted.pdf', 'fileSize': 4445.0, 'size': '4445.0MB' |
