#!/usr/bin/env python3
"""Verify Gate 1 artifacts and ALL_OBJECTS reconcile."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from catalog import SQLITE_PATH, connect_db
from conn import REPORT_DIR, connect_readonly, q, scrub

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR


def main() -> int:
    required = [
        OUT / "object-inventory.csv",
        OUT / "table-column-catalog.csv",
        OUT / "schema-inventory.md",
        OUT / "oracle-database-profile.md",
        OUT / "gate1-profile.json",
        SQLITE_PATH,
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("MISSING", missing)
        return 1
    profile = json.loads((OUT / "gate1-profile.json").read_text())
    if profile.get("reconcile") != "PASS":
        print("RECONCILE_FAIL", profile)
        return 2
    sid = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    db = connect_db()
    sqlite_c = db.execute(
        "SELECT COUNT(*) FROM db_object WHERE snapshot_id=?", (sid,)
    ).fetchone()[0]
    db.close()
    ora = connect_readonly()
    cur = ora.cursor()
    oracle_c = q(cur, "SELECT COUNT(*) AS c FROM all_objects")[0]["c"]
    cur.close()
    ora.close()
    if int(sqlite_c) != int(oracle_c):
        print(f"LIVE_RECONCILE_FAIL sqlite={sqlite_c} oracle={oracle_c}")
        return 3
    print(f"GATE1_VERIFY_PASS snapshot={sid} objects={sqlite_c}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        sys.exit(9)
