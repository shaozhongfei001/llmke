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


def test_graph_route_not_verified_but_community_now_verified():
    caps = describe()["capabilities"]
    # 未打补丁的上游行为：检索命中不等于图执行，只能 NOT_VERIFIED
    assert caps["retrieve_graph_route"]["status"] == "NOT_VERIFIED"
    # 社区/global 已按"消费标准事实导出"实现并有真实运行证据
    assert caps["community_report"]["status"] == "VERIFIED"
    assert caps["community_report"]["evidence"]
    # 谓词归一已落在 normalize.build_store（显式字典 + 数值解析 + 来源绑定），有真跑证据
    assert caps["engine_predicate_normalization"]["status"] == "VERIFIED"
    assert caps["engine_predicate_normalization"]["evidence"]
    # 断言层语义已验证，但引擎接线未做——两者要分开记，不能互相顶替
    assert caps["platform_assertion_layer"]["status"] == "VERIFIED"


def test_verified_without_evidence_is_rejected(monkeypatch):
    broken = dict(caps_mod.CAPABILITIES)
    broken["fake_cap"] = {"status": "VERIFIED", "note": "吹的", "evidence": None}
    monkeypatch.setattr(caps_mod, "CAPABILITIES", broken)
    with pytest.raises(ValueError):
        caps_mod.describe()
