# R13 能力矩阵自检

总计 0/1 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| PARSE_RETRY_STORM | FAIL | 窗口=30分钟 阈值>3条/文件 超限文件=无 file_id 在窗口内产生 >3 条 task status∈(98,99)超窗未结束=0 原地重启未计数=1 条任务原地重启但 retry_times=0（无限重试且计数失效）：[{'task': '479', 'file_id': '451', 'status': '3', 'retry_times': '0', 'gap_min': 9}] |
