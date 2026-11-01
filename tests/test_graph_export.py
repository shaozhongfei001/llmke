"""图导出：只测导出策略（排序/过滤/截断/原子写），不加载真实引擎。

用鸭子类型的假图对象，避免把 igraph 拖进单测；真跑（30 节点/109 边）在证据文档里。
"""

import json
import os

import pytest

from graph_engine_adapter.export import export_facts, export_graph


class FakeAttr(dict):
    def attributes(self):
        return dict(self)


class FakeVertex(FakeAttr):
    """引擎里 `vs["name"]` 就是节点 id（entity-<hash>），没有单独的展示名。"""

    def __init__(self, node_id, content=None, hash_id=None):
        super().__init__(name=node_id, content=content, hash_id=hash_id)


class FakeEdge:
    def __init__(self, source, target, weight):
        self.source = source
        self.target = target
        self._attrs = {"weight": weight}

    def attributes(self):
        return dict(self._attrs)


class FakeGraph:
    def __init__(self, vertices, edges):
        self.vs = vertices
        self.es = edges

    def vcount(self):
        return len(self.vs)

    def ecount(self):
        return len(self.es)


def graph_fixture():
    vs = [FakeVertex("entity-b", content="内容乙", hash_id="h2"),
          FakeVertex("entity-a", content="内容甲", hash_id="h1"),
          FakeVertex("entity-c", content="内容丙", hash_id="h3")]
    es = [FakeEdge(1, 0, 2.0), FakeEdge(0, 1, 5.0), FakeEdge(2, 0, 0.5)]
    return FakeGraph(vs, es)


def read_jsonl(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def test_nodes_and_edges_sorted_deterministically(tmp_path):
    out = export_graph(graph_fixture(), str(tmp_path))
    nodes = read_jsonl(os.path.join(str(tmp_path), "nodes.jsonl"))
    edges = read_jsonl(os.path.join(str(tmp_path), "edges.jsonl"))

    assert [n["id"] for n in nodes] == ["entity-a", "entity-b", "entity-c"]
    assert [(e["source"], e["target"]) for e in edges] == [
        ("entity-a", "entity-b"), ("entity-b", "entity-a"), ("entity-c", "entity-b")]
    assert out["nodes"]["count"] == 3 and out["edges"]["count"] == 3


def test_same_input_twice_produces_identical_sha(tmp_path):
    """导出物要能进 diff：顺序不稳就等于每次都"全变了"。"""
    a = export_graph(graph_fixture(), str(tmp_path / "a"))
    b = export_graph(graph_fixture(), str(tmp_path / "b"))
    assert a["nodes"]["sha256"] == b["nodes"]["sha256"]
    assert a["edges"]["sha256"] == b["edges"]["sha256"]


def test_min_weight_drops_weak_edges(tmp_path):
    out = export_graph(graph_fixture(), str(tmp_path), min_weight=1.0)
    edges = read_jsonl(os.path.join(str(tmp_path), "edges.jsonl"))
    assert len(edges) == 2
    assert all(e["weight"] >= 1.0 for e in edges)
    assert out["source_edges"] == 3          # 源图边数如实保留，不假装过滤前就是 2


def test_limit_nodes_keeps_hubs_and_reports_dropped_edges(tmp_path):
    out = export_graph(graph_fixture(), str(tmp_path), limit_nodes=2)
    nodes = read_jsonl(os.path.join(str(tmp_path), "nodes.jsonl"))
    edges = read_jsonl(os.path.join(str(tmp_path), "edges.jsonl"))
    kept = {n["id"] for n in nodes}
    assert len(nodes) == 2
    # 不留下悬空边：留下的边两端都必须在保留集合里
    assert all(e["source"] in kept and e["target"] in kept for e in edges)
    assert out["dropped_edges"] == 3 - len(edges)


def test_atomic_write_leaves_no_tmp_file(tmp_path):
    export_graph(graph_fixture(), str(tmp_path))
    leftovers = [p for p in os.listdir(str(tmp_path)) if p.endswith(".tmp")]
    assert leftovers == []


def test_export_facts_reads_real_key_not_empty_entities(tmp_path):
    """真实落盘是 extracted_triples；extracted_entities 常常是空列表。

    先读错字段的版本导出 2 条事实（全库实为 29 条）却报成功——静默残缺，必须钉住。
    """
    docs = [{"idx": "c1", "passage": "块1", "extracted_entities": [],
             "extracted_triples": [["A", "rel", "B"], ["X", "rel", "Y"]]}]
    path = str(tmp_path / "facts.jsonl")
    out = export_facts(docs, path)
    assert out["facts"] == 2
    assert {r["subject"] for r in read_jsonl(path)} == {"A", "X"}


def test_export_facts_sorted_and_skips_malformed(tmp_path):
    docs = [{"idx": "块2", "extracted_triples": [["B", "rel", "C"], ["A", "rel", "B"]]},
            {"idx": "块1", "extracted_triples": [["A", "rel", "B"], ["坏三元组"]]}]
    path = str(tmp_path / "facts.jsonl")
    out = export_facts(docs, path)
    rows = read_jsonl(path)
    assert out["facts"] == 3
    assert [(r["chunk"], r["subject"]) for r in rows] == [
        ("块1", "A"), ("块2", "A"), ("块2", "B")]


def test_export_does_not_touch_engine(tmp_path):
    """只读：导出不得修改图（误改会污染正在服务的引擎）。"""
    g = graph_fixture()
    before = (g.vcount(), g.ecount())
    export_graph(g, str(tmp_path))
    assert (g.vcount(), g.ecount()) == before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
