# R13 能力矩阵自检

总计 2/2 PASS（另有 INFO 0 条不计入判定）

| 能力 | 结果 | 详情 |
|---|---|---|
| PARSE_QUEUE_STALL | PASS | 队列分布={'PENDING(1)':0,'DEAL_ING(2)':0,'RETRY_ING(3)':0,'成功(4)':482,'失败(5)':78} status=99合计=0 其中超5分钟未推进=0 最老PENDING=None分钟 孤儿任务=0（所属文件已删，不计入卡住判定，见 PARSE_ORPHAN_TASK） 判定=队列健康 |
| PARSE_ORPHAN_TASK | PASS | 无孤儿任务（未完成任务都能找到所属文件） |
