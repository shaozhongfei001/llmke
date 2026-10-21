"""P-03 — 证据必须绑定「真实输入范围」，而不是整棵树。

旧行为：任何 docs/** 改动都让开发门禁与 QA 证据 STALE（反复返工的根因）。
新行为：STALE 判定用 control_digest；仅声明依赖文档的门禁额外比较 doc_digest；
        旧记录（无 digest_scheme）保持整树语义，不回溯改写。
"""
import fixture_helpers  # noqa: F401  （建立 scripts/ 的导入路径）
from fixture_helpers import make_loop, guard, devpass, load, dump
from baseline_support import atomic_json


def test_doc_change_does_not_invalidate_dev_evidence(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    (root / "docs" / "NOTE.md").write_text("documentation only, no control semantics\n")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode == 0, p.stdout + p.stderr


def test_control_change_invalidates_evidence(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    (root / "scripts" / "extra.py").write_text("x = 1\n")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode != 0
    assert "STALE" in p.stdout


def test_doc_dependent_gate_rejects_doc_change(tmp_path):
    """traceability_gate 读 docs/baseline/TRACE.yaml，必须对文档变化敏感。"""
    root, d = make_loop(tmp_path)
    loop = load(d / "LOOP.yaml")
    loop["gates"][0]["id"] = "traceability_gate"
    loop["gates"][1]["depends_on"] = ["traceability_gate"]
    dump(d / "LOOP.yaml", loop)
    from freeze_baseline import run as freeze
    freeze(root, write=True)
    p = guard(root, "run-gate", "--loop", "T1", "--gate", "traceability_gate",
              "--executor", "dev-1")
    assert p.returncode == 0, p.stdout + p.stderr
    (root / "docs" / "NOTE.md").write_text("doc changed\n")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode != 0
    assert "dependent documents changed" in p.stdout


def test_new_records_declare_digest_scheme(tmp_path):
    root, d = make_loop(tmp_path)
    rec = devpass(root)
    assert rec["digest_scheme"] == 2
    assert len(rec["control_sha256"]) == 64 and len(rec["doc_sha256"]) == 64


def test_legacy_record_keeps_whole_tree_semantics(tmp_path):
    """旧记录没有 digest_scheme：不得回溯改写，仍按整树哈希判定。"""
    root, d = make_loop(tmp_path)
    devpass(root)
    m = load(d / "evidence/manifest.json")
    rec = m["gates"]["repo_structure_gate"]
    for key in ("digest_scheme", "control_sha256", "doc_sha256"):
        rec.pop(key, None)
    atomic_json(d / "evidence/manifest.json", m)
    assert guard(root, "evidence-check", "--loop", "T1").returncode == 0
    (root / "docs" / "NOTE.md").write_text("legacy scheme still sees this\n")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode != 0
    assert "STALE" in p.stdout
