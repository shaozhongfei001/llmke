#!/usr/bin/env python3
"""R12 初始化种子：角色 / 管理员账号 / 菜单 / 接口权限。

背景（事实，来自源码）：
- 鉴权链：user_info -> user_role -> role_info -> role_resource -> resource_info(resource_type=2)
  -> resource_interface -> interface_info(url, method, app_name_abbreviate)
- 网关 AuthFilter 只校验 JWT；下游 `AuthenticateAppServiceImpl.authenticate` 再按
  `url.substring(1, url.indexOf('/',1))` 取 appName 查 Redis 里的接口清单做精确匹配。
- 因此必须把「各应用前缀」的 OPER 资源与 interface_info 建好关联，否则除 noToken/noAuth 外的
  所有业务接口都会被判定为无权限。

本脚本生成的是「新建空库初始化数据」，不是旧库迁移数据；执行前会打印将写入的行数。
"""
import hashlib
import os
import re
import subprocess
import sys

MYSQL = [
    "docker", "exec", "-i", "r12-mysql", "mysql", "--default-character-set=utf8mb4",
    "-uroot", "-p${R12_MYSQL_PASSWORD}", "gienrag",
]

ROOT = "/home/szf/data/dev/llmke-r12"
AUTH_SRC = f"{ROOT}/services/rag-java/rag-parent/rag-auth-service/src/main/java/com/gientech/ragauthservice/interfaces"

PLAIN_PASSWORD = "Admin@12345"


def md5_hex_like_java(s: str) -> str:
    """复刻 `new BigInteger(1, digest).toString(16)`：无前导零补位。"""
    d = hashlib.md5(s.encode("utf-8")).hexdigest()
    return d.lstrip("0") or "0"


def sql(stmt: str) -> str:
    p = subprocess.run(MYSQL + ["-N", "-e", stmt], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"mysql failed: {p.stderr[:400]}\nSQL: {stmt[:200]}")
    return p.stdout


def scan_auth_interfaces():
    """扫描 auth 控制器，产出去重后的 (url, METHOD) 列表（等价 InitInterface 逻辑）。"""
    out = set()
    for fn in sorted(os.listdir(AUTH_SRC)):
        if not fn.endswith(".java"):
            continue
        src = open(os.path.join(AUTH_SRC, fn), encoding="utf-8").read()
        m = re.search(r'@RequestMapping\(\s*(?:value\s*=\s*)?"([^"]+)"', src)
        prefix = m.group(1) if m else ""
        prefix = prefix.strip("/")
        for mm in re.finditer(
            r'@(Post|Get|Put|Delete)Mapping\(\s*(?:value\s*=\s*)?"?([^")\s]*)"?', src
        ):
            method, sub = mm.group(1).upper(), mm.group(2)
            sub = sub.strip("/")
            url = "/auth/" + "/".join([p for p in [prefix, sub] if p])
            out.add((url, method))
    return sorted(out)


def main():
    pwd_hash = md5_hex_like_java(PLAIN_PASSWORD)
    stmts = []

    # 1) 角色
    stmts.append("DELETE FROM role_resource;")
    stmts.append("DELETE FROM role_info;")
    stmts.append(
        "INSERT INTO role_info(id,name,description,seq,status,is_dtl,gmt_create,gmt_modified) VALUES"
        "(1,'超级管理员','平台内置超级管理员',1,1,'0',NOW(),NOW()),"
        "(2,'管理员','知识库管理员',2,1,'0',NOW(),NOW()),"
        "(3,'普通用户','默认业务用户',3,1,'0',NOW(),NOW());"
    )

    # 2) 管理员账号（重建，口令 md5(AES 解密后明文)）
    stmts.append("DELETE FROM user_role;")
    stmts.append("DELETE FROM user_info WHERE user_name='admin';")
    stmts.append(
        "INSERT INTO user_info(user_name,user_password,user_realname,status,"
        "dept_id,dept_name,organization_id,app_key,system_source,is_dtl,gmt_create,gmt_modified,create_by) VALUES"
        f"('admin','{pwd_hash}','系统管理员',1,1,'总部',1,'rag-qa',1,'0',NOW(),NOW(),'seed');"
    )
    stmts.append(
        "INSERT INTO user_role(user_id,role_id) SELECT id,1 FROM user_info WHERE user_name='admin';"
    )

    # 3) 菜单（resource_type=1）
    stmts.append("DELETE FROM resource_info;")
    menus = [
        ("智能对话", "/chats/main", "chat", 1),
        ("知识库", "/chats/knowledgeBase", "book", 2),
        ("知识检索", "/chats/knowledgeSearch", "search", 3),
        ("助手配置", "/chats/setting", "setting", 4),
        ("用户反馈", "/chats/feedback", "feedback", 5),
        ("敏感词", "/chats/sensitiveWords", "shield", 6),
        ("系统管理", "/system", "system", 7),
    ]
    values = ",".join(
        f"('{n}','{u}','{u}','menu',NULL,{s},'1','1','{c}',NOW(),NOW())" for n, u, c, s in menus
    )
    stmts.append(
        "INSERT INTO resource_info(name,url,description,icon,pid,seq,status,resource_type,code,gmt_create,gmt_modified) VALUES "
        + values + ";"
    )

    # 4) 每个应用前缀一个 OPER 资源
    apps = [("index", "知识库索引服务"), ("qa", "问答服务"), ("auth", "认证服务"),
            ("sensitive", "敏感词服务"), ("graph", "图谱服务")]
    values = ",".join(
        f"('{a}-api','/{a}/**','{d}','api',NULL,{i+10},'1','2','{a}',NOW(),NOW())"
        for i, (a, d) in enumerate(apps)
    )
    stmts.append(
        "INSERT INTO resource_info(name,url,description,icon,pid,seq,status,resource_type,code,gmt_create,gmt_modified) VALUES "
        + values + ";"
    )

    # 5) auth 接口登记（其它应用由各服务 InitInterface 自动登记）
    stmts.append("DELETE FROM interface_info WHERE app_name_abbreviate='auth';")
    pairs = scan_auth_interfaces()
    if pairs:
        vals = ",".join(
            f"('rag-auth-service','auth','{u}','{u}','{m}',NOW(),NOW(),'seed','seed')" for u, m in pairs
        )
        stmts.append(
            "INSERT INTO interface_info(app_name,app_name_abbreviate,name,url,method,gmt_create,gmt_modified,create_by,update_by) VALUES "
            + vals + ";"
        )

    # 6) resource_interface：把接口挂到对应应用的 OPER 资源
    stmts.append("DELETE FROM resource_interface;")
    stmts.append(
        "INSERT INTO resource_interface(resource_id,interface_id,is_del,gmt_create,gmt_modified,create_by,update_by) "
        "SELECT r.id, i.id, 1, NOW(), NOW(), 'seed','seed' FROM resource_info r JOIN interface_info i "
        "ON i.app_name_abbreviate = r.code WHERE r.resource_type='2';"
    )

    # 7) 角色授权：超管/管理员拿全部（菜单+接口），普通用户拿菜单
    stmts.append(
        "INSERT INTO role_resource(role_id,resource_id,status,gmt_create,gmt_modified) "
        "SELECT 1, id, 1, NOW(), NOW() FROM resource_info;"
    )
    stmts.append(
        "INSERT INTO role_resource(role_id,resource_id,status,gmt_create,gmt_modified) "
        "SELECT 2, id, 1, NOW(), NOW() FROM resource_info;"
    )
    stmts.append(
        "INSERT INTO role_resource(role_id,resource_id,status,gmt_create,gmt_modified) "
        "SELECT 3, id, 1, NOW(), NOW() FROM resource_info WHERE resource_type='1';"
    )

    print(f"[seed] auth interfaces scanned: {len(pairs)}")
    print(f"[seed] admin password plaintext: {PLAIN_PASSWORD}  md5(hex)={pwd_hash}")
    for s in stmts:
        sql(s)
    print("[seed] done")
    print(sql("SELECT (SELECT COUNT(*) FROM role_info) roles,(SELECT COUNT(*) FROM user_info) users,"
              "(SELECT COUNT(*) FROM resource_info) res,(SELECT COUNT(*) FROM interface_info) ifaces,"
              "(SELECT COUNT(*) FROM resource_interface) res_iface,(SELECT COUNT(*) FROM role_resource) role_res;"))


if __name__ == "__main__":
    sys.exit(main())
