"""P4-L13-C · 缺陷 10（客户端侧）：`post_fence_revoke` 不带 `root` 必须 fail-closed。

**双环境可跑**（不需要 fastapi/pydantic）。
与 `tests/test_fence_revoke_root_l13c.py`（HTTP 层 400）配套：
客户端先拒，HTTP 层再拒 —— 两道都 fail-closed，任何一道漏了都不会写生产。
"""
from __future__ import annotations

import pytest

from ingest_pipeline import graph_client as G
from ingest_pipeline import kb_pipeline as K


def test_post_fence_revoke_without_root_fails_closed(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(G, "_post", lambda *a, **kw: called.append((a, kw)) or {})

    with pytest.raises(K.PipelineRefused) as ei:
        G.post_fence_revoke("kb_9", ["291"], graph_api="http://127.0.0.1:18094")

    assert ei.value.code == "GRAPH_ROOT_MISSING", ei.value.code
    assert not called, "缺 root 时**不得**发出任何 HTTP 请求（否则就是写到生产的那条路径）"


def test_post_fence_revoke_with_blank_root_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(G, "_post", lambda *a, **kw: pytest.fail("不应发请求"))
    with pytest.raises(K.PipelineRefused) as ei:
        G.post_fence_revoke("kb_9", ["291"], root="   ",
                            graph_api="http://127.0.0.1:18094")
    assert ei.value.code == "GRAPH_ROOT_MISSING"


def test_post_fence_revoke_sends_root_in_payload(monkeypatch) -> None:
    seen = {}

    def fake_post(base, path, payload, timeout):
        seen.update({"base": base, "path": path, "payload": payload})
        return {"revoked": ["291"], "count": 1, "generation": 1, "persisted": True}

    monkeypatch.setattr(G, "_post", fake_post)
    body = G.post_fence_revoke("kb_9", ["291"], root="/shadow/graph-root",
                               graph_api="http://127.0.0.1:18094")

    assert seen["payload"]["root"] == "/shadow/graph-root", (
        f"payload 必须带 root，实际 {seen['payload']}")
    assert body["persisted"] is True
