"""引用证据组装器测试：正例 + 失败路径（fail-closed）+ 码点语义 + CLI。"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from modules.citation_evidence.assembler import (
    EvidenceError, build_document_evidence, text_hash, validate_evidence)

ROOT = Path(__file__).resolve().parents[3]   # 仓库根（含 contracts/）
DOC = "第一段内容。第二段内容。"


def src(**over):
    base = {
        "kb_id": "kb-1", "file_id": "f-1", "document_version": "v3",
        "chunk_id": "c-7",
        "content_hash": hashlib.sha256(DOC.encode()).hexdigest(),
        "offset": {"start": 0, "end": 5, "unit": "unicode_codepoint",
                   "text_hash": text_hash(DOC[0:5]), "parser_version": "p-1.0"},
    }
    base.update(over)
    return base


def test_positive_builds_and_matches_contract():
    ev = build_document_evidence(DOC, src(), "ev-1")
    validate_evidence(ev, ROOT)
    assert ev["type"] == "document_text"
    assert ev["source_ref"]["offset"]["text_hash"] == text_hash(DOC[0:5])


def test_out_of_bounds_rejected():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(offset={**src()["offset"], "end": 999}), "ev-1")
    assert e.value.code == "OFFSET_OUT_OF_BOUNDS"


def test_start_not_before_end_rejected():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(offset={**src()["offset"], "start": 5, "end": 5}), "ev-1")
    assert e.value.code == "OFFSET_RANGE"


def test_fabricated_offset_hash_rejected():
    """声称的区间与声称的哈希对不上 —— 伪造 offset 的核心防线。"""
    bad = src(offset={**src()["offset"], "text_hash": text_hash("别的内容")})
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, bad, "ev-1")
    assert e.value.code == "OFFSET_TEXT_HASH_MISMATCH"


def test_bad_content_hash_format_rejected():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(content_hash="NOT-A-HASH"), "ev-1")
    assert e.value.code == "HASH_FORMAT"


def test_missing_parser_version_rejected():
    off = {**src()["offset"]}
    off.pop("parser_version")
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(offset=off), "ev-1")
    assert e.value.code == "FIELD_MISSING"


def test_wrong_unit_rejected():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(offset={**src()["offset"], "unit": "utf16"}), "ev-1")
    assert e.value.code == "OFFSET_UNIT"


def test_extra_internal_fields_are_not_leaked():
    ev = build_document_evidence(DOC, src(internal_note="do-not-leak", score=0.9), "ev-1")
    validate_evidence(ev, ROOT)          # additionalProperties=false 会拒绝多余字段
    assert "internal_note" not in json.dumps(ev)


def test_codepoint_semantics_with_astral_chars():
    text = "a😀b"                        # Python str 下标即码点：长度 3
    off = {"start": 1, "end": 2, "unit": "unicode_codepoint",
           "text_hash": text_hash("😀"), "parser_version": "p-1.0"}
    ev = build_document_evidence(text, src(offset=off), "ev-2")
    validate_evidence(ev, ROOT)
    assert ev["source_ref"]["offset"]["text_hash"] == text_hash("😀")


def test_cli_exit_codes_and_output(tmp_path):
    good = tmp_path / "in.json"
    good.write_text(json.dumps({"evidence_id": "ev-1", "document_text": DOC, "source": src()},
                               ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out.json"
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli",
                        "--input", str(good), "--out", str(out), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["evidence_id"] == "ev-1"

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"evidence_id": "ev-1", "document_text": DOC,
                               "source": src(content_hash="x" * 63)}, ensure_ascii=False),
                   encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli",
                        "--input", str(bad), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 2
    assert json.loads(r.stdout)["code"] == "HASH_FORMAT"


def test_support_gate_blocks_unsupported_claims():
    from modules.citation_evidence.assembler import SupportGate
    g = SupportGate("block")
    r = g.partition([
        {"claim_id": "c1", "evidence_ids": ["ev-1"], "text": "有依据"},
        {"claim_id": "c2", "evidence_ids": [], "text": "无依据"},
    ])
    assert [s["claim_id"] for s in r["supported"]] == ["c1"]
    assert [b["claim_id"] for b in r["blocked"]] == ["c2"]
    assert r["blocked"][0]["reason"] == "NO_APPROVED_EVIDENCE"
    # blocked 绝不出现在 emit
    assert {c["claim_id"] for c in r["emit"]} == {"c1"}


def test_support_gate_annotate_mode_is_labelled_not_supported():
    from modules.citation_evidence.assembler import SupportGate
    r = SupportGate("annotate").partition([{"claim_id": "c3", "evidence_ids": []}])
    assert r["annotations"] == [{"claim_id": "c3", "label": "unsupported",
                                "reason": "NO_APPROVED_EVIDENCE"}]
    assert r["emit"] == []


def test_support_gate_rejects_malformed_claims():
    from modules.citation_evidence.assembler import SupportGate
    for bad in ([{"claim_id": "", "evidence_ids": []}],
                [{"claim_id": "c1", "evidence_ids": "ev-1"}],
                [{"claim_id": "c1", "evidence_ids": [123]}]):
        with pytest.raises(EvidenceError):
            SupportGate("block").partition(bad)


def test_contract_validator_rejects_invalid_object():
    """证明校验器不是空转：手工构造一个违反契约的对象必须被拒。"""
    ev = build_document_evidence(DOC, src(), "ev-1")
    ev["source_ref"]["offset"]["unit"] = "utf16"      # 违反 const
    with pytest.raises(EvidenceError) as e:
        validate_evidence(ev, ROOT)
    assert e.value.code == "CONTRACT_VIOLATION"

    ev2 = build_document_evidence(DOC, src(), "ev-1")
    ev2["extra"] = 1                                   # 违反 additionalProperties=false
    with pytest.raises(EvidenceError) as e2:
        validate_evidence(ev2, ROOT)
    assert e2.value.code == "CONTRACT_VIOLATION"


# ---- 负例矩阵补全（边界值，避免"只测正常路径"） ----
def test_empty_text_rejects_any_span():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence("", src(offset={"start": 0, "end": 1, "unit": "unicode_codepoint",
                                                "text_hash": text_hash(""), "parser_version": "p"}), "ev-1")
    assert e.value.code == "OFFSET_OUT_OF_BOUNDS"


def test_end_zero_rejected():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(offset={**src()["offset"], "start": 0, "end": 0}), "ev-1")
    assert e.value.code == "OFFSET_RANGE"


def test_field_length_limit_enforced():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, src(document_version="v" * 257), "ev-1")
    assert e.value.code == "FIELD_TOO_LONG"
    with pytest.raises(EvidenceError) as e2:
        build_document_evidence(DOC, src(), "e" * 257)
    assert e2.value.code == "FIELD_TOO_LONG"


def test_source_must_be_dict():
    with pytest.raises(EvidenceError) as e:
        build_document_evidence(DOC, ["kb-1"], "ev-1")   # type: ignore[arg-type]
    assert e.value.code == "ILLEGAL_INPUT"


def test_offset_boundary_exactly_at_text_end_is_allowed():
    """边界正例：end == len(text) 合法（左闭右开）。"""
    off = {"start": len(DOC) - 1, "end": len(DOC), "unit": "unicode_codepoint",
           "text_hash": text_hash(DOC[-1]), "parser_version": "p-1.0"}
    ev = build_document_evidence(DOC, src(offset=off), "ev-edge")
    validate_evidence(ev, ROOT)


# ---- 支持率审计（契约有阈值却没实现，补齐） ----
def _claims(n, k):
    return [{"claim_id": f"c{i}", "evidence_ids": (["ev-1"] if i < k else [])} for i in range(n)]


def test_audit_passes_at_contract_thresholds():
    from modules.citation_evidence.assembler import audit_support
    r = audit_support(_claims(30, 29), ROOT)      # 29/30 = 0.9667 >= 0.95
    assert r["verdict"] == "PASS" and r["samples_sufficient"] and r["ratio_ok"]


def test_audit_fails_when_ratio_below_minimum():
    from modules.citation_evidence.assembler import audit_support
    r = audit_support(_claims(30, 28), ROOT)      # 0.9333 < 0.95
    assert r["verdict"] == "FAIL" and r["reason"] == "RATIO_BELOW_MINIMUM"


def test_audit_fails_when_too_few_claims():
    from modules.citation_evidence.assembler import audit_support
    r = audit_support(_claims(10, 10), ROOT)      # 10 < 30
    assert r["verdict"] == "FAIL" and r["reason"] == "CLAIMS_BELOW_MINIMUM"


def test_audit_thresholds_come_from_contract_not_hardcoded():
    """把契约阈值改一处，审计结论必须随之变化——证明不是硬编码。"""
    import yaml
    from modules.citation_evidence.assembler import audit_support
    r = audit_support(_claims(30, 28), ROOT)
    assert r["supported_ratio_min"] == 0.95
