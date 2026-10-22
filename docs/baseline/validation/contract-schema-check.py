#!/usr/bin/env python3
"""契约字段 ↔ 数据库列 一致性检查（防"契约改了、库没跟上"）。

为什么需要：
    `contracts/schema/llmke-core.json#/$defs/DocumentEvidence` 是证据对象的**权威结构**，
    而 `document_evidence` 表是它的持久化形态。两者由不同人维护，最容易漂移：
    契约新增必填字段 -> 代码开始产出 -> 落库时发现没有列 -> 数据丢失或运行期报错。

它检查什么：
    1. 契约 `DocumentEvidence` 的必填字段，是否都能在表里找到对应列（含嵌套映射）；
    2. `Offset` 的 `unit` 常量是否与表默认值一致；
    3. 表里是否有契约未定义的列（多余列本身不是错，但要求显式说明用途）。

映射表是显式的（下方 MAP），不做"猜"：猜出来的映射会在契约重命名时静默失配。

用法：
    python3 docs/baseline/validation/contract-schema-check.py
退出码：0 一致；2 有缺失/不一致。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "contracts/schema/llmke-core.json"
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.2.sql"
TABLE = "document_evidence"

# 契约路径 -> 表列名（显式映射，不推断）
MAP = {
    "evidence_id": "evidence_id",
    "type": None,                       # 固定值 'document_text'，不落列（由表含义决定）
    "source_ref.kb_id": "kb_id",
    "source_ref.file_id": "file_id",
    "source_ref.document_version": "document_version",
    "source_ref.chunk_id": "chunk_id",
    "source_ref.content_hash": "content_hash",
    "source_ref.offset.start": "offset_start",
    "source_ref.offset.end": "offset_end",
    "source_ref.offset.unit": "offset_unit",
    "source_ref.offset.text_hash": "text_hash",
    "source_ref.offset.parser_version": "parser_version",
}


def columns_of(sql: str, table: str) -> dict[str, str]:
    m = re.search(rf"CREATE TABLE (?:IF NOT EXISTS )?`{table}` \((.*?)\n\) ENGINE", sql, re.S)
    if not m:
        raise SystemExit(f"FAIL: 在 schema 中找不到表 {table}")
    cols = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"\s*`(\w+)`\s+([A-Za-z]+(?:\([^)]*\))?)", line)
        if mm:
            cols[mm.group(1)] = mm.group(2).upper()
    return cols


def collect_required(node: dict, prefix: str = "") -> list[str]:
    """展开契约里的必填字段路径（只跟 $defs 一层，够用且不会跑偏）。"""
    out = []
    for name, spec in (node.get("properties") or {}).items():
        path = f"{prefix}{name}"
        out.append(path)
        if isinstance(spec, dict) and spec.get("type") == "object" and spec.get("properties"):
            out.extend(collect_required(spec, path + "."))
        ref = spec.get("$ref") if isinstance(spec, dict) else None
        if ref:
            out.append(path + ".<ref>")
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", type=Path, default=CORE)
    ap.add_argument("--schema", type=Path, default=SCHEMA)
    a = ap.parse_args()
    core = json.loads(a.core.read_text(encoding="utf-8"))
    defs = core.get("$defs") or {}
    if "DocumentEvidence" not in defs:
        print("FAIL: 契约缺少 $defs.DocumentEvidence")
        return 2
    sql = a.schema.read_text(encoding="utf-8")
    cols = columns_of(sql, TABLE)

    # 契约里 DocumentEvidence 的 properties（source_ref 通过 $ref 指向 SourceRef）
    de = defs["DocumentEvidence"]
    required = set(de.get("required") or [])
    problems = []

    missing_required = required - {"type"} - {"source_ref"}
    for field in sorted(required - {"type", "source_ref", "evidence_id"}):
        if field not in cols:
            problems.append(f"契约必填字段 `{field}` 在表 {TABLE} 中无对应列")

    # source_ref 展开校验
    src = defs.get("SourceRef") or {}
    src_req = set(src.get("required") or [])
    src_map = {
        "kb_id": "kb_id", "file_id": "file_id", "document_version": "document_version",
        "chunk_id": "chunk_id", "content_hash": "content_hash", "offset": None,
    }
    for field in sorted(src_req):
        col = src_map.get(field, "MISSING")
        if col == "MISSING":
            problems.append(f"SourceRef 必填字段 `{field}` 未在映射表中登记（契约可能新增字段）")
        elif col and col not in cols:
            problems.append(f"SourceRef.{field} 映射列 `{col}` 不存在")

    off = defs.get("Offset") or {}
    off_req = set(off.get("required") or [])
    off_map = {"start": "offset_start", "end": "offset_end", "unit": "offset_unit",
               "text_hash": "text_hash", "parser_version": "parser_version"}
    for field in sorted(off_req):
        col = off_map.get(field, "MISSING")
        if col == "MISSING":
            problems.append(f"Offset 必填字段 `{field}` 未登记映射")
        elif col not in cols:
            problems.append(f"Offset.{field} 映射列 `{col}` 不存在")

    # unit 常量 vs 表默认值
    unit_const = ((off.get("properties") or {}).get("unit") or {}).get("const")
    m = re.search(rf"`offset_unit`.*?DEFAULT '([^']+)'", sql)
    db_unit = m.group(1) if m else None
    if unit_const and db_unit and unit_const != db_unit:
        problems.append(f"offset_unit 常量不一致：契约 `{unit_const}` vs 表默认 `{db_unit}`")

    # 映射表里登记但表里没有的列
    for path, col in MAP.items():
        if col and col not in cols:
            problems.append(f"映射 {path} -> `{col}` 缺列")

    known = {c for c in MAP.values() if c} | {"created_at", "created_by"}
    extra = sorted(set(cols) - known)
    print(f"契约必填={len(required)}  SourceRef 必填={len(src_req)}  Offset 必填={len(off_req)}")
    print(f"表 {TABLE} 列={len(cols)}；契约未定义但表里有的列（需说明用途）：{extra or '无'}")
    if problems:
        for p in problems:
            print("FAIL:", p)
        print(f"\n结论: FAIL（{len(problems)} 项不一致）")
        return 2
    print("\n结论: PASS（契约必填字段均有列，offset_unit 常量一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
