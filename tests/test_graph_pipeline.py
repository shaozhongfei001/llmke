"""检索编排：路线先判、原因留档、引用收口。用假 retriever，不加载模型。"""

import pytest

from graph_engine_adapter import Assertion, AssertionStore, SourceRef
from graph_engine_adapter.pipeline import find_seeds, retrieve


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def dense(self, query, top_k):
        self.calls.append(("dense", query, top_k))
        return [{"text": "稠密命中", "sources": [{"file_id": "333"}]}]

    def graph(self, query, seeds, top_k):
        self.calls.append(("graph", query, tuple(seeds), top_k))
        return [{"text": "图命中", "sources": [{"file_id": "333"}]}]


def make_store():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲", "甲产品")
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=8000, unit="万元",
                    key="额度", sources=[SourceRef("333", "a" * 64)]))
    return s


def test_seeds_found_from_query():
    s = make_store()
    assert find_seeds("产品甲的额度是多少", s) == ["p_jia"]
    assert find_seeds("完全不相关的问题", s) == []


def test_graph_route_when_seeds_have_assertions():
    s, r = make_store(), FakeRetriever()
    out = retrieve("产品甲的额度", store=s, retriever=r)
    assert out["route"] == "GRAPH" and out["reason"] == "SEEDS_WITH_ASSERTIONS"
    assert out["passed"] is True
    assert r.calls and r.calls[0][0] == "graph"


def test_graph_disabled_falls_back_with_reason():
    s, r = make_store(), FakeRetriever()
    out = retrieve("产品甲的额度", store=s, retriever=r, graph_enabled=False)
    assert out["route"] == "DENSE_FALLBACK"
    assert out["reason"] == "GRAPH_DISABLED"
    assert r.calls[0][0] == "dense"


def test_no_seed_falls_back_even_if_dense_finds_something():
    s, r = make_store(), FakeRetriever()
    out = retrieve("没有任何实体的问题", store=s, retriever=r)
    assert out["route"] == "DENSE_FALLBACK"
    assert out["reason"] == "NO_SEED_ENTITY"
    assert out["hit_count"] == 1          # 稠密确实有结果
    assert out["passed"] is True          # 普通查询允许回退


def test_require_graph_query_cannot_pass_on_fallback():
    s, r = make_store(), FakeRetriever()
    out = retrieve("没有任何实体的问题", store=s, retriever=r, require_graph=True)
    assert out["route"] == "DENSE_FALLBACK"
    assert out["passed"] is False        # 强制图验收不能靠回退通过


def test_citations_are_linked_and_invalid_flagged():
    s, r = make_store(), FakeRetriever()
    ok = retrieve("产品甲的额度", store=s, retriever=r, known_files={"333"})
    assert [c["label"] for c in ok["citations"]] == ["p_jia.额度@333"]
    assert ok["invalid_citations"] == []

    bad = retrieve("产品甲的额度", store=s, retriever=r, known_files={"999"})
    assert bad["citations"] == []
    assert [c["label"] for c in bad["invalid_citations"]] == ["p_jia.额度@333"]


def test_scope_filter_affects_route_decision():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=1, unit="万元", key="额度",
                    visibility={"secret"}, sources=[SourceRef("999", "b" * 64)]))
    r = FakeRetriever()
    out = retrieve("产品甲的额度", store=s, retriever=r, scopes={"public"})
    # 断言对该 scope 不可见 → 视为无种子事实 → 回退，而不是偷偷用隐藏事实
    assert out["route"] == "DENSE_FALLBACK"
    assert out["reason"] == "SEEDS_WITHOUT_ASSERTIONS"
