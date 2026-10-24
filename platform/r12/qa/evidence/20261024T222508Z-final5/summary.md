# R12 独立复核运行 20261024T222508Z

PASS=10 FAIL=2 BLOCKED=0

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S2 | 知识库存在(qa_r12_final) | PASS | kbId=10 primitive=kb_10 private=0 |
| S3 | 复用库内已有文件（未重传） | PASS | kbId=10 文件数=5 |
| S4 | 解析完成且 chunk 落地 51 | PASS | fileId=51 status=3 ES分块=1 接口返回=0 |
| S4 | 分块可经产品接口取回 51 | FAIL | fileId=51 ES=1 但 getFileChunks=0（点击引用定位的前提不成立） |
| S4 | 解析完成且 chunk 落地 52 | PASS | fileId=52 status=3 ES分块=2 接口返回=1 |
| S4 | 分块可经产品接口取回 52 | PASS | fileId=52 ES=2 接口=1 |
| S4 | 解析完成且 chunk 落地 53 | PASS | fileId=53 status=3 ES分块=1 接口返回=0 |
| S4 | 分块可经产品接口取回 53 | FAIL | fileId=53 ES=1 但 getFileChunks=0（点击引用定位的前提不成立） |
| S4 | 解析完成且 chunk 落地 54 | PASS | fileId=54 status=3 ES分块=2 接口返回=2 |
| S4 | 分块可经产品接口取回 54 | PASS | fileId=54 ES=2 接口=2 |
| S4 | 解析完成且 chunk 落地 55 | PASS | fileId=55 status=3 ES分块=1 接口返回=1 |
| S4 | 分块可经产品接口取回 55 | PASS | fileId=55 ES=1 接口=1 |
