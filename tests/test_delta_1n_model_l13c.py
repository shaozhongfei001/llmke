"""P4-L13-C · 请求模型层的 `file_ids`（**仅 hipporag 可跑**：需要 pydantic/fastapi）。

配套 `services/rag-alg/index_data_service/tests/test_delta_1n_l13c.py`（纯函数，双环境）。
这里只验「HTTP 层收不收」：契约 §2.1 要求 `docs[*].file_ids` 是数组，
单值 `file_id` 属于 L9 的实现缺陷，必须被拒（而不是默默当成空 id 建出脏来源）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi（既有环境限制）")
pytest.importorskip("pydantic", reason="同上")

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "services/rag-alg/index_data_service"
if str(IDX) not in sys.path:
    sys.path.insert(0, str(IDX))

from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from graph_engine_adapter import api as A  # noqa: E402


def _client(calls=None):
    calls = calls if calls is not None else []

    def runner(req):
        calls.append(req)
        return {"schema": "llmke.graph-delta.v1", "status": "BUILT", "kb": req.kb,
                "root": "/tmp/fake", "requested_mode": req.requested_mode,
                "effective_mode": "FULL", "snapshot": "/tmp/fake-snapshot"}

    return TestClient(A.create_app(delta_runner=runner)), calls


# --------------------------------------------------------------- 模型层
def test_builddoc_accepts_file_ids_array() -> None:
    doc = A.BuildDoc(file_ids=["290", "291"], text="正文")
    assert doc.file_ids == ["290", "291"]


def test_builddoc_rejects_single_value_file_id() -> None:
    """单值 `file_id` 是 L9 的旧形态：必须被拒，否则 1:N 语义会被静默降级。"""
    with pytest.raises(ValidationError):
        A.BuildDoc(file_id="290", text="正文")


def test_builddoc_rejects_empty_file_ids() -> None:
    with pytest.raises(ValidationError):
        A.BuildDoc(file_ids=[], text="正文")


# --------------------------------------------------------------- 路由层
def test_route_accepts_file_ids_and_passes_them_through() -> None:
    client, calls = _client()
    resp = client.post("/v2/graph/delta", json={
        "kb": "kb_9", "docs": [{"file_ids": ["290", "291"], "text": "正文"}],
        "requested_mode": "auto"})
    assert resp.status_code == 200, resp.text
    assert calls and list(calls[0].docs[0].file_ids) == ["290", "291"]


def test_route_rejects_single_file_id_body() -> None:
    """这正是 C3a 撞到的 422：平台按契约发 `file_ids`，旧模型只认 `file_id`。"""
    client, calls = _client()
    resp = client.post("/v2/graph/delta", json={
        "kb": "kb_9", "docs": [{"file_ids": ["290"], "text": "正文"}]})
    assert resp.status_code == 200

    resp = client.post("/v2/graph/delta", json={
        "kb": "kb_9", "docs": [{"file_id": "290", "text": "正文"}]})
    assert resp.status_code == 422, resp.text
    assert "file_ids" in resp.text
