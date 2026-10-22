"""P-06 — 预算耗尽的批次必须有终态，而不是永久卡在 IN_DEV。

终态语义：历史结论保留（不参与 STALE 判定），但不得再执行门禁、不得 finish。
"""
import fixture_helpers  # noqa: F401
from fixture_helpers import make_loop, guard, devpass, load
from baseline_support import atomic_json


def set_status(d, status, render=True):
    state = load(d / "STATE.json")
    state["status"] = status
    atomic_json(d / "STATE.json", state)
    if render:
        assert guard(d.parents[1], "render-views", "--loop", "T1").returncode == 0


def test_superseded_cannot_run_gate(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    set_status(d, "SUPERSEDED")
    p = guard(root, "run-gate", "--loop", "T1", "--gate", "repo_structure_gate",
              "--executor", "dev-1")
    assert p.returncode != 0
    assert "BLOCKED/DRAFT/DONE" in p.stdout + p.stderr


def test_terminal_state_ignores_candidate_staleness(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    m = load(d / "evidence/manifest.json")
    m["gates"]["repo_structure_gate"]["control_sha256"] = "0" * 64
    atomic_json(d / "evidence/manifest.json", m)
    assert guard(root, "evidence-check", "--loop", "T1").returncode != 0
    set_status(d, "SUPERSEDED")
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode == 0, p.stdout + p.stderr


def test_retired_behaves_like_terminal(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    set_status(d, "RETIRED")
    m = load(d / "evidence/manifest.json")
    m["gates"]["repo_structure_gate"]["control_sha256"] = "1" * 64
    atomic_json(d / "evidence/manifest.json", m)
    assert guard(root, "evidence-check", "--loop", "T1").returncode == 0


def test_terminal_cannot_finish(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    set_status(d, "SUPERSEDED")
    assert guard(root, "finish", "--loop", "T1").returncode != 0


def test_unknown_state_still_rejected(tmp_path):
    root, d = make_loop(tmp_path)
    devpass(root)
    set_status(d, "ARCHIVED", render=False)
    p = guard(root, "evidence-check", "--loop", "T1")
    assert p.returncode != 0
    assert "invalid state" in p.stdout + p.stderr
