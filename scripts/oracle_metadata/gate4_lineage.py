#!/usr/bin/env python3
"""Gate 4 (v2) — per-statement object + field lineage.

Fixes vs v1:
- Each DML statement parses ONLY its own line-range segment (no cross-
  statement column mis-assignment).
- Comments stripped before parsing; target columns strictly [A-Z0-9_$#]+.
- INSERT..SELECT mapped positionally with expression classification.
- UPDATE SET and MERGE handled with appropriate granularity.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from catalog import connect_db
from conn import BUSINESS_FOCUS, REPORT_DIR, connect_readonly, q, require_focus, scrub
from plsql_utils import (
    classify_expression,
    extract_columns,
    segment_lines,
    split_top_level,
    strip_comments,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
PRIVATE = ROOT / "data" / "metadata" / "source_private"

INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+([A-Za-z][\w$#.\"]*)\s*(?:NOLOGGING|LOGGING)?\s*(?:\(([^)]*)\))?\s*",
    re.IGNORECASE,
)
SUBQUERY_ALIAS_RE = re.compile(
    r"\bAS\s+([A-Za-z][\w$#]*)\b", re.IGNORECASE
)
SELECT_FROM_RE = re.compile(r"\bSELECT\b(.*?)\bFROM\b(.*)", re.IGNORECASE | re.S)
FROM_ITEM_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+([A-Za-z][\w$#.\"]*)", re.IGNORECASE
)
UPDATE_RE = re.compile(
    r"UPDATE\s+([A-Za-z][\w$#.\"]*)\s+(?:\w+\s+)?SET\s+(.*?)(?:\bWHERE\b|;|$)",
    re.IGNORECASE | re.S,
)
MERGE_RE = re.compile(
    r"MERGE\s+INTO\s+([A-Za-z][\w$#.\"]*).*?\bUSING\s+(.*?)\bON\s*\(",
    re.IGNORECASE | re.S,
)
SET_PAIR_RE = re.compile(r"^\s*([A-Za-z][\w$#]*)\s*=\s*(.+)$", re.S)
COL_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_$#]*$")
ALIAS_RE = re.compile(r"\bAS\s+([A-Za-z][\w$#]*)\s*$", re.IGNORECASE)
BARE_ALIAS_RE = re.compile(r"\s+([A-Za-z][\w$#]*)\s*$")
DISTINCT_RE = re.compile(r"^\s*DISTINCT\s+", re.IGNORECASE)
VALUES_RE = re.compile(r"\bVALUES\s*\((.*)\)\s*;?\s*$", re.IGNORECASE | re.S)


def lid(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def split_owner_name(ref, default_owner):
    ref = ref.strip().strip('"')
    if "." in ref:
        o, n = ref.split(".", 1)
        return o.upper(), n.upper().strip('"')
    return default_owner.upper(), ref.upper()


def parse_from_tables(seg: str) -> list[str]:
    return [t.strip().strip('"').upper() for t in FROM_ITEM_RE.findall(seg)]


def _skip_ws(seg, i):
    while i < len(seg) and seg[i].isspace():
        i += 1
    return i


def _skip_balanced_parens(seg, i):
    """i points at '('. Returns index just past the matching ')'."""
    depth, in_q = 0, False
    while i < len(seg):
        ch = seg[i]
        if in_q:
            if ch == "'":
                if i + 1 < len(seg) and seg[i + 1] == "'":
                    i += 2
                    continue
                in_q = False
            i += 1
            continue
        if ch == "'":
            in_q = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def extract_select_items(seg: str, start_pos: int = 0):
    """Extract the MAIN top-level SELECT list; skips WITH CTEs; FROM at depth 0."""
    i = _skip_ws(seg, start_pos)
    if re.match(r"WITH\b", seg[i:], re.IGNORECASE):
        i += 4
        while i < len(seg):
            while i < len(seg) and seg[i] != "(":
                i += 1
            if i >= len(seg):
                return [], ""
            i = _skip_balanced_parens(seg, i)
            i = _skip_ws(seg, i)
            if i < len(seg) and seg[i] == ",":
                i += 1
                continue
            break
    m = re.match(r"\s*SELECT\b", seg[i:], re.IGNORECASE)
    if not m:
        return [], ""
    i += m.end()
    depth, in_q, j = 0, False, i
    while j < len(seg):
        ch = seg[j]
        if in_q:
            if ch == "'":
                if j + 1 < len(seg) and seg[j + 1] == "'":
                    j += 2
                    continue
                in_q = False
            j += 1
            continue
        if ch == "'":
            in_q = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and re.match(r"FROM\b", seg[j:], re.IGNORECASE):
            break
        j += 1
    if j >= len(seg):
        return [], ""
    return split_top_level(seg[i:j].strip()), seg[j:]


CASE_ALIAS_RE = re.compile(
    r"\b((?:(?:SUM|COUNT|AVG|MIN|MAX|NVL)\s*\(\s*)?CASE\b.*?\bEND\s*\)?)\s+AS\s+([A-Za-z][\w$#]*)\b",
    re.IGNORECASE | re.S,
)


def build_inner_defs(seg: str) -> dict[str, list[str]]:
    """Map `expr AS alias` definitions (incl. CTE/subquery selects); all candidates kept."""
    defs: dict[str, list[str]] = {}
    case_spans = []
    for m in CASE_ALIAS_RE.finditer(seg):
        expr = re.sub(r"\s+", " ", m.group(1)).strip()[:400]
        defs.setdefault(m.group(2).upper(), []).append(expr)
        case_spans.append((m.start(), m.end()))

    def in_case(pos):
        return any(a <= pos < b for a, b in case_spans)

    for m in re.finditer(
        r"([^,()\n][^,\n]*?)\s+AS\s+([A-Za-z][\w$#]*)\b", seg, re.IGNORECASE
    ):
        if in_case(m.start()):
            continue
        expr = m.group(1).strip()
        if re.search(r"\b(FROM|JOIN|INTO)\b", expr, re.IGNORECASE):
            continue
        if expr.upper() in ("END", "ELSE", "THEN"):
            continue
        defs.setdefault(m.group(2).upper(), []).append(expr[:400])
    return defs


def resolve_chain(col: str, inner_defs: dict[str, list[str]], max_depth: int = 4) -> str:
    """Resolve CTE/subquery alias chain across candidate definitions.

    `SUM(SEC_BAL)` where SEC_BAL == current alias is a re-aggregation wrapper;
    skip it and prefer deeper candidates like `SUM(T1.WJFLCJ)`.
    """
    cur = col.upper()
    best = col.upper()
    fallback = ""
    for _ in range(max_depth):
        cands = inner_defs.get(cur) or []
        progressed = False
        for nxt in cands:
            if nxt.upper() == cur:
                continue
            m = re.fullmatch(
                r"(?:SUM|COUNT|AVG|MIN|MAX)\s*\(\s*(?:[A-Za-z][\w$#]*\.)?([A-Za-z][\w$#]*)\s*\)",
                nxt.strip(),
                re.IGNORECASE,
            )
            if m and m.group(1).upper() == cur:
                fallback = fallback or nxt  # re-aggregation wrapper; keep as fallback
                continue
            if m and inner_defs.get(m.group(1).upper()):
                deeper_cands = [
                    d
                    for d in inner_defs[m.group(1).upper()]
                    if d.upper() != m.group(1).upper()
                ]
                if deeper_cands:
                    best = deeper_cands[0]
                    cur = best.upper()
                    progressed = True
                    break
            best = nxt
            cur = nxt.upper()
            progressed = True
            break
        if not progressed:
            break
    if best == col.upper() and fallback:
        return fallback
    return best


def build_field_rows(
    sid_snapshot, statement, seg, t_owner, t_obj, target_cols, select_items, src_tables,
    table_cols=None,
):
    rows = []
    has_subquery = "(" in (SELECT_FROM_RE.search(seg).group(2) if SELECT_FROM_RE.search(seg) else "")
    inner_defs = build_inner_defs(seg)
    positional_ok = target_cols and select_items and len(target_cols) == len(select_items)
    col_source = "INSERT_COL_LIST"
    if not target_cols and select_items:
        if table_cols and len(table_cols) == len(select_items):
            target_cols = [c for c in table_cols]
            positional_ok = True
            col_source = "TABLE_DICT_POSITIONAL"
        else:
            target_cols = []
            for i, item in enumerate(select_items):
                m = ALIAS_RE.search(item) or BARE_ALIAS_RE.search(item)
                if m and not re.fullmatch(
                    r"[A-Za-z][\w$#]*(\.[A-Za-z][\w$#]*)?", item.strip()
                ):
                    target_cols.append(m.group(1).upper())
                else:
                    cols = extract_columns(item)
                    target_cols.append(cols[-1] if len(cols) == 1 else f"COL{i+1}")
            positional_ok = len(target_cols) == len(select_items)
            col_source = "ALIAS_DERIVED"
    known_cols = set(table_cols or [])
    for i, col in enumerate(target_cols or []):
        if not COL_NAME_RE.match(col):
            continue
        expr = select_items[i].strip() if positional_ok else ""
        expr = DISTINCT_RE.sub("", expr)
        if positional_ok and expr and col != f"COL{i+1}":
            bm = BARE_ALIAS_RE.search(expr)
            if bm and bm.group(1).upper() == col and not re.fullmatch(
                r"[A-Za-z][\w$#]*(\.[A-Za-z][\w$#]*)?", expr
            ):
                expr = expr[: bm.start()].strip()
        # resolve subquery/CTE alias chain:
        # `T2.SEC_BAL` → SUM(SEC_BAL) → SUM(T1.WJFLCJ)
        resolved_via = ""
        bare_m = re.fullmatch(r"(?:[A-Za-z][\w$#]*\.)?([A-Za-z][\w$#]*)", expr or "")
        if bare_m and bare_m.group(1).upper() in inner_defs:
            chain_expr = resolve_chain(bare_m.group(1).upper(), inner_defs)
            if chain_expr.upper() not in (expr.upper(), bare_m.group(1).upper()):
                resolved_via = bare_m.group(1).upper()
                expr = chain_expr
        expr = re.sub(r"\s+AS\s*$", "", expr or "").strip()
        ttype = classify_expression(expr) if expr else "UNKNOWN"
        src_cols = extract_columns(expr) if expr else []
        src_col_str = ",".join(src_cols) if src_cols else "UNKNOWN"
        src_obj = src_tables[0] if len(src_tables) == 1 else (
            "MULTI" if src_tables else "UNKNOWN"
        )
        so, sn = split_owner_name(src_obj, t_owner) if src_obj not in ("UNKNOWN", "MULTI") else (src_obj, src_obj)
        # confidence rules
        confidence = "CODE_CONFIRMED" if (positional_ok and expr) else "PARTIAL"
        notes = []
        if known_cols and col not in known_cols:
            confidence = "PARTIAL"
            notes.append("target_col_not_in_table_dict")
        if col_source == "ALIAS_DERIVED":
            confidence = "PARTIAL" if confidence == "CODE_CONFIRMED" and col not in known_cols else confidence
            notes.append(f"col_source={col_source}")
        if has_subquery and ttype == "DIRECT_COPY" and not resolved_via:
            confidence = "PARTIAL"
            notes.append("subquery_alias_unresolved")
            ttype = "SUBQUERY_DERIVED"
        if resolved_via:
            notes.append(f"resolved_via={resolved_via}")
            # provenance from the whole segment (CTE inner FROMs), not just main FROM
            deep_tables = parse_from_tables(seg)
            if deep_tables:
                so, sn = (
                    split_owner_name(deep_tables[-1], t_owner)
                    if len(deep_tables) == 1
                    else ("MULTI", ",".join(sorted(set(deep_tables)))[:180])
                )
        if notes:
            expr = (expr + " " if expr else "") + f"/* {';'.join(notes)} */"
        rows.append(
            {
                "lineage_id": lid("fld", sid_snapshot, statement["statement_id"], col, i),
                "source_owner": so,
                "source_object": sn,
                "source_column": src_col_str,
                "transformation_type": ttype,
                "transformation_expression": expr[:400] if expr else "UNRESOLVED",
                "filters": "",
                "group_by": "",
                "partition_by": "",
                "target_owner": t_owner,
                "target_object": t_obj,
                "target_column": col.upper(),
                "producer_owner": statement["owner"],
                "producer_object": statement["object_name"],
                "evidence_statement_id": statement["statement_id"],
                "code_start_line": statement["start_line"],
                "code_end_line": statement["end_line"],
                "source_hash": statement.get("source_hash") or "",
                "confidence": confidence,
            }
        )
    return rows


def parse_insert(statement, seg, table_cols=None):
    t_owner = statement["target_owner"] or statement["owner"]
    t_obj = statement["target_object"] or "UNKNOWN"
    m = INSERT_RE.search(seg)
    col_list = []
    if m and m.group(2):
        col_list = [
            c.strip().strip('"').upper()
            for c in m.group(2).split(",")
            if COL_NAME_RE.match(c.strip().strip('"').upper() or " ")
        ]
    select_items, src_tables = [], parse_from_tables(seg)
    search_from = m.end() if m else 0
    items, from_rest = extract_select_items(seg, search_from)
    if items:
        select_items = items
        src_tables = parse_from_tables(from_rest)
    elif col_list:
        # INSERT INTO t (cols) VALUES (...) form
        vm = VALUES_RE.search(seg)
        if vm:
            select_items = split_top_level(vm.group(1).strip())
            src_tables = []  # VALUES items come from variables/constants
    fields = build_field_rows(
        None, statement, seg, t_owner, t_obj, col_list, select_items, src_tables,
        table_cols=table_cols,
    )
    return src_tables, fields


def parse_update(statement, seg):
    t_owner = statement["target_owner"] or statement["owner"]
    t_obj = statement["target_object"] or "UNKNOWN"
    m = UPDATE_RE.search(seg)
    fields = []
    src_tables = parse_from_tables(seg) or [f"{t_owner}.{t_obj}"]
    if m:
        set_clause = m.group(2).strip()
        for pair in split_top_level(set_clause):
            pm = SET_PAIR_RE.match(pair)
            if not pm:
                continue
            col, expr = pm.group(1).upper(), pm.group(2).strip()
            if not COL_NAME_RE.match(col):
                continue
            src_cols = extract_columns(expr)
            fields.append(
                {
                    "lineage_id": lid("fld", statement["statement_id"], col),
                    "source_owner": t_owner,
                    "source_object": t_obj,
                    "source_column": ",".join(src_cols) if src_cols else "UNKNOWN",
                    "transformation_type": classify_expression(expr),
                    "transformation_expression": expr[:400],
                    "filters": "",
                    "group_by": "",
                    "partition_by": "",
                    "target_owner": t_owner,
                    "target_object": t_obj,
                    "target_column": col,
                    "producer_owner": statement["owner"],
                    "producer_object": statement["object_name"],
                    "evidence_statement_id": statement["statement_id"],
                    "code_start_line": statement["start_line"],
                    "code_end_line": statement["end_line"],
                    "source_hash": statement.get("source_hash") or "",
                    "confidence": "CODE_CONFIRMED",
                }
            )
    return src_tables, fields


def parse_merge(statement, seg):
    t_owner = statement["target_owner"] or statement["owner"]
    t_obj = statement["target_object"] or "UNKNOWN"
    src_tables = parse_from_tables(seg)
    m = MERGE_RE.search(seg)
    if m:
        src_ref = m.group(2).strip()
        fm = FROM_ITEM_RE.search("FROM " + src_ref)
        if fm:
            src_tables = [fm.group(1).strip().strip('"').upper()]
    fields = []  # MERGE field-level kept PARTIAL via insert/update sub-clauses — v2: object level only
    return src_tables, fields


def main() -> int:
    require_focus()
    sid_snapshot = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    db = connect_db()
    ora = connect_readonly()
    cur = ora.cursor()

    db.execute("DELETE FROM object_lineage WHERE snapshot_id=?", (sid_snapshot,))
    db.execute("DELETE FROM field_lineage WHERE snapshot_id=?", (sid_snapshot,))

    object_rows, field_rows = [], []

    # ---- View lineage (EDWCRM) ----
    views = q(
        cur,
        "SELECT owner, view_name FROM all_views WHERE owner = :o",
        {"o": BUSINESS_FOCUS},
    )
    for v in views:
        text = ""
        try:
            cur.execute(
                "SELECT DBMS_METADATA.GET_DDL('VIEW', :n, :o) FROM dual",
                {"n": v["view_name"], "o": v["owner"]},
            )
            row = cur.fetchone()
            text = str(row[0]) if row and row[0] else ""
        except Exception as e:
            text = f"-- VIEW_TEXT_UNREADABLE {scrub(e)}"
        clean = strip_comments(text)
        for src in set(parse_from_tables(clean)):
            so, sn = split_owner_name(src, v["owner"])
            oid = lid("obj", so, sn, v["owner"], v["view_name"], "VIEW")
            object_rows.append(
                {
                    "lineage_id": oid,
                    "source_owner": so,
                    "source_object": sn,
                    "producer_owner": v["owner"],
                    "producer_object": v["view_name"],
                    "producer_type": "VIEW",
                    "target_owner": v["owner"],
                    "target_object": v["view_name"],
                    "evidence_statement_id": oid,
                    "confidence": "CODE_CONFIRMED"
                    if "UNREADABLE" not in text
                    else "PARTIAL",
                }
            )

    # ---- Statement-driven lineage ----
    stmts = [
        dict(
            zip(
                [
                    "statement_id", "owner", "object_name", "object_type",
                    "statement_kind", "sql_text", "target_owner", "target_object",
                    "start_line", "end_line", "dynamic_class", "source_hash",
                ],
                row,
            )
        )
        for row in db.execute(
            """SELECT s.statement_id, s.owner, s.object_name, s.object_type,
                      s.statement_kind, s.sql_text, s.target_owner, s.target_object,
                      s.start_line, s.end_line, s.dynamic_class, p.source_hash
               FROM sql_statement s
               LEFT JOIN program_unit p
                 ON p.snapshot_id=s.snapshot_id AND p.owner=s.owner
                AND p.object_name=s.object_name AND p.object_type=s.object_type
               WHERE s.snapshot_id=?""",
            (sid_snapshot,),
        )
    ]

    src_cache: dict[str, str] = {}

    def unit_text(owner, name, otype):
        key = f"{owner}.{name}.{otype}"
        if key not in src_cache:
            path = PRIVATE / f"{owner}.{name}.{otype.replace(' ', '_')}.sql"
            raw = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            src_cache[key] = strip_comments(raw)
        return src_cache[key]

    # table column dictionary for validation / positional fallback
    table_dict: dict[tuple[str, str], list[str]] = {}
    for r in db.execute(
        """SELECT owner, table_name, column_name FROM column_metadata
           WHERE snapshot_id=? ORDER BY owner, table_name, column_id""",
        (sid_snapshot,),
    ):
        table_dict.setdefault((r[0], r[1]), []).append(r[2])

    for st in stmts:
        if st["dynamic_class"] == "FULLY_DYNAMIC":
            continue
        kind = st["statement_kind"]
        if kind not in ("INSERT", "UPDATE", "MERGE", "DELETE", "CREATE"):
            continue
        if st["dynamic_class"] == "PARTIALLY_DYNAMIC":
            continue  # registered in dynamic-sql-register; no forged lineage
        full = unit_text(st["owner"], st["object_name"], st["object_type"])
        seg = (
            segment_lines(full, st["start_line"], st["end_line"])
            if full
            else (st["sql_text"] or "")
        )
        if not seg.strip():
            seg = st["sql_text"] or ""

        t_owner = st["target_owner"] or st["owner"]
        t_obj = st["target_object"] or ""
        tcols = table_dict.get((t_owner, t_obj)) if t_obj else None

        src_tables, fields = [], []
        if kind == "INSERT":
            src_tables, fields = parse_insert(st, seg, table_cols=tcols)
        elif kind == "UPDATE":
            src_tables, fields = parse_update(st, seg)
        elif kind == "MERGE":
            src_tables, fields = parse_merge(st, seg)
        elif kind in ("DELETE", "CREATE"):
            src_tables = parse_from_tables(seg)
            if kind == "CREATE":
                items, from_rest = extract_select_items(seg)
                if items:
                    fields = build_field_rows(
                        None, st, seg,
                        t_owner,
                        t_obj or "UNKNOWN",
                        [], items, parse_from_tables(from_rest),
                        table_cols=tcols,
                    )

        for src in set(src_tables) or {"UNKNOWN"}:
            so, sn = (
                split_owner_name(src, st["owner"]) if src != "UNKNOWN" else ("UNKNOWN", "UNKNOWN")
            )
            oid = lid("obj", so, sn, st["owner"], st["object_name"], st["statement_id"])
            object_rows.append(
                {
                    "lineage_id": oid,
                    "source_owner": so,
                    "source_object": sn,
                    "producer_owner": st["owner"],
                    "producer_object": st["object_name"],
                    "producer_type": st["object_type"],
                    "target_owner": st["target_owner"] or st["owner"],
                    "target_object": st["target_object"] or "UNKNOWN",
                    "evidence_statement_id": st["statement_id"],
                    "confidence": "CODE_CONFIRMED" if src != "UNKNOWN" else "PARTIAL",
                }
            )
        field_rows.extend(fields)

    # ---- persist ----
    for r in object_rows:
        db.execute(
            "INSERT OR REPLACE INTO object_lineage VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid_snapshot, r["lineage_id"], r["source_owner"], r["source_object"],
                r["producer_owner"], r["producer_object"], r["producer_type"],
                r["target_owner"], r["target_object"], r["evidence_statement_id"],
                r["confidence"],
            ),
        )
    for r in field_rows:
        db.execute(
            """INSERT OR REPLACE INTO field_lineage VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sid_snapshot, r["lineage_id"], r["source_owner"], r["source_object"],
                r["source_column"], r["transformation_type"],
                r["transformation_expression"], r["filters"], r["group_by"],
                r["partition_by"], r["target_owner"], r["target_object"],
                r["target_column"], r["producer_owner"], r["producer_object"],
                r["evidence_statement_id"], r["code_start_line"], r["code_end_line"],
                r["source_hash"], r["confidence"],
            ),
        )
    db.commit()

    # ---- exports ----
    if object_rows:
        with (OUT / "object-lineage.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(object_rows[0].keys()))
            w.writeheader()
            w.writerows(object_rows)
    if field_rows:
        with (OUT / "field-lineage.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(field_rows[0].keys()))
            w.writeheader()
            w.writerows(field_rows)

    # integrity: no dirty column names, every CODE_CONFIRMED row has evidence,
    # and target columns must exist in table dictionary when known
    dirty = [
        r for r in field_rows
        if not COL_NAME_RE.match(r["target_column"])
    ]
    no_ev = [
        r for r in field_rows
        if r["confidence"] == "CODE_CONFIRMED" and not r["evidence_statement_id"]
    ]
    dict_violations = [
        r for r in field_rows
        if (r["target_owner"], r["target_object"]) in table_dict
        and r["target_column"] not in table_dict[(r["target_owner"], r["target_object"])]
        and r["confidence"] == "CODE_CONFIRMED"
    ]
    conf_counts = {}
    for r in field_rows:
        conf_counts[r["confidence"]] = conf_counts.get(r["confidence"], 0) + 1

    (OUT / "data-flow-graph.json").write_text(
        json.dumps(
            {
                "version": "v2",
                "object_lineage_count": len(object_rows),
                "field_lineage_count": len(field_rows),
                "field_confidence": conf_counts,
            },
            ensure_ascii=False, indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    gate = "PASS" if (not dirty and not no_ev and not dict_violations and object_rows) else "FAIL"
    summary = {
        "version": "v2.2",
        "object_lineage_count": len(object_rows),
        "field_lineage_count": len(field_rows),
        "field_confidence": conf_counts,
        "dirty_target_columns": len(dirty),
        "code_confirmed_without_evidence": len(no_ev),
        "code_confirmed_target_not_in_dict": len(dict_violations),
        "gate4": gate,
    }
    (OUT / "gate4-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    cur.close()
    ora.close()
    db.close()
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        raise
