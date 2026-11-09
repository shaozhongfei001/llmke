#!/usr/bin/env python3
"""为 MinerU PDF 产物补第 4 件 `document_ir.json`（平台侧补口，**不是** doc2md 原生输出）。

事实（实测，非推断）
------------------
doc2md 的 `parse-mineru-pdf` 落盘的是三件套 + `ir_source/{content_list,middle}.json`，
其 `mineru_pdf_parser.py` 里**没有**任何 document_ir 相关调用；而 DOCX 走的
`markitdown_parser._build_document_ir` 会写第 4 件。于是 PDF 产物进不了 ParseArtifact
（`store.commit(mode="v2")` 要求四件套）。

本脚本做什么
----------
调用 **doc2md 自己的** `build_from_mineru_content_list` 与 `validate_document_ir`
（不自己发明 IR 格式、不猜位置），把缺失的第 4 件补齐后写回产物目录。
补出来的 IR 带 `provenance.ir_source` 与块级偏移，能过 doc2md 自带校验器。

必须如实标注的边界
----------------
- 这不是 doc2md 原生产出的第 4 件，是平台侧补口；排查时要能看出这一层。
  脚本会在 IR 的 provenance 里加 `ir_filled_by=llmke/v2_fill_mineru_ir`。
- 只在 `document_ir.json` 缺失时补；已有就报错退出，不覆盖（避免掩盖上游修复）。

用法
----
    python scripts/v2_fill_mineru_ir.py --parsed-dir <parsed/by_hash/aa/bb/uid>
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_DOC2MD_CWD = "/home/szf/data/dev/doc2md/backend"
FILLER_TAG = "llmke/v2_fill_mineru_ir"


def fill_mineru_ir(parsed_dir: Path, *, doc2md_cwd: str = DEFAULT_DOC2MD_CWD) -> dict:
    """补齐 MinerU 产物的 document_ir.json，返回写入的 IR 载荷。"""
    root = Path(parsed_dir)
    if not root.is_dir():
        raise RuntimeError(f"产物目录不存在：{root}")
    ir_path = root / "document_ir.json"
    if ir_path.is_file():
        raise RuntimeError(f"document_ir.json 已存在，拒绝覆盖：{ir_path}")

    manifest_path = root / "parse_manifest.json"
    text_path = root / "parsed_text.md"
    content_list_path = root / "ir_source" / "content_list.json"
    for p in (manifest_path, text_path, content_list_path):
        if not p.is_file():
            raise RuntimeError(f"缺少必需产物：{p}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    text = text_path.read_text(encoding="utf-8")
    content_list = json.loads(content_list_path.read_text(encoding="utf-8"))
    if not isinstance(content_list, list) or not content_list:
        raise RuntimeError("content_list.json 为空或不是数组，无法构造 IR")

    if doc2md_cwd not in sys.path:
        sys.path.insert(0, doc2md_cwd)
    from app.services.document_ir_builder import build_from_mineru_content_list  # noqa: E402
    from app.services.document_ir_schema import validate_document_ir  # noqa: E402

    ir = build_from_mineru_content_list(
        content_list=content_list,
        parsed_text=text,
        sha256=manifest.get("sha256"),
        content_uid=manifest.get("content_uid"),
        source_vault_path=manifest.get("source_vault_path"),
        page_count=None,
        # 必须把 asset_files（relative_path → sha256）交给 builder：
        # 否则每个 figure 的 asset_sha256 都是 None，校验会以 FIGURE_INVALID 拒绝整份 IR。
        # 无图的 PDF 不触发该校验，所以这个问题此前没暴露。
        manifest_assets=manifest.get("asset_files"),
    )
    payload = ir.to_dict()
    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        # 让"这第 4 件是平台补的"在产物里可追溯，而不是冒充 doc2md 原生输出
        provenance["ir_filled_by"] = FILLER_TAG
        # 时间戳必须取 manifest 的生成时间，不能用"现在"：
        # 同一份解析重复补口若写入不同时间，字节就变了，快照会判 ARTIFACT_CONFLICT
        # （实测：重跑同一 PDF 时冲突，正是因为这里写了当前时间）。
        manifest_time = manifest.get("generated_at")
        if manifest_time:
            provenance["generated_at"] = manifest_time
    # 校验同样需要 asset_files：figure 的 asset_sha256 必须与 parse_manifest 对齐
    # （fail-closed），不传会被判 ASSET_ALIGNMENT_INVALID。
    validate_document_ir(payload, parsed_text=text,
                         manifest_assets=manifest.get("asset_files"))

    ir_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description="为 MinerU PDF 产物补齐 document_ir.json")
    p.add_argument("--parsed-dir", required=True, help="parsed/by_hash/aa/bb/<uid> 目录")
    p.add_argument("--doc2md-cwd", default=DEFAULT_DOC2MD_CWD)
    args = p.parse_args()
    try:
        payload = fill_mineru_ir(Path(args.parsed_dir), doc2md_cwd=args.doc2md_cwd)
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "FILLED",
        "schema_version": payload.get("schema_version"),
        "blocks": len(payload.get("blocks") or []),
        "tables": len(payload.get("tables") or []),
        "figures": len(payload.get("figures") or []),
        "reading_order": len(payload.get("reading_order") or []),
        "ir_filled_by": FILLER_TAG,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
