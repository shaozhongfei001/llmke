# R13 能力矩阵自检

总计 0/1 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| PARSE_CONVERT_PATH | FAIL | 窗口=60分钟 6 条任务因转换产物缺失失败（NoSuchKey *.pdf）：[{'task': '497', 'file_id': '469', 'err': '{"msg":"???????????????????? LOG_ID: 1543618","success":false,"task_id":497,"task_statuses":[{"fail_reason":"?????S3 operation failed; code: NoSuchKey'}, {'task': '495', 'file_id': '467', 'err': '{"msg":"???????????????????? LOG_ID: 1543618","success":false,"task_id":495,"task_statuses":[{"fail_reason":"?????S3 operation failed; code: NoSuchKey'}, {'task': '494', 'file_id': '466', 'err': '{"msg":"???????????????????? LOG_ID: 1543618","success":false,"task_id":494,"task_statuses":[{"fail_reason":"?????S3 operation failed; code: NoSuchKey'}] ← Office→PDF 转换不可用或回落仍传 .pdf（解析器读不到对象） |
