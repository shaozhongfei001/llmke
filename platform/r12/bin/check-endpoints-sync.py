#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R14-LIVE-12：接口注册表与代码的同步门禁。

## 为什么需要这个门禁

网关做**接口级**鉴权：请求进来先查 `interface_info`（url+method 是否登记），
再查 `resource_interface`（该接口是否挂到某个菜单/资源），最后看角色有没有那个资源。
任何一环缺，返回的都是同一个错：

    401 {"errorCode":"30021","errorMsg":"没有足够的权限"}

于是"没登记"和"你没权限"在外部表现完全一样。这两天的两次故障都是这一类：
  · 17 条 /graph/* 只有 interface_info、没有 resource_interface → 图谱页全红；
  · /index/knowledgeBase/api/delete 压根没登记 → 删库接口 401（而前端走的是另一条路径）。

这类问题不能靠"踩到再补"，因为补的时候你并不确定还有几条没补。
所以做成门禁：**代码里有、注册表里没有** 就是一条待办，退出码非 0。

## 用法

    check-endpoints-sync.py                     # 只报告，缺失则退出码 1
    check-endpoints-sync.py --warn-only          # 只报告，永远退出 0（装机时用）
    check-endpoints-sync.py --fix                # 自动补 interface_info（不自动挂资源）
    check-endpoints-sync.py --fix --resource-id 8  # 补登记并挂到指定资源
    check-endpoints-sync.py --include-api        # 把 /api/** 也算进"缺失"（默认单列）

## 关于 /api/** 这一套（两套控制器是设计，不是重复实现）

· `XxxController`    → 路径 `/knowledgeBase/**`，主体来自 UserContext（JWT 会话），前端在调；
· `XxxApiController` → 路径 `/api/knowledgeBase/**`（含 context-path 即 `/index/api/knowledgeBase/**`），
  主体来自 OpenApiHeader（platform/userId；网关的 apiKey 分支见 AuthFilter），
  是给外部系统按 appKey 接入用的对外接口面。

两者是**两套认证主体**，不是同一功能的两次实现：内部面靠会话，对外面靠 appKey。
实测两套都已登记（/api 那套 43 条），所以它们都能用；真正的风险不是"存在两套"，
而是**两套各自演进时，注册表只跟上其中一套**。这个门禁同时覆盖两套，正是为了防止这一点。

（记录一次踩坑：我最初按 `/api/%` 查注册表得 0 条，便断定对外面未登记；
 实际存储形态带 context-path，是 `/index/api/%`。前缀不一致，结论就会反。）
"""

import argparse
import os
import re
import subprocess
import sys

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
R12 = os.path.dirname(BIN_DIR)
REPO = os.path.dirname(os.path.dirname(R12))

JAVA_PARENT = os.path.join(REPO, "services", "rag-java", "rag-parent")

MYSQL_CT = os.environ.get("R12_MYSQL_CT", "r12-mysql")
MYSQL_DB = os.environ.get("R12_MYSQL_DB", "gienrag")

METHODS = {"Get": "GET", "Post": "POST", "Put": "PUT", "Delete": "DELETE", "Patch": "PATCH"}


def mysql(sql):
    """读库：走 docker exec，避免脚本再引一个 mysql 客户端依赖。"""
    pw = os.environ.get("R12_MYSQL_ROOT_PASSWORD", "")
    if not pw:
        env_file = os.environ.get("R12_ENV_FILE", os.path.join(R12, ".env"))
        if os.path.isfile(env_file):
            with open(env_file, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("R12_MYSQL_ROOT_PASSWORD="):
                        pw = line.split("=", 1)[1].strip()
                        break
    if not pw:
        print("  [FAIL] 缺少 R12_MYSQL_ROOT_PASSWORD（或 platform/r12/.env）", file=sys.stderr)
        sys.exit(2)
    out = subprocess.run(
        ["docker", "exec", "-e", "MYSQL_PWD=" + pw, MYSQL_CT,
         "mysql", "-uroot", "--default-character-set=utf8mb4", "-N", "-B", MYSQL_DB, "-e", sql],
        capture_output=True, text=True)
    if out.returncode != 0:
        print("  [FAIL] 查库失败: " + (out.stderr or "").strip()[:200], file=sys.stderr)
        sys.exit(2)
    return out.stdout


def mysql_write(sql):
    pw = os.environ.get("R12_MYSQL_ROOT_PASSWORD", "")
    if not pw:
        env_file = os.environ.get("R12_ENV_FILE", os.path.join(R12, ".env"))
        if os.path.isfile(env_file):
            with open(env_file, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith("R12_MYSQL_ROOT_PASSWORD="):
                        pw = line.split("=", 1)[1].strip()
                        break
    return subprocess.run(
        ["docker", "exec", "-e", "MYSQL_PWD=" + pw, MYSQL_CT,
         "mysql", "-uroot", "--default-character-set=utf8mb4", "-N", "-B", MYSQL_DB, "-e", sql],
        capture_output=True, text=True)


# tools-database 这类是"库"，本身没有 application.yml，被 rag-index-service 打进同一个进程，
# 因此它的 context-path 取宿主服务的（实测 /index/database/** 走的就是 index 服务）。
CONTEXT_OVERRIDES = {"tools-database": "index"}


def discover_modules():
    """发现所有含 src/main/java 的模块，支持 rag-parent/tools/* 这一层。

    第一版只扫 rag-parent 的直接子目录，于是 tools-database 下 22 条 /index/database/**
    全被当成"注册表里的残留"。**扫不全会把活接口误判成死接口**，这和漏登记一样危险。
    """
    found = []
    for name in sorted(os.listdir(JAVA_PARENT)):
        if name == "target":
            continue
        path = os.path.join(JAVA_PARENT, name, "src", "main", "java")
        if os.path.isdir(path):
            found.append(name)
            continue
        nested = os.path.join(JAVA_PARENT, name)
        if not os.path.isdir(nested):
            continue
        for sub in sorted(os.listdir(nested)):
            if sub == "target":
                continue
            if os.path.isdir(os.path.join(nested, sub, "src", "main", "java")):
                found.append(sub)
    return found


def context_path(module_dir):
    """从外部配置覆盖目录或 jar 内配置取 server.servlet.context-path。"""
    candidates = [
        os.path.join(R12, "conf", module_dir, "application-r12.yml"),
        os.path.join(JAVA_PARENT, module_dir, "src", "main", "resources", "config", "application-r12.yml"),
        os.path.join(JAVA_PARENT, module_dir, "src", "main", "resources", "application-r12.yml"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        m = re.search(r"context-path:\s*([^\s#]+)", text)
        if m:
            return m.group(1).strip("'\"")
    return CONTEXT_OVERRIDES.get(module_dir, "")


def join_path(*parts):
    segs = []
    for p in parts:
        if not p:
            continue
        segs.extend([s for s in str(p).strip().strip("/").split("/") if s])
    return "/" + "/".join(segs)


def strip_comments(text):
    """剥掉 // 与 /* */ 注释。

    为什么必须做：AiController 里 `getRerankModelInfos` 整段是被注释掉的，
    不剥注释就会扫出一条"缺失接口"，然后去补登记一条**根本不存在的接口**——
    补完只会得到一个 404，比原来更难查。门禁的假阳性比漏报更消耗信任。
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    lines = []
    for line in text.split("\n"):
        idx = line.find("//")
        if idx >= 0 and '"' not in line[:idx]:
            line = line[:idx]
        lines.append(line)
    return "\n".join(lines)


def java_root(module_dir):
    """模块的源码根：先按 rag-parent/<mod> 找，再按 rag-parent/<组>/<mod> 找。"""
    direct = os.path.join(JAVA_PARENT, module_dir, "src", "main", "java")
    if os.path.isdir(direct):
        return direct
    for group in sorted(os.listdir(JAVA_PARENT)):
        nested = os.path.join(JAVA_PARENT, group, module_dir, "src", "main", "java")
        if os.path.isdir(nested):
            return nested
    return ""


def scan_module(module_dir):
    """返回 [(url, method, file:line)]。"""
    base = java_root(module_dir)
    if not base:
        return []
    ctx = context_path(module_dir)
    found = []
    for root, _dirs, files in os.walk(base):
        for name in files:
            if not name.endswith("Controller.java"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = strip_comments(fh.read())
            cm = re.search(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]*)"', text)
            class_path = cm.group(1) if cm else ""
            for m in re.finditer(r'@(Get|Post|Put|Delete|Patch)Mapping\s*(?:\(([^)]*)\))?', text):
                method = METHODS[m.group(1)]
                args = m.group(2) or ""
                pm = re.search(r'"([^"]*)"', args)
                method_path = pm.group(1) if pm else ""
                line = text[:m.start()].count("\n") + 1
                found.append((join_path(ctx, class_path, method_path), method, f"{name}:{line}"))
            # @RequestMapping(method = RequestMethod.X) 的写法
            for m in re.finditer(r'@RequestMapping\s*\(([^)]*RequestMethod\.[A-Z]+[^)]*)\)', text):
                body = m.group(1)
                mm = re.search(r'RequestMethod\.([A-Z]+)', body)
                pm = re.search(r'"([^"]*)"', body)
                if not mm:
                    continue
                line = text[:m.start()].count("\n") + 1
                found.append((join_path(ctx, class_path, pm.group(1) if pm else ""),
                              mm.group(1).upper(), f"{name}:{line}"))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="把缺失的接口补进 interface_info")
    ap.add_argument("--resource-id", type=int, default=0, help="补登记后挂到该资源 id（0=只登记不挂）")
    ap.add_argument("--include-api", action="store_true", help="把 /api/** 也算进缺失判定")
    ap.add_argument("--warn-only", action="store_true", help="永远退出 0（装机/巡检用）")
    args = ap.parse_args()

    modules = sorted(discover_modules())
    code = []
    for mod in modules:
        for url, method, where in scan_module(mod):
            code.append({"url": url, "method": method, "module": mod, "where": where})

    rows = mysql("select url, method, app_name, app_name_abbreviate from interface_info;")
    db = {}
    bucket_bad = []
    for line in rows.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        url, method = parts[0].strip(), parts[1].strip().upper()
        app = parts[2].strip() if len(parts) > 2 else ""
        abbr = parts[3].strip() if len(parts) > 3 else ""
        db[(url, method)] = app
        # R14-LIVE-13：网关的 authenticate() 用 **URL 首段** 作为权限缓存的 hash field
        # （AuthenticateAppServiceImpl: appName = url.substring(1, url.indexOf("/",1))）。
        # 若登记时的 app_name_abbreviate 与首段不一致，接口会被放进错误的桶，
        # 缓存里明明有这条、鉴权却永远 false —— 实测 /index/database/** 挂成 "database"
        # 时，请求表现为 401/30021，和"没登记"一模一样。
        seg = url.strip("/").split("/")[0]
        if abbr and seg and abbr != seg:
            bucket_bad.append((url, method, app, abbr, seg))

    missing = [c for c in code if (c["url"], c["method"]) not in db]
    openapi = [c for c in missing if "/api/" in c["url"]]
    runtime = [c for c in missing if "/api/" not in c["url"]]

    code_set = {(c["url"], c["method"]) for c in code}
    stale = [k for k in db if k not in code_set]

    print("== 接口注册表同步检查 ==")
    print(f"  代码侧接口   {len(code)} 条（{len(modules)} 个服务）")
    print(f"  注册表       {len(db)} 条")

    print(f"\n-- 缺失：代码有、注册表无（{len(runtime)} 条）--")
    if runtime:
        for c in sorted(runtime, key=lambda x: (x["module"], x["url"])):
            print(f"  [MISS] {c['method']:6s} {c['url']}   ({c['module']} {c['where']})")
        print("  影响：调这些接口一律 401/30021，表现与\"没权限\"完全相同，极难定位。")
    else:
        print("  [ok] 无")

    print(f"\n-- 开放 API 面 /api/**：代码有、注册表无（{len(openapi)} 条）--")
    if openapi:
        for c in sorted(openapi, key=lambda x: x["url"])[:8]:
            print(f"  [OPEN] {c['method']:6s} {c['url']}   ({c['module']} {c['where']})")
        if len(openapi) > 8:
            print(f"  ... 另有 {len(openapi) - 8} 条")
        print("  说明：这套是 OpenApiController（appKey/apiKey 主体）预留面，当前无登记、无密钥、前端不调用。")
        print("        对外提供则需登记 + 配密钥；不打算对外则建议下线，避免\"看着有、用着 401\"。")
    else:
        print("  [ok] 无")

    if bucket_bad:
        print(f"\n-- 分桶不一致（{len(bucket_bad)} 条：app_name_abbreviate ≠ URL 首段）--")
        for url, method, app, abbr, seg in bucket_bad[:8]:
            print(f"  [BUCKET] {method:6s} {url}  app={app} abbr={abbr} 首段={seg}")
        if len(bucket_bad) > 8:
            print(f"  ... 另有 {len(bucket_bad) - 8} 条")
        print("  影响：权限缓存按首段分桶，桶名不对 => 缓存里有这条也查不到 => 401/30021。")
    else:
        print("\n-- 分桶一致性 --\n  [ok] 无")

    if stale:
        print(f"\n-- 注册表有、代码无（{len(stale)} 条，可能是历史残留或跨服务声明）--")
        for url, method in sorted(stale)[:8]:
            print(f"  [STALE] {method:6s} {url}")
        if len(stale) > 8:
            print(f"  ... 另有 {len(stale) - 8} 条")
    else:
        print("\n-- 注册表有、代码无 --\n  [ok] 无")

    fail_items = runtime + (openapi if args.include_api else [])
    if bucket_bad:
        fail_items = fail_items + [{"url": b[0], "method": b[1], "module": b[2]} for b in bucket_bad]

    if args.fix and fail_items:
        print("\n-- 自动补登记 --")
        added = 0
        for c in fail_items:
            app = c["module"]
            abbr = app.replace("rag-", "").replace("-service", "")
            sql = ("insert into interface_info(app_name,app_name_abbreviate,name,url,method,"
                   "gmt_create,gmt_modified,create_by,update_by) values("
                   f"'{app}','{abbr}','{app}:{c['method']} {c['url']}','{c['url']}','{c['method']}',"
                   "now(),now(),'check-endpoints-sync','check-endpoints-sync');")
            res = mysql_write(sql)
            if res.returncode != 0:
                print(f"  [FAIL] {c['method']} {c['url']}: {(res.stderr or '').strip()[:120]}")
                continue
            added += 1
            if args.resource_id:
                mid = mysql(f"select id from interface_info where url='{c['url']}' and method='{c['method']}' order by id limit 1;").strip()
                if mid.isdigit():
                    mysql_write("insert into resource_interface(resource_id,interface_id,is_del,gmt_create,gmt_modified,"
                                "create_by,update_by) values("
                                f"{args.resource_id},{mid},1,now(),now(),'check-endpoints-sync','check-endpoints-sync');")
        print(f"  补登记 {added} 条" + (f"，并挂到 resource_id={args.resource_id}" if args.resource_id else "（未挂资源，接口仍会 403，需再挂 resource_interface）"))

    print()
    if fail_items:
        print(f"== 未通过：{len(fail_items)} 条接口未登记 ==")
        return 0 if args.warn_only else 1
    print("== 通过：代码与注册表一致 ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
