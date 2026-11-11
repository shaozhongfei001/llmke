"""P4-L13-A · `POST /v2/fence/revoke`（契约 §3 缺口）、A5。

**只在 hipporag 跑**：需要 fastapi/pydantic。v2 的 skip 单列不计通过。

为什么要这个端点：18096 与 18094 是两个进程，`FenceState` 只在 18094 内存里，
而 `fence.save()` 只在 build/delta 结束时调用 —— 撤权没有别的跨进程路径。
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi（R-0 D-5）")

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter import api as A  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("LLMKE_V2_SNAPSHOT", raising=False)
    return TestClient(A.create_app())


def test_a5_revoke_endpoint_exists_and_revokes(client):
    resp = client.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["999"]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["revoked"] == ["999"]
    assert body["count"] == 1
    assert body["generation"] >= 1
    assert body["advanced"] is True
    assert body["kb"] == "kb_9"


def test_a5_revoke_is_idempotent(client):
    first = client.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["999"]}).json()
    second = client.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["999"]}).json()
    assert second["generation"] == first["generation"], "重复撤权不得重复递增 generation"
    assert second["advanced"] is False
    assert second["revoked"] == ["999"]


def test_a5_get_fence_by_kb_reads_revoked(client):
    client.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["999", "1000"]})
    by_kb = client.get("/v2/fence", params={"kb": "kb_9"}).json()
    assert by_kb["revoked"] == ["1000", "999"]
    assert by_kb["kb"] == "kb_9"

    # 缺省行为不变：不带 kb 仍读无库总览槽（L10 收口字段集）
    default = client.get("/v2/fence").json()
    assert set(default) == {"schema", "generation", "revoked", "count"}


def test_a5_kb_isolation(client):
    client.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["999"]})
    other = client.get("/v2/fence", params={"kb": "kb_other"}).json()
    assert other["revoked"] == [], "撤权必须按库隔离，不得串库"


def test_a5_empty_file_ids_rejected(client):
    resp = client.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": []})
    assert resp.status_code == 422, "空 file_ids 必须拒绝（防误撤整库）"


def test_a5_persisted_false_without_snapshot(client):
    body = client.post("/v2/fence/revoke", json={"kb": "kb_no_snapshot",
                                                 "file_ids": ["1"]}).json()
    assert body["persisted"] is False, "无快照时必须如实标 persisted=false（内存仍生效）"
    assert body["revoked"] == ["1"]
