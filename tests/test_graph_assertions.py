"""标准断言层：任务书九条业务场景的语义反证（构造数据，语义层）。"""

import pytest

from graph_engine_adapter.assertions import (
    DENSE_FALLBACK, GRAPH, Assertion, AssertionStore, SourceRef, decide_route)


def ref(file_id, locator="0-10", artifact="a" * 64, channel="text"):
    return SourceRef(file_id=file_id, artifact_id=artifact, channel=channel, locator=locator)


def store_with_products():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲", "甲产品")
    s.register_entity("p_yi", "产品乙")
    s.register_entity("cust_a", "客户A")
    s.add(Assertion(subject="p_jia", predicate="最高额度", object_value=8000, unit="万元",
                    key="额度", sources=[ref("333")]))
    return s


def test_bidirectional_predicate_is_not_merged_unless_symmetric():
    s = store_with_products()
    s.add(Assertion(subject="cust_a", predicate="申请", object_entity="p_jia",
                    sources=[ref("333")]))
    assert s.related("cust_a", "申请", "p_jia") is True
    # 单向谓词：反过来不成立
    assert s.related("p_jia", "申请", "cust_a") is False

    s.add(Assertion(subject="p_jia", predicate="互斥", object_entity="p_yi",
                    direction="symmetric", sources=[ref("333")]))
    assert s.related("p_yi", "互斥", "p_jia") is True


def test_ledger_handles_add_subtract_and_zero_adjustment():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    s.add(Assertion(subject="p_jia", predicate="额度调整", object_value=8000, unit="万元",
                    key="额度", op="set", sources=[ref("333")]))
    s.add(Assertion(subject="p_jia", predicate="额度调整", object_value=2000, unit="万元",
                    key="额度", op="add", sources=[ref("334")]))
    s.add(Assertion(subject="p_jia", predicate="额度调整", object_value=500, unit="万元",
                    key="额度", op="subtract", sources=[ref("334")]))
    s.add(Assertion(subject="p_jia", predicate="额度调整", object_value=0, unit="万元",
                    key="额度", op="add", sources=[ref("334")]))

    led = s.ledger("p_jia", "额度")
    assert led["total"] == 9500          # 8000 + 2000 - 500 + 0
    assert len(led["components"]) == 3
    assert led["unit"] == "万元"


def test_ledger_refuses_mixed_units():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=8000, unit="万元",
                    key="额度", sources=[ref("333")]))
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=1, unit="亿元",
                    key="额度", op="add", sources=[ref("334")]))
    with pytest.raises(ValueError):
        s.ledger("p_jia", "额度")


def test_numeric_assertion_requires_unit_and_source():
    s = AssertionStore()
    with pytest.raises(ValueError):
        s.add(Assertion(subject="p", predicate="额度", object_value=1, key="额度",
                        sources=[ref("333")]))
    with pytest.raises(ValueError):
        s.add(Assertion(subject="p", predicate="额度", object_value=1, unit="万元", key="额度",
                        sources=[]))


def test_alias_resolves_but_homonym_does_not_merge():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲", "甲产品")
    assert s.resolve("甲产品") == "p_jia"

    # 同名异体：两家不同的"产品甲"，必须靠 id 区分，不能靠名字
    s.register_entity("x1", "同名产品")
    s.register_entity("x2", "同名产品")
    assert s.entities_named("同名产品") == ["x1", "x2"]
    assert s.resolve("同名产品") is None        # 解析不唯一 → 逼调用方显式选


def test_multi_source_fact_delete_one_keeps_the_rest():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    a = Assertion(subject="p_jia", predicate="最高额度", object_value=8000, unit="万元",
                  key="额度", sources=[ref("333"), ref("334")])
    s.add(a)
    assert len(s.facts("p_jia", "最高额度")) == 1
    assert len(s.facts("p_jia", "最高额度")[0].sources) == 2

    dropped = s.remove_source("333")
    assert dropped == []                               # 还有 334 撑着
    assert s.facts("p_jia", "最高额度")[0].sources[0].file_id == "334"

    dropped = s.remove_source("334")
    assert dropped and s.facts("p_jia", "最高额度") == []


def test_orphan_entity_is_legal_but_yields_dense_fallback():
    s = AssertionStore()
    s.add_orphan("lonely", "孤立实体")
    assert s.stats()["orphans"] == 1
    assert s.facts("lonely") == []
    # 实体存在（能解析）但没有断言 → 走稠密回退，原因要精确到"没有断言"
    decision = decide_route(True, ["孤立实体"], s)
    assert decision == {"route": DENSE_FALLBACK, "reason": "SEEDS_WITHOUT_ASSERTIONS"}
    # 名字压根解析不出来 → 另一个原因，不要与"有实体无断言"混为一谈
    assert decide_route(True, ["查无此实体"], s)["reason"] == "SEEDS_UNKNOWN"


def test_version_window_selects_old_and_new_policy():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=5000, unit="万元",
                    key="额度", effective_from="2026-01-01", effective_to="2026-07-01",
                    sources=[ref("333")]))
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=8000, unit="万元",
                    key="额度", effective_from="2026-07-01", sources=[ref("334")]))

    assert s.effective_fact("p_jia", "额度", as_of="2026-03-15").object_value == 5000
    assert s.effective_fact("p_jia", "额度", as_of="2026-10-31").object_value == 8000
    assert s.effective_fact("p_jia", "额度", as_of="2025-12-31") is None


def test_invisible_change_does_not_pollute_visible_result():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=8000, unit="万元",
                    key="额度", visibility={"public"}, sources=[ref("333")]))
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=99999, unit="万元",
                    key="额度", op="add", visibility={"secret"}, sources=[ref("999")]))

    public = s.ledger("p_jia", "额度", scopes={"public"})
    assert public["total"] == 8000                    # 不可见的那笔不参与
    # 删掉不可见来源，可见结果不变
    s.remove_source("999")
    assert s.ledger("p_jia", "额度", scopes={"public"})["total"] == 8000


def test_route_decision_explains_itself():
    s = store_with_products()
    assert decide_route(False, ["产品甲"])["reason"] == "GRAPH_DISABLED"
    assert decide_route(True, [])["reason"] == "NO_SEED_ENTITY"
    assert decide_route(True, ["产品甲"], s)["route"] == GRAPH
    assert decide_route(True, ["产品甲"], s)["reason"] == "SEEDS_WITH_ASSERTIONS"


def test_citation_validation_reports_invalid():
    s = store_with_products()
    out = s.validate_citations(known_files={"333"})
    assert out["invalid"] == []
    s.add(Assertion(subject="p_jia", predicate="担保", object_value=None, unit=None,
                    sources=[ref("404")]))
    out = s.validate_citations(known_files={"333"})
    assert out["invalid"] == ["p_jia.担保@404"]
