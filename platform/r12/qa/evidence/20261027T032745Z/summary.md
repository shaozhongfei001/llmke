# R12 验收 20261027T032745Z

计划场景：['S6', 'S7']（未知：[]）
总计 20/25 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| PREP | 创建独立验收库 | PASS | http=200 kbId=15 kbName=R14-BASELINE-KB primitive=kb_15 旧库清理=0 |
| PREP | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=344 name=R12FIX-product-loan.docx |
| PREP | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=345 name=R12FIX-credit-ledger.xlsx |
| PREP | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=346 name=R12FIX-product-intro.pptx |
| PREP | 上传 PDF 数字版 | PASS | http=200 fileId=347 name=pdf-digital.pdf |
| PREP | 上传 DOCX 纯文本 | PASS | http=200 fileId=348 name=docx-plain.docx |
| PREP | 上传 DOCX 含表格 | PASS | http=200 fileId=349 name=docx-table.docx |
| PREP | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=350 name=pdf-scanned.pdf |
| PREP | 加密 PDF 已入库待解析 | PASS | http=200 fileId=351 |
| PREP | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=344 最终状态=3 耗时=30s |
| PREP | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=345 最终状态=3 耗时=0s |
| PREP | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=346 最终状态=3 耗时=0s |
| PREP | 解析完成 PDF 数字版 | PASS | fileId=347 最终状态=3 耗时=0s |
| PREP | 解析完成 DOCX 纯文本 | PASS | fileId=348 最终状态=3 耗时=18s |
| PREP | 解析完成 DOCX 含表格 | PASS | fileId=349 最终状态=3 耗时=15s |
| PREP | 解析完成 PDF 扫描件(OCR) | PASS | fileId=350 最终状态=3 耗时=0s |
| PREP | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=351 最终状态=4(4=失败) 耗时=42s |
| PREP | 真实模型回答（29字问题） | FAIL | http=403 帧数=0 答案长度=0 |
| PREP | 回答带引用 | FAIL | 引用条数=0 |
| S6 | 服务端可独立取回原文（不随请求传正文） | PASS | http=200 chunk数=1 首块长度=459 |
| S6 | 引用携带文件与定位信息 | FAIL | 引用 source 数=0 示例=[] |
| S6 | 答案要点可在引用原文中找到支撑 | FAIL | 答案命中要点=[] 其中被原文支撑=[] 引用块数=0 |
| S7 | 历史对话可恢复 | FAIL | http=200 session=kb_15 问答对数=0 问与答均有正文=False 本轮queryId=q-1793071772867 命中=False ← 空历史/缺答案/未命中本轮提问 不算通过 |
| S7 | 会话列表可查 | PASS | http=200 |
| COVERAGE | 选中的场景均已真实执行 | PASS | 选中=['S6', 'S7'] 实际执行=['S6', 'S7'] 未执行=[] 未知场景=[] |
