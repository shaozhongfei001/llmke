"""D10 评估器纯函数测试。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "services" / "rag-alg" / "index_data_service"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_engine_adapter import d10_eval  # noqa: E402


def _case(**kw):
    base = {"id": "T-01", "question": "q", "requires_citation": True,
            "disable_control": False}
    base.update(kw)
    return base


def test_pass_when_all_structural_checks_ok():
    r = d10_eval.evaluate_case(
        _case(),
        {"answer": "答案", "route": "GRAPH",
         "citations": [{"file_id": "1", "locator": "p1", "title": "t"}]},
        None)
    assert r["pass"] is True and r["reasons"] == []


def test_fail_missing_locator():
    r = d10_eval.evaluate_case(
        _case(),
        {"answer": "答案", "route": "GRAPH",
         "citations": [{"file_id": "1", "locator": ""}]}, None)
    assert r["pass"] is False
    assert any("locator" in x for x in r["reasons"])


def test_fail_fallback_without_reason():
    r = d10_eval.evaluate_case(
        _case(),
        {"answer": "答案", "route": "DENSE_FALLBACK",
         "citations": [{"file_id": "1", "locator": "p1"}]}, None)
    assert r["pass"] is False
    assert any("原因" in x for x in r["reasons"])


def test_fail_disable_control_missing():
    r = d10_eval.evaluate_case(
        _case(disable_control=True),
        {"answer": "答案", "route": "GRAPH",
         "citations": [{"file_id": "1", "locator": "p1"}]}, None)
    assert r["pass"] is False


def test_disable_control_passes_with_explicit_fallback_b():
    r = d10_eval.evaluate_case(
        _case(disable_control=True),
        {"answer": "答案", "route": "GRAPH",
         "citations": [{"file_id": "1", "locator": "p1"}]},
        {"answer": "b", "route": "DENSE_FALLBACK", "reason": "GRAPH_DISABLED",
         "citations": []})
    assert r["pass"] is True


def test_unknown_route_fails():
    r = d10_eval.evaluate_case(
        _case(), {"answer": "答案", "route": "NEBULA_LEGACY",
                  "citations": [{"file_id": "1", "locator": "p1"}]}, None)
    assert r["pass"] is False
