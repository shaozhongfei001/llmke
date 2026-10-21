#!/usr/bin/env python3
"""按 LLMKE 规范 V1 生成目标 schema（旧模型仅作参考）。

输入：`p0-02-entity-extract.py` 产出的实体模型 CSV（旧库参考）
输出：
    target-schema-v1.sql        目标 DDL
    target-schema-v1-mapping.csv 旧列 → 新列逐列映射（迁移脚本输入）
    target-model.csv            目标模型 CSV（供 p0-02-ddl-diff.py 回环校验）

改写的都是"表示层"，不改业务语义：
    create_by            -> created_by   VARCHAR(64) NOT NULL
    update_by / modify_by-> updated_by   VARCHAR(64) NOT NULL
    gmt_create           -> created_at   DATETIME(3) NOT NULL
    gmt_modified         -> updated_at   DATETIME(3) NOT NULL
    is_del / is_dtl      -> is_deleted   TINYINT(1) NOT NULL DEFAULT 0

显式偏差（与 SCHEMA-STANDARD-V1.md 的一致性说明）：
    文档写主键 `BIGINT UNSIGNED AUTO_INCREMENT`，此处输出 `BIGINT`。
    原因：旧库外键列（kb_id / file_id ...）都是 `BIGINT`，若主键改 UNSIGNED 而不改所有引用列，
    会出现"无符号/有符号混用"的隐式转换，反而让索引失效。要么全改、要么都不改 —— 属待确认项 §4。
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

# 第三元素是"可空"的取值，必须与实体模型同一套中文口径（"否"=NOT NULL）。
# 早先这里写 "NO"，与下面的 `nullable == "否"` 不匹配，导致审计列被输出成 NULL —— 已修。
AUDIT = {
    "create_by": ("created_by", "VARCHAR(64)", "否"),
    "update_by": ("updated_by", "VARCHAR(64)", "否"),
    "modify_by": ("updated_by", "VARCHAR(64)", "否"),
    "gmt_create": ("created_at", "DATETIME(3)", "否"),
    "gmt_modified": ("updated_at", "DATETIME(3)", "否"),
    "is_del": ("is_deleted", "TINYINT(1)", "否"),
    "is_dtl": ("is_deleted", "TINYINT(1)", "否"),
}
AUDIT_DEFAULT = {"is_deleted": "0"}


def norm_type(t: str, length: str) -> str:
    t = (t or "").upper().strip()
    length = (length or "").strip()
    if t == "DATETIME":
        return "DATETIME(3)"
    if t in ("VARCHAR", "CHAR"):
        return f"{t}({length or 255})"
    if "(" in t:
        return t
    return t or "VARCHAR(255)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, required=True, help="实体模型 CSV（旧库参考）")
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    if not a.model.is_file():
        print(f"FAIL: 模型 CSV 不存在: {a.model}")
        return 2

    rows = list(csv.DictReader(a.model.read_text(encoding="utf-8").splitlines()))
    tables: dict[str, list] = {}
    for r in rows:
        tables.setdefault(r["表名"], []).append(r)

    a.out_dir.mkdir(parents=True, exist_ok=True)
    ddl, mapping, target = [], [], []
    renames = 0
    for table in sorted(tables):
        cols = tables[table]
        body, pks = [], []
        seen_new = set()
        for c in cols:
            old, new = c["字段名"], c["字段名"]
            typ, nullable, default = norm_type(c["SQL类型"], c["长度"]), c["可空"], (c["默认值"] or "")
            if old.lower() in AUDIT:
                new, typ, nullable = AUDIT[old.lower()]
                default = AUDIT_DEFAULT.get(new, default)
                renames += 1
            if new in seen_new:          # 合并后的重名（如 update_by 与 modify_by 同时存在）
                mapping.append({"table": table, "old_column": old, "new_column": "(merged into " + new + ")",
                                "old_type": typ, "new_type": typ})
                continue
            seen_new.add(new)
            if c["主键"] == "是":
                pks.append(new)
            null_sql = "" if nullable == "否" else "NULL"
            if nullable == "否":
                null_sql = "NOT NULL"
            auto = " AUTO_INCREMENT" if c["自增"] == "是" else ""
            dflt = ""
            if default:
                numeric_type = typ.split("(")[0] in ("BIGINT", "INT", "TINYINT", "SMALLINT", "DECIMAL", "DOUBLE")
                if numeric_type and default.replace("-", "").isdigit():
                    dflt = f" DEFAULT {default}"
                else:
                    dflt = f" DEFAULT '{default}'"
            elif new in AUDIT_DEFAULT:
                dflt = f" DEFAULT {AUDIT_DEFAULT[new]}"
            comment = (c["注释"] or "").replace("'", "''")
            if old.lower() in AUDIT and old != new:
                comment = (comment + f"（原 {old}）").strip()
            parts = [f"  `{new}` {typ}", null_sql, auto.strip(), dflt.strip()]
            line = " ".join(p for p in parts if p)
            if comment:
                line += f" COMMENT '{comment}'"
            body.append(line)
            mapping.append({"table": table, "old_column": old, "new_column": new,
                            "old_type": c["SQL类型"] + (("(" + c["长度"] + ")") if c["长度"] else ""),
                            "new_type": typ})
            target.append({"表名": table, "字段名": new, "SQL类型": typ.split("(")[0],
                           "长度": typ.partition("(")[2].rstrip(")"),
                           "可空": nullable, "主键": "是" if c["主键"] == "是" else "",
                           "自增": c["自增"], "默认值": default, "注释": c["注释"] or ""})
        if pks:
            body.append(f"  PRIMARY KEY (`{pks[0]}`)")
        ddl.append(f"CREATE TABLE `{table}` (\n" + ",\n".join(body) +
                   "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;\n")

    (a.out_dir / "target-schema-v1.sql").write_text(
        "-- LLMKE 目标 schema V1（由 schema-generate.py 生成；旧模型仅作参考）\n"
        "-- 规范见 SCHEMA-STANDARD-V1.md；未含二级索引（无查询基线时不臆造）\n\n"
        + "\n".join(ddl), encoding="utf-8")

    with (a.out_dir / "target-schema-v1-mapping.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["table", "old_column", "new_column", "old_type", "new_type"])
        w.writeheader()
        w.writerows(mapping)

    with (a.out_dir / "target-model.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["表名", "字段名", "SQL类型", "长度", "可空", "主键", "自增", "默认值", "注释"])
        w.writeheader()
        w.writerows(target)

    print(f"表={len(tables)}  目标列={len(target)}  审计列改写={renames}  映射行={len(mapping)}")
    print(f"输出目录: {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
