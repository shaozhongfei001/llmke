"""图服务 HTTP 边界：契约字段与"图是否真跑"的透传。

依赖 fastapi/httpx，在工具 venv（3.10）里没有，因此用 importorskip；
真实运行环境是 hipporag venv（3.11）。
"""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter.api import create_app  # noqa: E402


class FakeGraph:
    def vcount(self):
        return 97

    def ecount(self):
        return 258


class FakeHP:
    graph = FakeGraph()


class FakeEngine:
    save_dir = "/tmp/snap"
    hp = FakeHP()

    def openie_docs(self):
        return [{"idx": "c1", "extracted_triples": [["a", "r", "b"]]},
                {"idx": "c2", "extracted_triples": [["c", "r", "d"], ["e", "r", "f"]]}]

    def retrieve(self, query, top_k=3):
        return {
            "executed_route": "GRAPH",
            "reason": "GRAPH_CALLED",
            "trace": {"graph_calls": 1, "rerank_fallback": True},
            "docs": ["块一", "块二"][:top_k],
        }


def client():
    return TestClient(create_app(engine_factory=lambda: FakeEngine()))


def test_health_reports_graph_size_and_facts():
    r = client().get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert d["nodes"] == 97 and d["edges"] == 258
    assert d["facts"] == 3          # 三元组条数，不是文档数


def test_query_passes_through_executed_route_and_trace():
    r = client().post("/v2/graph/query", json={"query": "单笔授信超过五亿元", "top_k": 2})
    assert r.status_code == 200
    d = r.json()
    assert d["executed_route"] == "GRAPH"
    assert d["trace"]["graph_calls"] == 1
    assert d["hit_count"] == 2
    assert [x["rank"] for x in d["docs"]] == [1, 2]


def test_query_without_sources_must_not_fake_citations():
    d = client().post("/v2/graph/query", json={"query": "x"}).json()
    assert d["citations"] == []
    assert d["sources_available"] is False


def test_empty_query_is_rejected():
    assert client().post("/v2/graph/query", json={"query": ""}).status_code == 422
