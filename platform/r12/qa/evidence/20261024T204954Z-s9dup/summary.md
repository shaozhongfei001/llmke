# R12 独立复核运行 20261024T204954Z

PASS=3 FAIL=1 BLOCKED=0

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S9 | 创建会话 | PASS | http=200 resp={"success": true, "errorMsg": null, "errorCode": null, "data": {"label": "QA独立复核会话", "sessionId": "qa-s9-1792874994", "gmtCreate": "2026-10-25 04:49:5 |
| S9 | 按 sessionId 恢复会话（label 往返一致） | PASS | http=200 期望label=QA独立复核会话 实际='QA独立复核会话' |
| S9 | 同一 sessionId 不得重复落库 | PASS | sessionId=qa-s9-1792874994 记录数=1（>1 表示无唯一约束，历史恢复可能取到空壳） |
| S9 | 提问后再建会话不得产生重复会话记录 | FAIL | sessionId=qa-s9-1792874994-dup 记录数=2；恢复返回 label=None |
