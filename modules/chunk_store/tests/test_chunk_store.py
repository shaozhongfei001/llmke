"""分块存储：单元用例（不做 IO）。"""
import hashlib

import pytest

from modules.chunk_store import (ChunkError, build_chunk, check_chunk_set, text_hash,
                                 to_evidence_source)
from modules.citation_evidence.assembler import build_document_evidence, validate_evidence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = "第一段内容。第二段内容。"
CH = hashlib.sha256(DOC.encode()).hexdigest()


def chunk(start, end, idx=0, cid="ch-1", pv="p-1.0", strat="S1", text=None):
    return build_chunk(DOC, chunk_id=cid, kb_id="kb-1", file_id="f-1",
                       document_version="v3", chunk_index=idx, start=start, end=end,
                       content_hash=CH, parser_version=pv, chunk_strategy=strat,
                       declared_text_hash=text)


def test_chunk_slices_by_codepoint():
    c = chunk(0, 6)
    assert c["text"] == DOC[0:6]
    assert c["text_hash"] == text_hash(DOC[0:6])
    assert c["offset"]["unit"] == "unicode_codepoint"


def test_astral_char_counts_as_one_codepoint():
    text = "a😀b"
    c = build_chunk(text, chunk_id="c", kb_id="k", file_id="f", document_version="v",
                    chunk_index=0, start=1, end=2, content_hash=CH,
                    parser_version="p", chunk_strategy="s")
    assert c["text"] == "😀"


def test_declared_hash_mismatch_rejected():
    with pytest.raises(ChunkError) as e:
        chunk(0, 6, text="0" * 64)
    assert e.value.code == "TEXT_HASH_MISMATCH"


def test_bounds_and_range_checked():
    for start, end, code in ((0, 999, "OFFSET_OUT_OF_BOUNDS"), (5, 5, "OFFSET_RANGE"),
                             (-1, 3, "OFFSET_RANGE")):
        with pytest.raises(ChunkError) as e:
            chunk(start, end)
        assert e.value.code == code


def test_chunk_converts_to_evidence_and_passes_contract():
    """关键链路：分块直接产出证据的 source，并过冻结契约校验。"""
    c = chunk(0, 6)
    ev = build_document_evidence(DOC, to_evidence_source(c), "ev-1")
    validate_evidence(ev, ROOT)
    assert ev["source_ref"]["offset"]["text_hash"] == c["text_hash"]


def test_set_rejects_overlap_and_duplicate_index():
    with pytest.raises(ChunkError) as e:
        check_chunk_set([chunk(0, 6, idx=0, cid="a"), chunk(4, 10, idx=1, cid="b")])
    assert e.value.code == "CHUNK_OVERLAP"

    with pytest.raises(ChunkError) as e2:
        check_chunk_set([chunk(0, 6, idx=0, cid="a"), chunk(6, 12, idx=0, cid="b")])
    assert e2.value.code == "DUPLICATE_CHUNK_INDEX"


def test_set_rejects_mixed_versions():
    with pytest.raises(ChunkError) as e:
        check_chunk_set([chunk(0, 6, idx=0, cid="a", pv="p-1.0"),
                         chunk(6, 12, idx=1, cid="b", pv="p-2.0")])
    assert e.value.code == "PARSER_VERSION_MIXED"

    with pytest.raises(ChunkError) as e2:
        check_chunk_set([chunk(0, 6, idx=0, cid="a", strat="S1"),
                         chunk(6, 12, idx=1, cid="b", strat="S2")])
    assert e2.value.code == "CHUNK_STRATEGY_MIXED"


def test_adjacent_chunks_allowed():
    check_chunk_set([chunk(0, 6, idx=0, cid="a"), chunk(6, 12, idx=1, cid="b")])
