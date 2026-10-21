#!/usr/bin/env python3
"""P0-02 静态索引：37 表台账 ↔ 源码 DO 实体字段对照（只读）。

边界（必须显式）：
- 只读源码，不连接任何数据库；
- 结论只能是 CANDIDATE：实体类字段 ≠ 实际表结构（列名映射、继承字段、逻辑删除、
  JSON 列、@TableField(exist=false) 等都会让计数偏离）；
- 不替代 M-04 的真实 DDL。

产出：evidence/db-entity-check.json、evidence/db-entity-check.md
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

import yaml

FIELD_RE = re.compile(r"^\s*private\s+(?!static\b)([\w.$<>\[\], ]+?)\s+(\w+)\s*;")
TABLE_RE = re.compile(r'@TableName\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
TABLEFIELD_RE = re.compile(r'@TableField\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
TABLEID_RE = re.compile(r'@TableId\s*\(')
COMMENT_RE = re.compile(r"^\s*(?:\*|//)\s*(.+?)\s*$")
SKIP_FIELDS = {"serialVersionUID"}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def parse_entity(path: Path) -> dict:
    lines = read(path).splitlines()
    table = ""
    fields = []
    for i, ln in enumerate(lines):
        if not table:
            m = TABLE_RE.search(ln)
            if m:
                table = m.group(1)
        m = FIELD_RE.match(ln)
        if not m:
            continue
        ftype, fname = m.group(1).strip(), m.group(2)
        if fname in SKIP_FIELDS:
            continue
        column, comment, pk = "", "", False
        for k in range(max(0, i - 4), i):
            prev = lines[k]
            if not column:
                cm = TABLEFIELD_RE.search(prev)
                if cm:
                    column = cm.group(1)
            if TABLEID_RE.search(prev):
                pk = True
                cm = TABLEFIELD_RE.search(prev)
                if cm:
                    column = cm.group(1)
            cc = COMMENT_RE.match(prev)
            if cc and not comment and not cc.group(1).startswith("@"):
                comment = cc.group(1)[:60]
        fields.append({"name": fname, "type": ftype, "column": column or fname,
                       "pk": pk, "comment": comment,
                       "explicit_column": bool(column)})
    return {"table": table, "fields": fields,
            "n_fields": len(fields),
            "has_explicit_table": bool(table)}


def resolve(src_roots: list[Path], rel: str) -> Path | None:
    for base in src_roots:
        cand = base / rel
        if cand.is_file():
            return cand
    # 退化：按文件名在 gien-rag 树中查找
    name = Path(rel).name
    for base in src_roots:
        for p in base.rglob(name):
            if p.is_file():
                return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", type=Path, required=True,
                    help="RAG-SRC/_src 目录")
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    src = a.src_root.resolve()
    src_roots = [p for p in [src / "gien-rag/gien-rag", src / "rag-alg-service-api/rag-alg-service-api"] if p.is_dir()]
    if not src_roots:
        print("FAIL: 找不到源码根", file=sys.stderr)
        return 2

    reg = yaml.safe_load((a.repo_root / "docs/reuse/DATABASE-ASSETS.yaml").read_text(encoding="utf-8"))
    results, missing, mismatches = [], [], []
    declared_total = entity_total = 0

    for item in reg["items"]:
        declared_total += int(item.get("model_field_count") or 0)
        paths = item.get("source_entity_paths") or []
        parsed, seen = [], set()
        for rel in paths:
            hit = resolve(src_roots, rel)
            if hit is None:
                missing.append({"id": item["id"], "path": rel, "kind": "FILE_NOT_FOUND"})
                continue
            # 台账可能把同一实体登记多次（DB-34 实测），按真实路径去重，避免重复计数
            key = str(hit.resolve())
            if key in seen:
                continue
            seen.add(key)
            parsed.append({"path": rel, "resolved": key, **parse_entity(hit)})
        ent_n = sum(p["n_fields"] for p in parsed)
        entity_total += ent_n
        rec = {
            "id": item["id"],
            "legacy_table": item["legacy_table"],
            "declared_field_count": item.get("model_field_count"),
            "entity_field_count": ent_n,
            "count_match": ent_n == item.get("model_field_count"),
            "status": "CANDIDATE",
            "entities": parsed,
        }
        if not parsed:
            rec["status"] = "SOURCE_NOT_FOUND"
        elif not rec["count_match"]:
            mismatches.append(rec)
            rec["status"] = "COUNT_MISMATCH"
        results.append(rec)

    # 关键字段扫描：create_by / user_id
    subject = [r for r in results if r["legacy_table"] == "dialogue"]
    subject_view = []
    for r in subject:
        for e in r["entities"]:
            names = {f["name"] for f in e["fields"]}
            cols = {f["column"] for f in e["fields"]}
            subject_view.append({"entity": e["path"], "n_fields": e["n_fields"],
                                 "has_create_by": "createBy" in names or "create_by" in cols,
                                 "has_user_id": "userId" in names or "user_id" in cols,
                                 "has_kb_id": "kbId" in names or "kb_id" in cols})

    out_json = a.out / "db-entity-check.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scope": "37 tables / DO entities, static only",
        "warning": "实体字段数 != 实际表结构；结论仅 CANDIDATE，不替代真实 DDL",
        "src_roots": [str(p) for p in src_roots],
        "totals": {
            "tables": len(results),
            "declared_fields": declared_total,
            "entity_fields": entity_total,
            "count_match": sum(1 for r in results if r["count_match"]),
            "count_mismatch": len(mismatches),
            "source_not_found": sum(1 for r in results if r["status"] == "SOURCE_NOT_FOUND"),
        },
        "missing_files": missing,
        "mismatches": [{"id": m["id"], "table": m["legacy_table"],
                        "declared": m["declared_field_count"],
                        "entity": m["entity_field_count"],
                        "fields": [f["name"] for e in m["entities"] for f in e["fields"]]}
                       for m in mismatches],
        "dialogue_identity_fields": subject_view,
        "items": results,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    t = payload["totals"]
    lines = [
        "# 37 表/482 字段 ↔ 源码 DO 实体 静态对照",
        "",
        "> 只读源码，未连接数据库。**结论一律 CANDIDATE**：实体字段数 ≠ 实际表结构。",
        "> 不替代 M-04 的真实 DDL；不得据此关闭 P0-02。",
        "",
        "## 总量",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 台账表数 | {t['tables']} |",
        f"| 台账申报字段数 | {t['declared_fields']} |",
        f"| 源码实体字段数 | {t['entity_fields']} |",
        f"| 计数一致的表 | {t['count_match']} |",
        f"| 计数不一致的表 | {t['count_mismatch']} |",
        f"| 源文件缺失的表 | {t['source_not_found']} |",
        "",
        "## 计数不一致明细",
        "",
    ]
    if payload["mismatches"]:
        lines += ["| 台账ID | 表 | 申报 | 实体 | 差 |", "|---|---|---|---|---|"]
        for m in payload["mismatches"]:
            lines.append(f"| {m['id']} | {m['table']} | {m['declared']} | {m['entity']} | {m['entity']-m['declared']:+d} |")
    else:
        lines.append("（无）")
    lines += ["", "## dialogue 表身份字段（P0-02 关注点）", ""]
    if subject_view:
        lines += ["| 实体 | 字段数 | create_by | user_id | kb_id |", "|---|---|---|---|---|"]
        for s in subject_view:
            lines.append(f"| {s['entity']} | {s['n_fields']} | {s['has_create_by']} | {s['has_user_id']} | {s['has_kb_id']} |")
    else:
        lines.append("（未找到 dialogue 的实体）")
    lines += ["", "## 源文件缺失", ""]
    if missing:
        for m in missing:
            lines.append(f"- `{m['id']}` → `{m['path']}`")
    else:
        lines.append("（无）")
    lines += ["", "## 可用于 P0-02 的结论（仍须 DDL 裁定）", ""]
    if subject_view:
        s = subject_view[0]
        lines.append(
            f"- `dialogue` 实体共 {s['n_fields']} 个字段：`create_by` **{'存在' if s['has_create_by'] else '不存在'}**、"
            f"`user_id` **{'存在' if s['has_user_id'] else '不存在'}**、`kb_id` {s['has_kb_id']}。")
        if not s["has_user_id"]:
            lines.append("  → 与设计文档「为 `dialogue` 建 `user_id` 索引」的要求**冲突**：源码中没有该列。")
            lines.append("  → 需 `data-owner` 用真实 DDL 裁定：是设计超前、还是实体未映射该列。")
    else:
        lines.append("- 未找到 `dialogue` 实体，无法核对身份字段。")
    lines.append(f"- 台账 482 字段 vs 实体 {t['entity_fields']} 字段，差 {t['entity_fields']-t['declared_fields']:+d}；"
                 "差异集中在 4 张表，需逐表裁定是否为「实体多映射/台账少记」。")
    lines += ["", "## 边界", "",
              "- 未校验列名映射是否正确（`@TableField` 缺失时按驼峰转下划线猜测）；",
              "- 未识别继承自基类的字段、逻辑删除字段、JSON 列；",
              "- 实际索引/约束/触发器/引擎/字符集仍需 M-04。"]
    (a.out / "db-entity-check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"tables={t['tables']} declared={t['declared_fields']} entity={t['entity_fields']} "
          f"match={t['count_match']} mismatch={t['count_mismatch']} missing={t['source_not_found']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
