"""P3-L10 · `api.py` 层断言：per-kb state 隔离（K1）/ 路由 fencing 递增（K2）/ 字段不变（K4）。

`api.py` 依赖 fastapi + pydantic，故本文件**只在 hipporag-toolenv 真跑**；
`llmke-v2-toolenv` 下 `importorskip` 跳过（既有环境限制，不计入通过数）。
`rebuild.py` 层的决定性验证在 `services/rag-alg/index_data_service/tests/test_fencing_l10.py`（v2 可跑）。

不启停 18094、不起监听端口：`TestClient` 是进程内 ASGI。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi（既有环境限制）")
pytest.importorskip("pydantic", reason="llmke-v2-toolenv 无 pydantic（既有环境限制）")

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "services/rag-alg/index_data_service"
if str(IDX) not in sys.path:
    sys.path.insert(0, str(IDX))

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter import api as A  # noqa: E402

# K4 基线：改造**前**实测的字段集（改造后必须逐字不变）
HEALTH_KEYS = {"cjk_compat", "community", "edges", "facts", "nodes", "schema",
               "snapshot", "status"}
STATUS_KEYS = {"cjk_compat", "community", "fence", "kb", "pointer", "schema", "snapshot"}
QUERY_KEYS = {"citations", "docs", "dropped_revoked", "executed_route", "fence_generation",
              "graph_enabled", "hit_count", "query", "reason", "schema", "seeds",
              "seeds_source", "sources_available", "trace"}
GLOBAL_KEYS = {"answer", "citation_check", "citations", "communities", "kb", "query",
               "reason", "schema", "sections", "snapshot", "status"}


class FakeEngine:
    """与 `tests/test_graph_api.py` 同形状：`retrieve` 必须吃 `use_graph`。"""

    def __init__(self, snapshot=None, *, save_dir=None, **_kwargs):
        # `_default_build` 用 `HippoRAGEngine(save_dir=...)`；`_load_engine` 传位置参
        self.save_dir = str(save_dir or snapshot)
        self.hp = None
        self.calls = []

    def openie_docs(self):
        return [{"idx": "c1", "passage": "甲", "extracted_triples": [["a", "r", "b"]]}]

    def build(self, texts):                     # 供 `_default_build` 的 full_build 用
        return {"chunks": len(texts)}

    def retrieve(self, query, seeds=None, top_k=3, use_graph=True):
        self.calls.append(query)
        return {"executed_route": "GRAPH", "reason": "GRAPH_CALLED",
                "trace": {"graph_calls": 1}, "docs": [f"{Path(self.save_dir).parent.name}:块"]}


def _make_root(tmp_path, kbs=("kb_A", "kb_B")):
    root = tmp_path / "api-root"
    for kb in kbs:
        snap = root / kb / "snapshot-x"
        snap.mkdir(parents=True)
        (snap / "kb.json").write_text(json.dumps({"kb_id": kb}), encoding="utf-8")
        (snap / "sources.json").write_text("{}", encoding="utf-8")
        (root / kb / "current.json").write_text(
            json.dumps({"dir": str(snap), "fencing": 1, "generation": 0,
                        "fingerprint": {"files": []}}), encoding="utf-8")
    return root


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    root = _make_root(tmp_path)
    monkeypatch.setenv("LLMKE_V2_ROOT", str(root))
    monkeypatch.delenv("LLMKE_V2_SNAPSHOT", raising=False)
    made = {}

    def fake_load(snapshot=None):
        eng = FakeEngine(snapshot)
        made[str(snapshot)] = eng
        return eng

    monkeypatch.setattr(A, "_load_engine", fake_load)
    app = A.create_app()
    return app, root, made


# --------------------------------------------------------------------------- K1
def test_k1_state_is_per_kb(app_env) -> None:
    """反例 R-1：`state` 仍全局单槽 → 跨 kb 污染，本断言 FAIL。"""
    app, root, made = app_env
    client = TestClient(app)

    client.post("/v2/graph/query", json={"query": "甲", "kb": "kb_A"})
    client.post("/v2/graph/query", json={"query": "乙", "kb": "kb_B"})
    client.post("/v2/graph/query", json={"query": "丙", "kb": "kb_A"})

    states = getattr(app.state, "states", None)
    assert states is not None, "create_app 必须把 per-kb 槽暴露为 app.state.states 供核对"
    assert {"kb_A", "kb_B"} <= set(states), f"缺少 per-kb 槽：{set(states)}"
    a, b = states["kb_A"], states["kb_B"]
    assert a is not b
    assert a["engine"] is not b["engine"], "两个库共用了同一个 engine 对象"
    assert a["snapshot"] != b["snapshot"]
    assert str(a["snapshot"]).endswith("kb_A/snapshot-x")
    assert str(b["snapshot"]).endswith("kb_B/snapshot-x")
    # 查完 B 之后，A 的槽不得被 B 覆盖
    assert str(a["snapshot"]).endswith("kb_A/snapshot-x")


def test_k1_query_returned_data_belongs_to_requested_kb(app_env) -> None:
    """行为层：A→B→A 之后，第三次查询必须仍返回 A 的引擎产物（不是 B 的）。"""
    app, root, made = app_env
    client = TestClient(app)
    client.post("/v2/graph/query", json={"query": "甲", "kb": "kb_A"})
    client.post("/v2/graph/query", json={"query": "乙", "kb": "kb_B"})
    third = client.post("/v2/graph/query", json={"query": "丙", "kb": "kb_A"}).json()
    payload = json.dumps(third["docs"], ensure_ascii=False)
    assert "kb_A:" in payload, third["docs"]
    assert "kb_B:" not in payload, "A 库的查询返回了 B 库的块（跨库污染）"


# --------------------------------------------------------------------------- K2（路由层）
def test_k2_build_increments_fencing_across_two_builds(app_env, monkeypatch) -> None:
    """反例 R-2：`_default_build` 写死 `fencing=1` → 两次建图 fencing 都为 1，本断言 FAIL。

    这里跑**真实** `_default_build`（只把引擎换成替身），因此覆盖的正是线上建图那条路。
    """
    from graph_engine_adapter import engine_hipporag as EH

    app, root, made = app_env
    monkeypatch.setattr(EH, "HippoRAGEngine", FakeEngine)
    monkeypatch.setattr(A, "_ensure_cjk_compat", lambda: {"installed": False})
    client = TestClient(app)

    body = {"kb": "kb_A", "docs": [{"file_ids": ["A"], "text": "甲", "locator": "chunk=0"}]}
    r1 = client.post("/v2/graph/build", json=body)
    assert r1.status_code == 200, r1.text
    f1 = json.loads((root / "kb_A" / "current.json").read_text(encoding="utf-8"))["fencing"]

    r2 = client.post("/v2/graph/build", json=body)
    assert r2.status_code == 200, r2.text
    f2 = json.loads((root / "kb_A" / "current.json").read_text(encoding="utf-8"))["fencing"]

    assert f1 >= 1, f"首次建图 fencing 必须 >= 1（or-0 地雷），实际 {f1}"
    assert f2 > f1, f"第二次建图 fencing 必须严格递增：{f1} -> {f2}"
    # /v2/status 回显必须与指针一致
    st = client.get("/v2/status?kb=kb_A").json()
    assert st["pointer"]["fencing"] == f2


# --------------------------------------------------------------------------- K4
def test_k4_endpoint_fields_unchanged(app_env) -> None:
    app, root, made = app_env
    client = TestClient(app)
    health = client.get("/health").json()
    status = client.get("/v2/status?kb=kb_A").json()
    query = client.post("/v2/graph/query", json={"query": "甲", "kb": "kb_A"}).json()
    glob = client.post("/v2/graph/global", json={"question": "甲", "kb": "kb_A"}).json()

    assert set(health) == HEALTH_KEYS
    assert set(status) == STATUS_KEYS
    assert set(query) == QUERY_KEYS
    assert set(glob) == GLOBAL_KEYS
    assert set(status["fence"]) == {"generation", "revoked"}
    assert set(status["pointer"]) == {"generation", "fencing", "built_at", "documents",
                                     "dropped_revoked"}


def test_k4_same_kb_same_result_as_before(app_env) -> None:
    """同一 kb 重复查询结果一致（state 结构改动不改变可观测行为）。"""
    app, root, made = app_env
    client = TestClient(app)
    first = client.post("/v2/graph/query", json={"query": "甲", "kb": "kb_A"}).json()
    second = client.post("/v2/graph/query", json={"query": "甲", "kb": "kb_A"}).json()
    assert first["docs"] == second["docs"]
    assert first["executed_route"] == second["executed_route"]
    assert first["fence_generation"] == second["fence_generation"]


NOT_BUILT_KEYS = {"schema", "kb", "query", "status", "reason", "hit_count", "docs",
                  "citations", "sources_available"}


def test_k4_unknown_kb_still_reports_not_built(app_env) -> None:
    """未建图的库仍返回 NOT_BUILT（字段集是它自己的那套，与正常查询不同）。"""
    app, root, made = app_env
    client = TestClient(app)
    out = client.post("/v2/graph/query", json={"query": "甲", "kb": "kb_none"}).json()
    assert out["status"] == "NOT_BUILT"
    assert set(out) == NOT_BUILT_KEYS
