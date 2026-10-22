#!/usr/bin/env python3
"""A2 扩展：全 37 张表的 ORM 映射覆盖率（只读，CANDIDATE）。

回答一个问题：**能不能用 ORM 层替代 DDL 来确认列？**
如果多数表连 resultMap 都没有，答案就是不能——这是本脚本要给出的证据。

判定口径：
- FULL：resultMap 覆盖了实体全部字段
- PARTIAL：有 resultMap 但未覆盖全部字段
- NONE：mapper 存在但没有 resultMap（手写 SQL）
- NO_MAPPER：找不到 mapper 文件
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_mapper_columns import (find, find_report, columns_from_mapper, entity_info,
                               camel_to_snake, columns_seen_in_sql)  # noqa: E402

import yaml  # noqa: E402


def do_from_paths(paths: list[str]) -> str | None:
    for p in paths:
        name = Path(p).name
        if name.endswith("DO.java"):
            return name[: -len(".java")]     # AnswerDO.java -> AnswerDO
    return None


def analyze(src: Path, tid: str, table: str, do_name: str) -> dict:
    java, java_hits = find_report(src, do_name + ".java")
    rec = {"id": tid, "table": table, "entity": do_name,
           "entity_found": bool(java), "mapper_found": False,
           "coverage": "NO_ENTITY", "entity_fields": 0, "mapped": 0,
           "unmapped": [], "sql_columns": 0}
    if not java:
        return rec

    ent = entity_info(java)
    fields = [n for _t, n in ent["fields"]]
    rec["entity_fields"] = len(fields)
    rec["extends"] = ent["extends"]

    # mapper 命名：AnswerDO -> AnswerMapper.xml（去掉 DO）
    stem = do_name[:-2] if do_name.endswith("DO") else do_name
    xml, xml_hits = find_report(src, stem + "Mapper.xml")
    rec["mapper_found"] = bool(xml)
    # 同名文件 >1 时必须显式报告：静默取首个会读错文件，污染所有下游结论
    if len(java_hits) > 1 or len(xml_hits) > 1:
        rec["ambiguous_files"] = {"entity_hits": java_hits, "mapper_hits": xml_hits}
    if not xml:
        rec["coverage"] = "NO_MAPPER"
        rec["unmapped"] = fields
        return rec

    m = columns_from_mapper(xml)
    colmap = m["result_map"]
    entity_cols = {camel_to_snake(n) for n in fields}
    sql_cols = columns_seen_in_sql(xml, entity_cols)
    mapped = [f for f in fields if f in colmap]
    unmapped = [f for f in fields if f not in colmap]
    rec.update(mapped=len(mapped), unmapped=unmapped,
               sql_columns=len(sql_cols), mapped_fields=mapped)
    if not colmap:
        rec["coverage"] = "NONE"          # 有 mapper 但无 resultMap
    elif len(unmapped) == 0:
        rec["coverage"] = "FULL"
    else:
        rec["coverage"] = "PARTIAL"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    src = a.src_root.resolve()

    reg = yaml.safe_load((a.repo_root / "docs/reuse/DATABASE-ASSETS.yaml")
                         .read_text(encoding="utf-8"))
    results, skipped = [], []
    for item in reg["items"]:
        do_name = do_from_paths(item.get("source_entity_paths") or [])
        if not do_name:
            skipped.append(item["id"])
            continue
        results.append(analyze(src, item["id"], item["legacy_table"], do_name))

    from collections import Counter
    cov = Counter(r["coverage"] for r in results)
    payload = {
        "scope": "全 37 表的 ORM 映射覆盖率（只读）",
        "warning": "FULL 也不等于 DDL：索引/约束/引擎/字符集不可见；结论一律 CANDIDATE",
        "totals": {"tables": len(results), **cov},
        "ambiguous_entity_or_mapper": [r["id"] for r in results if r.get("ambiguous_files")],
        "skipped_no_do": skipped,
        "coverage_legend": {
            "FULL": "resultMap 覆盖全部实体字段",
            "PARTIAL": "有 resultMap 但未覆盖全部字段",
            "NONE": "有 mapper 但无 resultMap（纯手写 SQL）",
            "NO_MAPPER": "找不到 mapper 文件",
            "NO_ENTITY": "找不到 DO 文件",
        },
        "tables": results,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    if re.search(r"(?<![\w.])(?:/home|/Users)/[A-Za-z0-9._-]+/", body):
        print("FAIL: personal absolute path in artifact")
        return 3
    a.out.write_text(body + "\n", encoding="utf-8")

    print(f"tables={len(results)} " + " ".join(f"{k}={v}" for k, v in cov.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
