"""P0-03 — controlled installer tests."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

FW = Path(__file__).resolve().parents[1]
INSTALLER = FW / "scripts" / "installer.py"


def run_installer(target: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(INSTALLER), "--target", str(target), *args],
        capture_output=True, text=True,
    )


def test_plan_writes_nothing(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    r = run_installer(target, "--mode", "plan")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CREATE" in r.stdout
    assert list(target.iterdir()) == []  # nothing written


def test_empty_dir_install_and_idempotent_rerun(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    r = run_installer(target, "--mode", "apply")
    assert r.returncode == 0, r.stdout + r.stderr
    manifest = json.loads((target / ".framework-manifest.json").read_text())
    assert manifest["framework_version"]
    assert manifest["files"]
    assert (target / ".cursor" / "rules" / "00-workspace-redlines.mdc").is_file()
    assert (target / "scripts" / "loop_guard.py").is_file()
    assert (target / "contracts" / "registry.yaml").is_file()
    snapshot = {
        str(p.relative_to(target)): p.read_bytes()
        for p in target.rglob("*") if p.is_file()
    }
    # second run: fully idempotent
    r2 = run_installer(target, "--mode", "apply")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "already up to date" in r2.stdout
    snapshot2 = {
        str(p.relative_to(target)): p.read_bytes()
        for p in target.rglob("*") if p.is_file()
    }
    assert snapshot == snapshot2
    # no nested rules dir (the original defect)
    assert not (target / ".cursor" / "rules" / "rules").exists()


def test_conflict_stops_protected_file(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    assert run_installer(target, "--mode", "apply").returncode == 0
    (target / "Makefile").write_text("# locally modified\n")
    r = run_installer(target, "--mode", "plan")
    assert r.returncode == 4
    assert "CONFLICT_STOP" in r.stdout
    assert (target / "Makefile").read_text() == "# locally modified\n"
    # protected files stop even with --force
    r = run_installer(target, "--mode", "apply", "--force")
    assert r.returncode == 4
    assert (target / "Makefile").read_text() == "# locally modified\n"


def test_force_overwrites_nonprotected_with_backup(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    assert run_installer(target, "--mode", "apply").returncode == 0
    victim = target / ".cursor" / "rules" / "00-workspace-redlines.mdc"
    framework_content = victim.read_bytes()
    local_edit = b"# project-specific edit\n"
    victim.write_bytes(local_edit)
    r = run_installer(target, "--mode", "apply", "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    assert victim.read_bytes() == framework_content  # overwritten with framework version
    manifest = json.loads((target / ".framework-manifest.json").read_text())
    backup_dir = manifest.get("backup_dir")
    assert backup_dir
    backups = list((target / backup_dir).rglob("00-workspace-redlines.mdc"))
    assert backups and backups[0].read_bytes() == local_edit  # user edit preserved


def test_rollback_on_mid_apply_failure(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    if os.geteuid() == 0:
        pytest.skip("cannot simulate write failure as root via chmod")
    # .cursor + loops install fine (early in payload order); scripts/ dir is
    # pre-created read-only so APPLY fails midway and must roll back.
    (target / "scripts").mkdir()
    os.chmod(target / "scripts", 0o555)
    try:
        r = run_installer(target, "--mode", "apply")
    finally:
        os.chmod(target / "scripts", 0o755)
    assert r.returncode != 0
    assert "rolled back" in (r.stdout + r.stderr)
    leftovers = [
        p for p in target.rglob("*")
        if p.is_file() and ".framework-backup" not in str(p)
    ]
    assert leftovers == [], f"rollback left files behind: {leftovers}"
    assert not (target / ".cursor").exists()
    assert not (target / "loops").exists()


def test_symlink_in_payload_rejected(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    fw_copy = tmp_path / "fw"
    os.symlink("/etc/hostname", fw_copy)  # not used directly; build a real copy below
    fw_real = tmp_path / "fw-real"
    subprocess.run(["cp", "-r", str(FW), str(fw_real)], check=True,
                   stdout=subprocess.DEVNULL)
    evil = fw_real / ".cursor" / "rules" / "evil-link"
    os.symlink("/etc/passwd", evil)
    r = subprocess.run(
        [sys.executable, str(INSTALLER), "--target", str(target),
         "--framework-root", str(fw_real), "--mode", "apply"],
        capture_output=True, text=True,
    )
    assert r.returncode == 3
    assert "symlink" in (r.stdout + r.stderr).lower()
    assert not (target / ".cursor").exists()


def test_path_traversal_dest_rejected(tmp_path):
    """validate_paths must reject '..' traversal and absolute dest paths."""
    sys.path.insert(0, str(FW / "scripts"))
    try:
        import installer
    finally:
        sys.path.pop(0)
    target = tmp_path / "proj"
    target.mkdir()
    evil = [
        installer.Entry(Path("/x"), Path("../escape.txt"), "../escape.txt", "0" * 64),
        installer.Entry(Path("/x"), Path("/abs/path"), "/abs/path", "0" * 64),
        installer.Entry(Path("/x"), Path("ok/file.txt"), "ok/file.txt", "0" * 64),
    ]
    errs = installer.validate_paths(evil, target)
    assert any("traversal" in e for e in errs)
    assert any("absolute" in e for e in errs)
    assert not any("ok/file.txt" in e and "REJECT" in e for e in errs)


def test_upgrade_changes_only_changed_files(tmp_path):
    target = tmp_path / "proj"
    target.mkdir()
    assert run_installer(target, "--mode", "apply").returncode == 0
    manifest1 = json.loads((target / ".framework-manifest.json").read_text())
    n1 = len(manifest1["files"])
    assert n1 > 0
    # upgrade: rerun apply -> all SKIP, no manifest rewrite
    mtime = (target / ".framework-manifest.json").stat().st_mtime_ns
    r = run_installer(target, "--mode", "apply")
    assert r.returncode == 0
    assert (target / ".framework-manifest.json").stat().st_mtime_ns == mtime


def test_target_escape_guard(tmp_path):
    r = run_installer(tmp_path / "nonexistent", "--mode", "plan")
    assert r.returncode == 2
    # target == framework root must be refused
    r = run_installer(FW, "--mode", "plan")
    assert r.returncode == 2
