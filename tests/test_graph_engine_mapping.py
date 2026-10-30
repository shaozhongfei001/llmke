"""C1：native_id ↔ input_unit ↔ SourceRef 映射（不依赖 hipporag/torch）。"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from graph_engine_adapter import InputUnit, SourceMap, input_unit_id, native_key, units_from_chunks  # noqa: E402


def _unit(text, *, art="a" * 64, seq=0, file_id="333", source="r12-rag/kb_9/x.docx/V0/x.docx"):
    return InputUnit(text, content_uid="c" * 64, parse_artifact_id=art, seq=seq,
                     source_ref={"file_id": file_id, "source": source, "offset": [[0, 10]]})


def test_same_text_from_two_sources_keeps_both_refs():
    """HippoRAG 按内容给 chunk 定 id；同文两份来源必须在映射表里都留着。"""
    sm = SourceMap()
    sm.add(_unit("同一段正文", art="a1", seq=0, file_id="333", source="k/x.docx"))
    sm.add(_unit("同一段正文", art="a2", seq=0, file_id="334", source="k/y.docx"))
    key = native_key("同一段正文")
    assert len(sm.units_for(key)) == 2                  # 引擎侧只会有 1 个 chunk
    refs = sm.sources_for(key)
    assert {r["file_id"] for r in refs} == {"333", "334"}   # 来源不丢
    assert sm.stats()["shared_chunks"] == 1
    assert sm.stats()["max_sources_per_chunk"] == 2


def test_input_unit_id_is_stable_and_engine_agnostic():
    first = input_unit_id("a" * 64, 3)
    assert first == input_unit_id("a" * 64, 3)
    assert first != input_unit_id("a" * 64, 4)
    assert first != input_unit_id("b" * 64, 3)          # 换快照必须换身份


def test_same_unit_twice_is_idempotent_but_content_change_is_refused():
    sm = SourceMap()
    sm.add(_unit("正文甲"))
    sm.add(_unit("正文甲"))                              # 幂等
    assert sm.stats()["units"] == 1
    with pytest.raises(ValueError):
        sm.add(_unit("正文乙"))                          # 同 id 不同正文 = 快照被改坏


def test_roundtrip_json_preserves_identity_and_null_sources():
    sm = SourceMap().extend([_unit("甲", seq=0), _unit("乙", seq=1)])
    payload = sm.to_json()
    again = SourceMap.from_json(payload)
    assert set(again._by_unit) == set(sm._by_unit)
    assert again.stats() == sm.stats()


def test_from_json_rejects_tampered_id():
    sm = SourceMap().extend([_unit("甲")])
    payload = sm.to_json()
    payload["units"][0]["input_unit_id"] = "0" * 64
    with pytest.raises(ValueError):
        SourceMap.from_json(payload)


def test_units_from_projection_chunks_keep_channel_and_offsets():
    chunks = [
        {"page_content": "正文块", "metadata": {
            "file_id": "999011", "chunk_index": 0, "parse_artifact_id": "a" * 64,
            "content_uid": "c" * 64, "channel": "text", "source": "k/a.docx/V0/a.docx",
            "offset": [[0, 12]]}},
        {"page_content": "| 指标 | 值 |", "metadata": {
            "file_id": "999011", "chunk_index": 17, "parse_artifact_id": "a" * 64,
            "content_uid": "c" * 64, "channel": "table", "source": "k/a.docx/V0/a.docx",
            "table_id": "t1"}},
    ]
    units = units_from_chunks(chunks)
    assert [u.channel for u in units] == ["text", "table"]
    assert units[0].source_ref["offset"] == [[0, 12]]
    assert units[1].source_ref["table_id"] == "t1"       # 表格不冒充正文来源
    assert all(u.parse_artifact_id == "a" * 64 for u in units)
