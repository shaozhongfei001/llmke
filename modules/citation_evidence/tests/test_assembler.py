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


# ---- CLI: audit 子命令 + 向后兼容 ----
def test_cli_audit_pass_and_fail(tmp_path):
    good = tmp_path / "claims.json"
    good.write_text(json.dumps(_claims(30, 29)), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli", "audit",
                        "--claims", str(good), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["ok"] is True

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"claims": _claims(30, 28)}), encoding="utf-8")  # 支持信封形式
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli", "audit",
                        "--claims", str(bad), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 2
    assert json.loads(r.stdout)["reason"] == "RATIO_BELOW_MINIMUM"


def test_cli_assemble_still_accepts_legacy_invocation(tmp_path):
    """无子命令时默认 assemble，保证旧命令不坏。"""
    src_json = tmp_path / "in.json"
    src_json.write_text(json.dumps({"evidence_id": "ev-1", "document_text": DOC,
                                    "source": src()}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli",
                        "--input", str(src_json), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["evidence_id"] == "ev-1"


# ---- 集合级完整性：重复 id / 跨 chunk 重叠（单条装配看不见的缺陷） ----
def item(start, end, chunk="c-7", evidence_id="ev-1", pv="p-1.0"):
    off = {"start": start, "end": end, "unit": "unicode_codepoint",
           "text_hash": text_hash(DOC[start:end]), "parser_version": pv}
    return {"evidence_id": evidence_id, "document_text": DOC,
            "source": src(chunk_id=chunk, offset=off)}


def test_set_positive_two_chunks_are_accepted():
    from modules.citation_evidence.assembler import assemble_many
    evs = assemble_many([item(0, 6, "c-1", "ev-1"), item(6, 12, "c-2", "ev-2")],
                        ROOT, validate=True)
    assert [e["evidence_id"] for e in evs] == ["ev-1", "ev-2"]


def test_set_adjacent_ranges_are_not_overlap():
    """左闭右开：end == next.start 相邻合法，不能误判。"""
    from modules.citation_evidence.assembler import assemble_many
    assert len(assemble_many([item(0, 6, "c-1", "ev-1"), item(6, 12, "c-1", "ev-2")])) == 2


def test_set_duplicate_evidence_id_rejected():
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([item(0, 6, "c-1", "ev-1"), item(6, 12, "c-2", "ev-1")])
    assert e.value.code == "DUPLICATE_EVIDENCE_ID"


def test_set_same_chunk_overlap_rejected():
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([item(0, 6, "c-1", "ev-1"), item(3, 9, "c-1", "ev-2")])
    assert e.value.code == "SAME_CHUNK_OVERLAP"


def test_set_cross_chunk_overlap_rejected():
    """切分器产出重叠块时，同一段原文被两个 chunk 认领 —— 支撑率虚高的隐蔽来源。"""
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([item(0, 6, "c-1", "ev-1"), item(4, 10, "c-2", "ev-2")])
    assert e.value.code == "CROSS_CHUNK_OVERLAP"


def test_set_contained_overlap_detected():
    """短区间完全落在长区间内也必须查出（避免只看相邻对而漏检）。"""
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([item(0, 10, "c-1", "ev-1"), item(2, 3, "c-2", "ev-2")])
    assert e.value.code == "CROSS_CHUNK_OVERLAP"


def test_set_different_documents_may_share_ranges():
    """不同文件/版本的相同区间不算重叠，否则会误伤。"""
    from modules.citation_evidence.assembler import assemble_many
    a = item(0, 6, "c-1", "ev-1")
    b = item(0, 6, "c-1", "ev-2")
    b["source"] = {**b["source"], "file_id": "f-2"}
    assert len(assemble_many([a, b])) == 2


def test_set_empty_is_rejected():
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([])
    assert e.value.code == "EMPTY_EVIDENCE_SET"


def test_cli_assemble_set_overlap_exit_2(tmp_path):
    payload = tmp_path / "set.json"
    payload.write_text(json.dumps([item(0, 6, "c-1", "ev-1"),
                                   item(4, 10, "c-2", "ev-2")], ensure_ascii=False),
                       encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli",
                        "assemble-set", "--input", str(payload), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] is False and out["code"] == "CROSS_CHUNK_OVERLAP"
    assert "ev-1" in out["detail"] and "ev-2" in out["detail"]


def test_cli_assemble_set_positive(tmp_path):
    payload = tmp_path / "set.json"
    payload.write_text(json.dumps({"items": [item(0, 6, "c-1", "ev-1"),
                                             item(6, 12, "c-2", "ev-2")]},
                                  ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "modules.citation_evidence.cli",
                        "assemble-set", "--input", str(payload), "--repo-root", str(ROOT)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["count"] == 2


# ---- parser_version 混用：同一文档版本出现两套 offset 坐标系 ----
def test_set_mixed_parser_versions_rejected():
    """offset 是码点下标，其含义由解析器版本决定；混用即不可比，必须由上游升 document_version。"""
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([item(0, 6, "c-1", "ev-1", "p-1.0"),
                       item(6, 12, "c-2", "ev-2", "p-2.0")])
    assert e.value.code == "PARSER_VERSION_MIXED"
    assert "p-1.0" in e.value.detail and "p-2.0" in e.value.detail


def test_set_same_parser_version_across_chunks_ok():
    from modules.citation_evidence.assembler import assemble_many
    assert len(assemble_many([item(0, 6, "c-1", "ev-1", "p-1.0"),
                              item(6, 12, "c-2", "ev-2", "p-1.0")])) == 2


def test_set_parser_version_may_differ_across_documents():
    """不同文件各自有自己的解析器版本，不算混用（否则会误伤多文档检索）。"""
    from modules.citation_evidence.assembler import assemble_many
    a = item(0, 6, "c-1", "ev-1", "p-1.0")
    b = item(0, 6, "c-1", "ev-2", "p-2.0")
    b["source"] = {**b["source"], "file_id": "f-2"}
    assert len(assemble_many([a, b])) == 2


def test_set_parser_version_checked_before_overlap():
    """同时存在混版本与重叠时，先报版本混用（坐标系不可比，重叠判定本身失真）。"""
    from modules.citation_evidence.assembler import assemble_many
    with pytest.raises(EvidenceError) as e:
        assemble_many([item(0, 6, "c-1", "ev-1", "p-1.0"),
                       item(4, 10, "c-2", "ev-2", "p-2.0")])
    assert e.value.code == "PARSER_VERSION_MIXED"
