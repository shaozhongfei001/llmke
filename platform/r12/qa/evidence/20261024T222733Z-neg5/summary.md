# R12 独立复核运行 20261024T222733Z

PASS=11 FAIL=2 BLOCKED=0

| 场景 | 用例 | 结论 | 说明 |
|---|---|---|---|
| S2 | 知识库存在(qa_r12_final) | PASS | kbId=10 primitive=kb_10 private=0 |
| S8 | N1 无 token 访问受保护接口 | PASS | 无 token http=401，对照 http=200 |
| S8 | N2 伪造 JWT（alg=none / 伪签名） | PASS | 3 种伪造 token 全部拒绝: alg_none->401, wrong_sig->401, random->401 |
| S8 | N3 篡改 token payload 保留原签名 | PASS | 篡改 token http=401 |
| S8 | N4 会话注销后旧 token 复用 | PASS | 注销后旧 token http=401 |
| S2 | 知识库存在(qa_r12_priv) | PASS | kbId=7 primitive=kb_7 private=1 |
| S8 | N5 越权：非属主读他人私有知识库 | FAIL | 越权：非属主 qa_user_b 读到他人私有库 kbId=7（owner=admin）共 1 条文件记录 |
| S8 | N5b 非属主按 fileId 直读他人文件 | PASS | http=200 data=null(未泄露) resp={"success": true, "errorMsg": null, "errorCode": null, "data": null} |
| S8 | N5c 越权删除他人私有库文件 | PASS | file_id=56 http=200 resp={"success": true, "errorMsg": null, "errorCode": null, "data": false} |
| S8 | N6 网关白名单端点未授权可达 | PASS | 2 个白名单端点均返回 (401, 403) |
| S8 | N6b 内部回写入口仍免 token（R12-KNOWN-01） | FAIL | 未授权可达: /index/parseTask/callback->500({'success': False, 'errorMsg': 'Cannot i); /index/knowledgeBase/file/uploadParsedFile?kbId=1&fileId=1&userId=1->500({'success': False, 'errorMsg': '知识库不存在',) |
| S8 | N7 坏文件必须明确失败（随机字节） | PASS | 进入解析失败态 status=4，chunk=0 |
| S8 | N8 扩展名伪装文件必须明确失败 | PASS | 进入解析失败态 status=4，chunk=0 |
