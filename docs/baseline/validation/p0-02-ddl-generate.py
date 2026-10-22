#!/usr/bin/env python3
"""P0-02 仪器：从 ORM 注解生成候选 DDL（MySQL）。

为什么需要生成而不是"找到"：
    实测确认 **材料里没有真实 DDL** —— RAG 源码树 0 个 `.sql`，
    `平台重构开发设计.docx` 等 20+ 份文档里 `CREATE TABLE` 出现 0 次，
    `数据库表结构.xlsx` 只有"表清单/字段明细"（与仓库里的 CSV 同源，483 行含表头）。
    而设计文档 5.1 写着"37 张表 DDL 原样复用"、5.3 写着"用现有 37 表 DDL 初始化新库"。

    既然"原样复用"的对象不存在，唯一可执行的判据是：**代码要求的 DDL 长什么样**。
    本工具从 `@TableName/@Column(type,length,isNull,isKey,isAutoIncrement,defaultValue,comment)`
    生成候选 DDL，作为与生产 `SHOW CREATE TABLE` 比对的基线。

它产出什么：
    - 每表 CREATE TABLE：列、类型（含长度）、NOT NULL、AUTO_INCREMENT、DEFAULT、列注释
    - 主键
    - 表注释（@TableComment）
    - 文件头注明来源与"非生产快照"字样，避免被当成真实 DDL 引用

它不产出什么：
    - 索引 / 外键 / 触发器 / 字符集的实际值（注解里没有）
    - 分区、行格式、排序规则
    → 这些必须在拿到生产 `SHOW CREATE TABLE` 后补齐

用法：
    python3 docs/baseline/validation/p0-02-ddl-generate.py --src <rag-parent> --out /tmp/entity-schema.sql
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

NUMERIC_NO_LEN = {"INT", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT"}


def load_extractor():
    spec = importlib.util.spec_from_file_location("ent", HERE / "p0-02-entity-extract.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_column(col: dict) -> str:
    ty = col["sql_type"]
    base = ty.split("(")[0]
    if base in NUMERIC_NO_LEN:
        ty = base                      # MySQL 8 不建议写显示宽度
    parts = [f"  `{col['column']}` {ty}"]
    if col["nullable"] == "否":
        parts.append("NOT NULL")
    if col["auto"] == "是":
        parts.append("AUTO_INCREMENT")
    d = (col.get("default") or "").strip()
    if d and d.upper() != "NULL":
        parts.append(f"DEFAULT '{d}'" if not re.fullmatch(r"-?\d+(\.\d+)?", d) else f"DEFAULT {d}")
    c = (col.get("comment") or "").replace("'", "''")
    if c:
        parts.append(f"COMMENT '{c}'")
    return " ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--engine", default="InnoDB")
    ap.add_argument("--charset", default="utf8mb4")
    a = ap.parse_args()
    if not a.src.is_dir():
        print(f"FAIL: 源码目录不存在: {a.src}")
        return 2

    ent = load_extractor()
    model: dict[str, dict] = {}
    for f in sorted(a.src.rglob("*.java")):
        if not f.name.endswith("DO.java"):
            continue
        code = ent.strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        if "@TableName" not in code:
            continue
        table, tcomment, rows = ent.parse_entity(f, code)
        if not rows:
            continue
        if table in model:                       # 同表多实体：保留先出现的，并提示
            print(f"WARN: 表 {table} 有多个实体定义，使用第一个（{model[table]['file']}），忽略 {f.name}")
            continue
        model[table] = {"comment": tcomment, "rows": rows, "file": f.name}

    lines = [
        "-- 由 ORM 注解生成的候选 DDL（不是生产快照）",
        f"-- 来源: {a.src.name} 下的 *DO.java（{len(model)} 表）",
        "-- 用途: 与生产 SHOW CREATE TABLE 比对；不含索引/外键/触发器/真实字符集",
        "",
    ]
    pkless = []
    for table, info in sorted(model.items()):
        cols = info["rows"]
        body = [render_column(c) for c in cols]
        pks = [c["column"] for c in cols if c["pk"] == "是"]
        if pks:
            body.append(f"  PRIMARY KEY (`{pks[0]}`)")
        else:
            pkless.append(table)
        tc = (info["comment"] or "").replace("'", "''")
        lines.append(f"-- {info['file']}")
        lines.append(f"CREATE TABLE `{table}` (")
        lines.append(",\n".join(body))
        lines.append(f") ENGINE={a.engine} DEFAULT CHARSET={a.charset}"
                     + (f" COMMENT='{tc}'" if tc else "") + ";")
        lines.append("")

    a.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"生成表={len(model)}  列={sum(len(v['rows']) for v in model.values())}  "
          f"无主键表={len(pkless)}{('（' + ', '.join(pkless) + '）') if pkless else ''}")
    print(f"输出: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
