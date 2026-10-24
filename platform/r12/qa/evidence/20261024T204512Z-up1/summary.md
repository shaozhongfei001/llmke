# R12 独立复核运行 20261024T204512Z

PASS=1 FAIL=5 BLOCKED=0

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S2 | 知识库存在(R12-QA-独立复核库) | PASS | kbId=2 primitive=kb_2 private=0 |
| S3 | 上传 PDF 数字版 | FAIL | http=500 resp={"success": false, "errorMsg": "模型类型不能为空", "errorCode": "7009", "data": null} |
| S3 | 上传 DOCX 含表格 | FAIL | http=500 resp={"success": false, "errorMsg": "模型类型不能为空", "errorCode": "7009", "data": null} |
| S3 | 上传 XLSX 表格 | FAIL | http=500 resp={"success": false, "errorMsg": "模型类型不能为空", "errorCode": "7009", "data": null} |
| S3 | 上传 PPTX 图片页 | FAIL | http=500 resp={"success": false, "errorMsg": "模型类型不能为空", "errorCode": "7009", "data": null} |
| S3 | 上传 扫描图片(纯图) | FAIL | http=500 resp={"success": false, "errorMsg": "模型类型不能为空", "errorCode": "7009", "data": null} |
