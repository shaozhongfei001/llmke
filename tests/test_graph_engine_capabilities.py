"""describe 的能力声明必须"有证据才能叫 VERIFIED"，且未实现的项不许缺省消失。"""

import pytest

from graph_engine_adapter import describe
from graph_engine_adapter import capabilities as caps_mod


def test_describe_shape_and_counts():
    d = describe()
    assert d["schema"] == "llmke.graph-engine.describe.v1"
    assert set(d["counts"]) == {"VERIFIED", "NOT_VERIFIED", "NOT_IMPLEMENTED"}
    assert sum(d["counts"].values()) == len(d["capabilities"])
    assert d["declared"] == sorted(d["capabilities"])


def test_every_verified_has_evidence():
    for name, cap in describe()["capabilities"].items():
        if cap["status"] == "VERIFIED":
            assert cap["evidence"], f"{name} 声明 VERIFIED 但没有证据指针"


def test_graph_route_is_not_verified_and_communities_not_implemented():
    caps = describe()["capabilities"]
    # 检索命中不等于图执行：没有 executed_route=GRAPH 的 trace 就只能 NOT_VERIFIED
    assert caps["retrieve_graph_route"]["status"] == "NOT_VERIFIED"
    assert caps["community_report"]["status"] == "NOT_IMPLEMENTED"
    assert caps["predicate_normalization"]["status"] == "NOT_IMPLEMENTED"


def test_verified_without_evidence_is_rejected(monkeypatch):
    broken = dict(caps_mod.CAPABILITIES)
    broken["fake_cap"] = {"status": "VERIFIED", "note": "吹的", "evidence": None}
    monkeypatch.setattr(caps_mod, "CAPABILITIES", broken)
    with pytest.raises(ValueError):
        caps_mod.describe()
