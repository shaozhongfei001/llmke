#!/usr/bin/env python3
"""P0-01 仪器：从 Java 源码提取路由，与「接口总表 CSV」比对。

为什么需要：
    P0-01 的已知事实是"清单记录数 506 ≠ 运行时可路由数"，且其中一个处理函数被记录成
    另一个方法名、其 @GetMapping 连同方法已被 // 注释。
    要把它变成可判定结论，必须能从源码重建路由表，而不是相信清单。

它检查什么：
    1. 源码里**活代码**中的路由（注释里的不算）；
    2. 与清单的三类差异：清单有源码无 / 源码有清单无 / 路径相同但方法或处理函数不同；
    3. 单独列出"只存在于注释里"的路由（这正是 P0-01 的第一条事实）。

它不判定什么：
    - 运行时是否真的可达（需要启动服务/框架扫描），静态提取只能证明"注解存在"；
    - 鉴权与网关路由（不在本工具范围）。

用法：
    python3 docs/baseline/validation/p0-01-route-extract.py \
        --src /path/to/gien-rag/rag-parent --csv docs/upstream/源码接口契约-接口总表.csv \
        [--out /tmp/routes.csv]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

# 注意：`@GetMapping` 允许**不带括号**（路径全在类级 @RequestMapping 上），
# 早先要求必须有 `(...)` 会漏掉这类接口——实测 rag-auth-service 的 /roleResource 三条就因此漏掉。
MAPPING_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch|Request)Mapping\b\s*(?:\(([^)]*)\))?", re.S)
STR_RE = re.compile(r'"([^"]*)"')
REQ_METHOD_RE = re.compile(r"RequestMethod\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)")
CLASS_RE = re.compile(r"(?:public\s+|final\s+|abstract\s+)*(?:class|interface)\s+(\w+)")
HANDLER_RE = re.compile(r"([A-Za-z_]\w*)\s*\(")


def split_code_and_comments(text: str):
    """把源码切成「活代码」与「注释内容」两份，正确处理字符串与块注释。"""
    code, comments = [], []
    i, n = 0, len(text)
    in_str = in_chr = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_str:
            code.append(c)
            if c == "\\":
                if nxt:
                    code.append(nxt)
                    i += 2
                    continue
            elif c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            code.append(c)
            if c == "\\":
                if nxt:
                    code.append(nxt)
                    i += 2
                    continue
            elif c == "'":
                in_chr = False
            i += 1
            continue
        if c == '"':
            in_str = True
            code.append(c)
            i += 1
            continue
        if c == "'":
            in_chr = True
            code.append(c)
            i += 1
            continue
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j == -1 else j
            comments.append(text[i:j])
            code.append("\n" * text.count("\n", i, j) or "\n")
            i = j
            continue
        if c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            seg = text[i:j]
            comments.append(seg)
            code.append("\n" * seg.count("\n") or "\n")   # 保留行号
            i = j
            continue
        code.append(c)
        i += 1
    return "".join(code), "\n".join(comments)


def extract_from_text(text: str, service: str, src_file: str, comment_only: bool):
    """从一段文本里抽取路由。comment_only 仅用于标注来源，不影响解析规则。"""
    out = []
    matches = list(MAPPING_RE.finditer(text))
    if not matches:
        return out

    # 类级别前缀：出现在 class 声明之前的最后一个 @RequestMapping
    prefix = ""
    first_method_idx = 0                      # 无 class 声明（如注释片段）时不要跳过前面的注解
    cm = CLASS_RE.search(text)
    if cm:
        for idx, m in enumerate(matches):
            if m.start() < cm.start() and m.group(1) == "Request":
                s = STR_RE.search(m.group(2))
                prefix = s.group(1) if s else ""
                first_method_idx = idx + 1
            elif m.start() < cm.start():
                first_method_idx = idx + 1

    for m in matches[first_method_idx:]:
        kind, attrs = m.group(1), (m.group(2) or "")
        s = STR_RE.search(attrs)
        path = s.group(1) if s else ""
        if kind == "Request":
            rm = REQ_METHOD_RE.findall(attrs)
            methods = [x.upper() for x in rm] or ["ANY"]
        else:
            methods = [kind.upper()]
        for meth in methods:
            # 处理函数：注解之后第一个标识符+(
            tail = text[m.end():m.end() + 800]
            handler = find_handler(tail)
            line = text.count("\n", 0, m.start()) + 1
            full = (prefix.rstrip("/") + "/" + path.lstrip("/")).rstrip("/") or "/"
            out.append({
                "service": service, "method": meth, "path": normalize_path(full),
                "handler": handler, "src_file": src_file, "line": line,
                "comment_only": comment_only,
            })
    return out


METHOD_DECL_RE = re.compile(
    r"\b(?:public|private|protected|static|final|synchronized|abstract|default)\b[^;{()]*?\b(\w+)\s*\(")


def find_handler(tail: str) -> str:
    """注解之后的方法名：跳过 @Xxx(...) 与修饰符，取第一个方法声明。

    不能简单地"注解后第一个 identifier("——@OperationLog(...) 这类注解会被误判成方法名。
    先剥掉注解，再找带修饰符的方法声明；仍找不到时退回裸声明。
    """
    cleaned = re.sub(r"@\w+\s*(\([^()]*(\([^()]*\)[^()]*)*\))?", " ", tail)
    m = METHOD_DECL_RE.search(cleaned)
    if m:
        return m.group(1)
    m = re.match(r"\s*[\w<>\[\],.\s?]+?\s(\w+)\s*\(", cleaned)
    return m.group(1) if m else ""


def normalize_path(p: str) -> str:
    p = re.sub(r"\{[^}]*\}", "{*}", p)     # 路径变量归一
    return re.sub(r"/{2,}", "/", p)


def service_of(path: Path) -> str:
    parts = path.parts
    for i, part in enumerate(parts):
        if part == "rag-parent" and i + 1 < len(parts):
            nxt = parts[i + 1]
            if nxt == "tools" and i + 2 < len(parts):
                return "tools/" + parts[i + 2]      # 清单里的服务名就是 tools/tools-database
            return nxt
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--show-commented", action="store_true", default=True)
    ap.add_argument("--stack", default="Java", help="只比对该栈的清单行；ALL 表示全部")
    a = ap.parse_args()

    if not a.src.is_dir():
        print(f"FAIL: 源码目录不存在: {a.src}")
        return 2
    files = sorted(a.src.rglob("*.java"))
    if not files:
        print(f"FAIL: 未找到 .java 文件: {a.src}")
        return 2

    live, commented, feign = [], [], 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        code, comments = split_code_and_comments(text)
        # @FeignClient 是**调用方**，不是服务端路由。不排除会把"出站调用"误算成"对外接口"，
        # 使"源码有、清单无"被系统性夸大。
        if "@FeignClient" in code:
            feign += 1
            continue
        rel = str(f)
        live += extract_from_text(code, service_of(f), rel, False)
        if comments.strip():
            commented += extract_from_text(comments, service_of(f), rel, True)

    if a.out:
        with a.out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(live[0].keys()) if live else
                               ["service", "method", "path", "handler", "src_file", "line", "comment_only"])
            w.writeheader()
            w.writerows(live)

    rows = list(csv.DictReader(a.csv.read_text(encoding="utf-8-sig").splitlines()))
    stack_key = "栈"
    if a.stack != "ALL":
        rows = [r for r in rows if r.get(stack_key) == a.stack]      # 源码树只含 Java，Python 不在其中
    print(f"源码 .java 文件={len(files)}（其中 Feign 客户端 {feign} 个，已排除）  "
          f"活代码路由={len(live)}  注释中路由={len(commented)}  清单路由={len(rows)}")

    live_keys = Counter((r["service"], r["method"], normalize_path(r["path"])) for r in live)
    cmt_keys = Counter((r["service"], r["method"], normalize_path(r["path"])) for r in commented)
    csv_keys = Counter((r["服务/模块"], (r["方法"] or "ANY").upper(), normalize_path(r["路径"])) for r in rows)

    only_csv = sorted(set(csv_keys) - set(live_keys))
    only_src = sorted(set(live_keys) - set(csv_keys))
    print(f"\n清单有、源码无 = {len(only_csv)}   源码有、清单无 = {len(only_src)}")
    for k in only_csv[:15]:
        hit = "（注释中确实存在）" if cmt_keys.get(k) else ""
        print(f"  CSV_ONLY: {k[1]:6} {k[2]}  [{k[0]}]{hit}")
    for k in only_src[:15]:
        print(f"  SRC_ONLY: {k[1]:6} {k[2]}  [{k[0]}]")

    # 同名路径但处理函数不同（P0-01 记录的具体缺陷）
    by_path_csv = {(r["服务/模块"], (r["方法"] or "ANY").upper(), normalize_path(r["路径"])): r
                   for r in rows}
    handler_mismatch = []
    for r in live:
        k = (r["service"], r["method"], r["path"])
        c = by_path_csv.get(k)
        if c and c["处理函数"] and r["handler"] and c["处理函数"] != r["handler"]:
            handler_mismatch.append((k, c["处理函数"], r["handler"]))
    print(f"\n处理函数不一致 = {len(handler_mismatch)}")
    for k, a_, b_ in handler_mismatch[:10]:
        print(f"  HANDLER_DIFF: {k[1]:6} {k[2]}  清单={a_} 源码={b_}")

    if commented:
        print(f"\n注释中仍保留的路由（共 {len(commented)} 条，前 10）：")
        for r in commented[:10]:
            print(f"  COMMENTED: {r['method']:6} {r['path']}  ({Path(r['src_file']).name}:{r['line']})")

    print("\n结论: 上述三类差异 + 注释路由即为 P0-01 待裁定清单；"
          "本工具只证明注解存在，不证明运行时可达。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
