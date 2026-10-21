#!/usr/bin/env python3
"""Gate 0 — Oracle read-only connection & privilege probe.

Reads credentials only from existing env / .env (ORACLE_METADATA_ENV_FILE).
Never prints passwords. Never executes DDL/DML/procedures.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import oracledb

from readonly_guard import ReadOnlyGuardError

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / os.getenv("ORACLE_METADATA_REPORT_DIR", "reports/oracle-metadata")
LOOP_DIR = ROOT / "loops" / os.getenv("ORACLE_METADATA_LOOP_DIR", "oracle-metadata-lineage")
ENV_FILE = Path(os.getenv("ORACLE_METADATA_ENV_FILE", str(ROOT / ".env")))

SENSITIVE_RE = re.compile(
    r"(PASSWORD|PWD|SECRET|TOKEN|WALLET|PASSWD)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default


def _mask_host(host: str) -> str:
    if not host:
        return ""
    if len(host) <= 3:
        return "***"
    return host[:3] + "***"


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "UNKNOWN"


def _q(cur, sql: str, binds: dict | None = None) -> list[dict[str, Any]]:
    cur.execute(sql, binds or {})
    if cur.description is None:
        return []
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _probe_view(cur, label: str, sql: str) -> dict[str, Any]:
    try:
        rows = _q(cur, sql)
        return {"access": "PASS", "sample_rows": len(rows), "error": None, "rows": rows}
    except oracledb.Error as e:
        msg = SENSITIVE_RE.sub(r"\1=***REDACTED***", str(e))
        return {"access": "FAIL", "sample_rows": 0, "error": msg, "rows": []}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOOP_DIR.mkdir(parents=True, exist_ok=True)
    (LOOP_DIR / "memory").mkdir(parents=True, exist_ok=True)
    (LOOP_DIR / "evidence" / "manifests").mkdir(parents=True, exist_ok=True)

    _load_dotenv(ENV_FILE)

    host = _env("ORACLE_HOST")
    port = int(_env("ORACLE_PORT", default="1521") or "1521")
    service = _env("ORACLE_SERVICE")
    user = _env("ORACLE_USER")
    password = _env("ORACLE_PASSWORD")
    lib_dir = os.getenv("ORACLE_CLIENT_DIR", "")

    config_sources = []
    if ENV_FILE.exists():
        config_sources.append(str(ENV_FILE.relative_to(ROOT)))
    for k in (
        "ORACLE_HOST",
        "ORACLE_CLIENT_DIR",
    ):
        if os.getenv(k):
            config_sources.append(f"env:{k}")

    report: dict[str, Any] = {
        "gate": "ORACLE-METADATA-GATE-0",
        "scan_started_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_head(),
        "oracle_connection_config_source": sorted(set(config_sources)),
        "connection_mode": "READ_ONLY",
        "host_masked": _mask_host(host),
        "port": port,
        "service_name": service,
        "connection": "FAIL",
        "read_only": "FAIL",
        "blockers": [],
    }

    if not all([host, service, user, password]):
        report["blockers"].append("MISSING_ORACLE_CREDENTIALS")
        _write(report)
        return 2

    try:
        if lib_dir:
            try:
                oracledb.init_oracle_client(lib_dir=lib_dir)
                report["client_mode"] = "thick"
            except Exception as e:
                report["client_mode"] = "thick_init_failed_fallback_thin"
                report["client_init_warning"] = SENSITIVE_RE.sub(
                    r"\1=***REDACTED***", str(e)
                )
        else:
            report["client_mode"] = "thin"

        # Fail-closed: the shared guard establishes AND verifies
        # SET TRANSACTION READ ONLY, or closes the connection and raises.
        from conn import connect_readonly

        try:
            conn = connect_readonly()
        except ReadOnlyGuardError as e:
            report["blockers"].append("READ_ONLY_NOT_ESTABLISHED")
            report["read_only"] = "FAIL"
            report["read_only_method"] = "SET TRANSACTION READ ONLY (verified)"
            report["connection_error"] = SENSITIVE_RE.sub(r"\1=***REDACTED***", str(e))
            _write(report)
            return 3
        report["connection"] = "PASS"
        report["read_only"] = "PASS"
        report["read_only_method"] = "SET TRANSACTION READ ONLY (verified)"
        report["nls_session"] = "SET"
    except Exception as e:
        report["blockers"].append("ORACLE_CONNECTION_FAILED")
        report["connection_error"] = SENSITIVE_RE.sub(r"\1=***REDACTED***", str(e))
        _write(report)
        return 3

    cur = conn.cursor()
    read_only_ok = True
    try:

        # Environment snapshot
        env_rows = _q(
            cur,
            """
            SELECT SYS_CONTEXT('USERENV','DB_NAME') AS db_name,
                   SYS_CONTEXT('USERENV','SERVICE_NAME') AS service_name,
                   SYS_CONTEXT('USERENV','CURRENT_USER') AS current_user,
                   SYS_CONTEXT('USERENV','CURRENT_SCHEMA') AS current_schema,
                   SYS_CONTEXT('USERENV','SESSION_USER') AS session_user,
                   SYS_CONTEXT('USERENV','IP_ADDRESS') AS ip_address
            FROM dual
            """,
        )
        env = env_rows[0] if env_rows else {}
        report["database_name"] = env.get("db_name")
        report["service_name_ctx"] = env.get("service_name")
        report["current_user"] = env.get("current_user")
        report["current_schema"] = env.get("current_schema")
        report["session_user"] = env.get("session_user")

        ver = _probe_view(cur, "v$version", "SELECT banner FROM v$version")
        if ver["access"] == "PASS" and ver["rows"]:
            report["oracle_version"] = ver["rows"][0].get("banner")
            report["oracle_version_status"] = "PASS"
        else:
            report["oracle_version"] = "INSUFFICIENT_PRIVILEGE"
            report["oracle_version_status"] = "INSUFFICIENT_PRIVILEGE"
            report["oracle_version_error"] = ver.get("error")

        # Privilege matrix
        privilege_matrix: dict[str, Any] = {}
        probes = {
            "ALL_OBJECTS": "SELECT COUNT(*) AS c FROM all_objects WHERE ROWNUM <= 1",
            "ALL_USERS": "SELECT COUNT(*) AS c FROM all_users WHERE ROWNUM <= 1",
            "ALL_SOURCE": "SELECT COUNT(*) AS c FROM all_source WHERE ROWNUM <= 1",
            "ALL_ARGUMENTS": "SELECT COUNT(*) AS c FROM all_arguments WHERE ROWNUM <= 1",
            "ALL_DEPENDENCIES": "SELECT COUNT(*) AS c FROM all_dependencies WHERE ROWNUM <= 1",
            "ALL_TAB_COLUMNS": "SELECT COUNT(*) AS c FROM all_tab_columns WHERE ROWNUM <= 1",
            "ALL_COL_COMMENTS": "SELECT COUNT(*) AS c FROM all_col_comments WHERE ROWNUM <= 1",
            "ALL_TAB_COMMENTS": "SELECT COUNT(*) AS c FROM all_tab_comments WHERE ROWNUM <= 1",
            "ALL_CONSTRAINTS": "SELECT COUNT(*) AS c FROM all_constraints WHERE ROWNUM <= 1",
            "ALL_INDEXES": "SELECT COUNT(*) AS c FROM all_indexes WHERE ROWNUM <= 1",
            "ALL_VIEWS": "SELECT COUNT(*) AS c FROM all_views WHERE ROWNUM <= 1",
            "ALL_MVIEWS": "SELECT COUNT(*) AS c FROM all_mviews WHERE ROWNUM <= 1",
            "ALL_SYNONYMS": "SELECT COUNT(*) AS c FROM all_synonyms WHERE ROWNUM <= 1",
            "ALL_SEQUENCES": "SELECT COUNT(*) AS c FROM all_sequences WHERE ROWNUM <= 1",
            "ALL_TRIGGERS": "SELECT COUNT(*) AS c FROM all_triggers WHERE ROWNUM <= 1",
            "ALL_PROCEDURES": "SELECT COUNT(*) AS c FROM all_procedures WHERE ROWNUM <= 1",
            "ALL_SCHEDULER_JOBS": "SELECT COUNT(*) AS c FROM all_scheduler_jobs WHERE ROWNUM <= 1",
            "ALL_SCHEDULER_PROGRAMS": "SELECT COUNT(*) AS c FROM all_scheduler_programs WHERE ROWNUM <= 1",
            "ALL_SCHEDULER_CHAINS": "SELECT COUNT(*) AS c FROM all_scheduler_chains WHERE ROWNUM <= 1",
            "ALL_DB_LINKS": "SELECT COUNT(*) AS c FROM all_db_links WHERE ROWNUM <= 1",
            "USER_ROLE_PRIVS": "SELECT granted_role FROM user_role_privs",
            "USER_SYS_PRIVS": "SELECT privilege FROM user_sys_privs",
            "SESSION_PRIVS": "SELECT privilege FROM session_privs WHERE ROWNUM <= 50",
        }
        for name, sql in probes.items():
            r = _probe_view(cur, name, sql)
            privilege_matrix[name] = {
                "access": r["access"],
                "error": r["error"],
            }
            if name in ("USER_ROLE_PRIVS", "USER_SYS_PRIVS", "SESSION_PRIVS") and r["rows"]:
                privilege_matrix[name]["values"] = [
                    list(row.values())[0] for row in r["rows"]
                ]

        # DBMS_METADATA probe (lightweight, dual only)
        try:
            cur.execute(
                "SELECT DBMS_METADATA.GET_DDL('TABLE', table_name, owner) "
                "FROM (SELECT owner, table_name FROM all_tables WHERE ROWNUM = 1)"
            )
            _ = cur.fetchone()
            privilege_matrix["DBMS_METADATA"] = {"access": "PASS", "error": None}
        except oracledb.Error as e:
            privilege_matrix["DBMS_METADATA"] = {
                "access": "FAIL",
                "error": SENSITIVE_RE.sub(r"\1=***REDACTED***", str(e)),
            }

        report["privilege_matrix"] = privilege_matrix
        report["all_source_access"] = privilege_matrix.get("ALL_SOURCE", {}).get("access")
        report["all_arguments_access"] = privilege_matrix.get("ALL_ARGUMENTS", {}).get(
            "access"
        )
        report["all_dependencies_access"] = privilege_matrix.get(
            "ALL_DEPENDENCIES", {}
        ).get("access")
        report["dbms_metadata_access"] = privilege_matrix.get("DBMS_METADATA", {}).get(
            "access"
        )
        report["scheduler_metadata_access"] = privilege_matrix.get(
            "ALL_SCHEDULER_JOBS", {}
        ).get("access")

        # Accessible schemas (object owners visible via ALL_OBJECTS)
        schemas = _probe_view(
            cur,
            "schemas",
            """
            SELECT owner, COUNT(*) AS object_count
            FROM all_objects
            GROUP BY owner
            ORDER BY owner
            """,
        )
        if schemas["access"] == "PASS":
            report["accessible_schemas"] = [
                {"owner": r["owner"], "object_count": int(r["object_count"])}
                for r in schemas["rows"]
            ]
        else:
            report["accessible_schemas"] = []
            report["blockers"].append("ALL_OBJECTS_INACCESSIBLE")

        # Object counts by type
        by_type = _probe_view(
            cur,
            "by_type",
            """
            SELECT object_type, COUNT(*) AS cnt
            FROM all_objects
            GROUP BY object_type
            ORDER BY object_type
            """,
        )
        if by_type["access"] == "PASS":
            report["visible_object_count_by_type"] = {
                r["object_type"]: int(r["cnt"]) for r in by_type["rows"]
            }
            report["visible_object_total"] = sum(
                int(r["cnt"]) for r in by_type["rows"]
            )
        else:
            report["visible_object_count_by_type"] = {}
            report["visible_object_total"] = None

        # Program counts
        prog = _probe_view(
            cur,
            "programs",
            """
            SELECT object_type, COUNT(*) AS cnt
            FROM all_objects
            WHERE object_type IN (
              'PROCEDURE','FUNCTION','PACKAGE','PACKAGE BODY','TRIGGER',
              'TYPE','TYPE BODY'
            )
            GROUP BY object_type
            ORDER BY object_type
            """,
        )
        if prog["access"] == "PASS":
            report["visible_program_count_by_type"] = {
                r["object_type"]: int(r["cnt"]) for r in prog["rows"]
            }
        else:
            report["visible_program_count_by_type"] = {}

        # ALL_USERS for inaccessible note (users without visible objects)
        users = _probe_view(
            cur,
            "all_users",
            "SELECT username FROM all_users ORDER BY username",
        )
        if users["access"] == "PASS":
            accessible_owners = {
                s["owner"] for s in report.get("accessible_schemas", [])
            }
            all_users = {r["username"] for r in users["rows"]}
            report["all_users_visible_count"] = len(all_users)
            report["inaccessible_schemas"] = sorted(all_users - accessible_owners)
            report["inaccessible_schemas_note"] = (
                "Users present in ALL_USERS with zero visible objects in ALL_OBJECTS; "
                "not necessarily privilege-denied schemas."
            )
        else:
            report["inaccessible_schemas"] = []
            report["inaccessible_schemas_note"] = "ALL_USERS inaccessible"

        report["privilege_limitations"] = []
        for k, v in privilege_matrix.items():
            if v.get("access") != "PASS":
                report["privilege_limitations"].append(
                    {"dictionary_view": k, "status": v.get("access"), "error": v.get("error")}
                )
        if report["oracle_version_status"] != "PASS":
            report["privilege_limitations"].append(
                {
                    "dictionary_view": "V$VERSION",
                    "status": "INSUFFICIENT_PRIVILEGE",
                    "error": report.get("oracle_version_error"),
                }
            )

        report["sensitive_data_controls"] = {
            "business_detail_rows": "DISABLED_BY_DEFAULT",
            "sample_rows": "EXPLICIT_OPT_IN_ONLY",
            "password_in_reports": "FORBIDDEN",
            "full_source_in_git": "FORBIDDEN_BY_DEFAULT",
            "source_code_storage_strategy": (
                "Hashes + line ranges in report dir; full source under "
                "data/metadata/source_private/ (local, gitignored) if retained"
            ),
            "local_sqlite_path": "data/metadata/oracle_metadata_catalog.sqlite",
        }
        report["source_code_storage_strategy"] = report["sensitive_data_controls"][
            "source_code_storage_strategy"
        ]
        report["local_sqlite_path"] = "data/metadata/oracle_metadata_catalog.sqlite"

        if report["connection"] != "PASS":
            report["blockers"].append("CONNECTION_FAIL")
        if not read_only_ok:
            report["blockers"].append("READ_ONLY_NOT_ESTABLISHED")
        for key in (
            "ALL_OBJECTS",
            "ALL_SOURCE",
            "ALL_ARGUMENTS",
            "ALL_DEPENDENCIES",
            "ALL_TAB_COLUMNS",
        ):
            if privilege_matrix.get(key, {}).get("access") != "PASS":
                report["blockers"].append(f"PRIVILEGE_GAP_{key}")

        report["gate0_status"] = "PASS" if not report["blockers"] else "BLOCKED"
        report["scan_completed_at"] = datetime.now(timezone.utc).isoformat()

    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            from conn import close_readonly

            close_readonly(conn)
        except Exception:
            pass

    _write(report)
    return 0 if report.get("gate0_status") == "PASS" else 1


def _write(report: dict[str, Any]) -> None:
    # scrub any accidental secrets
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    text = SENSITIVE_RE.sub(r"\1=***REDACTED***", text)
    report = json.loads(text)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "gate0-connection-report.json"
    md_path = OUT_DIR / "gate0-connection-report.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    schemas = report.get("accessible_schemas") or []
    schema_lines = "\n".join(
        f"- `{s['owner']}` — {s['object_count']} objects" for s in schemas[:80]
    )
    if len(schemas) > 80:
        schema_lines += f"\n- … +{len(schemas) - 80} more"

    obj_lines = "\n".join(
        f"| {k} | {v} |"
        for k, v in sorted((report.get("visible_object_count_by_type") or {}).items())
    )
    prog_lines = "\n".join(
        f"| {k} | {v} |"
        for k, v in sorted((report.get("visible_program_count_by_type") or {}).items())
    )
    priv_lines = "\n".join(
        f"| {k} | {v.get('access')} |"
        for k, v in sorted((report.get("privilege_matrix") or {}).items())
    )
    blockers = report.get("blockers") or []
    blocker_txt = (
        "\n".join(f"- {b}" for b in blockers) if blockers else "- (none)"
    )

    md = f"""# Gate 0 — Oracle Connection & Scope Baseline

- **gate0_status**: `{report.get('gate0_status')}`
- **connection**: `{report.get('connection')}`
- **read_only**: `{report.get('read_only')}` (`{report.get('read_only_method')}`)
- **scan_started_at**: `{report.get('scan_started_at')}`
- **scan_completed_at**: `{report.get('scan_completed_at')}`
- **code_commit**: `{report.get('code_commit')}`

## Connection (no secrets)

| Field | Value |
|------|-------|
| config_source | `{report.get('oracle_connection_config_source')}` |
| database_name | `{report.get('database_name')}` |
| service_name | `{report.get('service_name')}` / ctx `{report.get('service_name_ctx')}` |
| host_masked | `{report.get('host_masked')}` |
| port | `{report.get('port')}` |
| oracle_version | `{report.get('oracle_version')}` |
| current_user | `{report.get('current_user')}` |
| current_schema | `{report.get('current_schema')}` |
| connection_mode | `READ_ONLY` |
| client_mode | `{report.get('client_mode')}` |

## Accessible schemas (ALL_OBJECTS owners)

{schema_lines or '- (none)'}

## Visible object count by type

| object_type | count |
|-------------|------:|
{obj_lines or '| — | 0 |'}

**visible_object_total** = `{report.get('visible_object_total')}`

## Visible program count by type

| object_type | count |
|-------------|------:|
{prog_lines or '| — | 0 |'}

## Privilege matrix

| dictionary / API | access |
|------------------|--------|
{priv_lines or '| — | — |'}

- all_source_access: `{report.get('all_source_access')}`
- all_arguments_access: `{report.get('all_arguments_access')}`
- all_dependencies_access: `{report.get('all_dependencies_access')}`
- dbms_metadata_access: `{report.get('dbms_metadata_access')}`
- scheduler_metadata_access: `{report.get('scheduler_metadata_access')}`

## Privilege limitations

```json
{json.dumps(report.get('privilege_limitations') or [], ensure_ascii=False, indent=2)}
```

## Sensitive data controls

```json
{json.dumps(report.get('sensitive_data_controls') or {}, ensure_ascii=False, indent=2)}
```

## Blockers

{blocker_txt}

## Scope statement

当前报告范围仅覆盖：**当前 Oracle 连接账号可见范围内的对象与数据字典权限探测**。
未宣称全实例覆盖。未执行 DDL/DML/存储过程。未读取业务明细。
"""
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"gate0_status={report.get('gate0_status')}")


if __name__ == "__main__":
    sys.exit(main())
