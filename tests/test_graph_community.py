"""社区/global 报告：只吃校验过的事实，引用失效必须暴露，不许用普通 RAG 顶替。"""

from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef
from graph_engine_adapter.community import (build_communities, build_report, export_facts,
                                            validate_report_citations)


def ref(fid, loc="0-10"):
    return SourceRef(file_id=fid, artifact_id="a" * 64, channel="text", locator=loc)


def make_store():
    s = AssertionStore()
    s.register_entity("cust_a", "客户A")
    s.register_entity("prod", "产品甲")
    s.register_entity("lonely", "孤立实体")
    s.add(Assertion(subject="cust_a", predicate="申请", object_entity="prod", sources=[ref("333")]))
    s.add(Assertion(subject="prod", predicate="额度", object_value=8000, unit="万元", key="额度",
                    sources=[ref("333")]))
    s.add(Assertion(subject="lonely", predicate="无关联", object_entity="cust_a",
                    sources=[ref("404")]))       # 来源不可见
    return s


def test_export_excludes_invisible_sources():
    out = export_facts(make_store(), known_files={"333"})
    assert out["stats"]["exported"] == 2
    assert out["stats"]["excluded"] == 1
    assert out["excluded"][0]["reason"] == "SOURCE_NOT_VISIBLE"
    assert out["excluded"][0]["files"] == ["404"]


def test_communities_group_connected_entities_and_mark_isolated():
    s = AssertionStore()
    s.register_entity("a", "甲"); s.register_entity("b", "乙"); s.register_entity("c", "丙")
    s.add(Assertion(subject="a", predicate="关联", object_entity="b", sources=[ref("333")]))
    s.add(Assertion(subject="c", predicate="自述", object_entity="c", sources=[ref("333")]))
    communities = build_communities(export_facts(s, {"333"})["facts"])
    sizes = sorted(c["size"] for c in communities)
    assert sizes == [1, 2]
    assert any(c["isolated"] for c in communities)


def test_community_detection_is_deterministic():
    s = make_store()
    facts = export_facts(s, {"333"})["facts"]
    first = build_communities(facts)
    second = build_communities(list(reversed(facts)))
    assert [c["entities"] for c in first] == [c["entities"] for c in second]


def test_report_marks_blocked_when_no_facts():
    empty = AssertionStore()
    report = build_report(empty, known_files={"333"})
    assert report["status"] == "BLOCKED"
    assert report["communities"] == []


def test_report_status_partial_when_some_facts_excluded():
    report = build_report(make_store(), known_files={"333"})
    assert report["status"] == "READY"            # 被排除的计入 excluded，不影响其余
    assert report["export"]["excluded"] == 1
    assert all(section["facts"] for section in report["communities"])


def test_citations_are_validated_against_known_files():
    sections = [{"community": "c-1", "facts": [{"text": "x", "sources": ["333"]}]}]
    assert validate_report_citations(sections, {"333"})["invalid"] == []
    bad = validate_report_citations(sections, {"999"})
    assert bad["invalid"] and bad["valid"] == []


def test_report_policy_states_no_rag_substitute():
    report = build_report(make_store(), known_files={"333"})
    assert "不得" in report["policy"] or "不可" in report["policy"]
