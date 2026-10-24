# R12 独立复核运行 20261024T204628Z

PASS=6 FAIL=2 BLOCKED=3

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S2 | 知识库存在(R12-QA-独立复核库) | PASS | kbId=2 primitive=kb_2 private=0 |
| S8 | N1 无 token 访问受保护接口 | PASS | 无 token http=401，对照 http=200 |
| S8 | N2 伪造 JWT（alg=none / 伪签名） | FAIL | 未被规范化拒绝(5xx，非放行，属健壮性/信息泄露缺陷): random->500 |
| S8 | N3 篡改 token payload 保留原签名 | PASS | 篡改 token http=401 |
| S8 | N4 会话注销后旧 token 复用 | PASS | 注销后旧 token http=401 |
| S2 | 知识库存在(R12-QA-私有库(admin属主)) | PASS | kbId=3 primitive=kb_3 private=1 |
| S8 | N5 越权：非属主读他人私有知识库 | BLOCKED | 返回 200 但 0 条（无法区分'空库'与'被过滤'，需换已有文件的库复测） |
| S8 | N5b 非属主按 fileId 直读他人文件 | PASS | http=200 data=null(未泄露) resp={"success": true, "errorMsg": null, "errorCode": null, "data": null} |
| S8 | N6 网关白名单端点未授权可达 | FAIL | 未带任何凭证即可进入业务链路: /index/knowledgeBase/file/list?kbId=1&type=1->500({'success': False, 'errorMsg': 'Cannot p), /index/knowledgeBase/file/multiple/version?kbId=1&type=1->500({'success': False, 'errorMsg': "\n### Er), /index/parseTask/callback->500({'success': False, 'errorMsg': 'Cannot i), /index/knowledgeBase/file/uploadParsedFile?kbId=1&fileId=1&userId=1->500({'success': False, 'errorMsg': '知识库文件不存在) |
| S8 | N7 坏文件必须明确失败（随机字节） | BLOCKED | 被环境错误挡住而非被内容识别（7009 模型未登记）：该 PASS 会空转，须在上传链可用后重测 |
| S8 | N8 扩展名伪装文件必须明确失败 | BLOCKED | 被环境错误挡住而非被内容识别（7009 模型未登记）：该 PASS 会空转，须在上传链可用后重测 |
