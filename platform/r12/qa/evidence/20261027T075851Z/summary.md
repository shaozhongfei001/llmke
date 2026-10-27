# R12 验收 20261027T075851Z

计划场景：['S3', 'S4']（未知：[]）
总计 20/20 PASS ｜ FAIL 0 ｜ TIMEOUT 0
SLOW(>600s) 0 项

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| PREP | 删除上一轮验收库（保证基线独立可重复） | PASS | kbId=33 kbName=R14-BASELINE-KB http=200 |
| PREP | 创建独立验收库 | PASS | http=200 kbId=34 kbName=R14-BASELINE-KB primitive=kb_34 旧库清理=1 |
| PREP | 独立库助手配置就绪 | PASS | kbName=kb_34 configId=12（R14-BASELINE-CFG） |
| S3 | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=483 name=R12FIX-product-loan.docx |
| S3 | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=484 name=R12FIX-credit-ledger.xlsx |
| S3 | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=485 name=R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=486 name=pdf-digital.pdf |
| S3 | 上传 DOCX 纯文本 | PASS | http=200 fileId=487 name=docx-plain.docx |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=488 name=docx-table.docx |
| S3 | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=489 name=pdf-scanned.pdf |
| S3 | 加密 PDF 已入库待解析 | PASS | http=200 fileId=490 |
| S4 | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=483 最终状态=3 耗时=27s |
| S4 | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=484 最终状态=3 耗时=0s |
| S4 | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=485 最终状态=3 耗时=0s |
| S4 | 解析完成 PDF 数字版 | PASS | fileId=486 最终状态=3 耗时=0s |
| S4 | 解析完成 DOCX 纯文本 | PASS | fileId=487 最终状态=3 耗时=3s |
| S4 | 解析完成 DOCX 含表格 | PASS | fileId=488 最终状态=3 耗时=0s |
| S4 | 解析完成 PDF 扫描件(OCR) | PASS | fileId=489 最终状态=3 耗时=0s |
| S4 | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=490 负例 最终状态=4(失败·正确终态) 耗时=0s |
| COVERAGE | 选中的场景均已真实执行 | PASS | 选中=['S3', 'S4'] 实际执行=['S3', 'S4'] 未执行=[] 未知场景=[] |
