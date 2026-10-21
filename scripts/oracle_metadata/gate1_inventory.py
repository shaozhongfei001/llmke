#!/usr/bin/env python3
"""Gate 1 — full visible object inventory + focus-schema deep metadata."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from catalog import SQLITE_PATH, connect_db
from conn import (
    BUSINESS_FOCUS,
    REPORT_DIR,
    RUN_PREFIX,
    SYSTEM_OWNERS,
    connect_readonly,
    q,
    require_focus,
    q_batches,
    scrub,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
COLLECTOR_VERSION = f"{RUN_PREFIX}-gate1-0.1"


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "UNKNOWN"


def snapshot_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{RUN_PREFIX}-{ts}"


def analysis_depth(owner: str) -> str:
    if owner == BUSINESS_FOCUS:
        return "DEEP"
    if owner in SYSTEM_OWNERS:
        return "INVENTORY_ONLY"
    return "INVENTORY_ONLY"


def main() -> int:
    require_focus()
    OUT.mkdir(parents=True, exist_ok=True)
    sid = snapshot_id()
    started = datetime.now(timezone.utc).isoformat()
    ora = connect_readonly()
    ocur = ora.cursor()
    db = connect_db(reset=True)

    env = q(
        ocur,
        """
        SELECT SYS_CONTEXT('USERENV','DB_NAME') AS db_name,
               SYS_CONTEXT('USERENV','SERVICE_NAME') AS service_name,
               SYS_CONTEXT('USERENV','CURRENT_USER') AS current_user,
               SYS_CONTEXT('USERENV','CURRENT_SCHEMA') AS current_schema
        FROM dual
        """,
    )[0]
    try:
        ver = q(ocur, "SELECT banner FROM v$version")[0]["banner"]
    except Exception:
        ver = "INSUFFICIENT_PRIVILEGE"

    # Count for reconcile
    total_oracle = q(ocur, "SELECT COUNT(*) AS c FROM all_objects")[0]["c"]

    db.execute(
        """
        INSERT INTO db_snapshot(
          snapshot_id, scan_started_at, database_name, service_name, oracle_version,
          current_user, current_schema, collector_version, code_commit, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            sid,
            started,
            env["db_name"],
            env["service_name"],
            ver,
            env["current_user"],
            env["current_schema"],
            COLLECTOR_VERSION,
            git_head(),
            f"visible_all_objects_expected={total_oracle}; focus={BUSINESS_FOCUS}",
        ),
    )

    # Schemas
    schemas = q(
        ocur,
        "SELECT owner, COUNT(*) AS object_count FROM all_objects GROUP BY owner ORDER BY owner",
    )
    for s in schemas:
        db.execute(
            "INSERT INTO accessible_schema VALUES (?,?,?,?)",
            (sid, s["owner"], int(s["object_count"]), analysis_depth(s["owner"])),
        )
    db.commit()
    print(f"[gate1] schemas={len(schemas)} oracle_objects={total_oracle}")

    # Objects — full scan
    sql_obj = """
      SELECT owner, object_name, object_type,
             NVL(subobject_name,'') AS subobject_name,
             status,
             TO_CHAR(created,'YYYY-MM-DD HH24:MI:SS') AS created,
             TO_CHAR(last_ddl_time,'YYYY-MM-DD HH24:MI:SS') AS last_ddl_time,
             temporary, generated, secondary,
             NVL(edition_name,'') AS edition_name,
             object_id, data_object_id
      FROM all_objects
    """
    batch = []
    n = 0
    for row in q_batches(ocur, sql_obj, arraysize=2000):
        batch.append(
            (
                sid,
                env["db_name"],
                row["owner"],
                row["object_name"],
                row["object_type"],
                row["subobject_name"] or "",
                row["status"],
                row["created"],
                row["last_ddl_time"],
                row["temporary"],
                row["generated"],
                row["secondary"],
                row["edition_name"] or "",
                row["object_id"],
                row["data_object_id"],
                analysis_depth(row["owner"]),
            )
        )
        if len(batch) >= 2000:
            db.executemany(
                """INSERT OR REPLACE INTO db_object VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                batch,
            )
            n += len(batch)
            batch.clear()
            if n % 10000 == 0:
                db.commit()
                print(f"[gate1] objects inserted={n}")
    if batch:
        db.executemany(
            """INSERT OR REPLACE INTO db_object VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            batch,
        )
        n += len(batch)
    db.commit()
    print(f"[gate1] objects done={n}")

    # Deep EDWCRM tables
    tables = q(
        ocur,
        """
        SELECT t.owner, t.table_name, t.tablespace_name, t.partitioned, t.temporary,
               t.num_rows, t.blocks,
               TO_CHAR(t.last_analyzed,'YYYY-MM-DD HH24:MI:SS') AS last_analyzed,
               c.comments AS table_comment
        FROM all_tables t
        LEFT JOIN all_tab_comments c
          ON c.owner=t.owner AND c.table_name=t.table_name
        WHERE t.owner = :o
        """,
        {"o": BUSINESS_FOCUS},
    )
    for t in tables:
        db.execute(
            "INSERT OR REPLACE INTO table_metadata VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                t["owner"],
                t["table_name"],
                t["table_comment"],
                t["tablespace_name"],
                t["partitioned"],
                t["temporary"],
                t["num_rows"],
                t["blocks"],
                t["last_analyzed"],
                "statistics",
            ),
        )
    print(f"[gate1] tables EDWCRM={len(tables)}")

    cols = q(
        ocur,
        """
        SELECT tc.owner, tc.table_name, tc.column_id, tc.column_name, tc.data_type,
               tc.data_length, tc.data_precision, tc.data_scale, tc.nullable,
               tc.data_default AS default_value, tc.char_used, tc.char_length,
               cc.comments AS column_comment,
               tc.num_distinct, tc.num_nulls, tc.low_value, tc.high_value,
               TO_CHAR(tc.last_analyzed,'YYYY-MM-DD HH24:MI:SS') AS last_analyzed
        FROM all_tab_columns tc
        LEFT JOIN all_col_comments cc
          ON cc.owner=tc.owner AND cc.table_name=tc.table_name AND cc.column_name=tc.column_name
        WHERE tc.owner = :o
        """,
        {"o": BUSINESS_FOCUS},
    )
    for c in cols:
        # store low/high as hex-ish str to avoid blob issues
        low = c["low_value"]
        high = c["high_value"]
        if isinstance(low, (bytes, bytearray, memoryview)):
            low = bytes(low).hex()
        if isinstance(high, (bytes, bytearray, memoryview)):
            high = bytes(high).hex()
        db.execute(
            """INSERT OR REPLACE INTO column_metadata VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sid,
                c["owner"],
                c["table_name"],
                c["column_id"],
                c["column_name"],
                c["data_type"],
                c["data_length"],
                c["data_precision"],
                c["data_scale"],
                c["nullable"],
                str(c["default_value"]) if c["default_value"] is not None else None,
                c["char_used"],
                c["char_length"],
                c["column_comment"],
                c["num_distinct"],
                c["num_nulls"],
                low,
                high,
                c["last_analyzed"],
            ),
        )
    print(f"[gate1] columns EDWCRM={len(cols)}")

    # Constraints EDWCRM
    # SEARCH_CONDITION is LONG on 11g — avoid TO_CHAR(LONG); leave text NULL (PARTIAL).
    cons = q(
        ocur,
        """
        SELECT owner, constraint_name, constraint_type, table_name, status,
               r_owner, r_constraint_name
        FROM all_constraints WHERE owner = :o
        """,
        {"o": BUSINESS_FOCUS},
    )
    for con in cons:
        cols_c = q(
            ocur,
            """
            SELECT column_name FROM all_cons_columns
            WHERE owner=:o AND constraint_name=:c ORDER BY position
            """,
            {"o": con["owner"], "c": con["constraint_name"]},
        )
        db.execute(
            "INSERT OR REPLACE INTO constraint_metadata VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                con["owner"],
                con["constraint_name"],
                con["constraint_type"],
                con["table_name"],
                con["status"],
                None,  # search_condition LONG omitted — PARTIAL
                con["r_owner"],
                con["r_constraint_name"],
                ",".join(x["column_name"] for x in cols_c),
            ),
        )
    print(f"[gate1] constraints={len(cons)}")

    # Indexes EDWCRM
    idxs = q(
        ocur,
        """
        SELECT owner, index_name, table_name, uniqueness, status
        FROM all_indexes WHERE owner = :o
        """,
        {"o": BUSINESS_FOCUS},
    )
    for ix in idxs:
        icols = q(
            ocur,
            """
            SELECT column_name FROM all_ind_columns
            WHERE index_owner=:o AND index_name=:n ORDER BY column_position
            """,
            {"o": ix["owner"], "n": ix["index_name"]},
        )
        db.execute(
            "INSERT OR REPLACE INTO index_metadata VALUES (?,?,?,?,?,?,?)",
            (
                sid,
                ix["owner"],
                ix["index_name"],
                ix["table_name"],
                ix["uniqueness"],
                ix["status"],
                ",".join(x["column_name"] for x in icols),
            ),
        )
    print(f"[gate1] indexes={len(idxs)}")

    # Dependencies involving EDWCRM
    deps = q(
        ocur,
        """
        SELECT owner, name, type, referenced_owner, referenced_name, referenced_type,
               dependency_type
        FROM all_dependencies
        WHERE owner = :o OR referenced_owner = :o
        """,
        {"o": BUSINESS_FOCUS},
    )
    for d in deps:
        db.execute(
            "INSERT OR REPLACE INTO object_dependency VALUES (?,?,?,?,?,?,?,?)",
            (
                sid,
                d["owner"],
                d["name"],
                d["type"],
                d["referenced_owner"],
                d["referenced_name"],
                d["referenced_type"],
                d["dependency_type"],
            ),
        )
    print(f"[gate1] deps={len(deps)}")

    # Scheduler jobs (visible)
    try:
        jobs = q(
            ocur,
            """
            SELECT owner, job_name, job_type, job_action, enabled, state,
                   TO_CHAR(last_start_date,'YYYY-MM-DD HH24:MI:SS') AS last_start_date
            FROM all_scheduler_jobs
            """,
        )
    except Exception as e:
        jobs = []
        print("[gate1] scheduler fail", scrub(e))

    completed = datetime.now(timezone.utc).isoformat()
    sqlite_count = db.execute(
        "SELECT COUNT(*) AS c FROM db_object WHERE snapshot_id=?", (sid,)
    ).fetchone()[0]
    fp = hashlib.sha256(
        f"{env['db_name']}|{total_oracle}|{sid}".encode()
    ).hexdigest()[:16]
    db.execute(
        """UPDATE db_snapshot SET scan_completed_at=?, database_fingerprint=?
           WHERE snapshot_id=?""",
        (completed, fp, sid),
    )
    db.commit()

    # Export CSVs
    inv_path = OUT / "object-inventory.csv"
    with inv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "snapshot_id",
                "owner",
                "object_name",
                "object_type",
                "subobject_name",
                "status",
                "created",
                "last_ddl_time",
                "analysis_depth",
            ]
        )
        for row in db.execute(
            """SELECT snapshot_id, owner, object_name, object_type, subobject_name,
                      status, created, last_ddl_time, analysis_depth
               FROM db_object WHERE snapshot_id=? ORDER BY owner, object_type, object_name""",
            (sid,),
        ):
            w.writerow(row)

    col_path = OUT / "table-column-catalog.csv"
    with col_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "owner",
                "table_name",
                "column_id",
                "column_name",
                "data_type",
                "nullable",
                "column_comment",
                "num_distinct",
                "num_nulls",
            ]
        )
        for row in db.execute(
            """SELECT owner, table_name, column_id, column_name, data_type, nullable,
                      column_comment, num_distinct, num_nulls
               FROM column_metadata WHERE snapshot_id=? ORDER BY owner, table_name, column_id""",
            (sid,),
        ):
            w.writerow(row)

    # Schema inventory md
    by_type = list(
        db.execute(
            """SELECT object_type, COUNT(*) FROM db_object WHERE snapshot_id=?
               GROUP BY object_type ORDER BY object_type""",
            (sid,),
        )
    )
    schema_rows = list(
        db.execute(
            "SELECT owner, object_count, analysis_depth FROM accessible_schema WHERE snapshot_id=? ORDER BY owner",
            (sid,),
        )
    )
    (OUT / "schema-inventory.md").write_text(
        "# Schema Inventory (Gate 1)\n\n"
        f"- snapshot_id: `{sid}`\n"
        f"- oracle_all_objects: `{total_oracle}`\n"
        f"- sqlite_db_object: `{sqlite_count}`\n"
        f"- reconcile: `{'PASS' if int(total_oracle)==int(sqlite_count) else 'FAIL'}`\n\n"
        "## Schemas\n\n| owner | object_count | analysis_depth |\n|-------|-------------:|----------------|\n"
        + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in schema_rows)
        + "\n\n## Object types\n\n| type | count |\n|------|------:|\n"
        + "\n".join(f"| {a} | {b} |" for a, b in by_type)
        + "\n",
        encoding="utf-8",
    )

    # Scheduler export
    (OUT / "scheduler-jobs.json").write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    profile = {
        "snapshot_id": sid,
        "database_name": env["db_name"],
        "service_name": env["service_name"],
        "oracle_version": ver,
        "current_user": env["current_user"],
        "current_schema": env["current_schema"],
        "visible_object_total_oracle": int(total_oracle),
        "visible_object_total_sqlite": int(sqlite_count),
        "reconcile": "PASS" if int(total_oracle) == int(sqlite_count) else "FAIL",
        "business_focus_schema": BUSINESS_FOCUS,
        "edwcrm_tables": len(tables),
        "edwcrm_columns": len(cols),
        "edwcrm_constraints": len(cons),
        "edwcrm_indexes": len(idxs),
        "edwcrm_dependencies": len(deps),
        "scheduler_jobs": len(jobs),
        "sqlite_path": str(SQLITE_PATH.relative_to(ROOT)),
        "scan_started_at": started,
        "scan_completed_at": completed,
    }
    (OUT / "oracle-database-profile.md").write_text(
        "# Oracle Database Profile (Gate 1)\n\n```json\n"
        + json.dumps(profile, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    (OUT / "gate1-profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # latest snapshot pointer
    (OUT / "CURRENT_SNAPSHOT.txt").write_text(sid + "\n", encoding="utf-8")

    ocur.close()
    ora.close()
    db.close()

    if int(total_oracle) != int(sqlite_count):
        print(f"[gate1] RECONCILE FAIL oracle={total_oracle} sqlite={sqlite_count}")
        return 1
    print(f"[gate1] PASS snapshot={sid}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[gate1] ERROR", scrub(e), file=sys.stderr)
        raise
