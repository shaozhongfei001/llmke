"""撤权 fence：先挡读、再重建；只过滤不验代次等于赌引擎行为。"""

import pytest

from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef
from graph_engine_adapter.fence import (FenceState, StaleIndexError, assert_index_fresh,
                                        filter_hits, revoked_visible_leak)
from graph_engine_adapter.pipeline import retrieve


class FakeRetriever:
    """故意"不认识撤权"：无论 fence 怎么说，它都返回旧内容。"""

    def __init__(self):
        self.last_executed_route = "GRAPH"

    def dense(self, query, top_k):
        return [{"text": "旧的密级内容", "sources": [{"file_id": "999"}]}]

    def graph(self, query, seeds, top_k):
        return [{"text": "旧的密级内容", "sources": [{"file_id": "999"}]}]


def make_store():
    s = AssertionStore()
    s.register_entity("p", "产品甲")
    s.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元", key="额度",
                    sources=[SourceRef("999", "a" * 64)]))
    return s


def test_revoke_is_idempotent_and_bumps_generation_once():
    fence = FenceState()
    assert fence.revoke(["999"]) == 1
    assert fence.revoke(["999"]) == 1          # 重复撤权不再推进代次
    assert fence.revoke(["1000"]) == 2
    assert fence.is_revoked("999") and not fence.is_revoked("333")


def test_stale_index_is_rejected_before_reading():
    fence = FenceState()
    fence.revoke(["999"])
    with pytest.raises(StaleIndexError):
        assert_index_fresh(0, fence)           # 旧索引
    with pytest.raises(StaleIndexError):
        assert_index_fresh(None, fence)        # 未声明代次同样拒绝
    assert_index_fresh(1, fence)               # 重建后的索引才放行


def test_hits_with_only_revoked_sources_are_dropped_and_reported():
    fence = FenceState()
    fence.revoke(["999"])
    out = filter_hits([{"text": "x", "sources": [{"file_id": "999"}]},
                       {"text": "y", "sources": [{"file_id": "333"}, {"file_id": "999"}]}],
                      fence)
    assert len(out["hits"]) == 1
    assert out["hits"][0]["sources"] == [{"file_id": "333"}]     # 撤权来源被裁掉
    assert out["dropped"][0]["reason"] == "ALL_SOURCES_REVOKED"


def test_pipeline_drops_revoked_content_even_if_engine_returns_it():
    fence = FenceState()
    fence.revoke(["999"])
    out = retrieve("产品甲的额度", store=make_store(), retriever=FakeRetriever(),
                   known_files={"999"}, fence=fence, index_generation=1)
    assert out["hit_count"] == 0               # 引擎返回了，但平台拦住了
    assert out["fence"]["dropped"][0]["reason"] == "ALL_SOURCES_REVOKED"
    assert not revoked_visible_leak(out["hits"], fence)


def test_pipeline_refuses_stale_index_when_fence_active():
    fence = FenceState()
    fence.revoke(["999"])
    with pytest.raises(StaleIndexError):
        retrieve("产品甲的额度", store=make_store(), retriever=FakeRetriever(),
                 fence=fence, index_generation=0)


def test_without_fence_behaviour_is_unchanged():
    """没配 fence 时行为必须和以前一致：不能因为加了安全机制就悄悄改默认语义。"""
    out = retrieve("产品甲的额度", store=make_store(), retriever=FakeRetriever(),
                   known_files={"999"})
    assert out["hit_count"] == 1 and out["fence"]["generation"] is None
