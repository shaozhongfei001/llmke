"""引擎包装：executed_route 必须来自真实调用痕迹，不能靠"有结果"推断。"""

from graph_engine_adapter.engine_hipporag import EngineRetriever, HippoRAGEngine


class FakeSolution:
    def __init__(self, docs):
        self.docs = docs


class FakeHP:
    """假引擎：只有被调用 graph_search_with_fact_entities 时才算走了图。"""

    def __init__(self, docs, call_graph=True):
        self._docs = docs
        self._call_graph = call_graph
        self.graph_calls = 0
        self.node_name_to_vertex_idx = {"entity-产品甲": 0}
        self.chunk_embedding_store = self

    def get_all_id_to_rows(self):
        return {"chunk-a": {"content": "x"}}

    def graph_search_with_fact_entities(self, *a, **kw):
        self.graph_calls += 1
        return None

    def retrieve(self, queries, num_to_retrieve=3):
        if self._call_graph:
            self.graph_search_with_fact_entities(queries[0])
        return [FakeSolution(self._docs)]


def test_executed_route_graph_when_graph_method_called():
    eng = HippoRAGEngine(hp=FakeHP(["甲", "乙"]), save_dir="/tmp/x")
    out = eng.retrieve("查询", seeds=["entity-产品甲"], top_k=2)
    assert out["executed_route"] == "GRAPH"
    assert out["reason"] == "GRAPH_CALLED"
    assert out["trace"]["graph_calls"] == 1
    assert out["trace"]["seed_hits"] == ["entity-产品甲"]
    assert out["hit_count"] == 2


def test_executed_route_dense_when_graph_not_called():
    eng = HippoRAGEngine(hp=FakeHP(["甲"], call_graph=False), save_dir="/tmp/x")
    out = eng.retrieve("查询")
    assert out["executed_route"] == "DENSE_FALLBACK"
    assert out["reason"] == "GRAPH_NOT_CALLED"
    assert out["hit_count"] == 1          # 有结果也不代表走过图


def test_graph_method_is_restored_after_call():
    hp = FakeHP(["甲"])
    eng = HippoRAGEngine(hp=hp, save_dir="/tmp/x")
    eng.retrieve("查询")
    # 类方法上的包装必须撤掉：实例里不该残留被 trace 的副本
    assert "graph_search_with_fact_entities" not in hp.__dict__
    # 再调一次仍然计数（说明恢复成原方法而不是坏掉）
    before = hp.graph_calls
    eng.retrieve("查询")
    assert hp.graph_calls == before + 1


def test_engine_retriever_records_path_and_route():
    eng = HippoRAGEngine(hp=FakeHP(["甲"]), save_dir="/tmp/x")
    r = EngineRetriever(eng, source_lookup=lambda d: [{"file_id": "333"}])
    hits = r.graph("查询", ["entity-产品甲"], 2)
    assert hits[0]["sources"] == [{"file_id": "333"}]
    assert r.calls[0]["path"] == "graph"
    assert r.calls[0]["executed_route"] == "GRAPH"
