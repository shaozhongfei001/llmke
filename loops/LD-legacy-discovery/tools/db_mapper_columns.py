#!/usr/bin/env python3
"""A2：用 MyBatis Mapper XML 给四张差异表做逐列归因（只读）。

为什么用 Mapper：DO 只有属性名，Mapper 的 resultMap / Base_Column_List 才给出**列名**。
这比「按驼峰猜下划线」强，但**仍不等于 DDL**：索引、约束、引擎、字符集、触发器都看不到。

输出：evidence/db-mapper-columns.json、evidence/db-mapper-columns.md
结论分类：SOURCE_FACT（源码可证）/ PENDING_DDL（需真实 DDL 裁定）
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

RESULT_RE = re.compile(r'<(?:id|result)\s+[^>]*column="([^"]+)"[^>]*property="([^"]+)"', re.S)
RESULT_RE2 = re.compile(r'<(?:id|result)\s+[^>]*property="([^"]+)"[^>]*column="([^"]+)"', re.S)
COL_LIST_RE = re.compile(r'<sql\s+id="Base_Column_List"[^>]*>(.*?)</sql>', re.S)
IDENT_RE = re.compile(r'`?([A-Za-z_][A-Za-z0-9_]*)`?')
LOGIC_RE = re.compile(r'@TableLogic|logic-delete-field|logicDeleteField')
JSON_RE = re.compile(r'typeHandler\s*=|JSON|json', re.I)
EXTENDS_RE = re.compile(r'public\s+class\s+\w+\s+extends\s+([\w.]+)')

TABLES = {
    "DB-18": ("re_embedding_file", "ReEmbeddingFileDO", "ReEmbeddingFileMapper.xml"),
    "DB-19": ("re_embedding_retry_task", "ReEmbeddingRetryTaskDO", "ReEmbeddingRetryTaskMapper.xml"),
    "DB-20": ("re_embedding_task", "ReEmbeddingTaskDO", "ReEmbeddingTaskMapper.xml"),
    "DB-34": ("user_operate", "UserOperateDO", "UserOperateMapper.xml"),
    "DIALOGUE": ("dialogue", "DialogueDO", "DialogueMapper.xml"),
}


def find(root: Path, pattern: str) -> Path | None:
    hits = [p for p in root.rglob(pattern) if p.is_file()]
    return hits[0] if hits else None


def columns_from_mapper(xml: Path) -> dict:
    text = xml.read_text(encoding="utf-8", errors="replace")
    cols = {}
    for m in RESULT_RE.finditer(text):
        cols[m.group(2).strip()] = m.group(1).strip()
    for m in RESULT_RE2.finditer(text):
        cols.setdefault(m.group(1).strip(), m.group(2).strip())
    base = []
    m = COL_LIST_RE.search(text)
    if m:
        for tok in IDENT_RE.finditer(m.group(1)):
            v = tok.group(1)
            if v.lower() not in ("select", "from", "where", "as"):
                base.append(v)
    return {"result_map": cols, "base_column_list": base,
            "has_logic_delete": bool(LOGIC_RE.search(text)),
            "has_json_handler": bool(JSON_RE.search(text))}


SQL_BLOCK_RE = re.compile(r"<(select|insert|update|delete)\b.*?</\1>", re.S)


def columns_seen_in_sql(xml: Path, entity_columns: set[str]) -> set[str]:
    """从手写 SQL 中提取「出现过」的实体列名（弱证据：可能是 WHERE 条件里的其他表列）。"""
    text = xml.read_text(encoding="utf-8", errors="replace")
    seen = set()
    for block in SQL_BLOCK_RE.finditer(text):
        for ident in IDENT_RE.finditer(block.group(0)):
            v = ident.group(1).lower()
            if v in entity_columns:
                seen.add(v)
    return seen


def entity_info(java: Path) -> dict:
    text = java.read_text(encoding="utf-8", errors="replace")
    fields = re.findall(r"^\s*private\s+(?!static\b)([\w.$<>\[\], ]+?)\s+(\w+)\s*;", text, re.M)
    ext = EXTENDS_RE.search(text)
    return {"fields": [(t.strip(), n) for t, n in fields],
            "extends": ext.group(1) if ext else None,
            "has_table_logic": bool(LOGIC_RE.search(text))}


def camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    src = a.src_root.resolve()

    results, notes = [], []
    for tid, (table, do_name, mapper_name) in TABLES.items():
        java = find(src, do_name + ".java")
        xml = find(src, mapper_name)
        rec = {"table_id": tid, "table": table, "entity": do_name,
               "entity_found": bool(java), "mapper_found": bool(xml),
               "classification": "SOURCE_FACT", "items": [], "pending": []}
        if not java:
            rec["classification"] = "PENDING_DDL"
            notes.append(f"{tid}: 找不到 {do_name}.java")
            results.append(rec)
            continue
        ent = entity_info(java)
        rec["extends"] = ent["extends"]
        rec["entity_has_table_logic"] = ent["has_table_logic"]
        colmap = {}
        sql_cols = set()
        if xml:
            m = columns_from_mapper(xml)
            colmap = m["result_map"]
            entity_cols = {camel_to_snake(n) for _t, n in ent["fields"]}
            sql_cols = columns_seen_in_sql(xml, entity_cols)
            rec["mapper"] = {"result_map_size": len(colmap),
                             "base_column_list_size": len(m["base_column_list"]),
                             "has_logic_delete": m["has_logic_delete"],
                             "has_json_handler": m["has_json_handler"],
                             "columns_seen_in_sql": sorted(sql_cols),
                             "sql_column_evidence": "WEAK (手写 SQL 中出现的标识符，非 schema 定义)"}
        for ftype, fname in ent["fields"]:
            col = colmap.get(fname) or camel_to_snake(fname)
            mapped = fname in colmap
            item = {"field": fname, "type": ftype, "column_guess": col,
                    "mapped_in_resultmap": mapped,
                    "seen_in_sql": col.lower() in sql_cols,
                    "basis": "MAPPER_RESULTMAP" if mapped else "CAMEL_GUESS"}
            # 归因：无 resultMap 映射的字段，可能是非持久化属性
            if not mapped:
                item["attribution"] = "可能非持久化属性 / 或 resultMap 未列全 —— 待 DDL 裁定"
                rec["pending"].append(fname)
            if re.search(r"(@TableLogic)", "") or fname.lower() in ("isdel", "is_del", "deleted"):
                item["attribution"] = item.get("attribution", "疑似逻辑删除字段") 
                if fname.lower() in ("isdel", "is_del", "deleted"):
                    item["attribution"] = "疑似逻辑删除字段（源码可见，语义待 DDL/查询确认）"
            rec["items"].append(item)
        if ent["extends"]:
            rec["pending"].append(f"继承自 {ent['extends']} 的字段未计入")
        results.append(rec)

    payload = {
        "scope": "四张差异表 + dialogue：Mapper XML 列名 vs DO 字段",
        "warning": "Mapper 列名是源码事实，但不等于 DDL；索引/约束/引擎/字符集仍需 M-04",
        "classification_legend": {
            "SOURCE_FACT": "源码可直接证明（mapping 存在）",
            "CANDIDATE": "源码可推断，需 DDL 确认",
            "PENDING_DDL": "必须真实 DDL 才能裁定",
        },
        "tables": results,
        "notes": notes,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    if re.search(r"(?<![\w.])(?:/home|/Users)/[A-Za-z0-9._-]+/", body):
        print("FAIL: personal absolute path in artifact")
        return 3
    a.out.write_text(body + "\n", encoding="utf-8")

    for r in results:
        print(f"{r['table_id']:9s} {r['table']:26s} entity_fields={len(r['items']):2d} "
              f"mapped={sum(1 for i in r['items'] if i['mapped_in_resultmap']):2d} "
              f"pending={len(r['pending'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
