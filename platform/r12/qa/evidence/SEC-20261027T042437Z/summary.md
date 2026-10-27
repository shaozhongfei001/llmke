# R13 安全验收 20261027T042437Z

总计 16/16 PASS

| 用例 | 结果 | 详情 |
|---|---|---|
| SEC-1 无授权读知识库详情被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-2 无授权删知识库被拒且数据未变 | PASS | http=403 before=1/R12???? after=1/R12???? |
| SEC-3 无授权按已知对象键取原文被拒 | PASS | http=403 key=r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx |
| SEC-4 无授权提问被对象级授权拒绝 | PASS | http=403 errorCode=30016 configId=1 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-5 只读授权账号可读详情 | PASS | http=200 kbName=R12验收主链 |
| SEC-6 只读账号删知识库被拒 | PASS | http=403 after=1/R12???? |
| SEC-7 只读账号触发重解析被拒 | PASS | http=403 |
| SEC-8 超级管理员可读 | PASS | http=200 |
| SEC-9 撤权后读详情立即被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-10 库内口令为 BCrypt 而非 MD5 | PASS | admin	$2a$; r13_noauth	$2b$; r13_reader	$2b$ |
| SEC-11 属主可预览（返回真实 PDF） | PASS | http=200 head=%PDF-1.7 |
| SEC-12 无授权账号预览被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
| SEC-13 匿名预览被拒 | PASS | http=401 |
| SEC-14 前端 /preview/ 匿名直连已关闭 | PASS | http=403 |
| SEC-15 存储匿名直取被拒（直连+反代） | PASS | minio=403 nginx=403 |
| SEC-16 无法归属知识库的对象键被拒 | PASS | http=403 body={'success': False, 'errorMsg': '没有足够权限', 'errorCode': '30016', 'data': None} |
