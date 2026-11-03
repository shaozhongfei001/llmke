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

def test_auto_seed_from_snapshot_when_caller_gives_none(tmp_path):
    """T-A6：调用方没给 seeds 时，服务端从快照 openie 实体自动识别（唯一实体才算）。"""
    import json

    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "openie_results_ner_test.json").write_text(json.dumps({
        "docs": [{"idx": "c1", "extracted_entities": ["智造贷", "5000万元"],
                  "extracted_triples": [["智造贷", "单户最高授信额度为", "5000万元"]]}]
    }, ensure_ascii=False), encoding="utf-8")

    class EngineWithSnapshot(FakeEngine):
        save_dir = str(snap)

    eng = EngineWithSnapshot()
    c = TestClient(create_app(engine_factory=lambda: eng))
    d = c.post("/v2/graph/query", json={"query": "智造贷的单户最高授信额度是多少"}).json()
    assert d["seeds_source"] == "auto"
    assert "智造贷" in d["seeds"]
    assert "智造贷" in eng.last_call["seeds"]


def test_auto_seed_none_when_no_match_or_no_snapshot():
    """认不出实体/无快照 → seeds_source=none，不瞎猜。"""
    eng = FakeEngine()  # save_dir=/tmp/snap 无 openie 文件
    c = TestClient(create_app(engine_factory=lambda: eng))
    d = c.post("/v2/graph/query", json={"query": "一个完全不存在的问句xyz"}).json()
    assert d["seeds_source"] == "none"
    assert d["seeds"] == []

def test_graph_view_returns_nodes_and_edges():
    """D0：库级图谱查看数据源 —— nodes/edges 稳定排序返回。"""

    class V:
        def __init__(self, name):
            self.name = name

        def attributes(self):
            return {"name": self.name, "content": None, "hash_id": None}

        def __getitem__(self, key):
            return getattr(self, key)

    class E:
        def __init__(self, s, t, w=1.0):
            self.source, self.target, self._w = s, t, w

        def attributes(self):
            return {"weight": self._w}

    class G:
        vs = [V("乙"), V("甲")]
        es = [E(1, 0, 0.5)]

    class EngineWithView(FakeEngine):
        hp = FakeHP()

    EngineWithView.hp.graph = G()
    c = TestClient(create_app(engine_factory=lambda: EngineWithView()))
    d = c.get("/v2/graph/view").json()
    assert d["status"] == "ok"
    assert d["node_count"] == 2 and d["edge_count"] == 1
    # 按 id（Unicode 码点）确定性排序：U+4E59 乙 < U+7532 甲
    assert [n["name"] for n in d["nodes"]] == ["乙", "甲"]
    assert d["edges"] == [{"source": "甲", "target": "乙", "weight": 0.5}]


def test_graph_view_unavailable_is_not_500():
    """图缺失 → 200 + GRAPH_UNAVAILABLE + 空列表（前端可渲染空态，不炸）。"""

    class EngineNoGraph(FakeEngine):
        hp = FakeHP()

    EngineNoGraph.hp.graph = None
    c = TestClient(create_app(engine_factory=lambda: EngineNoGraph()))
    d = c.get("/v2/graph/view").json()
    assert d["status"] == "GRAPH_UNAVAILABLE"
    assert d["nodes"] == [] and d["edges"] == []

def test_build_persists_and_exposes_fence(tmp_path):
    """D8：build 从快照 fence.json 恢复并暴露 GET /v2/fence。"""

    def builder(docs, root):
        (tmp_path / "fence.json").write_text(
            '{"generation": 2, "revoked": {"r9": {"reason": "REVOKED", "generation": 1}}}',
            encoding="utf-8")
        return {"snapshot": str(tmp_path), "chunks": len(docs), "sources": 1}

    c = TestClient(create_app(engine_factory=lambda: FakeEngine(), builder=builder))
    c.post("/v2/graph/build", json={"docs": [{"file_id": "f1", "text": "正文"}]})
    d = c.get("/v2/fence").json()
    assert d["generation"] == 2 and d["revoked"] == ["r9"] and d["count"] == 1


def test_query_drops_fully_revoked_hits(tmp_path):
    """D8：检索命中来源全部被撤权 → 剔除并计数，不返回旧内容。"""
    (tmp_path / "sources.json").write_text(
        '{"c1": [{"file_id": "r9", "locator": "p1"}]}', encoding="utf-8")
    (tmp_path / "fence.json").write_text(
        '{"generation": 1, "revoked": {"r9": {"reason": "REVOKED", "generation": 1}}}',
        encoding="utf-8")

    def builder(docs, root):
        return {"snapshot": str(tmp_path), "chunks": len(docs), "sources": 1}

    class EngineRevoked(FakeEngine):
        save_dir = str(tmp_path)

        def openie_docs(self):
            return [{"idx": "c1", "passage": "块一", "extracted_triples": []}]

        def retrieve(self, query, seeds=None, top_k=3, use_graph=True):
            return {"executed_route": "GRAPH", "reason": "GRAPH_CALLED",
                    "trace": {"graph_calls": 1}, "docs": ["块一"], "hit_count": 1}

    c = TestClient(create_app(engine_factory=lambda: EngineRevoked(), builder=builder))
    c.post("/v2/graph/build", json={"docs": [{"file_id": "r9", "text": "块一"}]})
    d = c.post("/v2/graph/query", json={"query": "q"}).json()
    assert d["hit_count"] == 0
    assert d["dropped_revoked"] == 1
    assert d["fence_generation"] == 1

def test_entities_view_aggregates_store(tmp_path):
    """D4 Tab2：/v2/entities 聚合实体（名/别名/事实/多来源 title 回查）。"""
    import json

    (tmp_path / "openie_results_ner_t.json").write_text(json.dumps({
        "docs": [{"idx": "c1", "passage": "正文", "extracted_entities": ["华东精密", "星航贷"],
                  "extracted_triples": [["华东精密", "拟申请", "星航贷"]]}]
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "sources.json").write_text(
        '{"c1": [{"file_id": "f1", "locator": "p1", "title": "docx-a.docx"}]}',
        encoding="utf-8")

    def builder(docs, root):
        return {"snapshot": str(tmp_path), "chunks": 1, "sources": 1}

    c = TestClient(create_app(engine_factory=lambda: FakeEngine(), builder=builder))
    c.post("/v2/graph/build", json={"docs": [{"file_id": "f1", "text": "正文"}]})
    d = c.get("/v2/entities").json()
    assert d["entity_count"] == 2
    by_name = {e["name"]: e for e in d["entities"]}
    hd = by_name["华东精密"]
    assert hd["facts"][0]["predicate"] == "拟申请"
    assert hd["facts"][0]["object_entity"] == "星航贷"
    assert hd["facts"][0]["sources"][0]["title"] == "docx-a.docx"


def test_status_view_shape(tmp_path, monkeypatch):
    """D4 Tab5：/v2/status 透出 fence/pointer/community/cjk（无指针时字段为空值）。"""
    from graph_engine_adapter import rebuild as _rebuild

    root = tmp_path / "root"
    root.mkdir()
    _rebuild._write_pointer(str(root), {"schema": "x", "dir": "snapshot-1",
                                        "generation": 2, "fencing": 2,
                                        "documents": 1, "dropped_revoked": [],
                                        "built_at": "2026-11-03T00:00:00+0000",
                                        "mode": "FULL"})
    monkeypatch.setenv("LLMKE_V2_ROOT", str(root))
    c = TestClient(create_app(engine_factory=lambda: FakeEngine()))
    d = c.get("/v2/status").json()
    assert d["pointer"]["generation"] == 2
    assert d["pointer"]["fencing"] == 2
    assert d["fence"]["generation"] == 0
    assert "cjk_compat" in d

