#!/usr/bin/env python3
"""QA 用例依赖的测试夹具（明确标注为测试夹具，非产品改动）。

只做两件事：
1) 建一个「第二个用户」用于越权对照（走 DB 直插，等价于运维开户，不改业务代码）；
2) 打印夹具清理 SQL（不自动执行，避免销毁证据）。

安全约束：口令从 platform/r12/.env 读取，不打印。
"""
import hashlib
import os
import subprocess

ENV_FILE = "/home/szf/data/dev/llmke-r12/platform/r12/.env"

USER_B = "qa_user_b"          # 角色 2（管理员资源集，仅用于证明"非属主也能读到"）
USER_B_PW = "Qa!2345678"
USER_C = "qa_user_c"          # 角色 3（普通用户，验证最小权限是否真的最小）
USER_C_PW = "Qa!2345678"


def _env():
    out = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def mysql(sql):
    env = _env()
    pw = env["R12_MYSQL_ROOT_PASSWORD"]
    r = subprocess.run(
        ["mysql", "-h127.0.0.1", "-P13306", "-uroot", f"-p{pw}", "gienrag",
         "-N", "-e", sql],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"mysql 失败: {r.stderr[:300]}")
    return [l for l in r.stdout.splitlines() if l.strip()]


def ensure_user(user, password, role_id):
    md5 = hashlib.md5(password.encode()).hexdigest()
    exist = mysql(f"select id from user_info where user_name='{user}'")
    if exist:
        uid = exist[0].split("\t")[0]
    else:
        mysql("insert into user_info(user_name,user_password,user_realname,status,create_by,"
              "gmt_create,gmt_modified,is_dtl) values("
              f"'{user}','{md5}','QA夹具用户',1,'qa-fixture',now(),now(),'0')")
        uid = mysql(f"select id from user_info where user_name='{user}'")[0].split("\t")[0]
    mysql(f"delete from user_role where user_id={uid}")
    mysql(f"insert into user_role(role_id,user_id,status,is_dtl,gmt_create,gmt_modified,create_by)"
          f" values({role_id},{uid},1,'0',now(),now(),'qa-fixture')")
    return int(uid)


def main():
    ub = ensure_user(USER_B, USER_B_PW, 2)
    uc = ensure_user(USER_C, USER_C_PW, 3)
    print(f"夹具就绪: {USER_B}(id={ub}, role=2) {USER_C}(id={uc}, role=3)")
    print("清理 SQL（人工执行，勿自动跑，会销毁证据）:")
    print(f"  delete from user_role where user_id in ({ub},{uc});")
    print(f"  delete from user_info where id in ({ub},{uc});")


if __name__ == "__main__":
    main()
