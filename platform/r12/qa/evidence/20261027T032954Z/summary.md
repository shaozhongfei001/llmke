# R12 验收 20261027T032954Z

计划场景：['S6', 'S7']（未知：[]）
总计 27/27 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| PREP | 删除上一轮验收库（保证基线独立可重复） | PASS | kbId=15 kbName=R14-BASELINE-KB http=200 |
| PREP | 创建独立验收库 | PASS | http=200 kbId=16 kbName=R14-BASELINE-KB primitive=kb_16 旧库清理=1 |
| PREP | 独立库助手配置就绪 | PASS | kbName=kb_16 configId=12（R14-BASELINE-CFG） |
| PREP | 上传 中文 DOCX 业务夹具 | PASS | http=200 fileId=352 name=R12FIX-product-loan.docx |
| PREP | 上传 中文 XLSX 业务夹具 | PASS | http=200 fileId=353 name=R12FIX-credit-ledger.xlsx |
| PREP | 上传 中文 PPTX 业务夹具 | PASS | http=200 fileId=354 name=R12FIX-product-intro.pptx |
| PREP | 上传 PDF 数字版 | PASS | http=200 fileId=355 name=pdf-digital.pdf |
| PREP | 上传 DOCX 纯文本 | PASS | http=200 fileId=356 name=docx-plain.docx |
| PREP | 上传 DOCX 含表格 | PASS | http=200 fileId=357 name=docx-table.docx |
| PREP | 上传 PDF 扫描件(OCR) | PASS | http=200 fileId=358 name=pdf-scanned.pdf |
| PREP | 加密 PDF 已入库待解析 | PASS | http=200 fileId=359 |
| PREP | 解析完成 中文 DOCX 业务夹具 | PASS | fileId=352 最终状态=3 耗时=21s |
| PREP | 解析完成 中文 XLSX 业务夹具 | PASS | fileId=353 最终状态=3 耗时=0s |
| PREP | 解析完成 中文 PPTX 业务夹具 | PASS | fileId=354 最终状态=3 耗时=0s |
| PREP | 解析完成 PDF 数字版 | PASS | fileId=355 最终状态=3 耗时=0s |
| PREP | 解析完成 DOCX 纯文本 | PASS | fileId=356 最终状态=3 耗时=15s |
| PREP | 解析完成 DOCX 含表格 | PASS | fileId=357 最终状态=3 耗时=21s |
| PREP | 解析完成 PDF 扫描件(OCR) | PASS | fileId=358 最终状态=3 耗时=0s |
| PREP | 负例按预期失败 加密 PDF(应解析失败) | PASS | fileId=359 最终状态=4(4=失败) 耗时=24s |
| PREP | 真实模型回答（29字问题） | PASS | http=200 帧数=73 答案长度=200 |
| PREP | 回答带引用 | PASS | 引用条数=1 |
| S6 | 服务端可独立取回原文（不随请求传正文） | PASS | http=200 chunk数=1 首块长度=221 |
| S6 | 引用携带文件与定位信息 | PASS | 引用 source 数=1 示例=['r12-rag/kb_16/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx'] |
| S6 | 答案要点可在引用原文中找到支撑 | PASS | 答案命中要点=['5000', '三年', '授信额度'] 其中被原文支撑=['5000', '授信额度'] 引用块数=1 |
| S7 | 历史对话可恢复 | PASS | http=200 session=kb_16 问答对数=1 问与答均有正文=True 本轮queryId=q-1793071878016 命中=True |
| S7 | 会话列表可查 | PASS | http=200 |
| COVERAGE | 选中的场景均已真实执行 | PASS | 选中=['S6', 'S7'] 实际执行=['S6', 'S7'] 未执行=[] 未知场景=[] |
