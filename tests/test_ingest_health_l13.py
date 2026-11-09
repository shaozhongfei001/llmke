"""P4-L13-B · `/health` 的 liveness / readiness 分离（TL 15:2x 三条硬约束）。

背景：A 段把写入端点改成**惰性 fail-closed**（未配置时首次写入即拒），
这个方案的前提是「有可观测信号」。没有信号的话，惰性就降级成
「静默带病运行」，比构造期 fail-fast 更差。

判据（TL 明确要求，且防 watchdog 死循环）：
- `/health` **HTTP 恒 200**（liveness）—— 返 5xx 会让 watchdog 反复杀掉正常进程；
- readiness 写在 body：`write_targets.configured=false` ⇒ `status="degraded"`；
- 启动自检脚本读 `write_targets.configured` 并 `exit 1`（见 `platform/r12/bin/r12-kb-ingest-start.sh`）。

**只在 hipporag 跑**（需要 fastapi/pydantic）。
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi/pydantic")

from fastapi.testclient import TestClient  # noqa: E402

import kb_ingest_service as S  # noqa: E402

WRITE_ENVS = ("LLMKE_ES_BASE_URL", "LLMKE_MILVUS_BASE_URL",
              "LLMKE_ALLOW_DEFAULT_WRITE_TARGET")


@pytest.fixture()
def clean_env(monkeypatch):
    for key in WRITE_ENVS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_health_is_degraded_when_write_targets_missing(clean_env):
    client = TestClient(S.create_app(service=object()))
    resp = client.get("/health")

    assert resp.status_code == 200, "liveness 必须恒 200（否则 watchdog 会杀掉正常进程）"
    body = resp.json()
    assert body["write_targets"]["configured"] is False
    assert body["status"] == "degraded", "写入端点未配置却报 ok = 静默带病运行"
    assert set(body["write_targets"]) >= {"es", "milvus", "allow_default", "configured", "env"}


def test_health_is_ok_when_write_targets_configured(clean_env):
    clean_env.setenv("LLMKE_ES_BASE_URL", "http://es:19527")
    clean_env.setenv("LLMKE_MILVUS_BASE_URL", "http://mv:19526")
    client = TestClient(S.create_app(service=object()))
    body = client.get("/health").json()

    assert body["write_targets"]["configured"] is True
    assert body["status"] == "ok"


def test_health_allow_default_switch_marks_configured(clean_env):
    clean_env.setenv("LLMKE_ALLOW_DEFAULT_WRITE_TARGET", "1")
    body = TestClient(S.create_app(service=object())).get("/health").json()
    assert body["write_targets"]["allow_default"] is True
    assert body["write_targets"]["configured"] is True
    assert body["status"] == "ok"


def test_health_does_not_leak_secrets(clean_env):
    body = TestClient(S.create_app(service=object())).get("/health").json()
    text = repr(body)
    for key in ("SECRET", "PASSWORD", "TOKEN"):
        assert key not in text.upper()
    assert os.environ.get("LLMKE_ES_BASE_URL") is None
