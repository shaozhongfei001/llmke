#!/usr/bin/env python3
"""逐条核验 docs/reuse/INTERFACE-ASSETS.yaml 的 506 条记录是否存在于指定源码快照。

为什么需要解析而不是文本包含：清单里是**拼接后**的完整路径（类级 @RequestMapping("/ai")
+ 方法级 @PostMapping("/question") → /ai/question），直接搜 "/ai/question" 字面量会全部落空。
因此本脚本为每个源文件建立「路由表」，再按 (方法, 完整路径) 匹配清单行。

只读：不写源码头、不改清单。输出 JSON + Markdown 摘要。

用法：
  python3 verify_interface_inventory.py \
      --src-root <RAG-SRC/_src> --repo-root <项目根> --out <报告目录>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

JAVA_PREFIX = "gien-rag/"
PY_PREFIXES = ("alg_doc_parse_service", "alg_llm_inference_service",
               "alg_retrieval_service", "index_data_service")

JAVA_MAPPING = re.compile(r"@(Get|Post|Put|Delete|Patch|Request)Mapping\b")
QUOTED = re.compile(r'"([^"]*)"')
QUOTED_ANY = re.compile(r"['\"]([^'\"]*)['\"]")
PY_DECORATOR = re.compile(r"@(?:\w+\.)?(route|get|post|put|delete|patch)\s*\(")
# 本项目 Python 侧还有两种非装饰器写法：
#   XxxView(path="/x", ...)            —— 方法在 View 类的 def post/get 里
#   app.get('/version')(handler)       —— 函数式注册
PY_VIEW_REG = re.compile(r"\b(\w+)\s*\(\s*path\s*=\s*['\"](/[^'\"]*)['\"]")
PY_FUNC_REG = re.compile(r"\.(get|post|put|delete|patch)\s*\(\s*['\"](/[^'\"]*)['\"]")
PY_IMPORT = re.compile(r"^\s*from\s+([\w.]+)\s+import\s+(.+)$")
PY_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(")
JAVA_METHOD_NAME = re.compile(r"\b(\w+)\s*\(")


def resolve(src_root: Path, source_file: str) -> Path | None:
    if source_file.startswith(JAVA_PREFIX):
        return src_root / "gien-rag" / "gien-rag" / source_file[len(JAVA_PREFIX):]
    for p in PY_PREFIXES:
        if source_file.startswith(p + "/"):
            return src_root / "rag-alg-service-api" / "rag-alg-service-api" / source_file
    return None


def join_path(base: str, sub: str) -> str:
    base = (base or "").strip().rstrip("/")
    sub = (sub or "").strip()
    if not sub:
        return base or "/"
    if not sub.startswith("/"):
        sub = "/" + sub
    return (base + sub).replace("//", "/")


def paren_block(lines: list[str], start: int, limit: int = 12) -> tuple[str, int]:
    """从 start 行开始收集到括号配平为止的文本，返回 (文本, 结束行下标)。"""
    text, depth, i = "", 0, start
    while i < len(lines) and i - start <= limit:
        text += " " + lines[i].strip()
        depth += lines[i].count("(") - lines[i].count(")")
        if depth <= 0 and "(" in text:
            break
        i += 1
    return text, i


def commented_lines(lines: list[str]) -> set[int]:
    """返回处于注释中的行下标集合（// 、# 单行；/* */ 块）。"""
    out: set[int] = set()
    in_block = False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if in_block:
            out.add(i)
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*"):
            out.add(i)
            if "*/" not in s:
                in_block = True
            continue
        if s.startswith(("//", "#", "*")):
            out.add(i)
    return out


def java_routes(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    dead = commented_lines(lines)
    class_base = ""
    for i, ln in enumerate(lines):
        if re.search(r"\b(class|interface)\s+\w+", ln):
            for j in range(i, max(-1, i - 6), -1):
                if JAVA_MAPPING.search(lines[j]) and j not in dead:
                    m = QUOTED.search(lines[j])
                    if m:
                        class_base = m.group(1)
                    break
            break
    routes = []
    for i, ln in enumerate(lines):
        m = JAVA_MAPPING.search(ln)
        if not m:
            continue
        kind = m.group(1).upper()
        # 裸注解（如 `@GetMapping` 不带括号）表示无子路径，不能向后扫括号，否则会误吃方法签名
        block, end = (ln, i) if "(" not in ln else paren_block(lines, i)
        quoted = QUOTED.findall(block)
        subs = [quoted[0]] if quoted else [""]
        handler, handler_line = "", None
        for k in range(end, min(len(lines), end + 8)):
            nm = JAVA_METHOD_NAME.search(lines[k])
            if nm and lines[k].strip().startswith(("public", "protected", "private")):
                handler, handler_line = nm.group(1), k + 1
                break
        for sub in subs:
            routes.append({"method": "GET" if kind == "GET" else kind,
                           "path": join_path(class_base, sub), "handler": handler,
                           "line": i + 1, "handler_line": handler_line,
                           "commented": i in dead})
    return routes


def view_method(path: Path, module: str, cls: str) -> str:
    """在 urls.py 的模块根下找到 View 类文件，读出 def get/post 决定方法。"""
    rel = module.replace(".", "/") + ".py"
    for base in [path.parent, *path.parent.parents][:5]:
        cand = base / rel
        if cand.is_file():
            text = cand.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"def\s+(get|post|put|delete|patch)\s*\(", text)
            return m.group(1).upper() if m else "UNSPECIFIED"
    return "UNSPECIFIED"


def py_view_routes(path: Path) -> tuple[list[dict], dict]:
    """解析 urls.py 的 `XxxView(path="/x")` 与 `app.get('/x')(handler)` 两种写法。"""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    dead = commented_lines(lines)
    modules = {}
    for ln in lines:
        m = PY_IMPORT.match(ln)
        if m:
            for name in re.findall(r"\w+", m.group(2)):
                modules.setdefault(name, m.group(1))
    routes = []
    for i, ln in enumerate(lines):
        if i in dead:
            continue
        mv = PY_VIEW_REG.search(ln)
        if mv:
            cls, p = mv.group(1), mv.group(2)
            mod = modules.get(cls)
            method = view_method(path, mod, cls) if mod else "UNSPECIFIED"
            routes.append({"method": method, "path": p, "handler": cls,
                           "line": i + 1, "handler_line": i + 1, "commented": False})
            continue
        # 多行 View 实例化：XxxView(\n path="/x", ...)
        call = re.match(r"\s*(\w+)\s*\(\s*$", ln)
        if call and call.group(1).endswith(("View", "Api")):
            block, _ = paren_block(lines, i, limit=6)
            pm = re.search(r"path\s*=\s*['\"](/[^'\"]*)['\"]", block)
            if pm:
                cls = call.group(1)
                mod = modules.get(cls)
                method = view_method(path, mod, cls) if mod else "UNSPECIFIED"
                routes.append({"method": method, "path": pm.group(1), "handler": cls,
                               "line": i + 1, "handler_line": i + 1, "commented": False})
                continue
        mf = PY_FUNC_REG.search(ln)
        if mf and not ln.strip().startswith("@"):
            routes.append({"method": mf.group(1).upper(), "path": mf.group(2),
                           "handler": "", "line": i + 1, "handler_line": i + 1,
                           "commented": False})
    return routes


def py_routes(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    dead = commented_lines(lines)
    routes = []
    for i, ln in enumerate(lines):
        m = PY_DECORATOR.search(ln)
        if not m:
            continue
        block, end = paren_block(lines, i)
        kind = m.group(1).lower()
        if kind == "route":
            mm = re.search(r"methods\s*=\s*\[([^\]]*)\]", block)
            hit = QUOTED_ANY.search(mm.group(1)) if mm else None
            method = hit.group(1).upper() if hit else "GET"
        else:
            method = kind.upper()
        subs = [q for q in QUOTED_ANY.findall(block) if q.startswith("/")]
        handler, handler_line = "", None
        for k in range(end, min(len(lines), end + 4)):
            dm = PY_DEF.search(lines[k])
            if dm:
                handler, handler_line = dm.group(1), k + 1
                break
        for sub in subs:
            routes.append({"method": method, "path": sub, "handler": handler,
                           "line": i + 1, "handler_line": handler_line,
                           "commented": i in dead})
    routes.extend(py_view_routes(path))
    return routes


def classify(src_root: Path, row: dict, cache: dict) -> dict:
    rec = {"asset_id": row["asset_id"], "service": row["service"], "method": row["method"],
           "path": row["path"], "handler_reported": row.get("handler_reported") or "",
           "source_file": row["source_file"], "source_line": row["source_line"]}
    src = resolve(src_root, row["source_file"])
    if src is None:
        rec["status"] = "UNMAPPED_SOURCE_PREFIX"
        return rec
    if not src.is_file():
        rec["status"] = "FILE_MISSING"
        return rec
    key = str(src)
    if key not in cache:
        cache[key] = java_routes(src) if src.suffix == ".java" else py_routes(src)
    routes = cache[key]

    same_path = [r for r in routes if r["path"] == row["path"]]
    live = [r for r in same_path if not r["commented"]]
    if not same_path:
        rec["status"] = "PATH_NOT_IN_SOURCE"
        return rec
    if not live:
        rec["status"] = "PATH_ONLY_COMMENTED"
        rec["actual_line"] = same_path[0]["line"]
        return rec
    same_method = [r for r in live
                   if r["method"] == row["method"] or r["method"] == "UNSPECIFIED"]
    if same_method and same_method[0]["method"] == "UNSPECIFIED":
        rec["method_resolution"] = "UNSPECIFIED_VIEW_CLASS"
    if not same_method:
        rec["status"] = "METHOD_MISMATCH"
        rec["actual_method"] = live[0]["method"]
        rec["actual_line"] = live[0]["line"]
        return rec
    hit = same_method[0]
    rec["annotation_line"] = hit["line"]
    rec["handler_line"] = hit.get("handler_line")
    rec["actual_handler"] = hit["handler"]
    want = rec["handler_reported"]
    if want and hit["handler"] and want != hit["handler"]:
        rec["status"] = "HANDLER_MISMATCH"
        return rec
    try:
        declared = int(row["source_line"])
    except (TypeError, ValueError):
        declared = None
    candidates = [l for l in (hit["line"], hit.get("handler_line")) if l]
    if declared is None or not candidates:
        rec["line_drift"] = None
        rec["status"] = "OK"
        return rec
    # 清单行号记的是 handler 声明行或注解行，两种都接受；偏差 <=2 视为一致
    nearest = min(candidates, key=lambda l: abs(l - declared))
    rec["line_drift"] = nearest - declared
    rec["status"] = "OK" if abs(rec["line_drift"]) <= 2 else "LINE_DRIFT"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    inv = yaml.safe_load((a.repo_root / "docs/reuse/INTERFACE-ASSETS.yaml").read_text(encoding="utf-8"))
    rows = inv["items"]
    cache: dict = {}
    results = [classify(a.src_root, r, cache) for r in rows]

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "interface-inventory-check.json").write_text(
        json.dumps({"total": len(results), "counts": counts,
                    "source_files_parsed": len(cache), "results": results},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    bad = [r for r in results if r["status"] not in ("OK", "LINE_DRIFT")]
    md = ["# 506 条接口清单 vs 生产快照 核验摘要", "",
          f"- 清单总数：{len(results)}",
          f"- 解析源文件数：{len(cache)}",
          f"- 结果分布：`{json.dumps(counts, ensure_ascii=False)}`",
          f"- 非 OK/LINE_DRIFT 项：{len(bad)}", "",
          "| asset_id | 服务 | 清单方法 | 清单路径 | 状态 | 源码实际 |",
          "|---|---|---|---|---|---|"]
    for r in bad:
        actual = ""
        if r.get("actual_method"):
            actual = f"{r['actual_method']} {r['path']} @L{r.get('actual_line')}"
        elif r.get("actual_line"):
            actual = f"L{r['actual_line']}"
        md.append(f"| {r['asset_id']} | {r['service']} | {r['method']} | `{r['path']}` | "
                  f"{r['status']} | {actual} |")
    (a.out / "interface-inventory-check.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"counts": counts, "files_parsed": len(cache)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
