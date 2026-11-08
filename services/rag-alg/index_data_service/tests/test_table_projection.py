"""P1-L5 · T-D2MD-05 反例与断言（P1-L5-PLAN.md §三，TL 03:4x 裁定后）。

E1 两类表格载荷与线上形状对齐 / E2 `_table_pk` 稳定命中且不撞号 /
E3 span 不对齐 fail-closed / E4 投影确定性 / E5 不切模式；R-1~R-6 对应反例。

**离线**：不启停服务、不写线上 ES/Milvus/DB/18094、不切 INGEST_PROJECTION_MODE。
线上真值（38 个 metadata 键 / 2 个 pk）已固化在 fixtures/p1_l5/，测试不依赖在线服务。
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]  # /home/szf/data/dev/llmke-v2
sys.path.insert(0, str(ROOT / "services/rag-alg/index_data_service"))

from ingest_pipeline import kb_pipeline as K  # noqa: E402
from ingest_pipeline import summary as SUM  # noqa: E402
from parse_artifact import store as S  # noqa: E402
from rag_projection import projection as P  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p1_l5"
TRUTH = json.loads(
    (FIXTURES / "online_table_chunk_metadata_keys.json").read_text(encoding="utf-8")
)
ONLINE_KEYS = set(TRUTH["metadata_keys"])
ONLINE_PK = TRUTH["online_pk_truth"]

CONTENT_UID = "a" * 64
SHA256 = "b" * 64
TEXT = "说明如下。\n\n表格内容见 IR。\n"
FIXED_NOW = "2026-11-08 00:00:00"


# --------------------------------------------------------------------------- 现场 fixture
def _ir() -> dict:
    """含合并单元格（colspan=2）+ 图片（figure）+ 表格的 IR fixture。"""
    para = "说明如下。"
    start = TEXT.index(para)
    return {
        "schema_version": "document-ir/1.0",
        "document_uid": "doc-p1l5",
        "content_uid": CONTENT_UID,
        "sha256": SHA256,
        "source_vault_path": None,
        "provenance": {"parser_name": "mineru", "ir_source": "mineru_content_list",
                       "generated_at": FIXED_NOW},
        "page_count": 1,
        "coordinate_system": {"unit": "pixel"},
        "blocks": [
            {"block_id": "b0001", "type": "paragraph", "page_no": 1, "bbox": None,
             "reading_order": 0, "confidence": None,
             "content_ref": {"kind": "text_span", "source": "parsed_text.md",
                             "start_offset": start, "end_offset": start + len(para),
                             "text": para},
             "attrs": {}},
            {"block_id": "b0002", "type": "table", "page_no": 1, "bbox": None,
             "reading_order": 1, "confidence": None,
             "content_ref": {"kind": "table_ref", "table_id": "t001"},
             "attrs": {}},
        ],
        "tables": [{
            "table_id": "t001", "block_id": "b0002", "page_no": 1, "bbox": None,
            "html": None, "n_rows": 2, "n_cols": 2,
            "cells": [
                {"row": 0, "col": 0, "rowspan": 1, "colspan": 2,
                 "is_header": True, "text": "指标", "bbox": None},
                {"row": 1, "col": 0, "rowspan": 1, "colspan": 1,
                 "is_header": False, "text": "日均存款", "bbox": None},
                {"row": 1, "col": 1, "rowspan": 1, "colspan": 1,
                 "is_header": False, "text": "100", "bbox": None},
            ],
            "caption_block_id": None, "confidence": None,
        }],
        # 图片项：asset_path=None 使 _check_ir 不要求资产对齐（本 loop 不产出 figure 载荷）
        "figures": [{
            "figure_id": "f001", "block_id": "b0003", "page_no": 1, "bbox": None,
            "asset_path": None, "asset_sha256": None, "ocr_text": None,
            "caption": "图 1 示意", "caption_block_id": None,
            "image_quality_score": None, "confidence": None,
        }],
        "reading_order": ["b0001", "b0002"],
        "stats": {"block_count": 2, "table_count": 1, "figure_count": 1,
                  "blocks_without_bbox": 2, "blocks_low_confidence": 0},
    }


def _artifact(text: str) -> dict:
    return {
        "artifact_id": "pa-p1l5-fixture",
        "content_uid": CONTENT_UID,
        "schema_version": "llmke-parse-artifact/2.0",
        "parts": [{"role": "parsed_text", "relative_path": "parsed_text.md",
                   "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                   "size_bytes": len(text.encode("utf-8"))}],
        "quality": {"state": "COMPLETE",
                    "capabilities": ["text", "document_ir"], "warnings": []},
    }


def _snapshot(root: Path) -> Path:
    d = Path(root) / "snapshot"
    d.mkdir(parents=True, exist_ok=True)
    (d / "parsed_text.md").write_text(TEXT, encoding="utf-8")
    (d / "document_ir.json").write_text(
        json.dumps(_ir(), ensure_ascii=False), encoding="utf-8")
    (d / "artifact.json").write_text(
        json.dumps(_artifact(TEXT), ensure_ascii=False), encoding="utf-8")
    return d


def _policy() -> P.ProjectionPolicy:
    return P.ProjectionPolicy(index_name="kb_9", file_id="333")


def _payloads(root: Path, *, now: str | None = None) -> list:
    d = _snapshot(root)
    result = P.project(d, _policy(), mode="shadow")
    kwargs = dict(index_name="kb_9", file_id="333", file_name="p1l5.xlsx",
                  file_path="/vault/p1l5.xlsx", file_size=100, source="p1l5")
    # 阶段 A 签名无 now：不传，让 E4 的签名断言先在断言层 FAIL（而非 TypeError 空转）
    if "now" in inspect.signature(K.build_index_payloads).parameters:
        kwargs["now"] = now
    return K.build_index_payloads(result.chunks, **kwargs)


# --------------------------------------------------------------------------- E1 / R-1
def test_e1_two_channels_and_metadata_field_set(tmp_path: Path) -> None:
    payloads = _payloads(tmp_path)
    table_chunks = [p for p in payloads if p["index"] == "table_chunks_kb_9"]
    summaries = [p for p in payloads if p["index"] == "table_summary_kb_9"]
    assert table_chunks, "缺 table_chunks 载荷"
    assert summaries, "R-1：缺 table_summary 载荷 → E1 FAIL"
    meta = table_chunks[0]["metadata"]
    # 字段集与线上 _source.metadata 抽样真值一致（缺/多字段均 FAIL）
    assert set(meta) == ONLINE_KEYS, f"字段集差异: 缺={ONLINE_KEYS - set(meta)} 多={set(meta) - ONLINE_KEYS}"
    for key in TRUTH["truth_fields_for_e1"]:
        assert key in meta
    assert meta["channel"] == "table"
    assert meta["table_id"] == "t001"
    assert meta["parsed_text_ref"] == "table"
    assert meta["n_rows"] == 2 and meta["n_cols"] == 2
    assert meta["knowledge_base_name"] == "kb_9"
    # 线上 38 键无 table_summary_id：不得因回填把它写进 ES 载荷（§二 裁定 3 已知边界）
    assert "table_summary_id" not in meta
    s = summaries[0]
    assert s["metadata"]["channel"] == "table_summary"
    assert s["metadata"]["type"] == "table_summary"
    assert s["metadata"]["table_id"] == "t001"
    assert s["pk"] == s["metadata"]["pk"]
    assert isinstance(s["pk"], int)
    assert "[extractive]" in s["page_content"]  # 复用 summary.py 既有契约，离线确定性


# --------------------------------------------------------------------------- E2 / R-2
def test_e2_pk_stable_hits_online_truth_and_no_collision(tmp_path: Path) -> None:
    assert P._table_pk("kb_9", "329", 0) == ONLINE_PK["table|kb_9|329|0"]
    assert P._table_pk("kb_9", "333", 0) == ONLINE_PK["table|kb_9|333|0"]
    # 内容寻址：同一 (kb, file_id, ordinal) 重投影得到相同 pk 是正确语义
    assert P._table_pk("kb_9", "333", 0) == P._table_pk("kb_9", "333", 0)
    # 不同 ordinal / 不同 file_id 不撞号
    assert P._table_pk("kb_9", "333", 0) != P._table_pk("kb_9", "333", 1)
    assert P._table_pk("kb_9", "333", 0) != P._table_pk("kb_9", "329", 0)
    assert all(isinstance(v, int) for v in ONLINE_PK.values())
    # 禁改区：_table_pk seed 未被改成 table_chunk 口径
    src = Path(P.__file__).read_text(encoding="utf-8")
    assert 'seed = "|".join(["table", str(index_name).lower(), str(file_id), str(ordinal)])' in src
    assert "table_chunk|" not in src
    payloads = _payloads(tmp_path)
    pks = [p["pk"] for p in payloads]
    assert len(pks) == len(set(pks)), "产生重复行 / pk 撞号"


def test_r2_unadjudicated_seed_would_fail(tmp_path: Path) -> None:
    """R-2：两类载荷都必须在位，且 pk 全不撞号（阶段 A 缺 summary → 断言层 FAIL）。"""
    payloads = _payloads(tmp_path)
    assert any(p["index"] == "table_summary_kb_9" for p in payloads)
    assert any(p["index"] == "table_chunks_kb_9" for p in payloads)
    pks = [p["pk"] for p in payloads]
    assert len(pks) == len(set(pks))
    assert P._table_pk("kb_9", "333", 0) == 885155839145947657


# --------------------------------------------------------------------------- E3 / R-3
def _four_piece(root: Path, *, tamper_span: bool = False) -> Path:
    """store._check_source_consistency 所需的四件套（无 artifact.json，避免 UNKNOWN_TOP_LEVEL_FILE）。"""
    d = Path(root) / "four_piece"
    d.mkdir(parents=True, exist_ok=True)
    (d / "parsed_text.md").write_text(TEXT, encoding="utf-8")
    text_sha = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()
    (d / "parsed_metadata.json").write_text(
        json.dumps({"content_uid": CONTENT_UID, "sha256": SHA256,
                    "parser_name": "mineru"}, ensure_ascii=False), encoding="utf-8")
    (d / "parse_manifest.json").write_text(
        json.dumps({"content_uid": CONTENT_UID, "status": "SUCCESS",
                    "output_hash": text_sha, "asset_files": []},
                   ensure_ascii=False), encoding="utf-8")
    ir = _ir()
    if tamper_span:
        ir["blocks"][0]["content_ref"]["text"] = "不对齐的文字"
    (d / "document_ir.json").write_text(
        json.dumps(ir, ensure_ascii=False), encoding="utf-8")
    return d


def test_e3_span_mismatch_fail_closed_not_partial(tmp_path: Path) -> None:
    good = _four_piece(tmp_path / "good")
    S._check_source_consistency(good, S.collect_parts(good))  # 基线通过
    bad = _four_piece(tmp_path / "bad", tamper_span=True)
    with pytest.raises(S.ArtifactRefused) as err:
        S._check_source_consistency(bad, S.collect_parts(bad))
    assert err.value.code in ("IR_SPAN_MISMATCH", "TEXT_HASH_MISMATCH", "IR_SPAN_OUT_OF_RANGE")
    # R-3：不产出 PARTIAL 后继续 —— 投影链路也必须抛明确错误。
    # 用独立快照目录（带 artifact.json；collect_parts 的四件套目录不能有它）。
    proj = _snapshot(tmp_path / "proj")
    ir = json.loads((proj / "document_ir.json").read_text(encoding="utf-8"))
    ir["blocks"][0]["content_ref"]["text"] = "不对齐的文字"
    (proj / "document_ir.json").write_text(
        json.dumps(ir, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(P.ProjectionRefused) as proj_err:
        P.project(proj, _policy(), mode="snapshot")
    assert proj_err.value.code == "ARTIFACT_SPAN_MISMATCH"
    assert "PARTIAL" not in proj_err.value.code


# --------------------------------------------------------------------------- E4 / R-4
def test_e4_projection_is_deterministic(tmp_path: Path) -> None:
    # 阶段 A：build_index_payloads 无 now 透传 → 断言层 FAIL
    assert "now" in inspect.signature(K.build_index_payloads).parameters
    a = _payloads(tmp_path / "a", now=FIXED_NOW)
    b = _payloads(tmp_path / "b", now=FIXED_NOW)
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == \
           json.dumps(b, ensure_ascii=False, sort_keys=True), "R-4：两次投影载荷不同"
    # seq 与 pk 稳定
    assert [p["pk"] for p in a] == [p["pk"] for p in b]
    assert [p["metadata"]["chunk_index"] for p in a] == \
           [p["metadata"]["chunk_index"] for p in b]
    # 正文通道输出与改动前一致（既有 13 项测试在验收命令中另跑）
    text_payloads = [p for p in a if p["index"] == "kb_9"]
    assert text_payloads and text_payloads[0]["metadata"]["channel"] == "text"


# --------------------------------------------------------------------------- E5 / R-5
def test_e5_mode_still_legacy_no_snapshot_enabled(tmp_path: Path) -> None:
    assert P.mode_from_env({}) == "legacy"
    assert os.environ.get("INGEST_PROJECTION_MODE") in (None, "legacy")
    src = Path(P.__file__).read_text(encoding="utf-8")
    assert 'MODE_ENV = "INGEST_PROJECTION_MODE"' in src
    assert 'MODES = ("legacy", "snapshot", "shadow")' in src
    # R-5：运行时（读 env）未被切到 snapshot —— 投影应返回 NOT_APPLICABLE
    d = _snapshot(tmp_path)
    result = P.project(d, _policy(), mode=None)
    assert result.status == "NOT_APPLICABLE"
    assert result.chunks == []


# --------------------------------------------------------------------------- R-6
def test_r6_text_channel_and_summary_contract_regression(tmp_path: Path) -> None:
    payloads = _payloads(tmp_path)
    # 正文载荷形状与既有 build_index_payloads 一致
    text_payloads = [p for p in payloads if p["index"] == "kb_9"]
    assert text_payloads
    assert text_payloads[0]["metadata"]["channel"] == "text"
    assert text_payloads[0]["metadata"]["parsed_text_ref"] == "parsed_text.md"
    assert isinstance(text_payloads[0]["pk"], int)
    # summary.py 既有契约未被改口径（禁改区）
    assert callable(SUM.table_summary_id)
    assert SUM.table_summary_id("kb_9", "333", "t001") == \
           SUM.table_summary_id("kb_9", "333", "t001")
    # 禁改区静态检查（TL 裁定 3：v2sum|... 口径不动）
    src = Path(SUM.__file__).read_text(encoding="utf-8")
    assert 'seed = f"v2sum|{index_name}|{file_id}|{table_id}"' in src
