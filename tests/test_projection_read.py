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
    assert info["mode"] == "legacy" and info["switched"] == []
    # P2-L8：legacy 下通道名就是旧命名空间（新增字段，语义与改动前一致）
    assert info["channel_names"] == {"text": ["kb_9"],
                                     "table_chunks": ["table_chunks_kb_9"],
                                     "table_summary": ["table_summary_kb_9"],
                                     "faq": ["faq_kb_9"]}


def test_snapshot_switches_all_channels_by_explicit_mapping():
    """P2-L8 修正：原断言把错名 `table_chunks_v2cand_kb_9` 固化成契约（错的来源之一）。

    写侧（`index_writer._target_name`）产的是**整名前缀** `v2cand_table_chunks_kb_9`；
    读侧若还靠 `"table_chunks_" + 基础名` 拼接，永远拼不出写侧的名字。
    """
    names, info = resolve(["kb_9"], mode="snapshot", prefix="v2cand")
    assert names == ["v2cand_kb_9"]
    assert info["channel_names"]["table_chunks"] == ["v2cand_table_chunks_kb_9"]
    assert info["channel_names"]["table_summary"] == ["v2cand_table_summary_kb_9"]
    assert info["channel_names"]["faq"] == ["v2cand_faq_kb_9"]
    # 错名必须彻底消失（它是本 loop 要修的缺陷）
    assert "table_chunks_" + names[0] != "v2cand_table_chunks_kb_9"
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
