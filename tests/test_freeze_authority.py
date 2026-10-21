"""P-04 — 冻结元数据不得硬编码，缺失时拒绝写入。"""
import fixture_helpers  # noqa: F401
from fixture_helpers import dump, load
from freeze_baseline import run, AUTHORITY, MANIFEST
from contract_runtime import ContractViolation
import pytest


def project(tmp_path, version="1.1.1", authority=True):
    root = tmp_path / "p"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "a.py").write_text("x = 1\n")
    if version:
        (root / "VERSION").write_text(version + "\n")
    if authority:
        dump(root / AUTHORITY, {
            "authority": "unit-test window",
            "authorized_by": "tester",
            "authorized_at": "2026-10-21",
            "scope": ["test"],
            "change_list": [{"id": "P-T", "summary": "test"}],
        })
    return root


def test_write_without_authority_is_refused(tmp_path):
    root = project(tmp_path, authority=False)
    with pytest.raises(ContractViolation):
        run(root, write=True)
    assert not (root / MANIFEST).exists()


def test_incomplete_authority_is_refused(tmp_path):
    root = project(tmp_path, authority=True)
    dump(root / AUTHORITY, {"authority": "only a title"})
    with pytest.raises(ContractViolation) as exc:
        run(root, write=True)
    assert "missing fields" in str(exc.value)


def test_write_records_authority_and_revision(tmp_path):
    root = project(tmp_path)
    assert run(root, write=True) == []
    m1 = load(root / MANIFEST)
    assert m1["baseline_version"] == "1.1.1"
    assert m1["authority"] == "unit-test window"
    assert m1["authorized_by"] == "tester"
    assert m1["manifest_revision"] == 1
    assert m1["frozen_at"]
    assert run(root, write=True) == []
    assert load(root / MANIFEST)["manifest_revision"] == 2


def test_version_mismatch_is_detected(tmp_path):
    root = project(tmp_path)
    run(root, write=True)
    (root / "VERSION").write_text("9.9.9\n")
    assert run(root) == ["wrong baseline version"]


def test_control_change_is_detected(tmp_path):
    root = project(tmp_path)
    run(root, write=True)
    (root / "scripts" / "a.py").write_text("x = 2\n")
    errors = run(root)
    assert any("frozen control changed" in e for e in errors)
