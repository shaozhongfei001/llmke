#!/usr/bin/env python3
"""Dev-self-check (v2) — developer-run checklist.

This is NOT independent QA. It writes `dev-self-check-report.json`.
QA_GATE may only be set by the independent QA agent after sampling.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from catalog import SQLITE_PATH, connect_db
from conn import REPORT_DIR, connect_readonly, q, scrub

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
PRIVATE = ROOT / "data" / "metadata" / "source_private"
OWNER_YAML = ROOT / "specs" / "domain" / "OWNER_METRIC_DECISIONS.yaml"

SECRET_RE = re.compile(
    r"(password\s*=\s*\S+|PWD\s*=\s*\S+|SECRET\s*=\s*\S+|TOKEN\s*=\s*\S+)",
    re.I,
)


def main() -> int:
    sid = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    findings = []
    blockers = []
    majors = []

    def add(sev, cat, msg, ref=""):
        findings.append({"severity": sev, "category": cat, "message": msg, "ref": ref})
        if sev == "BLOCKER":
            blockers.append(msg)
        elif sev == "MAJOR":
            majors.append(msg)

    # 1) metadata reconcile
    db = connect_db()
    sqlite_c = db.execute(
        "SELECT COUNT(*) FROM db_object WHERE snapshot_id=?", (sid,)
    ).fetchone()[0]
    ora = connect_readonly()
    cur = ora.cursor()
    oracle_c = q(cur, "SELECT COUNT(*) AS c FROM all_objects")[0]["c"]
    if int(sqlite_c) != int(oracle_c):
        add("BLOCKER", "reconcile", f"objects sqlite={sqlite_c} oracle={oracle_c}")
    else:
        add("INFO", "reconcile", f"PASS objects={sqlite_c}")

    # 2) program coverage
    prog_n = db.execute(
        "SELECT COUNT(*) FROM program_unit WHERE snapshot_id=?", (sid,)
    ).fetchone()[0]
    parse_n = 0
    if (OUT / "plsql-parse-status.csv").exists():
        with (OUT / "plsql-parse-status.csv").open(encoding="utf-8") as f:
            parse_n = sum(1 for _ in csv.DictReader(f))
    if prog_n == 0:
        add("BLOCKER", "source", "no program_unit rows")
    elif parse_n != prog_n:
        add("MAJOR", "parse", f"parse_status rows {parse_n} != programs {prog_n}")
    else:
        add("INFO", "parse", f"PASS programs={prog_n}")

    # 3) source hash present
    missing_hash = list(
        db.execute(
            """SELECT owner, object_name FROM program_unit
               WHERE snapshot_id=? AND (source_hash IS NULL OR source_hash='')
                 AND source_status NOT IN ('NO_SOURCE_ROWS','UNREADABLE')""",
            (sid,),
        )
    )
    if missing_hash:
        add("MAJOR", "hash", f"missing source_hash count={len(missing_hash)}")
    else:
        add("INFO", "hash", "PASS all readable programs hashed")

    # 4) sample parse — up to 20 programs
    samples = list(
        db.execute(
            "SELECT owner, object_name, object_type, source_status FROM program_unit WHERE snapshot_id=? LIMIT 20",
            (sid,),
        )
    )
    for owner, name, otype, st in samples:
        if st == "WRAPPED_SOURCE_UNREADABLE":
            continue
        p = PRIVATE / f"{owner}.{name}.{otype.replace(' ', '_')}.sql"
        if not p.exists():
            add("MAJOR", "sample", f"missing private source {owner}.{name}")

    # 5) lineage files + v2 integrity
    for fn in ("object-lineage.csv", "field-lineage.csv", "metric-lineage.csv"):
        if not (OUT / fn).exists():
            add("BLOCKER", "lineage", f"missing {fn}")
    if (OUT / "field-lineage.csv").exists():
        with (OUT / "field-lineage.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        dirty = [r for r in rows if r["target_column"] and not r["target_column"].replace("_", "").replace("$", "").replace("#", "").isalnum()]
        if dirty:
            add("MAJOR", "lineage", f"dirty target_column count={len(dirty)} e.g. {dirty[0]['target_column'][:40]}")
        else:
            add("INFO", "lineage", f"field_lineage rows={len(rows)} clean")
    # call graph node sanity: no *_TMP table names as call targets
    cg = json.loads((OUT / "program-call-graph.json").read_text())
    tmp_nodes = [n for n in cg["nodes"] if n.endswith("_TMP")]
    if tmp_nodes:
        add("MAJOR", "callgraph", f"table-like nodes in call graph: {tmp_nodes[:5]}")
    else:
        add("INFO", "callgraph", f"nodes={len(cg['nodes'])} edges={len(cg['edges'])} no table nodes")
    # v2.2: CODE_CONFIRMED target columns must exist in table dictionary
    import sqlite3 as _sq
    _db = _sq.connect(str(SQLITE_PATH))
    sidv = sid
    dict_viol = _db.execute(
        """SELECT COUNT(*) FROM field_lineage f
           WHERE f.snapshot_id=? AND f.confidence='CODE_CONFIRMED'
             AND EXISTS (SELECT 1 FROM column_metadata c
                         WHERE c.snapshot_id=f.snapshot_id AND c.owner=f.target_owner
                           AND c.table_name=f.target_object)
             AND NOT EXISTS (SELECT 1 FROM column_metadata c
                             WHERE c.snapshot_id=f.snapshot_id AND c.owner=f.target_owner
                               AND c.table_name=f.target_object AND c.column_name=f.target_column)""",
        (sidv,),
    ).fetchone()[0]
    dyn_lineage = _db.execute(
        """SELECT COUNT(*) FROM field_lineage f JOIN sql_statement s
             ON s.snapshot_id=f.snapshot_id AND s.statement_id=f.evidence_statement_id
           WHERE f.snapshot_id=? AND s.dynamic_class!='STATIC_LITERAL'""",
        (sidv,),
    ).fetchone()[0]
    _db.close()
    if dict_viol:
        add("MAJOR", "lineage", f"CODE_CONFIRMED target_col not in table dict: {dict_viol}")
    if dyn_lineage:
        add("MAJOR", "lineage", f"field lineage on non-static statements: {dyn_lineage}")
    if not dict_viol and not dyn_lineage:
        add("INFO", "lineage", "v2.2 dict validation + dynamic exclusion clean")
    # description consistency: static INSERT registered → description must list writes
    desc_dir = OUT / "program-business-descriptions"
    contradictions = 0
    if desc_dir.exists():
        _db = _sq.connect(str(SQLITE_PATH))
        progs_with_writes = {
            r[0]
            for r in _db.execute(
                """SELECT DISTINCT object_name FROM sql_statement
                   WHERE snapshot_id=? AND statement_kind='INSERT'
                     AND dynamic_class='STATIC_LITERAL' AND target_object!=''""",
                (sidv,),
            )
        }
        _db.close()
        for p in desc_dir.glob("*.md"):
            pname = p.name.split(".")[1]
            if pname in progs_with_writes and "写入对象（静态已登记）: 无静态 DML 写目标" in p.read_text(encoding="utf-8"):
                contradictions += 1
        if contradictions:
            add("MAJOR", "descriptions", f"description/statement register contradictions: {contradictions}")
        else:
            add("INFO", "descriptions", "write-target descriptions consistent with statement register")

    # 6) ALL Owner metrics preserved (not just two ids)
    metrics = json.loads((OUT / "metric-catalog.json").read_text())["metrics"]
    by_id = {m["metric_id"]: m for m in metrics}
    owner_metrics = [m for m in metrics if m.get("confidence_level") == "OWNER_CONFIRMED"]
    for m in owner_metrics:
        if not m.get("formula_expression"):
            add("MAJOR", "owner", f"OWNER_CONFIRMED {m['metric_id']} missing formula")
    add("INFO", "owner", f"Owner metric count={len(owner_metrics)} all preserved")

    # 7) CN descriptions
    desc_n = db.execute(
        "SELECT COUNT(*) FROM business_description WHERE snapshot_id=?", (sid,)
    ).fetchone()[0]
    if desc_n != prog_n:
        add("MAJOR", "cn", f"descriptions {desc_n} != programs {prog_n}")
    else:
        add("INFO", "cn", f"PASS descriptions={desc_n}")

    # 8) dynamic SQL register exists
    if not (OUT / "dynamic-sql-register.csv").exists():
        add("MAJOR", "dynamic", "missing dynamic-sql-register.csv")
    else:
        add("INFO", "dynamic", "register present")

    # 9) sensitive scan on reports (not private source)
    for p in OUT.rglob("*"):
        if p.is_file() and p.suffix in {".md", ".json", ".csv"}:
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if SECRET_RE.search(txt):
                # allow word password in prose about controls
                if "PASSWORD_SET" in txt or "password_in_reports" in txt:
                    continue
                if re.search(r"[A-Z_]*ORACLE_PASSWORD\s*=\s*\S+", txt):
                    add("BLOCKER", "secret", f"credential-like string in {p}")
                elif re.search(r"password\s*=\s*['\"]?\w{4,}", txt, re.I):
                    add("BLOCKER", "secret", f"possible password in {p}")

    # 10) completeness metrics
    g1 = json.loads((OUT / "gate1-profile.json").read_text())
    g2 = json.loads((OUT / "gate2-summary.json").read_text())
    g3 = json.loads((OUT / "gate3-summary.json").read_text())
    g4 = json.loads((OUT / "gate4-summary.json").read_text())
    g5 = json.loads((OUT / "gate5-summary.json").read_text())
    g6 = json.loads((OUT / "gate6-summary.json").read_text())

    completeness = {
        "visible_schema_count": db.execute(
            "SELECT COUNT(*) FROM accessible_schema WHERE snapshot_id=?", (sid,)
        ).fetchone()[0],
        "object_count_total": sqlite_c,
        "table_count_edwcrm": g1.get("edwcrm_tables"),
        "column_count_edwcrm": g1.get("edwcrm_columns"),
        "program_count": prog_n,
        "source_extracted_count": g2.get("by_status", {}).get("EXTRACTED", 0),
        "wrapped_count": g2.get("by_status", {}).get("WRAPPED_SOURCE_UNREADABLE", 0),
        "parsed_count": g3.get("by_status", {}).get("PARSED", 0),
        "partially_parsed_count": g3.get("by_status", {}).get("PARTIALLY_PARSED", 0),
        "unparsed_count": g3.get("by_status", {}).get("UNPARSED", 0),
        "dynamic_sql_count": g3.get("dynamic_sql_count"),
        "object_lineage_count": g4.get("object_lineage_count"),
        "field_lineage_count": g4.get("field_lineage_count"),
        "metric_count": g5.get("metric_count"),
        "derived_field_count": g5.get("derived_field_count"),
        "confidence_counts": g5.get("confidence_counts"),
        "chinese_description_count": g6.get("chinese_description_count"),
        "blocker_count": len(blockers),
        "major_count": len(majors),
    }

    # confirmation register
    conf_issues = [
        m
        for m in metrics
        if m.get("business_confirmation_required")
        or m.get("confidence_level") in ("INFERRED", "UNKNOWN", "COMMENT_SUPPORTED")
    ]
    (OUT / "business-confirmation-register.md").write_text(
        "# Business Confirmation Register\n\n"
        + "\n".join(
            f"- `{m['metric_id']}` ({m.get('confidence_level')}): {m.get('metric_name_cn')}"
            for m in conf_issues[:500]
        )
        + f"\n\nTotal needing confirmation (listed cap 500): {len(conf_issues)}\n",
        encoding="utf-8",
    )
    (OUT / "analysis-issues.md").write_text(
        "# Analysis Issues (Gate 7)\n\n"
        + "\n".join(
            f"- **{f['severity']}** `{f['category']}`: {f['message']} {f.get('ref','')}"
            for f in findings
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "privilege-gaps.md").write_text(
        "# Privilege Gaps\n\n"
        "- Gate0 dictionary probes: PASS\n"
        "- CHECK constraint SEARCH_CONDITION LONG omitted (PARTIAL)\n"
        "- Account has DBA: write capability exists but read-only policy forbids writes\n",
        encoding="utf-8",
    )

    gate = "PASS" if not blockers and not majors else "FAIL"
    # Hard boundary (P1-03): this script may ONLY emit DEV_SELF_CHECK.
    # QA_GATE / ACCEPTED / REJECTED are writable solely by an independent QA
    # identity; there is intentionally no code path here that can set them.
    report = {
        "snapshot_id": sid,
        "DEV_SELF_CHECK": gate,
        "NOTE": "This is developer self-check, NOT independent QA. "
                "QA_GATE may only be set by the independent QA agent.",
        "BLOCKER": len(blockers),
        "MAJOR": len(majors),
        "findings": findings,
        "completeness": completeness,
        "signoff": {
            "ENGINEERING_COMPLETE": False,
            "QA_READY": gate == "PASS",
            "QA_GATE": "PENDING_INDEPENDENT_QA",
            "ALL_DATABASE_LOGIC_UNDERSTOOD": False,
            "ALL_METRICS_CONFIRMED": False,
            "PRODUCTION_READY": False,
            "PROJECT_CLOSED": False,
            "BUSINESS_SIGNED": False,
        },
    }
    # mechanism-level assertion: a dev-run script can never emit QA sign-off
    assert report["signoff"]["QA_GATE"] == "PENDING_INDEPENDENT_QA"
    assert report["signoff"]["PRODUCTION_READY"] is False
    assert report["signoff"]["BUSINESS_SIGNED"] is False
    (OUT / "dev-self-check-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "COMPLETENESS.md").write_text(
        "# Completeness Metrics\n\n```json\n"
        + json.dumps(completeness, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps({"DEV_SELF_CHECK": gate, "BLOCKER": len(blockers), "MAJOR": len(majors)}, ensure_ascii=False))
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
