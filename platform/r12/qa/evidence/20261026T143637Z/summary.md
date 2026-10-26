# R12 验收 20261026T143637Z

总计 17/17 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S2 | 知识库已存在（复用） | PASS | kbId=9 primitive=kb_9 |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=258 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=259 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=260 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=261 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=262 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=263 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=264 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=265 |
| S4 | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=258 最终状态=3 耗时=24s |
| S4 | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=259 最终状态=3 耗时=0s |
| S4 | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=260 最终状态=3 耗时=0s |
| S4 | 解析完成 PDF 数字版 | PASS | fileId=261 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 纯文本 | PASS | fileId=262 最终状态=3 耗时=15s |
| S4 | 解析完成 DOCX 含表格 | PASS | fileId=263 最终状态=3 耗时=15s |
| S4 | 解析完成 PDF 扫描件(OCR) | PASS | fileId=264 最终状态=3 耗时=0s |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=265 最终状态=4(4=失败) 耗时=27s |
