# R12 验收 20261024T215422Z

总计 7/7 PASS

| 场景 | 用例 | 结果 | 说明 |
|---|---|---|---|
| S2 | 知识库已存在（复用） | PASS | kbId=8 primitive=kb_8 |
| S5 | 真实模型回答（29字问题） | PASS | http=200 帧数=111 答案长度=2601 |
| S5 | 回答带引用 | PASS | 引用条数=1 |
| S6 | 服务端可独立取回原文（不随请求传正文） | PASS | http=200 chunk数=1 首块长度=0 |
| S6 | 引用携带文件与定位信息 | PASS | 引用 source 数=1 示例=['r12-rag/kb_8/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx'] |
| S7 | 历史对话可恢复 | PASS | http=200 resp={'success': True, 'errorMsg': None, 'errorCode': None, 'data': None} |
| S7 | 会话列表可查 | PASS | http=200 |
