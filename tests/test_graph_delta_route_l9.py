"""P3-L9 · J1 · `POST /v2/graph/delta` 路由与请求校验（**仅 hipporag-toolenv 可跑**）。

`llmke-v2-toolenv` 缺 fastapi / pydantic / starlette（既有环境限制，非本 loop 引入），
所以本文件用 `importorskip`：在 v2 环境**跳过**而不是报错——否则 "v2 主口径全绿"
就变成假绿。J2/J3/J4/J5/J8 的覆盖在 `services/rag-alg/index_data_service/tests/test_delta_build_l9.py`。

**不启停 18094、不起监听端口**：`TestClient` 是进程内 ASGI 调用。
"""
from __future__ import annotations

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


def _client(record=None):
    """注入 delta_runner 替身：校验失败时**不该**调用到它。"""
    calls = record if record is not None else []

    def runner(req):
        calls.append(req)
        return {"schema": "llmke.graph-delta.v1", "status": "BUILT", "kb": req.kb,
                "requested_mode": req.requested_mode, "effective_mode": "DELTA",
                "canary_source": "default->delta", "snapshot": "/tmp/fake-snapshot"}

    return TestClient(A.create_app(delta_runner=runner)), calls


def _doc(fid="A", text="甲"):
    # 契约 §2.1：docs 每项用 `file_ids` 数组（1:N 同文异源）；L9 原来写单值 `file_id`，
    # 是「两侧单测各自绿、跨进程一跑就 422」的根源（P4-L13-C 实测）。
    fids = [fid] if isinstance(fid, str) else list(fid)
    return {"file_ids": fids, "text": text, "locator": "chunk=0;f=A"}


# --------------------------------------------------------------------------- 路由存在性
def test_j1_route_exists() -> None:
    app = A.create_app(delta_runner=lambda req: {"status": "BUILT", "kb": req.kb})
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/v2/graph/delta" in paths
    # 既有 8 条不得因本 loop 消失（D-8：不改现有路由行为）
    for path in ("/health", "/v2/graph/build", "/v2/graph/query", "/v2/entities",
                 "/v2/status", "/v2/fence", "/v2/graph/view", "/v2/graph/global"):
        assert path in paths, path


def test_j1_valid_request_returns_payload() -> None:
    client, calls = _client()
    resp = client.post("/v2/graph/delta",
                       json={"kb": "kb_9", "docs": [_doc()], "requested_mode": "auto"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "BUILT"
    assert body["requested_mode"] == "auto"
    assert len(calls) == 1 and calls[0].kb == "kb_9"


# --------------------------------------------------------------------------- 校验（R-1）
def test_j1_unknown_mode_rejected_422() -> None:
    client, calls = _client()
    resp = client.post("/v2/graph/delta",
                       json={"kb": "kb_9", "docs": [_doc()], "requested_mode": "bogus"})
    assert resp.status_code == 422
    assert calls == []


def test_j1_full_requires_fallback_reason() -> None:
    """R-1：`requested_mode=full` 缺 `fallback_reason` → 422，且不调用 runner。"""
    client, calls = _client()
    resp = client.post("/v2/graph/delta",
                       json={"kb": "kb_9", "docs": [_doc()], "requested_mode": "full"})
    assert resp.status_code == 422
    assert "fallback_reason" in resp.text
    assert calls == []


def test_j1_full_with_reason_passes_validation() -> None:
    client, calls = _client()
    resp = client.post("/v2/graph/delta",
                       json={"kb": "kb_9", "docs": [_doc()], "requested_mode": "full",
                             "fallback_reason": "delta 基线缺失，人工确认全量"})
    assert resp.status_code == 200
    assert len(calls) == 1


def test_j1_docs_is_required() -> None:
    """`docs` 必填（TL D-10 修正①）：漏传不能被当成"建空图"。"""
    client, calls = _client()
    resp = client.post("/v2/graph/delta", json={"kb": "kb_9"})
    assert resp.status_code == 422
    assert calls == []


def test_j1_docs_must_not_be_empty_list_semantically() -> None:
    """空的 `docs` 能过 pydantic，但编排层必拒绝（`DOCS_EMPTY` → 422，不建空图）。"""
    client = TestClient(A.create_app())      # 用真实 delta_build（不注入替身）
    resp = client.post("/v2/graph/delta", json={"kb": "kb_9", "docs": []})
    assert resp.status_code == 422
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["reason"] == "DOCS_EMPTY"


def test_j1_kb_is_required() -> None:
    client, calls = _client()
    resp = client.post("/v2/graph/delta", json={"docs": [_doc()]})
    assert resp.status_code == 422
    assert calls == []


# --------------------------------------------------------------------------- 状态码映射
def test_j1_rejected_maps_to_4xx_and_keeps_payload() -> None:
    def runner(req):
        return {"schema": "llmke.graph-delta.v1", "status": "REJECTED", "kb": req.kb,
                "reason": "NO_BASELINE_SNAPSHOT", "requested_mode": req.requested_mode,
                "effective_mode": "DELTA"}

    client = TestClient(A.create_app(delta_runner=runner))
    resp = client.post("/v2/graph/delta",
                       json={"kb": "kb_9", "docs": [_doc()], "requested_mode": "delta"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "REJECTED" and body["reason"] == "NO_BASELINE_SNAPSHOT"


def test_j1_skipped_fresh_is_200() -> None:
    def runner(req):
        return {"schema": "llmke.graph-delta.v1", "status": "SKIPPED_FRESH", "kb": req.kb,
                "reason": "OK", "requested_mode": req.requested_mode,
                "effective_mode": "SKIPPED"}

    client = TestClient(A.create_app(delta_runner=runner))
    resp = client.post("/v2/graph/delta", json={"kb": "kb_9", "docs": [_doc()]})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SKIPPED_FRESH"


def test_j1_failed_maps_to_500() -> None:
    def runner(req):
        return {"schema": "llmke.graph-delta.v1", "status": "FAILED", "kb": req.kb,
                "reason": "RebuildFailed: boom", "requested_mode": req.requested_mode}

    client = TestClient(A.create_app(delta_runner=runner))
    resp = client.post("/v2/graph/delta", json={"kb": "kb_9", "docs": [_doc()]})
    assert resp.status_code == 500
    assert "boom" in resp.json()["reason"]
