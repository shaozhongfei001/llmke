#!/usr/bin/env python3
"""P0-02 仪器（实体侧）：从 Java DO 的 ORM 注解提取「实体模型」，并校验字段明细 CSV。

为什么必须做这一步：
    我们给 P0-02 用的基线是 `docs/upstream/数据库表结构-字段明细.csv`，它本身是
    "从 DO 推导出来的二手材料"。如果直接拿它比对 DDL，那么 **CSV 记错一项，DDL 就会被判成错**。
    真正的"实体模型"在源码里：`@TableName` / `@Column(name,type,length,isNull,isKey)`。

它产出什么：
    1. 每张表的列：列名、SQL 类型（含长度）、可空、主键、自增、注释 —— 均带源文件与行号；
    2. 实体模型 ↔ CSV 的差异（即"二手材料是否忠实"）；
    3. `--out` 输出 CSV，可替代字段明细作为 P0-02 的基线。

它不判定什么：
    - DDL 是否与实体一致（那是 p0-02-ddl-diff.py 的活）；
    - 字段业务语义（create_by 到底是用户 ID / 账号 / 姓名）——人工裁定。

用法：
    python3 docs/baseline/validation/p0-02-entity-extract.py \
        --src <rag-parent> [--fields-csv docs/upstream/数据库表结构-字段明细.csv] [--out /tmp/entity-model.csv]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIELD_CSV = REPO / "docs/upstream/数据库表结构-字段明细.csv"

TABLE_NAME_RE = re.compile(r'@TableName\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
TABLE_COMMENT_RE = re.compile(r'@TableComment\s*\(\s*"([^"]*)"')
# 字段可能带初始值（如 `private Integer tempStatus = Xxx.CODE;`）；早先要求紧跟 `;` 会漏掉这类字段，
# 表现为假的"CSV 有、实体无"。
FIELD_RE = re.compile(r"\b(?:private|protected|public)\s+([\w.<>\[\],\s]+?)\s+(\w+)\s*(?:=[^;]*)?;")
COL_NAME_RE = re.compile(r'@Column\s*\([^)]*?name\s*=\s*"([^"]+)"', re.S)
TF_NAME_RE = re.compile(r'@TableField\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
TID_NAME_RE = re.compile(r'@TableId\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
COL_TYPE_RE = re.compile(r"type\s*=\s*MySqlTypeConstant\.(\w+)")
COL_LEN_RE = re.compile(r"\blength\s*=\s*(\d+)")
IS_NULL_RE = re.compile(r"isNull\s*=\s*(true|false)")
IS_KEY_RE = re.compile(r"isKey\s*=\s*(true|false)")
IS_AUTO_RE = re.compile(r"isAutoIncrement\s*=\s*(true|false)")
COMMENT_RE = re.compile(r'comment\s*=\s*"([^"]*)"')
DEFAULT_RE = re.compile(r'defaultValue\s*=\s*"([^"]*)"')
EXIST_FALSE_RE = re.compile(r"@TableField\s*\([^)]*exist\s*=\s*false", re.S)

JAVA_TO_SQL = {
    "Long": "BIGINT", "long": "BIGINT",
    "Integer": "INT", "int": "INT",
    "Short": "SMALLINT", "Byte": "TINYINT",
    "String": "VARCHAR(255)",
    "Date": "DATETIME", "LocalDateTime": "DATETIME", "LocalDate": "DATE",
    "BigDecimal": "DECIMAL(10,2)", "Double": "DOUBLE", "double": "DOUBLE",
    "Float": "FLOAT", "float": "FLOAT", "Boolean": "TINYINT(1)", "boolean": "TINYINT(1)",
}


def strip_comments(text: str) -> str:
    out, i, n = [], 0, len(text)
    in_str = in_chr = False
    while i < n:
        c, nxt = text[i], text[i + 1] if i + 1 < n else ""
        if in_str or in_chr:
            out.append(c)
            if c == "\\" and nxt:
                out.append(nxt)
                i += 2
                continue
            if in_str and c == '"':
                in_str = False
            elif in_chr and c == "'":
                in_chr = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == "'":
            in_chr = True
        elif c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append("\n" * max(1, text.count("\n", i, j)))
            i = j
            continue
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append("\n" * max(1, text.count("\n", i, j)))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


NUMERIC = {"INT", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT", "BIT"}


def split_type(s: str):
    base, _, rest = s.partition("(")
    return base.strip().upper(), rest.rstrip(")").strip()


def type_diff(csv_type: str, ent_type: str, ent_len_known: bool):
    """返回差异描述或 None。

    两条降噪规则（都是实测踩出来的）：
    1. 数值型显示宽度（INT(10) vs INT）在 MySQL 8 已废弃，不判为差异；
    2. 只有一方给出长度时不判长度——否则 CSV 写了长度、实体没写的情况会全量假红。
    """
    b1, l1 = split_type(csv_type)
    b2, l2 = split_type(ent_type)
    if b1 != b2:
        return f"类型 {csv_type} vs {ent_type}"
    if b1 in NUMERIC:
        return None
    if not (l1 and l2 and ent_len_known):
        return None
    if l1 != l2:
        return f"长度 {csv_type} vs {ent_type}"
    return None


def snake(name: str) -> str:
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return re.sub(r"_+", "_", s)


def table_of(path: Path, code: str) -> tuple[str, str]:
    m = TABLE_NAME_RE.search(code)
    cls = re.search(r"class\s+(\w+)", code)
    name = m.group(1) if m else snake(re.sub(r"DO$", "", cls.group(1)) if cls else path.stem)
    c = TABLE_COMMENT_RE.search(code)
    return name, (c.group(1) if c else "")


def parse_entity(path: Path, code: str):
    table, tcomment = table_of(path, code)
    rows = []
    for m in FIELD_RE.finditer(code):
        jtype = " ".join(m.group(1).split())
        jname = m.group(2)
        start = max(code.rfind(";", 0, m.start()), code.rfind("{", 0, m.start()),
                    code.rfind("}", 0, m.start()))
        block = code[start + 1:m.start()]
        if "static" in block.split() or jname == "serialVersionUID":
            continue
        if EXIST_FALSE_RE.search(block):
            continue
        col = (COL_NAME_RE.search(block) or TF_NAME_RE.search(block) or TID_NAME_RE.search(block))
        column = col.group(1) if col else snake(jname)
        ctype = COL_TYPE_RE.search(block)
        clen = COL_LEN_RE.search(block)
        len_known = False
        if ctype:
            sql_type = ctype.group(1).upper()
            if clen and "(" not in sql_type:
                sql_type = f"{sql_type}({clen.group(1)})"
                len_known = True
        else:
            base = JAVA_TO_SQL.get(jtype.split("<")[0], "VARCHAR(255)")
            if clen:
                base = f"{base.split('(')[0]}({clen.group(1)})"
                len_known = True
            sql_type = base
            len_known = len_known or "(" in base
        isnull = IS_NULL_RE.search(block)
        # 没写 isNull 不等于"可空"——那是"未声明"。当成 True 会把 CSV 的 NOT NULL 全判成差异。
        nullable = None if not isnull else (isnull.group(1) == "true")
        iskey = IS_KEY_RE.search(block)
        isauto = IS_AUTO_RE.search(block)
        pk = bool(iskey and iskey.group(1) == "true") or bool(re.search(r"@TableId", block))
        auto = bool(isauto and isauto.group(1) == "true") or "@TableId" in block and "AUTO" in block
        cmt = COMMENT_RE.search(block)
        rows.append({
            "table": table, "column": column, "sql_type": sql_type,
            "nullable": "" if nullable is None else ("是" if nullable else "否"),
            "pk": "是" if pk else "", "auto": "是" if auto else "",
            "comment": cmt.group(1) if cmt else "", "len_known": len_known,
            "default": (DEFAULT_RE.search(block).group(1) if DEFAULT_RE.search(block) else ""),
            "java_field": jname, "java_type": jtype,
            "src_file": str(path), "line": code.count("\n", 0, m.start()) + 1,
        })
    return table, tcomment, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--fields-csv", type=Path, default=FIELD_CSV)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if not a.src.is_dir():
        print(f"FAIL: 源码目录不存在: {a.src}")
        return 2

    files = sorted(p for p in a.src.rglob("*.java")
                   if p.name.endswith("DO.java") or "@TableName" in p.read_text(encoding="utf-8", errors="replace"))
    model = {}
    for f in files:
        code = strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        if "@TableName" not in code:
            continue
        table, tcomment, rows = parse_entity(f, code)
        if not rows:
            continue
        # 同表多实体（实测 user_operate 在 auth 与 common 各有一份）：
        # 必须择优，不能合并——合并会产生重复列并让下游比对出现幽灵差异。
        # 择优规则：显式 @Column 更多的定义更可信（隐式驼峰映射依赖全局配置）。
        cand = {"comment": tcomment, "rows": rows, "file": f.name,
                "explicit": code.count("@Column")}
        cur = model.get(table)
        if cur is None:
            model[table] = cand
        elif cand["explicit"] > cur["explicit"]:
            print(f"WARN: 表 {table} 有多个实体，改用 {f.name}（@Column {cand['explicit']} > {cur['explicit']}）")
            model[table] = cand
        else:
            print(f"WARN: 表 {table} 有多个实体，保留 {cur['file']}（@Column {cur['explicit']} >= {cand['explicit']}），忽略 {f.name}")

    total_cols = sum(len(v["rows"]) for v in model.values())
    print(f"实体文件={len(files)}  实体表={len(model)}  实体列={total_cols}")

    if a.out:
        with a.out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["表名", "字段名", "SQL类型", "长度", "主键", "自增",
                                               "可空", "默认值", "注释", "Java字段", "Java类型",
                                               "源文件", "行号"])
            w.writeheader()
            for t, v in sorted(model.items()):
                for r in v["rows"]:
                    t_, _, rest = r["sql_type"].partition("(")
                    w.writerow({"表名": t, "字段名": r["column"], "SQL类型": t_,
                                "长度": rest.rstrip(")"), "主键": r["pk"], "自增": r["auto"],
                                "可空": r["nullable"], "默认值": r.get("default", ""), "注释": r["comment"],
                                "Java字段": r["java_field"], "Java类型": r["java_type"],
                                "源文件": r["src_file"], "行号": r["line"]})

    # ---- 与字段明细 CSV 对账：CSV 是二手材料，必须能证明它忠实 ----
    if not a.fields_csv or not Path(a.fields_csv).is_file():
        print("（未提供字段明细 CSV，跳过对账）")
        return 0
    base = {}
    for r in csv.DictReader(Path(a.fields_csv).read_text(encoding="utf-8-sig").splitlines()):
        base.setdefault((r["表名"] or "").strip(), {})[(r["字段名"] or "").strip()] = r

    only_entity_t = sorted(set(model) - set(base))
    only_csv_t = sorted(set(base) - set(model))
    diffs = []
    for t in sorted(set(model) & set(base)):
        ent = {r["column"]: r for r in model[t]["rows"]}
        csvt = base[t]
        for c in sorted(set(ent) - set(csvt)):
            diffs.append(f"CSV_MISSING_COLUMN: {t}.{c}（实体 {ent[c]['sql_type']}，{Path(ent[c]['src_file']).name}:{ent[c]['line']}）")
        for c in sorted(set(csvt) - set(ent)):
            diffs.append(f"ENTITY_MISSING_COLUMN: {t}.{c}（CSV 有，实体无）")
        for c in sorted(set(ent) & set(csvt)):
            e, v = ent[c], csvt[c]
            csv_type = (v["SQL类型"] or "").upper()
            if v["长度"]:
                csv_type = f"{csv_type}({v['长度']})"
            td = type_diff(csv_type, e["sql_type"], e.get("len_known", False))
            if td:
                diffs.append(f"TYPE_DIFF: {t}.{c} {td}（{Path(e['src_file']).name}:{e['line']}）")
            if e["nullable"] and (v["可空"] or "") != e["nullable"]:
                diffs.append(f"NULL_DIFF: {t}.{c} CSV {v['可空'] or '?'} 实体 {e['nullable']}")

    print(f"\n对账 CSV：CSV 表={len(base)}  实体表={len(model)}  "
          f"仅实体表={len(only_entity_t)}  仅CSV表={len(only_csv_t)}  列差异={len(diffs)}")
    for t in only_entity_t:
        print(f"  ONLY_ENTITY_TABLE: {t}（{len(model[t]['rows'])} 列）")
    for t in only_csv_t:
        print(f"  ONLY_CSV_TABLE:    {t}")
    for d in diffs[:20]:
        print("  " + d)
    if len(diffs) > 20:
        print(f"  ...（共 {len(diffs)} 条，仅显示前 20）")

    print("\n结论: 上面每一条都是「二手材料与源码不符」；"
          "修 CSV 之前，不要拿它去判定 DDL 对错。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
