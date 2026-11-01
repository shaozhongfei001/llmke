"""pipeline 接入生效期/可见域后置过滤：默认关闭，打开后必须真的丢。

这里用真 `AssertionStore` + 假 retriever（不加载 1.9GB 模型），验的是**编排接线**：
参数有没有透到过滤层、掉了多少有没有回传、默认路径有没有被改变。
"""

import pytest

from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef
from graph_engine_adapter.pipeline import retrieve

REF = SourceRef(file_id="333", artifact_id="a" * 64, channel="text", locator="0-10")


class FakeRetriever:
    last_executed_route = "DENSE_FALLBACK"

    def __init__(self, hits):
        self._hits = hits

    def dense(self, query, top_k):
        return self._hits

    def graph(self, query, seeds, top_k):
        return self._hits


def hit(text="块1"):
    return {"text": text, "sources": [{"file_id": "333", "artifact_id": "a" * 64,
                                       "channel": "text", "locator": "0-10"}]}


def store_with(effective_from=None, effective_to=None, scope=None):
    s = AssertionStore()
    s.add(Assertion(subject="cust", predicate="额度", object_value=3000, unit="万元",
                    key="额度",
                    sources=[REF], effective_from=effective_from,
                    effective_to=effective_to,
                    visibility={scope} if scope else {"public"}))
    return s


def test_default_path_is_unchanged():
    out = retrieve("额度是多少", store=store_with(effective_from="2026-01-01"),
                   retriever=FakeRetriever([hit()]), graph_enabled=False)
    assert out["hit_count"] == 1
    assert "version_filter" not in out          # 不传参数就不该有任何新字段


def test_as_of_outside_window_drops_hit_and_reports_stats():
    out = retrieve("额度是多少", store=store_with(effective_from="2027-01-01"),
                   retriever=FakeRetriever([hit()]), graph_enabled=False,
                   as_of="2026-06-01")
    assert out["hit_count"] == 0
    assert out["version_filter"]["stats"]["dropped"] == 1
    assert out["version_filter"]["dropped"][0]["reason"] == "OUT_OF_WINDOW"


def test_as_of_inside_window_keeps_hit():
    out = retrieve("额度是多少", store=store_with(effective_from="2026-01-01",
                                                effective_to="2027-01-01"),
                   retriever=FakeRetriever([hit()]), graph_enabled=False,
                   as_of="2026-06-01")
    assert out["hit_count"] == 1
    assert out["version_filter"]["stats"]["dropped"] == 0


def test_scope_denied_drops_hit():
    out = retrieve("额度是多少", store=store_with(),
                   retriever=FakeRetriever([hit()]), graph_enabled=False,
                   filter_scopes={"kb_7"}, doc_scopes={"333": {"kb_9"}})
    assert out["hit_count"] == 0
    assert out["version_filter"]["dropped"][0]["reason"] == "SCOPE_DENIED"


def test_unknown_scope_is_fail_closed():
    """可见性查不到就丢：漏掉一条不该看的，比多挡一条严重得多。"""
    out = retrieve("额度是多少", store=store_with(),
                   retriever=FakeRetriever([hit()]), graph_enabled=False,
                   filter_scopes={"kb_9"}, doc_scopes={})
    assert out["hit_count"] == 0
    assert out["version_filter"]["dropped"][0]["reason"] == "UNKNOWN_SCOPE"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
