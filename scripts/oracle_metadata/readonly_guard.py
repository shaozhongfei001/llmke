#!/usr/bin/env python3
"""Shared Oracle read-only guard — the ONLY sanctioned way to open a
working unit against Oracle in this framework.

Fail-closed contract:
1. Connect (driver-injectable for tests; oracledb in production).
2. Every working unit explicitly executes SET TRANSACTION READ ONLY.
3. Establishment is verified (a probe SELECT must succeed afterwards).
4. ANY failure at any step -> close the connection, write scrubbed
   failure evidence, raise ReadOnlyGuardError (callers exit non-zero).
5. No PASS_SOFT, no policy-only fallback, no write retry, no autocommit.
6. execute_readonly() refuses anything that is not SELECT/WITH/SET/EXPLAIN.

Tests must inject a fake driver; real connections are forbidden in tests.
"""
from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SENSITIVE_RE = re.compile(
    r"(PASSWORD|PWD|SECRET|TOKEN|WALLET|PASSWD)\s*[=:]\s*\S+",
    re.IGNORECASE,
)
WRITE_RE = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER\s+(?!SESSION\b)|DROP|TRUNCATE"
    r"|GRANT|REVOKE|CALL|EXEC(?:UTE)?\s+(?!.*SELECT)|BEGIN|DECLARE)\b",
    re.IGNORECASE,
)
READ_PREFIX_RE = re.compile(r"^\s*(SELECT|WITH|SET\s+TRANSACTION|ALTER\s+SESSION|EXPLAIN)\b", re.IGNORECASE)


class ReadOnlyGuardError(RuntimeError):
    """Raised when the read-only working unit cannot be established or is violated."""


def scrub(msg: object) -> str:
    return SENSITIVE_RE.sub(r"\1=***REDACTED***", str(msg))


def execute_readonly(cur, sql: str, binds: dict | None = None):
    """Execute only verifiably read-only SQL; refuse writes by construction."""
    if WRITE_RE.search(sql) or not READ_PREFIX_RE.match(sql):
        raise ReadOnlyGuardError(f"refused non-read-only SQL: {sql[:80]!r}")
    cur.execute(sql, binds or {})


def _write_failure_evidence(evidence_dir: Path | None, stage: str, error: object) -> None:
    if evidence_dir is None:
        return
    try:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "guard": "oracle-readonly-guard",
            "verdict": "FAIL",
            "stage": stage,
            "error": scrub(error),
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        (evidence_dir / "readonly-guard-failures.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass  # never mask the original guard failure


@contextmanager
def readonly_session(
    *,
    driver: Any = None,
    connect_params: dict | None = None,
    evidence_dir: Path | None = None,
) -> Iterator[Any]:
    """Open a verified read-only Oracle session.

    driver: module-like with makedsn/connect (oracledb or a test fake).
    connect_params: {host, port, service, user, password, lib_dir?}.
    On any failure the connection is closed, evidence written, and
    ReadOnlyGuardError raised. There is no soft pass.
    """
    if driver is None:
        import oracledb as driver  # noqa: N813
    params = dict(connect_params or {})
    missing = [k for k in ("host", "service", "user", "password") if not params.get(k)]
    if missing:
        _write_failure_evidence(evidence_dir, "CONFIG", f"missing params: {missing}")
        raise ReadOnlyGuardError(f"missing connection params: {', '.join(missing)}")

    conn = None
    stage = "CONNECT"
    try:
        lib_dir = params.get("lib_dir") or os.getenv("ORACLE_CLIENT_DIR", "")
        if lib_dir and hasattr(driver, "init_oracle_client"):
            try:
                driver.init_oracle_client(lib_dir=lib_dir)
            except Exception:
                pass  # thin-mode fallback is acceptable; RO txn below is not
        dsn = driver.makedsn(params["host"], int(params.get("port", 1521)),
                             service_name=params["service"])
        conn = driver.connect(user=params["user"], password=params["password"], dsn=dsn)

        cur = conn.cursor()
        try:
            execute_readonly(cur, "ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
            execute_readonly(cur, "ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")
        except Exception as e:
            raise ReadOnlyGuardError(f"NLS session setup failed: {scrub(e)}")

        stage = "SET_TRANSACTION_READ_ONLY"
        try:
            cur.execute("SET TRANSACTION READ ONLY")
        except Exception as e:
            raise ReadOnlyGuardError(
                f"SET TRANSACTION READ ONLY failed — refusing to continue: {scrub(e)}"
            )

        stage = "VERIFY"
        try:
            cur.execute("SELECT 1 AS ro_probe FROM dual")
            row = cur.fetchone()
            if not row or int(row[0]) != 1:
                raise ReadOnlyGuardError("read-only probe returned no row")
        except ReadOnlyGuardError:
            raise
        except Exception as e:
            raise ReadOnlyGuardError(f"read-only verification probe failed: {scrub(e)}")

        yield conn

        try:
            cur.close()
        except Exception:
            pass
    except ReadOnlyGuardError as e:
        _write_failure_evidence(evidence_dir, stage, e)
        raise
    except Exception as e:
        _write_failure_evidence(evidence_dir, stage, e)
        raise ReadOnlyGuardError(f"{stage} failed: {scrub(e)}") from e
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def params_from_env(env=os.environ) -> dict:
    """Connection params come ONLY from env / local untracked config."""
    return {
        "host": env.get("ORACLE_HOST", ""),
        "port": env.get("ORACLE_PORT", "1521") or "1521",
        "service": env.get("ORACLE_SERVICE", ""),
        "user": env.get("ORACLE_USER", ""),
        "password": env.get("ORACLE_PASSWORD", ""),
        "lib_dir": env.get("ORACLE_CLIENT_DIR", ""),
    }
