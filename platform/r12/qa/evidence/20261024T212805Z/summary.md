# R12 验收 20261024T212805Z

总计 5/6 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S2 | 知识库已存在（复用） | PASS | kbId=4 primitive=kb_4 |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=14 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=15 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=16 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=17 name=pdf-scanned.pdf |
| S3 | 加密 PDF 明确失败（负例） | FAIL | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': [{'id': '18', 'kbId': '4', 'fileName': 'pdf-encrypted.pdf', 'fileSize': 4445.0, 'size': '4445.0MB |
