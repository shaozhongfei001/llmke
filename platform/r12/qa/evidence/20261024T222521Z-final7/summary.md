# R12 独立复核运行 20261024T222521Z

PASS=11 FAIL=2 BLOCKED=0

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S2 | 知识库存在(qa_r12_final) | PASS | kbId=10 primitive=kb_10 private=0 |
| S3 | 复用库内已有文件（未重传） | PASS | kbId=10 文件数=5 |
| S2 | 检索配置已存在（复用） | PASS | configId=7 kb=kb_10 |
| S5 | 提问1（21字）得到模型回答 | PASS | http=200 帧=26 答案长度=199 |
| S5 | 提问1 返回引用 | PASS | 引用条数=2 |
| S5 | 提问2（23字）得到模型回答 | PASS | http=200 帧=28 答案长度=201 |
| S5 | 提问2 返回引用 | PASS | 引用条数=2 |
| S5 | 换措辞后命中相同文件（语义检索证据） | PASS | 措辞1文件=['51', '53'] 措辞2文件=['51', '53'] 交集=['51', '53'] |
| S6 | 引用 file_id 属于本库已上传文件 | PASS | 2 个引用 file_id 全部属于本库(5 个文件) |
| S6 | 提问请求体不含正文文本字段 | PASS | payload 字段=['configId', 'content', 'queryId', 'sessionId', 'sysType', 'type'] content=21≈问题=21 |
| S6 | 答案要点能在引用原文中找到支撑（强要素覆盖 ≥60%） | FAIL | 强要素 54 个，覆盖 48.1%（2-gram 参考值 54.5%）；缺失示例 ['2554505273717269223', '品的单户最高', '贷产品的单户', '3898013562284726271', '产品的单户'] |
| S6 | 引用定位信息合法（pdf 有页码 / 非 pdf 有 offset 或坐标） | PASS | docx#51 pages=[0] off=True; pptx#53 pages=[0] off=True |
| S6 | 引用所属文件的分块可被接口取到（点击定位前提） | FAIL | docx#51 chunk_api=0; pptx#53 chunk_api=0 |
