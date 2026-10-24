# R12 独立复核运行 20261024T212542Z

PASS=22 FAIL=2 BLOCKED=5

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S1 | 登录后取菜单 | PASS | http=200 success=True menus=7 |
| S1 | 取当前用户身份 | PASS | userName=admin |
| S1 | 登录响应不回显口令/哈希 | PASS | 响应中 userPassword 字段为 null，未回显 |
| S2 | 知识库存在(qa_r12_indep) | PASS | kbId=5 primitive=kb_5 private=0 |
| S3 | 上传 PDF 数字版 | PASS | http=200 fileId=9 name=pdf-digital.pdf |
| S3 | 上传 DOCX 含表格 | PASS | http=200 fileId=10 name=docx-table.docx |
| S3 | 上传 XLSX 表格 | PASS | http=200 fileId=11 name=table-ledger.xlsx |
| S3 | 上传 PPTX 图片页 | PASS | http=200 fileId=12 name=image-slide.pptx |
| S3 | 上传 扫描图片(纯图) | PASS | http=200 fileId=13 name=scan-text.png |
| S4 | 解析完成且 chunk 落地 PDF 数字版 | PASS | fileId=9 status=3 chunk=2 |
| S4 | 解析完成且 chunk 落地 DOCX 含表格 | PASS | fileId=10 status=3 chunk=1 |
| S4 | 解析完成且 chunk 落地 XLSX 表格 | PASS | fileId=11 status=3 chunk=1 |
| S4 | 解析完成 PPTX 图片页 | BLOCKED | fileId=12 最终状态=4 |
| S4 | 解析完成且 chunk 落地 扫描图片(纯图) | PASS | fileId=13 status=3 chunk=1 |
| S2 | 创建独立检索配置 | PASS | http=200 configId=2 kb=kb_5  |
| S5 | 提问1（21字）得到模型回答 | PASS | http=200 帧=144 答案长度=4134 |
| S5 | 提问1 返回引用 | BLOCKED | 引用条数=0 |
| S5 | 提问2（24字）得到模型回答 | PASS | http=200 帧=324 答案长度=3358 |
| S5 | 提问2 返回引用 | BLOCKED | 引用条数=0 |
| S6 | 引用 file_id 属于本库已上传文件 | BLOCKED | 本轮无引用 |
| S6 | 提问请求体不含正文文本字段 | PASS | payload 字段=['configId', 'content', 'queryId', 'sessionId', 'sysType', 'type'] content=21≈问题=21 |
| S6 | 引用内容能在原文 chunk 中找到支撑 | BLOCKED | 本轮无引用可核对 |
| S7 | 按 sessionId 恢复历史对话 | PASS | http=200 success=True 长度=2936 |
| S7 | 历史中包含本轮流式回答 | FAIL | 查找片段='é\x93¶è¡\x8cæ\x89¿{"sessionId' 命中=False |
| S7 | 会话列表可查 | PASS | http=200 total=8 |
| S9 | 创建会话 | PASS | http=200 resp={"success": true, "errorMsg": null, "errorCode": null, "data": {"label": "QA独立复核会话", "sessionId": "qa-s9-1792877293", "gmtCreate": "2026-10-25 05:28:1 |
| S9 | 按 sessionId 恢复会话（label 往返一致） | PASS | http=200 期望label=QA独立复核会话 实际='QA独立复核会话' |
| S9 | 同一 sessionId 不得重复落库 | PASS | sessionId=qa-s9-1792877293 记录数=1（>1 表示无唯一约束，历史恢复可能取到空壳） |
| S9 | 提问后再建会话不得产生重复会话记录 | FAIL | sessionId=qa-s9-1792877293-dup 记录数=2；恢复返回 label=None |
