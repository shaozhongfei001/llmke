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

    def retrieve(self, query, seeds=None, top_k=3, use_graph=True):
        self.last_call = {"query": query, "seeds": list(seeds or []),
                          "top_k": top_k, "use_graph": use_graph}
        return {
            "executed_route": "GRAPH",
            "reason": "GRAPH_CALLED",
            "trace": {"graph_calls": 1, "rerank_fallback": True,
                      "seed_hits": list(seeds or [])},
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


def test_query_forwards_seeds_and_graph_switch():
    """D6 接线：HTTP 层的 seeds / enable_graph 必须原样到引擎。

    没有这条，种子永远停在边缘（线上 trace 里 seed_hits 恒为 []），
    "禁用图对照"也无从发起。
    """
    eng = FakeEngine()
    c = TestClient(create_app(engine_factory=lambda: eng))
    d = c.post("/v2/graph/query", json={"query": "智造贷的利率基准",
                                        "seeds": ["ent:智造贷"], "enable_graph": False}).json()
    assert eng.last_call["seeds"] == ["ent:智造贷"]
    assert eng.last_call["use_graph"] is False
    assert d["seeds"] == ["ent:智造贷"]
    assert d["graph_enabled"] is False
    assert d["trace"]["seed_hits"] == ["ent:智造贷"]


def test_query_without_sources_must_not_fake_citations():
    d = client().post("/v2/graph/query", json={"query": "x"}).json()
    assert d["citations"] == []
    assert d["sources_available"] is False


def test_empty_query_is_rejected():
    assert client().post("/v2/graph/query", json={"query": ""}).status_code == 422


def test_build_delegates_and_returns_snapshot(tmp_path):
    seen = {}

    def builder(docs, root):
        seen["docs"] = docs
        seen["root"] = root
        return {"snapshot": str(tmp_path), "chunks": len(docs), "sources": 1}

    c = TestClient(create_app(engine_factory=lambda: FakeEngine(), builder=builder))
    r = c.post("/v2/graph/build", json={"docs": [{"file_id": "f1", "text": "正文"}],
                                        "root": str(tmp_path)})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "BUILT" and d["chunks"] == 1
    assert seen["docs"][0].file_id == "f1"


def test_build_failure_returns_reason_not_silent(tmp_path):
    def boom(docs, root):
        raise RuntimeError("llm down")

    c = TestClient(create_app(engine_factory=lambda: FakeEngine(), builder=boom))
    r = c.post("/v2/graph/build", json={"docs": [{"file_id": "f1", "text": "正文"}]})
    assert r.status_code == 500
    assert "llm down" in r.json()["detail"]


def test_query_attaches_sources_when_snapshot_has_mapping(tmp_path):
    (tmp_path / "sources.json").write_text(
        '{"c1": [{"file_id": "333", "locator": "p1"}]}', encoding="utf-8")

    class EngineWithSources(FakeEngine):
        save_dir = str(tmp_path)

        def openie_docs(self):
            return [{"idx": "c1", "passage": "块一", "extracted_triples": [["a", "r", "b"]]}]

    c = TestClient(create_app(engine_factory=lambda: EngineWithSources()))
    d = c.post("/v2/graph/query", json={"query": "x", "top_k": 2}).json()
    assert d["sources_available"] is True
    assert d["docs"][0]["idx"] == "c1"
    assert d["citations"][0]["file_id"] == "333"
    assert d["docs"][1]["sources"] == []          # 没映射的块不硬凑来源


def test_build_accepts_bound_artifact(tmp_path):
    seen = {}

    def builder(docs, root):
        seen["docs"] = docs
        return {"snapshot": str(tmp_path), "chunks": len(docs)}

    c = TestClient(create_app(engine_factory=lambda: FakeEngine(), builder=builder))
    r = c.post("/v2/graph/build", json={
        "artifact": {"artifact_id": "a" * 64, "document_id": "doc-1",
                     "chunks": [{"text": "正文", "locator": "p1"}]},
        "root": str(tmp_path)})
    assert r.status_code == 200
    d = r.json()
    assert d["artifact_id"] == "a" * 64 and d["content_hash"]
    assert seen["docs"][0].file_id == "doc-1"


def test_build_rejects_invalid_artifact(tmp_path):
    c = TestClient(create_app(engine_factory=lambda: FakeEngine(),
                              builder=lambda docs, root: {"snapshot": str(tmp_path)}))
    r = c.post("/v2/graph/build", json={
        "artifact": {"artifact_id": "not-a-hash", "chunks": [{"text": "x", "locator": "p1"}]}})
    assert r.status_code == 400
    assert "artifact invalid" in r.json()["detail"]


def test_build_without_docs_or_artifact_is_rejected():
    c = TestClient(create_app(engine_factory=lambda: FakeEngine(),
                              builder=lambda docs, root: {"snapshot": "/tmp/x"}))
    assert c.post("/v2/graph/build", json={}).status_code == 400
