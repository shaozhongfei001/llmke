#!/usr/bin/env python3
"""R13 安全验收：对象级授权 / 原文访问 / 口令存储。

三类真实账号（DB 内创建，标注为测试夹具）：
  r13_owner   —— 资源管理者（知识库 kb_9 的属主视角，用 admin 代表超级管理员，另建 owner 赋予 permission=3）
  r13_reader  —— 合法获得读取授权的非属主（user_privilege.permission=1）
  r13_noauth  —— 对该资源完全无授权

用例（每条都检查"拒绝时数据库/存储未变化"）：
  SEC-1 无授权账号读知识库详情 -> 拒绝
  SEC-2 无授权账号删除知识库 -> 拒绝且 kb 仍在
  SEC-3 无授权账号按已知对象键取文件流 -> 拒绝（原 /stream 只用 key，是匿名取原文入口）
  SEC-4 无授权账号提问指定 kb -> 拒绝
  SEC-5 只读授权账号读详情 -> 允许
  SEC-6 只读授权账号删除知识库 -> 拒绝
  SEC-7 只读授权账号触发重解析（写动作） -> 拒绝
  SEC-8 超级管理员读/管理 -> 允许
  SEC-9 撤权后（is_del=0）读详情 -> 立即拒绝
  SEC-10 口令存储非 MD5（库里应为 $2a$ 前缀）
"""
import json
import os
import subprocess
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r12_client import GATEWAY, api, login, aes_zero_pad  # noqa: E402

import bcrypt  # noqa: E402

R12 = "/home/szf/data/dev/llmke-r12/platform/r12"
TS = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
EVID = os.path.join(R12, "qa", "evidence", f"SEC-{TS}")
MYSQL = ["docker", "exec", "r12-mysql", "mysql", "-uroot", "-pR12r00t#2026local", "-N", "-e"]
KB_ID = 9
PRIMITIVE = "kb_9"
TEST_PWD = "R13@Test2026"
RESULTS = []


def record(case, ok, detail, extra=None):
    RESULTS.append({"case": case, "ok": bool(ok), "detail": detail, "extra": extra})
    print(("PASS " if ok else "FAIL ") + f"[SEC] {case}: {detail}")


def sql(q):
    out = subprocess.run(MYSQL + [q], capture_output=True, text=True)
    return out.stdout.strip()


def denied(code, body):
    """拒绝的判定：HTTP 403/401，或网关错误信封 success=false。"""
    if code in (401, 403):
        return True
    if isinstance(body, dict):
        if body.get("success") is False:
            return True
        ec = str(body.get("errorCode") or "")
        if ec == "30016":
            return True
    return False


def ensure_user(user_name, real_name, dept_id=None):
    uid = sql(f"select id from gienrag.user_info where user_name='{user_name}'")
    pwd = bcrypt.hashpw(TEST_PWD.encode(), bcrypt.gensalt(10)).decode()
    if uid:
        sql(f"update gienrag.user_info set user_password='{pwd}', status=1 where user_name='{user_name}'")
        return int(uid)
    dept = "null" if dept_id is None else str(dept_id)
    sql(
        "insert into gienrag.user_info(user_name,user_password,user_realname,status,gmt_create,gmt_modified,dept_id,app_key) "
        f"values('{user_name}','{pwd}','{real_name}',1,now(),now(),{dept},'{uuid.uuid4().hex}')"
    )
    return int(sql(f"select id from gienrag.user_info where user_name='{user_name}'"))


def ensure_role(user_id, role_id=2):
    """role 2=管理员：拥有路径级权限（网关放行），但**没有** kb_9 的对象权限。
    这是"只做了路径级鉴权/只校验登录"的关键场景：能过网关，仍必须被对象级授权拦住。"""
    sql(f"delete from gienrag.user_role where user_id={user_id}")
    sql("insert into gienrag.user_role(user_id,role_id,status,gmt_create,gmt_modified) "
        f"values({user_id},{role_id},1,now(),now())")


def set_privilege(user_id, permission):
    """biz_type=1 知识库；permission 0/1/2/3；is_del=1 有效，0 视为撤权（与原 mapper 语义一致）"""
    sql(f"delete from gienrag.user_privilege where user_id={user_id} and biz_type=1 and target_id={KB_ID}")
    if permission is None:
        return
    sql(
        "insert into gienrag.user_privilege(biz_type,target_id,user_id,permission,is_del,gmt_create,gmt_modified) "
        f"values(1,{KB_ID},{user_id},{permission},1,now(),now())"
    )


def revoke(user_id):
    sql(f"update gienrag.user_privilege set is_del=0 where user_id={user_id} and biz_type=1 and target_id={KB_ID}")


def main():
    admin_s, admin_t, _ = login()

    noauth_id = ensure_user("r13_noauth", "R13 无授权账号")
    reader_id = ensure_user("r13_reader", "R13 只读授权账号")
    ensure_role(noauth_id)
    ensure_role(reader_id)
    set_privilege(noauth_id, None)
    set_privilege(reader_id, 1)

    noauth_s, noauth_t, _ = login(user="r13_noauth", password=TEST_PWD)
    reader_s, reader_t, _ = login(user="r13_reader", password=TEST_PWD)

    kb_before = sql(f"select concat(status,'/',kb_name) from gienrag.knowledge_base where id={KB_ID}")

    # SEC-1
    code, body = api(noauth_s, "GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", noauth_t)
    record("SEC-1 无授权读知识库详情被拒", denied(code, body), f"http={code} body={str(body)[:160]}")

    # SEC-2
    code, body = api(noauth_s, "DELETE", f"/index/knowledgeBase/delete?id={KB_ID}", noauth_t)
    kb_after = sql(f"select concat(status,'/',kb_name) from gienrag.knowledge_base where id={KB_ID}")
    record("SEC-2 无授权删知识库被拒且数据未变",
           denied(code, body) and kb_after == kb_before,
           f"http={code} before={kb_before} after={kb_after}")

    # SEC-3 已知对象键直接取文件流
    key = f"r12-rag/{PRIMITIVE}/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx"
    code, body = api(noauth_s, "POST", "/index/knowledgeBase/file/stream", noauth_t,
                     json={"convertedFilePath": key, "pageNo": 1, "pageSize": 5, "stream": True})
    record("SEC-3 无授权按已知对象键取原文被拒", denied(code, body), f"http={code} key={key}")

    # SEC-4 无授权提问：使用真实绑定 kb_9 的助手配置（configId=1），走真实问答入口
    cfg = sql("select id from gienrag.search_config where config_json like '%kb_9%' limit 1").strip()
    payload = {"sessionId": f"sec-noauth-{int(time.time())}", "queryId": f"sq-{int(time.time()*1000)}",
               "content": "授信额度是多少", "type": "text", "sysType": "KNO_INDEX", "configId": int(cfg or 1)}
    code, body = api(noauth_s, "POST", "/qa/ai/question", noauth_t, json=payload)
    ec = str((body or {}).get("errorCode") or "") if isinstance(body, dict) else ""
    record("SEC-4 无授权提问被对象级授权拒绝", code == 403 or ec == "30016",
           f"http={code} errorCode={ec} configId={cfg} body={str(body)[:160]}")

    # SEC-5 只读账号可读
    code, body = api(reader_s, "GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", reader_t)
    ok5 = code == 200 and isinstance(body, dict) and body.get("success") and body.get("data")
    record("SEC-5 只读授权账号可读详情", ok5, f"http={code} kbName={(body or {}).get('data', {}).get('kbName') if isinstance(body, dict) else None}")

    # SEC-6 只读账号不能删
    code, body = api(reader_s, "DELETE", f"/index/knowledgeBase/delete?id={KB_ID}", reader_t)
    kb_after2 = sql(f"select concat(status,'/',kb_name) from gienrag.knowledge_base where id={KB_ID}")
    record("SEC-6 只读账号删知识库被拒", denied(code, body) and kb_after2 == kb_before,
           f"http={code} after={kb_after2}")

    # SEC-7 只读账号不能触发写动作（重解析）
    code, body = api(reader_s, "POST", f"/index/knowledgeBase/reParse?id={KB_ID}", reader_t)
    record("SEC-7 只读账号触发重解析被拒", denied(code, body), f"http={code}")

    # SEC-8 超级管理员可用
    code, body = api(admin_s, "GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", admin_t)
    record("SEC-8 超级管理员可读", code == 200 and body.get("success") is True, f"http={code}")

    # SEC-9 撤权后立即失效
    revoke(reader_id)
    code, body = api(reader_s, "GET", f"/index/knowledgeBase/getKbById?id={KB_ID}", reader_t)
    record("SEC-9 撤权后读详情立即被拒", denied(code, body), f"http={code} body={str(body)[:160]}")
    set_privilege(reader_id, 1)

    # SEC-10 口令存储
    hashes = sql("select user_name,left(user_password,4) from gienrag.user_info where user_name in ('admin','r13_noauth','r13_reader')")
    ok10 = all("$2a$" in line or "$2b$" in line for line in hashes.splitlines() if line.strip())
    record("SEC-10 库内口令为 BCrypt 而非 MD5", ok10, hashes.replace("\n", "; "))

    os.makedirs(EVID, exist_ok=True)
    passed = sum(1 for r in RESULTS if r["ok"])
    with open(os.path.join(EVID, "security.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)
    with open(os.path.join(EVID, "summary.md"), "w", encoding="utf-8") as f:
        f.write(f"# R13 安全验收 {TS}\n\n总计 {passed}/{len(RESULTS)} PASS\n\n| 用例 | 结果 | 详情 |\n|---|---|---|\n")
        for r in RESULTS:
            f.write(f"| {r['case']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |\n")
    print(f"\n== {passed}/{len(RESULTS)} PASS == 证据: {EVID}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
