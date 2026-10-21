#!/usr/bin/env python3
"""llmke-ir/1.0 映射契约测试（SYNTHETIC）。

性质：**合成样本 + 反例**，用于验证 `UNIFIED-IR-DRAFT-V1.0.md` 里定义的映射规则与不变量
是否可被机器判定。它不是生产验证，不证明任何解析准确率，也不关闭任何 P0。

覆盖：
  M-1  doc2md 正常 IR           → parse_status=PASSED，blocks/tables/assets 保留
  M-2  document_ir 缺失         → parse_status=PARTIAL（不得当成功）
  N-1  DEPENDENCY_MISSING 透传  → parse_status=DEPENDENCY_MISSING（不得折叠成 PASSED）
  N-2  缺 bbox                  → bbox=null 且计入 blocks_without_bbox（不得估算）
  N-3  DOCX 出现 page_no        → 违反不变量 I-1，必须拒绝
  N-4  text_span 缺 text_hash   → 违反不变量 I-3，必须拒绝
  N-5  表格合并未识别            → cells[].merge_detected 必须为 false（不得假装已识别）

用法：
  python3 loops/LD-legacy-discovery/spike/ir_mapping_check.py
退出码：0 = 全部通过；1 = 有用例失败。
"""
from __future__ import annotations

import hashlib
import json
import sys

DOC2MD_STATUS_MAP = {
    "PARSED": "PASSED",
    "SKIPPED": "SKIPPED",
    "DEPENDENCY_MISSING": "DEPENDENCY_MISSING",
    "UNSUPPORTED_WITH_HINT": "UNSUPPORTED",
}

BLOCK_TYPES = {"heading", "paragraph", "table", "figure", "formula", "caption", "header", "footer"}
COORD_UNITS = {"pdf_point", "pixel", "none"}


class MappingError(ValueError):
    pass


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def map_doc2md(doc: dict, *, engine="doc2md", engine_version="005_mvp_v1") -> dict:
    """把 doc2md 的 document_ir 映射为 llmke-ir/1.0（草案规则）。"""
    full_text = "\n".join(b.get("content_ref", {}).get("text", "") for b in doc.get("blocks", []))
    th = text_hash(full_text)

    if doc.get("parse_status_hint") and doc["parse_status_hint"] in DOC2MD_STATUS_MAP.values():
        status = doc["parse_status_hint"]
    else:
        status = DOC2MD_STATUS_MAP.get(doc.get("decision", "PARSED"), "PARTIAL")
    if doc.get("document_ir_missing"):
        status = "PARTIAL"

    unit = doc.get("coordinate_system", {}).get("unit", "pixel")
    if unit not in COORD_UNITS:
        raise MappingError(f"坐标单位不在闭集内: {unit}")

    blocks, no_bbox = [], 0
    for b in doc.get("blocks", []):
        btype = b.get("type", "paragraph")
        raw_type = None
        if btype not in BLOCK_TYPES:
            raw_type, btype = btype, "paragraph"
        bbox = b.get("bbox")
        if bbox is None:
            no_bbox += 1
        page_no = b.get("page_no")
        if engine == "deepdoc_docx" and page_no is not None:
            raise MappingError("DOCX 路径不得出现 page_no（不变量 I-1）")
        cref = dict(b.get("content_ref") or {})
        if cref.get("kind") == "text_span":
            if not cref.get("text_hash"):
                raise MappingError("text_span 缺 text_hash（不变量 I-3）")
        attrs = dict(b.get("attrs") or {})
        if raw_type:
            attrs["raw_type"] = raw_type
        blocks.append({
            "block_id": b.get("block_id"),
            "type": btype,
            "page_no": page_no,
            "bbox": bbox,
            "reading_order": b.get("reading_order", 0),
            "confidence": b.get("confidence"),
            "content_ref": cref,
            "attrs": attrs,
        })

    tables = []
    for t in doc.get("tables", []):
        cells = [{
            "row": c.get("row"), "col": c.get("col"),
            "row_span": c.get("row_span", 1), "col_span": c.get("col_span", 1),
            "text": c.get("text", ""),
            "is_header": bool(c.get("is_header", False)),
            # deepdoc 的合并识别是未完成 TODO → 永远 false，绝不假装已识别
            "merge_detected": False if engine == "deepdoc_docx" else bool(c.get("merge_detected", False)),
        } for c in t.get("cells", [])]
        tables.append({"table_id": t.get("table_id"), "caption": t.get("caption"), "cells": cells})

    assets = [{
        "asset_id": a.get("asset_id"), "kind": a.get("kind", "image"),
        "asset_path": a.get("asset_path"), "sha256": a.get("sha256"), "ext": a.get("ext"),
        "page_no": a.get("page_no"), "bbox": a.get("bbox"),
    } for a in doc.get("assets", [])]

    return {
        "schema_version": "llmke-ir/1.0",
        "doc_id": doc.get("content_uid"),
        "sha256": doc.get("sha256"),
        "parse_engine": engine,
        "engine_version": engine_version,
        "parse_status": status,
        "status_reasons": doc.get("status_reasons", []),
        "page_count": doc.get("page_count"),
        "coordinate_system": {"unit": unit if doc.get("page_count") is not None else "none",
                              "origin": "top_left", "page_ref": "per_page"},
        "text_hash": th,
        "blocks": blocks,
        "tables": tables,
        "assets": assets,
        "stats": {"block_count": len(blocks), "table_count": len(tables),
                  "asset_count": len(assets), "blocks_without_bbox": no_bbox},
    }


# ---------------- 用例 ----------------

def base_doc(**over):
    doc = {
        "content_uid": "probe-1", "sha256": "a" * 64, "page_count": 2,
        "coordinate_system": {"unit": "pdf_point", "origin": "top_left", "page_ref": "per_page"},
        "decision": "PARSED",
        "blocks": [
            {"block_id": "b1", "type": "paragraph", "page_no": 1, "bbox": [0, 0, 10, 10],
             "reading_order": 0, "content_ref": {"kind": "inline_text", "text": "第一段"}},
            {"block_id": "b2", "type": "table", "page_no": 1, "bbox": [0, 10, 10, 20],
             "reading_order": 1, "content_ref": {"kind": "table_ref", "table_id": "t1"}},
        ],
        "tables": [{"table_id": "t1", "cells": [
            {"row": 0, "col": 0, "text": "指标", "is_header": True},
            {"row": 1, "col": 0, "text": "日均存款"},
        ]}],
        "assets": [],
    }
    doc.update(over)
    return doc


def main() -> int:
    cases = []

    def check(name, fn, *, expect="ok"):
        """expect=ok：必须成功执行且断言成立；expect=raise：必须抛 MappingError。

        为什么区分：若不区分，正例里意外抛 MappingError 会被记成"正确拒绝"，
        于是"测试通过"但实际没覆盖目标逻辑（假绿）。
        """
        try:
            fn()
        except AssertionError as e:
            cases.append((name, "FAIL", str(e)))
            return
        except MappingError as e:
            cases.append((name, "PASS", f"正确拒绝：{e}") if expect == "raise"
                         else (name, "FAIL", f"意外拒绝：{e}"))
            return
        if expect == "raise":
            cases.append((name, "FAIL", "期望被拒绝，但未拒绝"))
        else:
            cases.append((name, "PASS", ""))

    # M-1 正常
    def m1():
        ir = map_doc2md(base_doc())
        assert ir["parse_status"] == "PASSED", ir["parse_status"]
        assert ir["stats"]["block_count"] == 2 and ir["stats"]["table_count"] == 1
        assert len(ir["text_hash"]) == 64
        assert ir["coordinate_system"]["unit"] == "pdf_point"
    check("M-1 doc2md 正常 IR → PASSED", m1)

    # M-2 document_ir 缺失
    def m2():
        ir = map_doc2md(base_doc(document_ir_missing=True))
        assert ir["parse_status"] == "PARTIAL", ir["parse_status"]
    check("M-2 document_ir 缺失 → PARTIAL", m2)

    # N-1 DEPENDENCY_MISSING 透传
    def n1():
        ir = map_doc2md(base_doc(decision="DEPENDENCY_MISSING"))
        assert ir["parse_status"] == "DEPENDENCY_MISSING", ir["parse_status"]
        assert ir["parse_status"] != "PASSED"
    check("N-1 DEPENDENCY_MISSING 不得折叠成 PASSED", n1)

    # N-2 缺 bbox 不计估算
    def n2():
        doc = base_doc()
        doc["blocks"][0]["bbox"] = None
        ir = map_doc2md(doc)
        assert ir["blocks"][0]["bbox"] is None
        assert ir["stats"]["blocks_without_bbox"] == 1, ir["stats"]
    check("N-2 缺 bbox → null 且计数", n2)

    # N-3 DOCX 不得有 page_no
    def n3():
        doc = base_doc(page_count=None, coordinate_system={"unit": "none"})
        map_doc2md(doc, engine="deepdoc_docx")  # page_no=1 → 应抛 MappingError
        raise AssertionError("DOCX 出现 page_no 却未被拒绝")
    check("N-3 DOCX 出现 page_no → 拒绝", n3, expect="raise")

    # N-4 text_span 缺 text_hash
    def n4():
        doc = base_doc()
        doc["blocks"][0]["content_ref"] = {"kind": "text_span", "text": "x",
                                           "source": "s", "start_offset": 0, "end_offset": 1}
        map_doc2md(doc)
        raise AssertionError("text_span 缺 text_hash 却未被拒绝")
    check("N-4 text_span 缺 text_hash → 拒绝", n4, expect="raise")

    # N-5 表格合并不得假装已识别
    def n5():
        doc = base_doc(page_count=None, coordinate_system={"unit": "none"})
        for b in doc["blocks"]:      # 先隔离 I-1，避免被 page_no 提前拦截（否则本用例空转）
            b["page_no"] = None
        doc["tables"][0]["cells"][0]["merge_detected"] = True
        ir = map_doc2md(doc, engine="deepdoc_docx")
        assert all(c["merge_detected"] is False for c in ir["tables"][0]["cells"]), ir["tables"]
    check("N-5 DOCX 合并未识别 → merge_detected=false", n5)

    width = max(len(c[0]) for c in cases)
    for name, verdict, note in cases:
        print(f"{name:<{width}}  {verdict}" + (f"  ({note})" if note else ""))
    failed = [c for c in cases if c[1] == "FAIL"]
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed  [SYNTHETIC: 仅验证映射规则，不代表解析准确率]")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
