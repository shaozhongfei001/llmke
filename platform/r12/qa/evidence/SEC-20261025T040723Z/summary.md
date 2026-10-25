# R13 安全验收 20261025T040723Z

总计 9/10 PASS

| 用例 | 结果 | 详情 |
|---|---|---|
| SEC-1 无授权读知识库详情被拒 | PASS | http=401 body={'errorCode': '30021', 'errorMsg': '没有足够的权限', 'success': False} |
| SEC-2 无授权删知识库被拒且数据未变 | PASS | http=401 before=1/R12???? after=1/R12???? |
| SEC-3 无授权按已知对象键取原文被拒 | PASS | http=401 key=r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx |
| SEC-4 无授权提问被拒 | PASS | http=401 body={'errorCode': '30021', 'errorMsg': '没有足够的权限', 'success': False} |
| SEC-5 只读授权账号可读详情 | FAIL | http=401 kbName=None |
| SEC-6 只读账号删知识库被拒 | PASS | http=401 after=1/R12???? |
| SEC-7 只读账号触发重解析被拒 | PASS | http=401 |
| SEC-8 超级管理员可读 | PASS | http=200 |
| SEC-9 撤权后读详情立即被拒 | PASS | http=401 body={'errorCode': '30021', 'errorMsg': '没有足够的权限', 'success': False} |
| SEC-10 库内口令为 BCrypt 而非 MD5 | PASS | admin	$2a$; r13_noauth	$2b$; r13_reader	$2b$ |
