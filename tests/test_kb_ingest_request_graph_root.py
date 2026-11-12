"""P6-L17 · `graph_root` / `graph_api` 必须由请求驱动，而不是启动期绑死的 env 值。

回归背景（STEP2-I 实测）：`_delta_runner` 闭包捕获启动期 `LLMKE_V2_GRAPH_ROOT`；
`IngestRequest.graph_root` 只是声明了字段，service 路径（`plan` / `commit` / `_delta`）
从未消费它，导致 STEP2-F 路径 A 只能靠「改 env + 重启 18096」换图根。

本测试锁定修复后的行为：请求给了就按请求绑定，没给仍回退 env（默认值语义不变），
注入 service 的兼容缝不被破坏。替身零写入、不发网络。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi", reason="需 fastapi/pydantic")
pytest.importorskip("pydantic", reason="同上")

from fastapi.testclient import TestClient  # noqa: E402

import kb_ingest_service as S  # noqa: E402


def _body(**kw):
    base = {"kb": "kb_9", "file_id": 290, "operation": "UPSERT",
            "doc2md_dir": "/doc2md-out"}
    base.update(kw)
    return base


class _FakeService:
    """替身：记录收到的 payload，并短路成 SKIPPED_FRESH（不写任何索引/图）。"""

    def __init__(self, runs):
        self._runs = runs

    def run(self, payload):
        self._runs.append(payload)
        return {"status": "SKIPPED_FRESH", "kb": payload.get("kb")}


@pytest.fixture
def spy(monkeypatch):
    monkeypatch.setenv("LLMKE_V2_GRAPH_ROOT", "/env/FIXED-ROOT")
    binds, runs = [], []

    def fake_build(graph_api=None, graph_root=None):
        binds.append({"graph_api": graph_api, "graph_root": graph_root})
        return _FakeService(runs)

    monkeypatch.setattr(S, "_build_service", fake_build)
    client = TestClient(S.create_app())
    return client, binds, runs


def test_request_graph_root_overrides_startup_env(spy):
    client, binds, _ = spy
    resp = client.post("/kb/ingest", json=_body(graph_root="/req/ROOT-A"))
    assert resp.status_code == 200, resp.text
    assert binds[-1]["graph_root"] == "/req/ROOT-A"
    assert binds[-1]["graph_root"] != "/env/FIXED-ROOT"


def test_two_requests_bind_different_roots(spy):
    client, binds, _ = spy
    client.post("/kb/ingest", json=_body(graph_root="/req/ROOT-A"))
    client.post("/kb/ingest", json=_body(graph_root="/req/ROOT-B"))
    assert [b["graph_root"] for b in binds[-2:]] == ["/req/ROOT-A", "/req/ROOT-B"]


def test_graph_api_is_request_driven_too(spy):
    client, binds, _ = spy
    client.post("/kb/ingest", json=_body(graph_api="http://127.0.0.1:19994",
                                         graph_root="/req/ROOT-C"))
    assert binds[-1] == {"graph_api": "http://127.0.0.1:19994",
                         "graph_root": "/req/ROOT-C"}


def test_omitting_graph_root_keeps_startup_binding(spy):
    """不给 graph_root/graph_api → 不重建 service，保持启动绑定（向后兼容）。"""
    client, binds, runs = spy
    startup_calls = len(binds)
    resp = client.post("/kb/ingest", json=_body())
    assert resp.status_code == 200, resp.text
    assert len(binds) == startup_calls
    assert runs[-1]["graph_root"] is None


def test_injected_service_is_not_replaced(spy):
    """注入 service 的兼容缝：按请求重建只作用于默认构造的 service。"""
    _, binds, _ = spy
    injected_runs = []
    injected = _FakeService(injected_runs)
    client = TestClient(S.create_app(service=injected))
    resp = client.post("/kb/ingest", json=_body(graph_root="/req/ROOT-D"))
    assert resp.status_code == 200, resp.text
    assert injected_runs and injected_runs[-1]["graph_root"] == "/req/ROOT-D"
    assert not any(b["graph_root"] == "/req/ROOT-D" for b in binds)


def test_delta_runner_closure_carries_request_root(monkeypatch):
    """真实 `_build_service`：闭包里的 root 必须等于调用参数，不是 env。"""
    import ingest_pipeline.graph_client as gc

    seen = []
    monkeypatch.setenv("LLMKE_V2_GRAPH_ROOT", "/env/FIXED-ROOT")
    monkeypatch.setattr(
        gc, "post_graph_delta",
        lambda *a, **kw: (seen.append(kw.get("root")) or {"status": "BUILT"}))
    svc = S._build_service(graph_root="/req/ROOT-E")
    plan = SimpleNamespace(kb="kb_9", wanted_docs=[], removed=[],
                           diff={"set_digest": None, "reason": "X"},
                           fallback_reason=None)
    svc._delta(plan)
    assert seen == ["/req/ROOT-E"]
