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


def test_graph_route_verified_only_with_replayable_evidence():
    """图路由升 VERIFIED 的条件比"有 evidence 字符串"更硬：

    D6 的坑是"检索有命中"被当成"图执行过"。所以这里要求：
    ①状态是 VERIFIED；②证据指针带 sha256（可被评审方对文件复算）；
    ③note 里必须点名两组对照与判据字段，不能只有一句"已跑通"。
    """
    caps = describe()["capabilities"]
    route = caps["retrieve_graph_route"]
    assert route["status"] == "VERIFIED"
    assert "A2-pure-graph-route.md" in route["evidence"]
    assert "sha256" in route["evidence"]
    for token in ("graph_calls", "rerank_fallback", "facts_after_rerank", "DENSE_FALLBACK"):
        assert token in route["note"], f"能力说明缺判据字段 {token}，会退化成口头宣告"
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
