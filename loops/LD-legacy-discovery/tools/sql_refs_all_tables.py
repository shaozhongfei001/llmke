#!/usr/bin/env python3
"""A1：全 37 表的列引用索引，**每一列都带证据等级**。

第六轮只做了 4 张表；扩展到全表时最大的坑是「列从哪来」：
台账只有字段计数、没有字段名清单，所以候选列只能两类来源：

  MAPPER_FACT      : resultMap 里显式声明的 column（源码事实）
  CAMEL_INFERENCE  : 由 DO 属性名驼峰转下划线推断（**推断，不是事实**）

判定"被引用"时只认 SQL/映射中真实出现的标识符，并且**继承推断来的列名不算引用**。
没有任何一列可以据此断言数据库存在。
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sql_column_refs import statements, TABLE_RE  # noqa: E402
from db_mapper_columns import find, columns_from_mapper, entity_info  # noqa: E402

import yaml  # noqa: E402


def norm(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    src = a.src_root.resolve()

    reg = yaml.safe_load((a.repo_root / "docs/reuse/DATABASE-ASSETS.yaml").read_text(encoding="utf-8"))
    tables, meta = {}, {}
    for item in reg["items"]:
        t = item["legacy_table"]
        tables[t] = set()
        meta[t] = {"id": item["id"], "declared": item.get("model_field_count"),
                   "entity": None, "mapper_cols": set(), "inferred": set()}

    # 1) 列来源：resultMap（事实）+ 驼峰推断（推断）
    for t in list(tables):
        do = None
        for item in reg["items"]:
            if item["legacy_table"] == t:
                for p in item.get("source_entity_paths") or []:
                    if Path(p).name.endswith("DO.java"):
                        do = Path(p).name[: -len(".java")]
        if not do:
            continue
        java = find(src, do + ".java")
        if not java:
            continue
        meta[t]["entity"] = do
        fields = [n for _t, n in entity_info(java)["fields"]]
        stem = do[: -len("DO")] if do.endswith("DO") else do
        xml = find(src, stem + "Mapper.xml")
        mapped = set()
        if xml:
            rm = columns_from_mapper(xml)["result_map"]
            mapped = {c.lower() for c in rm.values()}
        meta[t]["mapper_cols"] = mapped
        # 判定映射方式：MyBatis-Plus 的 BaseMapper 实体没有 XML SQL，
        # 运行时由框架按驼峰→下划线约定生成 SQL。此时"零 SQL 引用"不代表不被访问。
        mapper_java = find(src, stem + "Mapper.java")
        mp = False
        if mapper_java:
            mj = mapper_java.read_text(encoding="utf-8", errors="replace")
            mp = "BaseMapper" in mj
        n_stmt = 0
        if xml:
            x = xml.read_text(encoding="utf-8", errors="replace")
            n_stmt = len(re.findall(r"<(select|insert|update|delete)\b", x))
        meta[t]["mapping_mode"] = ("MP_BASEMAPPER" if (mp and n_stmt == 0)
                                   else ("XML_SQL" if n_stmt else "RESULTMAP_ONLY"))
        meta[t]["table_annotation"] = bool(re.search(r'@TableName\s*\(', java.read_text(encoding="utf-8", errors="replace")))
        for f in fields:
            c = norm(f)
            tables[t].add(c)
            if c not in mapped:
                meta[t]["inferred"].add(c)

    # 2) 单次遍历：收集每个表在 SQL 中被引用的列
    referenced = {t: set() for t in tables}
    files = [p for p in src.rglob("*") if p.is_file()
             and p.suffix in (".xml", ".java", ".sql") and "/.git/" not in p.as_posix()]
    scanned = 0
    for p in files:
        try:
            stmts = statements(p)
        except Exception:
            continue
        if not stmts:
            continue
        scanned += 1
        for st in stmts:
            body = st["text"]
            hit_tables = {x.lower() for x in TABLE_RE.findall(body)} & set(tables)
            for t in hit_tables:
                for c in tables[t]:
                    if re.search(rf"(?<![\w]){re.escape(c)}(?![\w])", body, re.I):
                        referenced[t].add(c)

    out_tables = []
    for t, cols in tables.items():
        m = meta[t]
        ref = referenced[t]
        out_tables.append({
            "table_id": m["id"], "table": t, "entity": m["entity"],
            "declared_count": m["declared"], "entity_fields": len(cols),
            "columns_total": len(cols),
            "columns_mapper_fact": len(cols - m["inferred"]),
            "columns_camel_inference": len(m["inferred"]),
            "columns_referenced": len(ref),
            "mapping_mode": m.get("mapping_mode", "UNKNOWN"),
            "table_annotation": m.get("table_annotation", False),
            "zero_reference_explained": ("MP_BASEMAPPER：运行时由框架生成 SQL，XML 中本就无 SQL"
                                         if m.get("mapping_mode") == "MP_BASEMAPPER" and not ref
                                         else ""),
            "columns_unreferenced": sorted(cols - ref),
            "unreferenced_from_mapper_fact": sorted((cols - m["inferred"]) - ref),
            "evidence_levels": {
                "MAPPER_FACT": "resultMap 显式声明",
                "MP_BASEMAPPER_CONVENTION": "MyBatis-Plus 按驼峰→下划线映射（框架约定，非 DDL）",
                "CAMEL_INFERENCE": "DO 属性驼峰推断（无框架约定支撑时）",
                "SQL_REFERENCE": "SQL/映射文本中出现（不等于 DB 存在）",
            },
            "inferred_basis": ("MP_BASEMAPPER_CONVENTION"
                               if m.get("mapping_mode") == "MP_BASEMAPPER" else "CAMEL_INFERENCE"),
            "referenced_columns": sorted(ref),
        })

    payload = {
        "scope": "全 37 表列引用索引（只读）",
        "warning": "列名多为驼峰推断；SQL 出现不等于数据库存在；本索引不能替代 DDL",
        "files_with_statements": scanned,
        "totals": {
            "tables": len(out_tables),
            "columns": sum(x["columns_total"] for x in out_tables),
            "mapper_fact": sum(x["columns_mapper_fact"] for x in out_tables),
            "camel_inference": sum(x["columns_camel_inference"] for x in out_tables),
            "referenced": sum(x["columns_referenced"] for x in out_tables),
        },
        "tables": sorted(out_tables, key=lambda x: x["table_id"]),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    if re.search(r"(?<![\w.])(?:/home|/Users)/[A-Za-z0-9._-]+/", body):
        print("FAIL: personal absolute path")
        return 3
    a.out.write_text(body + "\n", encoding="utf-8")

    t = payload["totals"]
    print(f"tables={t['tables']} columns={t['columns']} "
          f"mapper_fact={t['mapper_fact']} camel_inference={t['camel_inference']} "
          f"referenced={t['referenced']} files={scanned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
