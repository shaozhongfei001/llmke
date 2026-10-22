#!/usr/bin/env python3
"""B1：只读索引「源码 SQL 对目标列」的引用（SOURCE_SQL_REFERENCE）。

能证明什么：**源码里哪些 SQL 语句引用了这个列名**。
不能证明什么：
  - 不能证明数据库里存在该列（只有 DDL 能证明）；
  - 不能证明该列有数据、有索引、有约束；
  - 源码中「没搜到」也不等于「该列不存在」（可能是 SELECT *、动态 SQL、继承字段、间接映射）。

因此每条记录都带 proof_scope 字段，禁止把本索引当作 DDL 替代。
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

TARGETS = {
    "re_embedding_file": ["is_del", "gmt_create", "gmt_modified", "create_by", "update_by", "kb_id", "task_id"],
    "re_embedding_retry_task": ["is_del", "gmt_create", "gmt_modified", "create_by", "update_by", "kb_id", "file_id"],
    "re_embedding_task": ["is_del", "gmt_create", "gmt_modified", "create_by", "update_by", "kb_id", "total_file_num", "uid"],
    "user_operate": ["is_del", "gmt_created", "gmt_modified", "create_by", "update_by", "user_id"],
    "dialogue": ["is_del", "gmt_create", "gmt_modified", "create_by", "update_by", "user_id", "kb_id", "session_id"],
}

STMT_XML_RE = re.compile(
    r"<(select|insert|update|delete)\b([^>]*)>(.*?)</\1>", re.S | re.I)
STMT_ID_RE = re.compile(r'id\s*=\s*"([^"]+)"')
TABLE_RE = re.compile(r"(?:from|join|into|update)\s+`?([a-zA-Z_][\w]*)`?", re.I)
ANNOT_RE = re.compile(r"@(Select|Insert|Update|Delete)\s*\(\s*(.*?)\)\s*(?:@|\n|$)", re.S)
STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"', re.S)


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def statements(path: Path) -> list[dict]:
    """把一个文件切成若干 SQL 语句块，带 mapper id / 类型 / 起始行。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    out = []
    if path.suffix == ".xml":
        for m in STMT_XML_RE.finditer(text):
            kind, attrs, body = m.group(1).upper(), m.group(2), m.group(3)
            mid = STMT_ID_RE.search(attrs)
            out.append({"kind": kind, "mapper_id": mid.group(1) if mid else "",
                        "text": body, "line": line_of(text, m.start())})
    if path.suffix in (".java", ".sql"):
        if path.suffix == ".java":
            for m in ANNOT_RE.finditer(text):
                kind = m.group(1).upper()
                body = " ".join(STRING_RE.findall(m.group(2))) or m.group(2)
                out.append({"kind": kind, "mapper_id": "(annotation)",
                            "text": body, "line": line_of(text, m.start())})
        else:
            for m in re.finditer(r"([^;]+);", text):
                body = m.group(1)
                if re.search(r"\b(select|insert|update|delete)\b", body, re.I):
                    kind = re.search(r"\b(select|insert|update|delete)\b", body, re.I).group(1).upper()
                    out.append({"kind": kind, "mapper_id": "(sql-file)",
                                "text": body, "line": line_of(text, m.start())})
    # 补：XML 里的动态 SQL 往往被 <where>/<if> 包裹，已包含在 body 内，无需再切分
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    src = a.src_root.resolve()

    files = [p for p in src.rglob("*") if p.is_file()
             and p.suffix in (".xml", ".java", ".sql")
             and "/.git/" not in p.as_posix()]

    refs, select_star, scanned = [], [], 0
    for p in files:
        try:
            stmts = statements(p)
        except Exception:
            continue
        if not stmts:
            # 纯 MyBatis-Plus 映射：文件里只有 resultMap、没有 SQL 语句，也不能跳过
            if p.suffix != ".xml":
                continue
            stem0 = p.stem[: -len("Mapper")] if p.stem.endswith("Mapper") else p.stem
            if re.sub(r"(?<!^)(?=[A-Z])", "_", stem0).lower() not in TARGETS:
                continue
        scanned += 1
        file_tables = set()
        for st in stmts:
            file_tables |= {t.lower() for t in TABLE_RE.findall(st["text"])}
        # 纯 MyBatis-Plus 实体：mapper 里可能只有 resultMap、没有 FROM，
        # 或语句里用的是别名/其他表；一律按文件名回推补一条（并集，不覆盖语句推导）
        if p.suffix == ".xml":
            stem = p.stem
            if stem.endswith("Mapper"):
                stem = stem[: -len("Mapper")]
            guess = re.sub(r"(?<!^)(?=[A-Z])", "_", stem).lower()
            if guess in TARGETS:
                file_tables.add(guess)
        # resultMap 的列同样是对该表的引用（映射层证据），必须单列类型，不能混入 SELECT
        if p.suffix == ".xml":
            text = p.read_text(encoding="utf-8", errors="replace")
            for rm in re.finditer(r"<resultMap\b.*?</resultMap>", text, re.S):
                block = rm.group(0)
                for cm in re.finditer(r"<(?:id|result)\b[^>]*column=\"([^\"]+)\"", block):
                    col = cm.group(1).strip().lower()
                    for table in file_tables & set(TARGETS):
                        if col in TARGETS[table]:
                            refs.append({
                                "table": table, "column": col, "sql_type": "RESULT_MAP_MAPPING",
                                "mapper_id": "(resultMap)",
                                "file": p.relative_to(src).as_posix(),
                                "line": line_of(text, rm.start() + cm.start()),
                                "evidence_class": "SOURCE_SQL_REFERENCE",
                                "proof_scope": "仅证明 ORM 映射声明了该列；不证明数据库存在该列",
                            })
        for st in stmts:
            body = st["text"]
            tables = {t.lower() for t in TABLE_RE.findall(body)}
            # SELECT * 单独标记（列完全不在 SQL 文本里，无法据此判断列存在性）
            if st["kind"] == "SELECT" and re.search(r"select\s+\*", body, re.I):
                for t in tables:
                    if t in TARGETS:
                        select_star.append({"table": t, "file": p.relative_to(src).as_posix(),
                                            "line": st["line"], "mapper_id": st["mapper_id"],
                                            "note": "SELECT *：列名不在 SQL 文本中，本索引无法据此判定"})
            for table, cols in TARGETS.items():
                if table not in tables:
                    continue
                for col in cols:
                    if re.search(rf"(?<![\w]){re.escape(col)}(?![\w])", body, re.I):
                        refs.append({
                            "table": table, "column": col, "sql_type": st["kind"],
                            "mapper_id": st["mapper_id"],
                            "file": p.relative_to(src).as_posix(),
                            "line": st["line"],
                            "evidence_class": "SOURCE_SQL_REFERENCE",
                            "proof_scope": "仅证明源码 SQL 引用了该列名；不证明数据库存在该列",
                        })

    # 汇总：表 × 列 → 是否有引用
    summary = {}
    for table, cols in TARGETS.items():
        summary[table] = {}
        for col in cols:
            hits = [r for r in refs if r["table"] == table and r["column"] == col]
            summary[table][col] = {
                "referenced": bool(hits),
                "hits": len(hits),
                "sql_types": sorted({h["sql_type"] for h in hits}),
                "files": sorted({h["file"] for h in hits})[:5],
            }

    payload = {
        "scope": "B1 源码 SQL 对目标列的引用索引（只读）",
        "warning": "SOURCE_SQL_REFERENCE 不是数据库存在性证明；未搜到也不等于不存在",
        "files_scanned": scanned,
        "tables": TARGETS,
        "summary": summary,
        "references": refs,
        "select_star": select_star,
        "limits": [
            "SELECT * 的语句无法据文本判断列",
            "动态 SQL（<if>/<where>）按语句整体判定，未区分分支",
            "继承字段、间接映射、MyBatis-Plus 注解实体不在本索引范围",
        ],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    if re.search(r"(?<![\w.])(?:/home|/Users)/[A-Za-z0-9._-]+/", body):
        print("FAIL: personal absolute path")
        return 3
    a.out.write_text(body + "\n", encoding="utf-8")

    for table, cols in summary.items():
        line = " ".join(f"{c}={'Y' if v['referenced'] else 'n'}" for c, v in cols.items())
        print(f"{table:26s} {line}")
    print(f"refs={len(refs)} select_star={len(select_star)} files={scanned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
