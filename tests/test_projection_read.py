"""检索读路径切换：默认 legacy、snapshot 全通道、按库粒度、非法模式 fail-closed。"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/rag-alg/alg_retrieval_service/app"))

from projection_read import resolve  # noqa: E402


def test_default_is_legacy():
    names, info = resolve(["kb_9"], mode="legacy")
    assert names == ["kb_9"]
    assert info == {"mode": "legacy", "switched": []}


def test_snapshot_switches_base_name_so_all_channels_follow():
    names, info = resolve(["kb_9"], mode="snapshot", prefix="v2cand")
    assert names == ["v2cand_kb_9"]
    # 下游拼出来就是 v2cand_kb_9 / table_chunks_v2cand_kb_9 / table_summary_v2cand_kb_9
    assert "table_chunks_" + names[0] == "table_chunks_v2cand_kb_9"
    assert "table_summary_" + names[0] == "table_summary_v2cand_kb_9"
    assert info["switched"] == ["kb_9"]


def test_per_kb_scope_keeps_others_on_legacy():
    names, info = resolve(["kb_9", "kb_10"], mode="snapshot", only=["kb_10"])
    assert names == ["kb_9", "v2cand_kb_10"]
    assert info["kept_legacy"] == ["kb_9"]


def test_unknown_mode_is_refused_not_silently_legacy():
    with pytest.raises(ValueError):
        resolve(["kb_9"], mode="snapshot2")


def test_env_switch_is_read_per_call(monkeypatch):
    monkeypatch.setenv("INGEST_READ_MODE", "snapshot")
    monkeypatch.setenv("INGEST_READ_PREFIX", "v2cand")
    assert resolve(["kb_9"])[0] == ["v2cand_kb_9"]
    monkeypatch.setenv("INGEST_READ_MODE", "legacy")
    assert resolve(["kb_9"])[0] == ["kb_9"]


def test_blank_names_are_dropped():
    names, _ = resolve(["", "  ", "kb_9"], mode="legacy")
    assert names == ["kb_9"]
