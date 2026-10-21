#!/usr/bin/env python3
"""Gate 2 — extract PL/SQL source + arguments for business-focus (+ referenced)."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

from catalog import connect_db
from conn import BUSINESS_FOCUS, REPORT_DIR, connect_readonly, q, require_focus, scrub

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
PRIVATE = ROOT / "data" / "metadata" / "source_private"

# Default: hash-only source retention (object id + sha256 + line count +
# scrubbed digest). Full PL/SQL source is stored ONLY when the operator
# explicitly opts in locally via ORACLE_METADATA_KEEP_FULL_SOURCE=1, and the
# private dir is gitignored either way. Never committed to git.
KEEP_FULL_SOURCE = os.getenv("ORACLE_METADATA_KEEP_FULL_SOURCE", "0") == "1"
PROGRAM_TYPES = (
    "PROCEDURE",
    "FUNCTION",
    "PACKAGE",
    "PACKAGE BODY",
    "TRIGGER",
    "TYPE",
    "TYPE BODY",
)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def is_wrapped(text: str) -> bool:
    t = text.lstrip().lower()
    return t.startswith("wrapped") or "\nwrapped\n" in ("\n" + t[:200])


def main() -> int:
    require_focus()
    OUT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    sid = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    db = connect_db()
    ora = connect_readonly()
    cur = ora.cursor()

    # Programs in EDWCRM + any non-system referenced by EDWCRM dependencies
    programs = q(
        cur,
        """
        SELECT owner, object_name, object_type, status,
               TO_CHAR(created,'YYYY-MM-DD HH24:MI:SS') AS created,
               TO_CHAR(last_ddl_time,'YYYY-MM-DD HH24:MI:SS') AS last_ddl_time
        FROM all_objects
        WHERE owner = :o AND object_type IN (
          'PROCEDURE','FUNCTION','PACKAGE','PACKAGE BODY','TRIGGER','TYPE','TYPE BODY'
        )
        ORDER BY object_type, object_name
        """,
        {"o": BUSINESS_FOCUS},
    )

    # Also pull referenced program units from deps (non-PUBLIC)
    ref = q(
        cur,
        """
        SELECT DISTINCT referenced_owner AS owner, referenced_name AS object_name,
               referenced_type AS object_type
        FROM all_dependencies
        WHERE owner = :o
          AND referenced_type IN (
            'PROCEDURE','FUNCTION','PACKAGE','PACKAGE BODY','TRIGGER'
          )
          AND referenced_owner NOT IN ('SYS','PUBLIC','SYSTEM')
        """,
        {"o": BUSINESS_FOCUS},
    )
    seen = {(p["owner"], p["object_name"], p["object_type"]) for p in programs}
    for r in ref:
        key = (r["owner"], r["object_name"], r["object_type"])
        if key not in seen:
            # fill status
            meta = q(
                cur,
                """
                SELECT status,
                       TO_CHAR(created,'YYYY-MM-DD HH24:MI:SS') AS created,
                       TO_CHAR(last_ddl_time,'YYYY-MM-DD HH24:MI:SS') AS last_ddl_time
                FROM all_objects
                WHERE owner=:o AND object_name=:n AND object_type=:t
                """,
                {"o": r["owner"], "n": r["object_name"], "t": r["object_type"]},
            )
            if meta:
                programs.append(
                    {
                        "owner": r["owner"],
                        "object_name": r["object_name"],
                        "object_type": r["object_type"],
                        "status": meta[0]["status"],
                        "created": meta[0]["created"],
                        "last_ddl_time": meta[0]["last_ddl_time"],
                    }
                )
                seen.add(key)

    source_index = []
    for p in programs:
        lines = q(
            cur,
            """
            SELECT line, text FROM all_source
            WHERE owner=:o AND name=:n AND type=:t
            ORDER BY line
            """,
            {"o": p["owner"], "n": p["object_name"], "t": p["object_type"]},
        )
        if not lines:
            # try DBMS_METADATA
            source_status = "NO_SOURCE_ROWS"
            full = ""
            try:
                typ_map = {
                    "PROCEDURE": "PROCEDURE",
                    "FUNCTION": "FUNCTION",
                    "PACKAGE": "PACKAGE_SPEC",
                    "PACKAGE BODY": "PACKAGE_BODY",
                    "TRIGGER": "TRIGGER",
                    "TYPE": "TYPE_SPEC",
                    "TYPE BODY": "TYPE_BODY",
                }
                ddl_type = typ_map.get(p["object_type"], p["object_type"])
                cur.execute(
                    "SELECT DBMS_METADATA.GET_DDL(:t, :n, :o) FROM dual",
                    {"t": ddl_type, "n": p["object_name"], "o": p["owner"]},
                )
                row = cur.fetchone()
                if row and row[0]:
                    full = str(row[0])
                    source_status = "DDL_ONLY"
            except Exception as e:
                source_status = "UNREADABLE"
                full = f"-- ERROR {scrub(e)}"
        else:
            full = "".join(x["text"] or "" for x in lines)
            if is_wrapped(full):
                source_status = "WRAPPED_SOURCE_UNREADABLE"
            else:
                source_status = "EXTRACTED"

        h = sha256_text(full) if full else ""
        line_count = full.count("\n") + 1 if full else 0
        # private store: hash-only by default; full source only via explicit opt-in
        safe_name = f"{p['owner']}.{p['object_name']}.{p['object_type'].replace(' ', '_')}.sql"
        priv = PRIVATE / safe_name
        if source_status in ("EXTRACTED", "DDL_ONLY"):
            if KEEP_FULL_SOURCE:
                priv.write_text(full, encoding="utf-8", errors="replace")
            else:
                priv.write_text(
                    f"-- HASH_ONLY sha256={h} lines={line_count} "
                    f"(set ORACLE_METADATA_KEEP_FULL_SOURCE=1 to retain source locally)\n",
                    encoding="utf-8",
                )
        elif source_status == "WRAPPED_SOURCE_UNREADABLE":
            priv.write_text(
                f"-- WRAPPED_SOURCE_UNREADABLE hash={h}\n", encoding="utf-8"
            )

        db.execute(
            "DELETE FROM source_code WHERE snapshot_id=? AND owner=? AND object_name=? AND object_type=?",
            (sid, p["owner"], p["object_name"], p["object_type"]),
        )
        for ln in lines:
            db.execute(
                "INSERT INTO source_code VALUES (?,?,?,?,?,?,?)",
                (
                    sid,
                    p["owner"],
                    p["object_name"],
                    p["object_type"],
                    int(ln["line"]),
                    ln["text"] if KEEP_FULL_SOURCE else f"[REDACTED sha256={h[:16]}]",
                    h,
                ),
            )
        db.execute(
            "INSERT OR REPLACE INTO program_unit VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                p["owner"],
                p["object_name"],
                p["object_type"],
                p["status"],
                h,
                len(full),
                source_status,
                p["created"],
                p["last_ddl_time"],
            ),
        )
        source_index.append(
            {
                "owner": p["owner"],
                "object_name": p["object_name"],
                "object_type": p["object_type"],
                "source_status": source_status,
                "source_hash": h,
                "source_length": len(full),
                "private_path": str(priv.relative_to(ROOT))
                if priv.exists()
                else None,
                "line_count": len(lines),
            }
        )

    # Arguments for EDWCRM programs
    args = q(
        cur,
        """
        SELECT owner, package_name, object_name, NVL(overload,0) AS overload,
               subprogram_id, NVL(argument_name,'') AS argument_name,
               position, sequence, data_level, data_type, in_out, defaulted,
               type_owner, type_name
        FROM all_arguments
        WHERE owner = :o
        """,
        {"o": BUSINESS_FOCUS},
    )
    db.execute(
        "DELETE FROM program_argument WHERE snapshot_id=? AND owner=?",
        (sid, BUSINESS_FOCUS),
    )
    for a in args:
        db.execute(
            "INSERT OR REPLACE INTO program_argument VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                a["owner"],
                a["package_name"] or "",
                a["object_name"],
                int(a["overload"] or 0),
                a["subprogram_id"],
                a["argument_name"] or "",
                a["position"],
                a["sequence"],
                a["data_level"],
                a["data_type"],
                a["in_out"],
                a["defaulted"],
                a["type_owner"],
                a["type_name"],
            ),
        )

    db.commit()

    # Exports
    (OUT / "source-index.json").write_text(
        json.dumps(
            {"snapshot_id": sid, "programs": source_index},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with (OUT / "procedure-inventory.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "owner",
                "object_name",
                "object_type",
                "status",
                "source_status",
                "source_hash",
                "source_length",
            ]
        )
        for row in db.execute(
            """SELECT owner, object_name, object_type, status, source_status,
                      source_hash, source_length
               FROM program_unit WHERE snapshot_id=? ORDER BY owner, object_type, object_name""",
            (sid,),
        ):
            w.writerow(row)

    with (OUT / "program-argument-catalog.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(
            [
                "owner",
                "package_name",
                "object_name",
                "argument_name",
                "position",
                "data_type",
                "in_out",
            ]
        )
        for row in db.execute(
            """SELECT owner, package_name, object_name, argument_name, position,
                      data_type, in_out
               FROM program_argument WHERE snapshot_id=? ORDER BY owner, object_name, position""",
            (sid,),
        ):
            w.writerow(row)

    # coverage check
    missing = [
        x
        for x in source_index
        if x["source_status"]
        not in (
            "EXTRACTED",
            "WRAPPED_SOURCE_UNREADABLE",
            "DDL_ONLY",
            "NO_SOURCE_ROWS",
            "UNREADABLE",
        )
    ]
    # every program must have hash or explicit unread status
    bad = [x for x in source_index if not x["source_hash"] and x["source_status"] not in ("NO_SOURCE_ROWS", "UNREADABLE")]
    summary = {
        "snapshot_id": sid,
        "program_count": len(source_index),
        "by_status": {},
        "argument_count": len(args),
        "source_storage": "FULL_SOURCE_OPT_IN" if KEEP_FULL_SOURCE else "HASH_ONLY_DEFAULT",
        "gate2": "PASS" if not bad else "FAIL",
    }
    for x in source_index:
        summary["by_status"][x["source_status"]] = (
            summary["by_status"].get(x["source_status"], 0) + 1
        )
    (OUT / "gate2-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    cur.close()
    ora.close()
    db.close()
    return 0 if summary["gate2"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        raise
