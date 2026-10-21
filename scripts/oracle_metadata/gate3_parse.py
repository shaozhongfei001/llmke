#!/usr/bin/env python3
"""Gate 3 (v2) — static SQL/PLSQL parse with corrected statement
segmentation and call-graph detection.

Fixes vs v1:
- Comments stripped before matching (line numbers preserved).
- Each DML statement gets exact start_line/end_line via terminating ';'.
- DML-qualified names (INSERT INTO EDWCRM.T1(...)) excluded from call graph.
- Bare direct calls (UP_F_CUST_SIGN_IFO(...)) recognized via program whitelist.
- 3-part calls (DBETL.PACK_LOG_UTL.PROC_X) keep owner.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from catalog import connect_db
from conn import REPORT_DIR, scrub
from plsql_utils import (
    find_statement_end,
    line_of,
    strip_comments,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
PRIVATE = ROOT / "data" / "metadata" / "source_private"

DML_RE = re.compile(
    r"\b(INSERT\s+INTO|MERGE\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+TABLE)\s+"
    r"([A-Za-z][A-Za-z0-9_$#]*(?:\.[A-Za-z][A-Za-z0-9_$#]*)?)",
    re.IGNORECASE,
)
EXEC_IMM_RE = re.compile(
    r"EXECUTE\s+IMMEDIATE\s+(.+?);", re.IGNORECASE | re.DOTALL
)
CALL3_RE = re.compile(
    r"\b([A-Za-z][\w$#]*)\.([A-Za-z][\w$#]*)\.([A-Za-z][\w$#]*)\s*\("
)
CALL2_RE = re.compile(r"\b([A-Za-z][\w$#]*)\.([A-Za-z][\w$#]*)\s*\(")
# Span of "INSERT INTO <qualified.table> [hint/keyword...] (" to exclude from call detection
DML_TABLE_SPAN_RE = re.compile(
    r"\b(?:INSERT\s+INTO|MERGE\s+INTO|UPDATE|DELETE\s+FROM)\s+"
    r"[A-Za-z][\w$#]*(?:\.[A-Za-z][\w$#]*)?(?:\s+[A-Za-z]+){0,3}\s*\(",
    re.IGNORECASE,
)
STRING_SPAN_RE = re.compile(r"'(?:[^']|'')*'", re.S)

SQL_FUNC_EXCLUDE = {
    "NVL", "NVL2", "COALESCE", "TO_CHAR", "TO_DATE", "TO_NUMBER", "CAST",
    "SUBSTR", "TRIM", "ROUND", "TRUNC", "SUM", "COUNT", "AVG", "MAX", "MIN",
    "DECODE", "REGEXP_REPLACE", "REGEXP_SUBSTR", "ADD_MONTHS", "LAST_DAY",
    "MONTHS_BETWEEN", "GREATEST", "LEAST", "NULLIF",
}
DECL_PREFIX_RE = re.compile(r"\b(PROCEDURE|FUNCTION|END|CREATE|BODY)\s+$", re.I)


def classify_dynamic(frag: str) -> str:
    if not frag:
        return "FULLY_DYNAMIC"
    if frag.strip().startswith("'"):
        if "||" in frag:
            return "PARTIALLY_DYNAMIC"
        return "STATIC_LITERAL"
    return "FULLY_DYNAMIC"


def sid(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def parse_unit(owner, name, otype, raw_text, source_hash, program_names):
    """Return (statements, parse_status, dynamic_rows, call_edges)."""
    statements, dynamic, calls = [], [], []
    if not raw_text:
        return statements, "UNPARSED", dynamic, calls
    if raw_text.startswith("-- WRAPPED"):
        return statements, "WRAPPED", dynamic, calls

    text = strip_comments(raw_text)

    # exclusion spans for DML table references + string literals (for call detection)
    excl_spans = [(m.start(), m.end()) for m in DML_TABLE_SPAN_RE.finditer(text)]
    string_spans = [(m.start(), m.end()) for m in STRING_SPAN_RE.finditer(text)]

    def in_excl(pos):
        return any(a <= pos < b for a, b in excl_spans)

    def in_string(pos):
        return any(a <= pos < b for a, b in string_spans)

    # --- DML statements with true line ranges ---
    for m in DML_RE.finditer(text):
        kind_raw = re.sub(r"\s+", " ", m.group(1)).upper()
        kind = kind_raw.split()[0]
        in_str = in_string(m.start())
        after = text[m.end() : m.end() + 30]
        concatenated = in_str and ("||" in after.split("\n", 1)[0] or after.lstrip().startswith("'"))
        target_ref = m.group(2).strip('"')
        t_owner, t_obj = (
            target_ref.split(".", 1)
            if "." in target_ref
            else (owner, target_ref)
        )
        start_pos = m.start()
        end_pos = find_statement_end(text, start_pos)
        seg = text[start_pos:end_pos]
        start_line = line_of(text, start_pos)
        end_line = line_of(text, end_pos)
        if in_str:
            # DML inside string literal → part of dynamic SQL; not a static target
            dynamic_class = "PARTIALLY_DYNAMIC"
            if concatenated:
                t_owner, t_obj = "", ""
        else:
            dynamic_class = "STATIC_LITERAL"
        statements.append(
            {
                "statement_id": sid(owner, name, otype, kind_raw, t_obj or start_line, start_line),
                "owner": owner,
                "object_name": name,
                "object_type": otype,
                "subprogram": "",
                "statement_kind": kind,
                "dynamic_class": dynamic_class,
                "start_line": start_line,
                "end_line": end_line,
                "sql_text": seg[:8000],
                "parse_status": "PARTIALLY_PARSED",
                "target_owner": t_owner.upper(),
                "target_object": t_obj.upper().strip('"'),
                "source_hash": source_hash,
            }
        )

    # --- dynamic SQL ---
    for m in EXEC_IMM_RE.finditer(text):
        frag = m.group(1).strip()
        klass = classify_dynamic(frag)
        start_line = line_of(text, m.start())
        stmt_id = sid(owner, name, "EXEC_IMM", start_line)
        dynamic.append(
            {
                "owner": owner,
                "object_name": name,
                "object_type": otype,
                "start_line": start_line,
                "dynamic_class": klass,
                "fragment": frag[:500],
                "statement_id": stmt_id,
            }
        )
        statements.append(
            {
                "statement_id": stmt_id,
                "owner": owner,
                "object_name": name,
                "object_type": otype,
                "subprogram": "",
                "statement_kind": "EXECUTE_IMMEDIATE",
                "dynamic_class": klass,
                "start_line": start_line,
                "end_line": start_line,
                "sql_text": frag[:4000],
                "parse_status": "PARTIALLY_PARSED"
                if klass != "FULLY_DYNAMIC"
                else "UNPARSED",
                "target_owner": "",
                "target_object": "",
                "source_hash": source_hash,
            }
        )

    # --- calls: 3-part first, then 2-part, then bare ---
    seen_call_positions = set()
    for m in CALL3_RE.finditer(text):
        o_, p_, s_ = (m.group(1).upper(), m.group(2).upper(), m.group(3).upper())
        if p_ in SQL_FUNC_EXCLUDE or in_excl(m.start()) or in_string(m.start()):
            continue
        seen_call_positions.add(m.start())
        calls.append(
            {
                "caller_owner": owner,
                "caller_name": name,
                "callee_owner": o_,
                "callee_package": p_,
                "callee_subprogram": s_,
                "line": line_of(text, m.start()),
                "call_form": "QUALIFIED_3PART",
            }
        )
    for m in CALL2_RE.finditer(text):
        if m.start() in seen_call_positions or in_excl(m.start()) or in_string(m.start()):
            continue
        p_, s_ = m.group(1).upper(), m.group(2).upper()
        if p_ in SQL_FUNC_EXCLUDE:
            continue
        # skip if preceded by another qualifier (already handled by 3-part at same start-1 offset)
        prev = text[max(0, m.start() - 1) : m.start()]
        if prev == ".":
            continue
        # skip declaration contexts like "PROCEDURE PKG.SUB(" (rare) — keep simple
        calls.append(
            {
                "caller_owner": owner,
                "caller_name": name,
                "callee_owner": "",
                "callee_package": p_,
                "callee_subprogram": s_,
                "line": line_of(text, m.start()),
                "call_form": "QUALIFIED_2PART",
            }
        )
    # bare direct calls against known program names
    for pname in program_names:
        if pname == name:
            continue
        for m in re.finditer(rf"\b{re.escape(pname)}\s*\(", text):
            if in_excl(m.start()) or in_string(m.start()):
                continue
            prev_char = text[max(0, m.start() - 1) : m.start()]
            if prev_char == ".":
                continue
            lookback = text[max(0, m.start() - 40) : m.start()]
            if DECL_PREFIX_RE.search(lookback):
                continue
            calls.append(
                {
                    "caller_owner": owner,
                    "caller_name": name,
                    "callee_owner": owner,
                    "callee_package": "",
                    "callee_subprogram": pname,
                    "line": line_of(text, m.start()),
                    "call_form": "BARE_DIRECT",
                }
            )

    parse_status = "PARTIALLY_PARSED" if text.strip() else "UNPARSED"
    if not statements and not calls:
        parse_status = "PARTIALLY_PARSED" if text.strip() else "UNPARSED"
    return statements, parse_status, dynamic, calls


def main() -> int:
    sid_snapshot = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    db = connect_db()
    programs = list(
        db.execute(
            "SELECT owner, object_name, object_type, source_hash, source_status FROM program_unit WHERE snapshot_id=?",
            (sid_snapshot,),
        )
    )
    program_names = {r[1] for r in programs}

    # clear v1 statement data for this snapshot
    db.execute("DELETE FROM sql_statement WHERE snapshot_id=?", (sid_snapshot,))

    parse_rows, dyn_rows = [], []
    call_graph = {"nodes": [], "edges": []}
    node_set = set()
    stmt_count = 0

    for owner, name, otype, shash, sstatus in programs:
        node_set.add(f"{owner}.{name}")
        if sstatus == "WRAPPED_SOURCE_UNREADABLE":
            parse_rows.append(
                {
                    "owner": owner,
                    "object_name": name,
                    "object_type": otype,
                    "parse_status": "WRAPPED",
                    "source_hash": shash,
                }
            )
            continue
        path = PRIVATE / f"{owner}.{name}.{otype.replace(' ', '_')}.sql"
        raw = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        stmts, pstatus, dyn, calls = parse_unit(
            owner, name, otype, raw, shash or "", program_names
        )
        parse_rows.append(
            {
                "owner": owner,
                "object_name": name,
                "object_type": otype,
                "parse_status": pstatus,
                "source_hash": shash,
            }
        )
        for s in stmts:
            stmt_count += 1
            db.execute(
                """INSERT OR REPLACE INTO sql_statement
                   (snapshot_id, statement_id, owner, object_name, object_type, subprogram,
                    statement_kind, dynamic_class, start_line, end_line, sql_text,
                    parse_status, target_owner, target_object)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sid_snapshot,
                    s["statement_id"],
                    s["owner"],
                    s["object_name"],
                    s["object_type"],
                    s["subprogram"],
                    s["statement_kind"],
                    s["dynamic_class"],
                    s["start_line"],
                    s["end_line"],
                    s["sql_text"],
                    s["parse_status"],
                    s["target_owner"],
                    s["target_object"],
                ),
            )
        dyn_rows.extend(dyn)
        for c in calls:
            call_graph["edges"].append(c)
            node = (
                f"{c['callee_owner'] + '.' if c['callee_owner'] else ''}"
                f"{c['callee_package'] + '.' if c['callee_package'] else ''}"
                f"{c['callee_subprogram']}"
            )
            node_set.add(node)

    call_graph["nodes"] = sorted(node_set)
    db.commit()

    with (OUT / "plsql-parse-status.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["owner", "object_name", "object_type", "parse_status", "source_hash"],
        )
        w.writeheader()
        w.writerows(parse_rows)
    with (OUT / "dynamic-sql-register.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "owner", "object_name", "object_type", "start_line",
                "dynamic_class", "fragment", "statement_id",
            ],
        )
        w.writeheader()
        w.writerows(dyn_rows)
    unparsed = [r for r in parse_rows if r["parse_status"] == "UNPARSED"]
    with (OUT / "unparsed-object-register.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["owner", "object_name", "object_type", "parse_status", "source_hash"],
        )
        w.writeheader()
        w.writerows(unparsed)
    (OUT / "program-call-graph.json").write_text(
        json.dumps(call_graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    missing = [r for r in parse_rows if not r.get("parse_status")]
    summary = {
        "version": "v2",
        "program_count": len(parse_rows),
        "with_parse_status": len(parse_rows) - len(missing),
        "by_status": {},
        "statement_count": stmt_count,
        "dynamic_sql_count": len(dyn_rows),
        "call_edges": len(call_graph["edges"]),
        "bare_direct_edges": sum(
            1 for e in call_graph["edges"] if e["call_form"] == "BARE_DIRECT"
        ),
        "qualified3_edges": sum(
            1 for e in call_graph["edges"] if e["call_form"] == "QUALIFIED_3PART"
        ),
        "gate3": "PASS" if not missing and len(parse_rows) == len(programs) else "FAIL",
    }
    for r in parse_rows:
        summary["by_status"][r["parse_status"]] = (
            summary["by_status"].get(r["parse_status"], 0) + 1
        )
    (OUT / "gate3-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    db.close()
    return 0 if summary["gate3"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        raise
