"""P0-05 — Oracle read-only guard fail-closed tests (mock driver only).

Real Oracle connections are forbidden in framework tests.
"""
import json
import sys
from pathlib import Path

import pytest

FW = Path(__file__).resolve().parents[1]
OM = FW / "scripts" / "oracle_metadata"
sys.path.insert(0, str(OM))

import readonly_guard as guard  # noqa: E402


class FakeError(Exception):
    pass


class FakeCursor:
    def __init__(self, fail_on_ro=False, fail_on_probe=False):
        self.fail_on_ro = fail_on_ro
        self.fail_on_probe = fail_on_probe
        self.executed = []
        self.closed = False

    def execute(self, sql, binds=None):
        self.executed.append(sql.strip())
        if "SET TRANSACTION READ ONLY" in sql and self.fail_on_ro:
            raise FakeError("ORA-08177: cannot serialize access")
        if "ro_probe" in sql and self.fail_on_probe:
            raise FakeError("ORA-00942: table or view does not exist")

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return []

    @property
    def description(self):
        return None

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def make_driver(fail_on_ro=False, fail_on_probe=False):
    cursor = FakeCursor(fail_on_ro=fail_on_ro, fail_on_probe=fail_on_probe)
    conn = FakeConn(cursor)

    class Driver:
        Error = FakeError

        @staticmethod
        def makedsn(host, port, service_name=None):
            return f"FAKE://{host}:{port}/{service_name}"

        @staticmethod
        def connect(user=None, password=None, dsn=None):
            return conn

        @staticmethod
        def init_oracle_client(lib_dir=None):
            return None

    return Driver, conn, cursor


PARAMS = {"host": "h", "port": 1521, "service": "s", "user": "u", "password": "p"}


def test_readonly_session_established(tmp_path):
    Driver, conn, cursor = make_driver()
    with guard.readonly_session(
        driver=Driver, connect_params=PARAMS, evidence_dir=tmp_path
    ) as c:
        assert c is conn
        assert any("SET TRANSACTION READ ONLY" in s for s in cursor.executed)
        assert any("ro_probe" in s for s in cursor.executed)
    assert conn.closed  # closed at session end
    assert not (tmp_path / "readonly-guard-failures.json").exists()


def test_readonly_failure_closes_and_raises(tmp_path):
    Driver, conn, cursor = make_driver(fail_on_ro=True)
    with pytest.raises(guard.ReadOnlyGuardError):
        with guard.readonly_session(
            driver=Driver, connect_params=PARAMS, evidence_dir=tmp_path
        ):
            pass
    assert conn.closed  # connection closed on failure
    evidence = json.loads((tmp_path / "readonly-guard-failures.json").read_text())
    assert evidence["verdict"] == "FAIL"
    assert evidence["stage"] == "SET_TRANSACTION_READ_ONLY"
    assert "ORA-08177" in evidence["error"]
    # the failure vocabulary contains no soft-pass escape
    assert "PASS_SOFT" not in json.dumps(evidence)
    assert "POLICY" not in json.dumps(evidence)


def test_verify_probe_failure_raises(tmp_path):
    Driver, conn, _ = make_driver(fail_on_probe=True)
    with pytest.raises(guard.ReadOnlyGuardError):
        with guard.readonly_session(
            driver=Driver, connect_params=PARAMS, evidence_dir=tmp_path
        ):
            pass
    assert conn.closed
    evidence = json.loads((tmp_path / "readonly-guard-failures.json").read_text())
    assert evidence["stage"] == "VERIFY"


def test_missing_params_refuses(tmp_path):
    Driver, _, _ = make_driver()
    with pytest.raises(guard.ReadOnlyGuardError):
        with guard.readonly_session(
            driver=Driver, connect_params={"host": "h"}, evidence_dir=tmp_path
        ):
            pass


def test_execute_readonly_refuses_writes():
    _, _, cursor = make_driver()
    for sql in (
        "INSERT INTO t VALUES (1)",
        "update t set x=1",
        "DELETE FROM t",
        "CREATE TABLE x (i int)",
        "DROP TABLE t",
        "GRANT SELECT ON t TO u",
        "BEGIN NULL; END;",
    ):
        with pytest.raises(guard.ReadOnlyGuardError):
            guard.execute_readonly(cursor, sql)
    for sql in ("SELECT 1 FROM dual", "WITH a AS (SELECT 1 x FROM dual) SELECT * FROM a"):
        guard.execute_readonly(cursor, sql)  # must not raise


def test_conn_module_fail_closed(tmp_path, monkeypatch):
    """conn.connect_readonly must raise (not return a connection) when RO fails."""
    import conn as conn_mod

    monkeypatch.setenv("ORACLE_HOST", "h")
    monkeypatch.setenv("ORACLE_SERVICE", "s")
    monkeypatch.setenv("ORACLE_USER", "u")
    monkeypatch.setenv("ORACLE_PASSWORD", "p")
    monkeypatch.setenv("ORACLE_METADATA_ENV_FILE", str(tmp_path / "nonexistent.env"))
    monkeypatch.setenv("ORACLE_METADATA_REPORT_DIR", str(tmp_path / "reports"))

    Driver, conn_obj, _ = make_driver(fail_on_ro=True)
    with pytest.raises(guard.ReadOnlyGuardError):
        conn_mod.connect_readonly(driver=Driver)

    Driver2, conn2, cursor2 = make_driver()
    c = conn_mod.connect_readonly(driver=Driver2)
    assert c is conn2
    assert any("SET TRANSACTION READ ONLY" in s for s in cursor2.executed)
    conn_mod.close_readonly(c)
    assert conn2.closed


def test_conn_module_requires_config(monkeypatch, tmp_path):
    import conn as conn_mod

    for k in ("ORACLE_HOST", "ORACLE_SERVICE", "ORACLE_USER", "ORACLE_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ORACLE_METADATA_ENV_FILE", str(tmp_path / "none.env"))
    with pytest.raises(guard.ReadOnlyGuardError):
        conn_mod.connect_readonly()


def test_no_soft_pass_vocabulary_in_sources():
    """P0-05 regression: PASS_SOFT / POLICY_ONLY may not exist as outcomes."""
    for f in OM.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        if f.name == "readonly_guard.py":
            continue  # the guard only documents the prohibition
        assert "PASS_SOFT" not in text, f"{f.name} still contains PASS_SOFT"
        assert "POLICY_ONLY" not in text, f"{f.name} still contains POLICY_ONLY"


def test_gate7_cannot_emit_qa_signoff():
    """P1-03: gate7 is a dev self-check; no code path may set QA_GATE=PASS."""
    src = (OM / "gate7_qa.py").read_text(encoding="utf-8")
    assert "DEV_SELF_CHECK" in src
    assert "PENDING_INDEPENDENT_QA" in src
    for forbidden in ('"QA_GATE": "PASS"', "'QA_GATE': 'PASS'",
                      '"QA_GATE": "ACCEPTED"', "QA_GATE = "):
        assert forbidden not in src, f"gate7 may emit {forbidden}"
    assert 'assert report["signoff"]["QA_GATE"] == "PENDING_INDEPENDENT_QA"' in src


def test_reconcile_uses_shared_guard():
    src = (
        FW / ".cursor" / "skills" / "oracle-metadata-reconciliation"
        / "scripts" / "reconcile.py"
    ).read_text(encoding="utf-8")
    assert "_load_readonly_guard" in src
    assert "readonly_session" in src
    assert "execute_readonly" in src
    assert "PASS_SOFT" not in src
    # no direct unguarded connect remains
    assert "oracledb.connect(" not in src
