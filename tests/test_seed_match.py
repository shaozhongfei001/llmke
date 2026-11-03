"""查询侧种子匹配：简称要认出来，但不能把查询引到错误的实体。

判据三条：精确优先、简称唯一才用、太短不认（宁可回退稠密，不可错认）。
"""

from graph_engine_adapter.assertions import AssertionStore
from graph_engine_adapter.pipeline import find_seeds
from graph_engine_adapter.seed_match import (diagnose, match_names, match_seeds,
                                             normalize_name)

NAMES = ["华东精密制造有限公司", "江南装备科技有限公司", "海川电子材料股份有限公司",
         "华东电子有限公司"]


def test_exact_name_wins():
    matched, method = match_names("华东精密制造有限公司的授信额度", NAMES)
    assert method == "exact"
    assert matched == ["华东精密制造有限公司"]


def test_full_name_without_org_suffix():
    matched, method = match_names("江南装备科技的评级", NAMES)
    assert method == "normalized"
    assert matched == ["江南装备科技有限公司"]


def test_abbreviated_prefix():
    """问句只写前四个字是常态：华东精密的额度。"""
    matched, _ = match_names("华东精密的额度是多少", NAMES)
    assert matched == ["华东精密制造有限公司"]


def test_abbreviated_middle():
    """简称不一定从第一个字开始：华东精密电子 常被叫 华东电子。"""
    matched, _ = match_names("华东电子的额度", NAMES)
    assert matched == ["华东电子有限公司"]


def test_ambiguous_short_form_is_dropped():
    """两个实体共享同一个简称时全放弃——错认会把查询带进错的子图。"""
    names = ["华东精密制造有限公司", "华东精密电子有限公司"]
    ids = {"华东精密制造有限公司": "ent:a", "华东精密电子有限公司": "ent:b"}
    out = match_seeds("华东精密的额度", names, ids.get)
    assert out["seeds"] == [] and out["method"] == "none"
    assert out["ambiguous"]


def test_two_names_of_one_entity_are_not_ambiguous():
    """引擎里同一实体常有 `ent:名称` 与原名两条登记，不能当两个实体而放弃种子。"""
    names = ["ent:华东精密制造有限公司", "华东精密制造有限公司"]
    ids = {n: "ent:hua" for n in names}
    out = match_seeds("华东精密的额度", names, ids.get)
    assert out["seeds"] == ["ent:hua"]


def test_too_short_fragment_is_not_matched():
    matched, method = match_names("华东的额度", NAMES)
    assert matched == [] and method == "none"


def test_unknown_query_has_no_seeds():
    matched, method = match_names("今天天气怎么样", NAMES)
    assert matched == [] and method == "none"


def test_normalize_strips_suffix_and_punctuation():
    assert normalize_name("华东 精密制造有限公司") == "华东精密制造"
    assert normalize_name("（江南）装备科技有限公司") == "江南装备科技"


def test_diagnose_reports_method_and_reason():
    store = AssertionStore()
    store.register_entity("ent:hua", "华东精密制造有限公司")
    out = diagnose("华东精密的额度", store)
    assert out["method"] == "normalized"
    assert out["seeds"] == ["ent:hua"]
    assert out["reason"]
    empty = diagnose("今天天气", store)
    assert empty["method"] == "none" and empty["seeds"] == []
    assert "回退稠密" in empty["reason"]


def test_pipeline_find_seeds_uses_abbreviation():
    store = AssertionStore()
    store.register_entity("ent:hua", "华东精密制造有限公司")
    store.register_entity("ent:jn", "江南装备科技有限公司")
    assert find_seeds("华东精密的额度", store) == ["ent:hua"]
    assert find_seeds("江南装备的评级", store) == ["ent:jn"]
    assert find_seeds("别的公司", store) == []
