#!/usr/bin/env python3
"""Shared read-only Oracle connection (no secrets in logs).

Fail-closed: delegates to readonly_guard. If SET TRANSACTION READ ONLY
cannot be established, ReadOnlyGuardError is raised and the connection is
closed — there is no soft pass. Connection params come ONLY from env or a
local untracked .env file. Framework tests must use mocks/stubs.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from readonly_guard import (
    ReadOnlyGuardError,
    execute_readonly,
    params_from_env,
    readonly_session,
    scrub,
)

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = Path(os.getenv("ORACLE_METADATA_ENV_FILE", str(ROOT / ".env")))
REPORT_DIR = ROOT / os.getenv("ORACLE_METADATA_REPORT_DIR", "reports/oracle-metadata")
RUN_PREFIX = os.getenv("ORACLE_METADATA_RUN_PREFIX", "run")


def load_dotenv() -> None:
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default


def connect_readonly(driver: Any = None):
    """Open a verified read-only connection. Raises ReadOnlyGuardError on failure."""
    load_dotenv()
    params = params_from_env()
    missing = [k for k in ("host", "service", "user", "password") if not params.get(k)]
    if missing:
        raise ReadOnlyGuardError(
            "missing Oracle env config: "
            + ", ".join(f"ORACLE_{k.upper()}" for k in missing)
            + " (set them in env or local .env — never commit real values)"
        )
    evidence_dir = REPORT_DIR
    ctx = readonly_session(driver=driver, connect_params=params, evidence_dir=evidence_dir)
    conn = ctx.__enter__()
    conn._readonly_guard_ctx = ctx  # keep context alive for cleanup on close
    return conn


def close_readonly(conn) -> None:
    ctx = getattr(conn, "_readonly_guard_ctx", None)
    if ctx is not None:
        ctx.__exit__(None, None, None)
    else:
        try:
            conn.close()
        except Exception:
            pass


def q(cur, sql: str, binds: dict | None = None) -> list[dict[str, Any]]:
    cur.execute(sql, binds or {})
    if cur.description is None:
        return []
    cols = [d[0].lower() for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def q_batches(cur, sql: str, binds: dict | None = None, arraysize: int = 5000):
    cur.arraysize = arraysize
    cur.execute(sql, binds or {})
    cols = [d[0].lower() for d in cur.description]
    while True:
        rows = cur.fetchmany(arraysize)
        if not rows:
            break
        for row in rows:
            yield dict(zip(cols, row))


SYSTEM_OWNERS = {
    "SYS",
    "SYSTEM",
    "PUBLIC",
    "XDB",
    "WMSYS",
    "CTXSYS",
    "MDSYS",
    "ORDSYS",
    "ORDDATA",
    "ORDPLUGINS",
    "OLAPSYS",
    "EXFSYS",
    "DBSNMP",
    "SYSMAN",
    "APEX_030200",
    "FLOWS_FILES",
    "OUTLN",
    "APPQOSSYS",
    "ORACLE_OCM",
    "OWBSYS",
    "OWBSYS_AUDIT",
    "SI_INFORMTN_SCHEMA",
    "ANONYMOUS",
    "XS$NULL",
}

# No default schema: projects must set ORACLE_METADATA_FOCUS_SCHEMA explicitly.
BUSINESS_FOCUS = os.getenv("ORACLE_METADATA_FOCUS_SCHEMA", "")


def require_focus() -> str:
    """Gates that filter by a focus schema must refuse to run unconfigured."""
    if not BUSINESS_FOCUS:
        raise SystemExit(
            "ERROR: ORACLE_METADATA_FOCUS_SCHEMA is not set. "
            "No default schema exists in the framework — set it explicitly "
            "(env or local .env) to your project's schema before running gates."
        )
    return BUSINESS_FOCUS
