# R12 验收 20261027T033900Z

计划场景：['S7']（未知：[]）
总计 24/24 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| PREP | 删除上一轮验收库（保证基线独立可重复） | PASS | kbId=18 kbName=R14-BASELINE-KB http=200 |
| PREP | 创建独立验收库 | PASS | http=200 kbId=19 kbName=R14-BASELINE-KB primitive=kb_19 旧库清理=1 |
| PREP | 独立库助手配置就绪 | PASS | kbName=kb_19 configId=12（R14-BASELINE-CFG） |
| PREP | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=368 name=R12FIX-product-loan.docx |
| PREP | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=369 name=R12FIX-credit-ledger.xlsx |
| PREP | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=370 name=R12FIX-product-intro.pptx |
| PREP | 上传 PDF 数字版 | PASS | http=200 fileId=371 name=pdf-digital.pdf |
| PREP | 上传 DOCX 纯文本 | PASS | http=200 fileId=372 name=docx-plain.docx |
| PREP | 上传 DOCX 含表格 | PASS | http=200 fileId=373 name=docx-table.docx |
| PREP | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=374 name=pdf-scanned.pdf |
| PREP | 加密 PDF 已入库待解析 | PASS | http=200 fileId=375 |
| PREP | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=368 最终状态=3 耗时=30s |
| PREP | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=369 最终状态=3 耗时=0s |
| PREP | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=370 最终状态=3 耗时=0s |
| PREP | 解析完成 PDF 数字版 | PASS | fileId=371 最终状态=3 耗时=0s |
| PREP | 解析完成 DOCX 纯文本 | PASS | fileId=372 最终状态=3 耗时=15s |
| PREP | 解析完成 DOCX 含表格 | PASS | fileId=373 最终状态=3 耗时=18s |
| PREP | 解析完成 PDF 扫描件(OCR) | PASS | fileId=374 最终状态=3 耗时=0s |
| PREP | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=375 最终状态=4(4=失败) 耗时=24s |
| PREP | 真实模型回答（29字问题） | PASS | http=200 帧数=117 答案长度=436 |
| PREP | 回答带引用 | PASS | 引用条数=2 |
| S7 | 历史对话可恢复 | PASS | http=200 session=kb_19 问答对数=1 问与答均有正文=True 本轮queryId=q-1793072430365 命中=True |
| S7 | 会话列表可查 | PASS | http=200 |
| COVERAGE | 选中的场景均已真实执行 | PASS | 选中=['S7'] 实际执行=['S7'] 未执行=[] 未知场景=[] |
