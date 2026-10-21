"""P0-04 — secret scanner fail-closed tests."""
import subprocess
import sys
from pathlib import Path

import pytest

FW = Path(__file__).resolve().parents[1]
SCAN = FW / "scripts" / "security_scan.py"


def run_scan(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCAN), "--root", str(root), *args],
        capture_output=True, text=True, cwd=str(root),
    )


@pytest.fixture
def sandbox(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "ok.txt").write_text("nothing sensitive here\n")
    return root


def test_real_credential_fails(sandbox):
    (sandbox / "leak.py").write_text('DB_PASSWORD = "Sup3rSecretRealPwd!"\n')
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "REAL_CREDENTIAL" in r.stdout


def test_real_connection_string_fails(sandbox):
    (sandbox / "cfg.txt").write_text(
        "dsn=oracle://scott:tiger99@dbprod.internal:1521/PROD\n"
    )
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "REAL_CONNECTION_STRING" in r.stdout
    assert "tiger99" not in r.stdout


def test_jdbc_connection_string_fails(sandbox):
    (sandbox / "cfg.txt").write_text(
        "url=jdbc:oracle:thin:@//10.20.30.40:1521/PROD\n"
    )
    r = run_scan(sandbox)
    assert r.returncode != 0


def test_private_key_fails(sandbox):
    (sandbox / "k.pem").write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n")
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "PRIVATE_KEY" in r.stdout


def test_personal_absolute_path_fails(sandbox):
    (sandbox / "run.sh").write_text("cd /home/jdoe/proj && make\n")
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "PERSONAL_ABSOLUTE_PATH" in r.stdout


def test_prod_host_ip_fails(sandbox):
    (sandbox / "notes.md").write_text("prod db at 10.64.12.19 port 1521\n")
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "SUSPECTED_PROD_HOST" in r.stdout


def test_env_placeholder_passes(sandbox):
    (sandbox / ".env.example").write_text(
        "ORACLE_PASSWORD=${ORACLE_PASSWORD}\n"
        "ORACLE_HOST=<db-host>\n"
        "TOKEN=<your-token>\n"
        "SDD_IDENTITY=<your-agent-name>\n"
    )
    r = run_scan(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr


def test_sensitive_runtime_artifact_tracked_fails(sandbox):
    subprocess.run(["git", "-C", str(sandbox), "init", "-q"], check=True)
    (sandbox / ".env").write_text("ORACLE_PASSWORD=x\n")
    (sandbox / "data.sqlite").write_text("fake-db")
    subprocess.run(
        ["git", "-C", str(sandbox), "add", "ok.txt", ".env", "data.sqlite"],
        check=True,
    )
    r = run_scan(sandbox, "--tracked-sensitive")
    assert r.returncode != 0
    assert "SENSITIVE_RUNTIME_ARTIFACT_TRACKED" in r.stdout


def test_framework_repo_itself_is_clean():
    """The framework repository must pass its own scanner."""
    r = run_scan(FW, "--tracked-sensitive")
    assert r.returncode == 0, r.stdout + r.stderr


def test_evidence_log_personal_path_is_exempt_but_counted(sandbox):
    """P-01：门禁证据日志含宿主路径属运行事实，不判失败，但必须计数（不得静默忽略）。"""
    log = sandbox / "loops" / "demo" / "evidence"
    log.mkdir(parents=True)
    (log / "gate.log").write_text("cd /home/jdoe/proj && python3 -m pytest\n")
    r = run_scan(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "evidence_logs_personal_path_skipped=1" in r.stdout


def test_evidence_log_exemption_does_not_cover_credentials(sandbox):
    """P-01 反例：豁免只针对个人路径，凭据仍必须失败。"""
    log = sandbox / "loops" / "demo" / "evidence"
    log.mkdir(parents=True)
    (log / "gate.log").write_text(
        "cd /home/jdoe/proj\ndsn=oracle://scott:tiger99@dbprod.internal:1521/PROD\n"
    )
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "REAL_CONNECTION_STRING" in r.stdout
    assert "tiger99" not in r.stdout


def test_same_path_outside_evidence_dir_still_fails(sandbox):
    """P-01 反例：同样的个人路径写在源码里必须失败。"""
    (sandbox / "loops" / "demo").mkdir(parents=True, exist_ok=True)
    (sandbox / "loops" / "demo" / "notes.md").write_text("cd /home/jdoe/proj\n")
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "PERSONAL_ABSOLUTE_PATH" in r.stdout


def test_yaml_bare_literal_is_not_a_code_variable(sandbox):
    content = "pass" + "word: " + "CanaryAlpha42"
    (sandbox / "config.yaml").write_text(content + "\n")
    r = run_scan(sandbox)
    assert r.returncode != 0
    assert "CanaryAlpha42" not in r.stdout
