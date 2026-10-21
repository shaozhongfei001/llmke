#!/usr/bin/env python3
"""P0-02 / 5.1 仪器：从 Mapper SQL 反推"该建哪些索引"。

背景：
    设计文档 5.1 要补三类索引，其中 `dialogue(user_id, gmt_create)` 因为 `dialogue` 没有
    `user_id` 列而**建不出来**（已证实）。而代码注解里 `@Index` 出现 0 次，无法直接读出索引。

它能给什么：
    从 `*.xml` 的 SQL 里提取"等值列 + 排序/范围列"的组合，按出现次数排序 —— 即**查询模式要求**的索引。
它给不了什么：
    **生产已经建了哪些索引**。这两件事必须分开：本工具的输出是"建议"，不是"现状"。

自检方式（本工具的可信度依据）：
    若它能重新发现设计文档已经写明的两条可行索引
    （`file_parse_task(status, gmt_create)`、`answer(dialogue_id, type)`），
    说明提取口径与人的判断一致；否则说明口径有偏差，输出不可用。

用法：
    python3 docs/baseline/validation/p0-02-index-infer.py --src <rag-parent> [--min-count 2] [--top 12]
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

STMT_RE = re.compile(r"<(select|insert|update|delete)\b[^>]*>(.*?)</\1>", re.S | re.I)
TABLE_AT_RE = re.compile(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+`?(\w+)`?", re.I)

WHERE_RE = re.compile(r"\bWHERE\b(.*?)(?:\bGROUP\s+BY\b|\bORDER\s+BY\b|\bLIMIT\b|$)", re.S | re.I)
ORDER_RE = re.compile(r"\bORDER\s+BY\b(.*?)(?:\bLIMIT\b|$)", re.S | re.I)
GROUP_RE = re.compile(r"\bGROUP\s+BY\b(.*?)(?:\bORDER\s+BY\b|\bLIMIT\b|$)", re.S | re.I)

EQ_RE = re.compile(r"\b(\w+)\s*(?:=|!=|<>)\s*(?:#\{|'|\d|\?)", re.I)
RANGE_RE = re.compile(r"\b(\w+)\s*(?:>|<|>=|<=|\bLIKE\b|\bBETWEEN\b|\bIN\b)", re.I)
ORD_COL_RE = re.compile(r"`?(\w+)`?\s*(?:ASC|DESC)?", re.I)

NOISE = {"and", "or", "not", "null", "is", "in", "like", "between", "select", "from",
         "where", "order", "group", "by", "limit", "asc", "desc", "case", "when", "then"}


def clean_sql(body: str) -> str:
    body = re.sub(r"<[^>]+>", " ", body)                    # 去掉 <if>/<where>/<foreach>
    body = re.sub(r"#\{[^}]*\}", " ? ", body)               # 参数占位统一
    body = re.sub(r"\$\{[^}]*\}", " ? ", body)
    body = re.sub(r"--[^\n]*", " ", body)
    return re.sub(r"\s+", " ", body)


def cols_of(pattern, text):
    out = []
    for m in pattern.finditer(text):
        c = m.group(1).lower()
        if c not in NOISE and c not in out:
            out.append(c)
    return out


def order_cols(text):
    m = ORDER_RE.search(text)
    if not m:
        return []
    out = []
    for part in m.group(1).split(","):
        mm = ORD_COL_RE.match(part.strip())
        if mm and mm.group(1).lower() not in NOISE:
            out.append(mm.group(1).lower())
    return out


JAVA_EQ_RE = re.compile(r"\.(?:eq)\(\s*(?:[^,()]+,)?\s*(\w+)::get(\w+)")
JAVA_RANGE_RE = re.compile(r"\.(?:ne|gt|ge|lt|le|like|likeLeft|likeRight|in)\(\s*(?:[^,()]+,)?\s*(\w+)::get(\w+)")
JAVA_ORDER_RE = re.compile(r"\.orderBy(?:Asc|Desc)\(\s*(\w+)::get(\w+)")
JAVA_GROUP_RE = re.compile(r"\.groupBy\(\s*(\w+)::get(\w+)")
CLASS_OF_DO = re.compile(r"(\w+)::get")


def java_candidates(src: Path, do_map: dict[str, str], field_map: dict[tuple, str]):
    """从 Java 的 LambdaQueryWrapper 链里提取列组合。

    为什么必须做这一步：本项目的查询主要写在 Java 侧，XML 只有 64 条单表语句；
    只扫 XML 会漏掉绝大多数查询模式（实测自检两条全 MISSING）。
    """
    out = Counter()
    for f in src.rglob("*.java"):
        txt = f.read_text(encoding="utf-8", errors="replace")
        if "::get" not in txt:
            continue
        for seg in txt.split(";"):
            if "::get" not in seg:
                continue
            m = CLASS_OF_DO.search(seg)
            if not m:
                continue
            cls = m.group(1)
            table = do_map.get(cls)
            if not table:
                continue
            def col(field):
                return field_map.get((cls, field)) or re.sub(r"(?<!^)(?=[A-Z])", "_", field).lower()
            eq = [col(x[1]) for x in JAVA_EQ_RE.findall(seg) if x[0] == cls]
            rng = [col(x[1]) for x in JAVA_RANGE_RE.findall(seg) if x[0] == cls]
            order = [col(x[1]) for x in JAVA_ORDER_RE.findall(seg) if x[0] == cls]
            grp = [col(x[1]) for x in JAVA_GROUP_RE.findall(seg) if x[0] == cls]
            eq = list(dict.fromkeys(eq))
            rng = list(dict.fromkeys(rng))
            if eq or rng or order or grp:
                out[(table.lower(), tuple(eq), tuple(rng), tuple(order), tuple(grp))] += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--show-all", action="store_true")
    a = ap.parse_args()
    if not a.src.is_dir():
        print(f"FAIL: 源码目录不存在: {a.src}")
        return 2

    # DO 类 -> 表 / (类, 字段) -> 列：从实体提取器复用，保证与 DDL 基线同口径
    import importlib.util
    spec = importlib.util.spec_from_file_location("ent", Path(__file__).resolve().parent / "p0-02-entity-extract.py")
    ent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ent)
    do_map: dict[str, str] = {}
    field_map: dict[tuple, str] = {}
    for jf in a.src.rglob("*.java"):
        if not jf.name.endswith("DO.java"):
            continue
        code = ent.strip_comments(jf.read_text(encoding="utf-8", errors="replace"))
        if "@TableName" not in code:
            continue
        table, _c, rows = ent.parse_entity(jf, code)
        cls = jf.stem
        do_map.setdefault(cls, table)
        for r in rows:
            field_map[(cls, r["java_field"])] = r["column"]

    cands: Counter = Counter(java_candidates(a.src, do_map, field_map))
    multi = 0
    stmts = 0
    for f in a.src.rglob("*.xml"):
        txt = f.read_text(encoding="utf-8", errors="replace")
        for m in STMT_RE.finditer(txt):
            body = clean_sql(m.group(2))
            tables = {t for t in TABLE_AT_RE.findall(body)}
            if len(tables) != 1:
                if tables:
                    multi += 1
                continue
            stmts += 1
            table = tables.pop().lower()
            eq = cols_of(EQ_RE, WHERE_RE.search(body).group(1) if WHERE_RE.search(body) else "")
            order = order_cols(body)
            grp = cols_of(GROUP_RE, GROUP_RE.search(body).group(1) if GROUP_RE.search(body) else "")
            key = (table, tuple(eq), (), tuple(order), tuple(grp))
            if eq or order or grp:
                cands[key] += 1

    print(f"XML 单表语句={stmts}  XML 多表/无法归属={multi}  "
          f"Java 侧 DO 类={len(do_map)}  合并后候选索引组合={len(cands)}")

    by_table = defaultdict(list)
    for (t, eq, rng, order, grp), n in cands.items():
        by_table[t].append((n, eq, rng, order, grp))

    # 自检：文档已写明且列存在的两条索引，应能在候选里出现
    checks = [
        ("file_parse_task", ("status",), ("gmt_create",)),
        ("answer", ("dialogue_id", "type"), ()),
    ]
    print("\n文档 5.1 三条索引与现有查询的关系：")
    print("  （文档原文是\"仅补充三类索引以支撑新查询\"，因此\"无现有查询使用\"是预期，不是工具失败）")
    for table, eq_prefix, order_prefix in checks:
        hit = False
        for n, eq, _rng, order, _grp in by_table.get(table, []):
            if tuple(eq[:len(eq_prefix)]) == eq_prefix and (not order_prefix or tuple(order[:len(order_prefix)]) == order_prefix):
                hit = True
                break
        print(f"  {'被现有查询使用' if hit else '无现有查询使用'}  {table}({', '.join(eq_prefix)}{', ' + ', '.join(order_prefix) if order_prefix else ''})")

    print(f"\n每表 Top 候选（出现次数 ≥{a.min_count}）：")
    for table in sorted(by_table):
        rows = [(n, eq, rng, order, grp) for n, eq, rng, order, grp in by_table[table] if n >= a.min_count]
        if not rows:
            continue
        rows.sort(reverse=True)
        print(f"\n  [{table}]")
        for n, eq, rng, order, grp in rows[: (999 if a.show_all else a.top)]:
            parts = []
            if eq:
                parts.append("等值(" + ",".join(eq) + ")")
            if rng:
                parts.append("范围(" + ",".join(rng) + ")")
            if order:
                parts.append("排序(" + ",".join(order) + ")")
            if grp:
                parts.append("分组(" + ",".join(grp) + ")")
            print(f"    ×{n:<3} {' + '.join(parts)}")

    print("\n说明：以上是「查询模式要求的索引」，不是「生产已建索引」；"
          "后者只能由 SHOW CREATE TABLE 得到。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
