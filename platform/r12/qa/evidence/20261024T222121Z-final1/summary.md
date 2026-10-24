# R12 独立复核运行 20261024T222121Z

PASS=27 FAIL=5 BLOCKED=0

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S1 | 登录后取菜单 | PASS | http=200 success=True menus=7 |
| S1 | 取当前用户身份 | PASS | userName=admin |
| S1 | 登录响应不回显口令/哈希 | PASS | 响应中 userPassword 字段为 null，未回显 |
| S2 | 创建知识库(qa_r12_final) | PASS | http=200 kbId=10 primitive=kb_10  |
| S3 | 上传 DOCX 中文业务文档 | PASS | http=200 fileId=51 name=/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-product-loan.docx |
| S3 | 上传 XLSX 授信台账 | PASS | http=200 fileId=52 name=/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-credit-ledger.xlsx |
| S3 | 上传 PPTX 产品介绍 | PASS | http=200 fileId=53 name=/home/szf/data/dev/llmke-r12/platform/r12/qa/fixtures/R12FIX-product-intro.pptx |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=54 name=/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/pdf-digital.pdf |
| S3 | 上传 扫描图片(纯图) | PASS | http=200 fileId=55 name=/home/szf/data/dev/llmke-r12/platform/r12/parse/fixtures/generated/scan-text.png |
| S4 | 解析完成且 chunk 落地 DOCX 中文业务文档 | FAIL | fileId=51 静默成功：status=3(解析成功) 但 chunk=0 |
| S4 | 解析完成且 chunk 落地 XLSX 授信台账 | PASS | fileId=52 status=3 chunk=1 |
| S4 | 解析完成且 chunk 落地 PPTX 产品介绍 | FAIL | fileId=53 静默成功：status=3(解析成功) 但 chunk=0 |
| S4 | 解析完成且 chunk 落地 PDF 数字版 | PASS | fileId=54 status=3 chunk=2 |
| S4 | 解析完成且 chunk 落地 扫描图片(纯图) | PASS | fileId=55 status=3 chunk=1 |
| S2 | 创建独立检索配置 | PASS | http=200 configId=7 kb=kb_10  |
| S5 | 提问1（21字）得到模型回答 | PASS | http=200 帧=26 答案长度=198 |
| S5 | 提问1 返回引用 | PASS | 引用条数=2 |
| S5 | 提问2（23字）得到模型回答 | PASS | http=200 帧=27 答案长度=198 |
| S5 | 提问2 返回引用 | PASS | 引用条数=2 |
| S5 | 换措辞后命中相同文件（语义检索证据） | PASS | 措辞1文件=['51', '53'] 措辞2文件=['51', '53'] 交集=['51', '53'] |
| S6 | 引用 file_id 属于本库已上传文件 | PASS | 2 个引用 file_id 全部属于本库(5 个文件) |
| S6 | 提问请求体不含正文文本字段 | PASS | payload 字段=['configId', 'content', 'queryId', 'sessionId', 'sysType', 'type'] content=21≈问题=21 |
| S6 | 答案要点能在引用原文中找到支撑 | FAIL | 逐条覆盖率: 51=0.0, 53=0.0 |
| S6 | 引用定位信息合法（pdf 有页码 / 非 pdf 有 offset 或坐标） | PASS | docx#51 pages=[0] off=True; pptx#53 pages=[0] off=True |
| S6 | 引用所属文件的分块可被接口取到（点击定位前提） | FAIL | docx#51 chunk_api=0; pptx#53 chunk_api=0 |
| S7 | 按 sessionId 恢复历史对话 | PASS | http=200 success=True 长度=6626 |
| S7 | 历史中包含本轮流式回答 | PASS | 查找片段='智造贷产品的单户最高授信额度为人民币50' 命中=True |
| S7 | 会话列表可查 | PASS | http=200 total=28 |
| S9 | 创建会话 | PASS | http=200 resp={"success": true, "errorMsg": null, "errorCode": null, "data": {"label": "QA独立复核会话", "sessionId": "qa-s9-1792880563", "gmtCreate": "2026-10-25 06:22:4 |
| S9 | 按 sessionId 恢复会话（label 往返一致） | PASS | http=200 期望label=QA独立复核会话 实际='QA独立复核会话' |
| S9 | 同一 sessionId 不得重复落库 | PASS | sessionId=qa-s9-1792880563 记录数=1（>1 表示无唯一约束，历史恢复可能取到空壳） |
| S9 | 提问后再建会话不得产生重复会话记录 | FAIL | sessionId=qa-s9-1792880563-dup 记录数=2；恢复返回 label=None |
