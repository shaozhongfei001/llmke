"""ParseArtifact 产物仓：不可变快照的构建、提交与复核（V2 / VL1-01）。

定位
----
doc2md 的 `parsed/by_hash` 目录可能被 force 重跑覆盖，平台不能把可变目录当长期引用。
本模块负责把"一次已完成解析"复制成**不可变快照**，并给出可复核的清单：

  source_dir（doc2md 产物目录）
    parsed_text.md / parsed_metadata.json / parse_manifest.json / document_ir.json
    assets/**                       （可选）
        │
        ├─ collect_parts()          逐件 sha256 + size
        ├─ build_artifact()         形状+一致性校验 → ParseArtifact（内存对象）
        └─ commit()                 staging 复制 → 逐件复核 → 源未变 → 原子改名

必须 fail-closed 的原因（都有实测依据）
--------------------------------------
- 复制期间源被改写 → 快照会混合两次解析，必须放弃候选而不是"尽力而为"。
- `parse_manifest.status=FAILED` 的产物不得发布（失败解析不能冒充成功）。
- IR 的 text_span 必须与 `parsed_text.md` 逐字一致；否则"原文引用"从第一步就是假的。
- 空 file_id / 空来源曾经让整批边入库却无法回指（B04），这里同样不允许"缺件先过"。

**注意**：本模块只做产物封装与校验，不做解析、不做分块、不做图。它不认识 Nebula/ES/Milvus。
"""

import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

COMMIT_SCHEMA = "llmke-parse-artifact/2.0"
IR_SCHEMA = "document-ir/1.0"

# 四件套：必须各存在且仅一份（对应 schema 的 singleton 角色）
SINGLETON_FILES = {
    "parsed_text.md": "parsed_text",
    "parsed_metadata.json": "parsed_metadata",
    "parse_manifest.json": "parse_manifest",
    "document_ir.json": "document_ir",
}
SINGLETON_ROLES = tuple(SINGLETON_FILES.values())

# doc2md 产物目录里"不是证据基准"的派生文件：只用于展示，不进证据集。
# 依据：doc2md `app/core/parsed_paths.py` 声明 parsed_dir 下含 rendered_md（派生展示轨），
# 而 V2 设计要求 parsed_text.md 才是不可变证据基准（01_UNIFIED_DESIGN_V2.md:15,76）。
DISPLAY_ONLY_FILES = {"rendered.md"}

# 解析器的结构化中间件目录（doc2md 017 additive，仅 MinerU 路径会写）。
# 合同 ArtifactPart.role 已定义 ir_source，因此收录为独立角色而不是当 asset。
IR_SOURCE_DIR = "ir_source"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ArtifactRefused(ValueError):
    """拒绝构建/提交。code 是稳定的机器可读原因，detail 供人看。"""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# ─────────────────────────────────────────────────────────────── 基础摘要


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ─────────────────────────────────────────────────────────────── 收集与摘要


def _walk_source(source_dir):
    """枚举源目录里的文件；拒绝符号链接与越界路径。返回 [(相对路径, 绝对路径)]。"""
    source = Path(source_dir)
    if not source.is_dir():
        raise ArtifactRefused("SOURCE_NOT_DIRECTORY", str(source_dir))
    if source.is_symlink():
        raise ArtifactRefused("SYMLINK_REFUSED", str(source_dir))
    out = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ArtifactRefused("SYMLINK_REFUSED", str(path))
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        if rel.startswith("../") or rel.startswith("/"):
            raise ArtifactRefused("PATH_ESCAPE", rel)
        out.append((rel, path))
    return out


def collect_parts(source_dir):
    """把源目录里属于产物的文件枚举成 ArtifactPart 列表（按 relative_path 排序）。

    规则：
      - 四件套必须存在且唯一，缺失即 MISSING_PART；
      - 未识别的顶层文件不静默收编，直接拒绝（UNKNOWN_TOP_LEVEL_FILE），
        避免把日志/临时文件当成产物发布；
      - `assets/**` 一律记为 asset 角色。
    """
    entries = _walk_source(source_dir)
    parts = []
    seen_roles = {}
    for rel, path in entries:
        if rel in SINGLETON_FILES:
            role = SINGLETON_FILES[rel]
        elif rel in DISPLAY_ONLY_FILES:
            continue          # 派生展示轨，不进证据集
        elif rel.startswith("assets/") and rel != "assets/":
            role = "asset"
        elif rel.startswith(IR_SOURCE_DIR + "/") and rel != IR_SOURCE_DIR + "/":
            role = "ir_source"
        else:
            raise ArtifactRefused("UNKNOWN_TOP_LEVEL_FILE", rel)
        seen_roles.setdefault(role, []).append(rel)
        parts.append({
            "role": role,
            "relative_path": rel,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
    for name, role in SINGLETON_FILES.items():
        got = seen_roles.get(role, [])
        if not got:
            raise ArtifactRefused("MISSING_PART", f"{role} ({name})")
        if len(got) > 1:
            raise ArtifactRefused("DUPLICATE_PART", f"{role}: {got}")
    return parts


def read_set_digest(parts):
    """读取集合摘要：对 (role, 路径, sha256, size) 的规范序做 sha256。

    用途：证明"这次快照读到的是这一组字节"。任何一件变化都会变。
    """
    core = sorted(
        [{"role": p["role"], "relative_path": p["relative_path"],
          "sha256": p["sha256"], "size_bytes": p["size_bytes"]} for p in parts],
        key=lambda x: (x["relative_path"], x["role"]),
    )
    return sha256_bytes(canonical_json(core))


def parser_fingerprint(producer):
    """解析指纹：代码/路由/模型/配置/adapter 的实际影响输入。"""
    return sha256_bytes(canonical_json(producer))


# ─────────────────────────────────────────────────────────── 源一致性校验


def _read_json(path, code):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ArtifactRefused(code, f"{path}: {exc}") from exc


def _check_text(text_bytes):
    if text_bytes.startswith(b"\xef\xbb\xbf"):
        raise ArtifactRefused("BOM_REFUSED", "parsed_text.md 带 BOM，需显式解码配置")
    try:
        return text_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactRefused("TEXT_DECODE_FAILED", str(exc)) from exc


def _check_ir(ir, text, asset_hashes):
    if ir.get("schema_version") != IR_SCHEMA:
        raise ArtifactRefused("IR_SCHEMA_MISMATCH", str(ir.get("schema_version")))
    blocks = ir.get("blocks")
    if not isinstance(blocks, list):
        raise ArtifactRefused("IR_BLOCKS_MISSING", "blocks 不是数组")
    ids = [b.get("block_id") for b in blocks]
    if len(ids) != len(set(ids)):
        raise ArtifactRefused("IR_DUPLICATE_BLOCK", str(ids))
    if ir.get("reading_order") != ids:
        raise ArtifactRefused("IR_READING_ORDER_MISMATCH", "reading_order 与 blocks 顺序不一致")
    for block in blocks:
        source = block.get("content_ref") or {}
        if source.get("kind") != "text_span":
            continue
        start, end = source.get("start_offset"), source.get("end_offset")
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text)):
            raise ArtifactRefused("IR_SPAN_OUT_OF_RANGE", f"{block.get('block_id')}: {start}..{end}")
        if text[start:end] != source.get("text"):
            raise ArtifactRefused("IR_SPAN_MISMATCH", f"{block.get('block_id')} 的文字与 MD 不一致")
    for table in ir.get("tables") or []:
        n_rows, n_cols = table.get("n_rows"), table.get("n_cols")
        occupied = set()
        for cell in table.get("cells") or []:
            if cell.get("bbox") is not None or "confidence" in cell:
                raise ArtifactRefused("IR_TABLE_CELL_EXTENDED", f"{table.get('table_id')}")
            row, col = cell.get("row"), cell.get("col")
            rowspan, colspan = cell.get("rowspan"), cell.get("colspan")
            if None in (row, col, rowspan, colspan) or row < 0 or col < 0 or rowspan < 1 or colspan < 1:
                raise ArtifactRefused("IR_TABLE_BAD_COORDINATE", f"{table.get('table_id')}: {cell}")
            if row + rowspan > n_rows or col + colspan > n_cols:
                raise ArtifactRefused("IR_TABLE_OUT_OF_MATRIX", f"{table.get('table_id')}")
            for r in range(row, row + rowspan):
                for c in range(col, col + colspan):
                    if (r, c) in occupied:
                        raise ArtifactRefused("IR_TABLE_CELL_OVERLAP", f"{table.get('table_id')}: {(r, c)}")
                    occupied.add((r, c))
        if len(occupied) != n_rows * n_cols:
            raise ArtifactRefused("IR_TABLE_INCOMPLETE", f"{table.get('table_id')}")
    for figure in ir.get("figures") or []:
        if figure.get("asset_path") is None:
            continue
        digest = figure.get("asset_sha256")
        if digest not in asset_hashes:
            raise ArtifactRefused("FIGURE_ASSET_NOT_IN_PARTS", str(figure.get("figure_id")))
    return blocks


def _check_source_consistency(source_dir, parts):
    """返回 (content_uid, legacy, metadata, ir, text, blocks)。

    任何一条不成立都拒绝，不做"先发布再修"。
    """
    source = Path(source_dir)
    text = _check_text((source / "parsed_text.md").read_bytes())
    legacy = _read_json(source / "parse_manifest.json", "PARSE_MANIFEST_INVALID")
    metadata = _read_json(source / "parsed_metadata.json", "PARSED_METADATA_INVALID")
    ir = _read_json(source / "document_ir.json", "DOCUMENT_IR_INVALID")

    if legacy.get("status") not in {"SUCCESS", "EMPTY"}:
        raise ArtifactRefused("FAILED_PARSE_REFUSED", str(legacy.get("status")))
    text_sha = sha256_bytes(text.encode("utf-8"))
    if legacy.get("output_hash") != text_sha:
        raise ArtifactRefused("TEXT_HASH_MISMATCH",
                             f"parse_manifest.output_hash={legacy.get('output_hash')} 实际={text_sha}")

    uids = {legacy.get("content_uid"), metadata.get("content_uid"), ir.get("content_uid")}
    if len(uids) != 1:
        raise ArtifactRefused("CONTENT_UID_MISMATCH", str(sorted(map(str, uids))))
    content_uid = uids.pop()
    if not isinstance(content_uid, str) or not _SHA256_RE.match(content_uid):
        raise ArtifactRefused("CONTENT_UID_INVALID", str(content_uid))

    asset_hashes = {p["sha256"] for p in parts if p["role"] == "asset"}
    legacy_assets = {x.get("sha256") for x in (legacy.get("asset_files") or [])}
    if asset_hashes != legacy_assets:
        raise ArtifactRefused("ASSET_MANIFEST_MISMATCH",
                             f"parts={sorted(asset_hashes)} manifest={sorted(x for x in legacy_assets if x)}")
    blocks = _check_ir(ir, text, asset_hashes)
    return content_uid, legacy, metadata, ir, text, blocks


def derive_quality(ir, text, blocks):
    """由实际结构推导质量状态与能力，不照抄调用方声明。"""
    warnings = []
    capabilities = ["text", "document_ir", "source_alignment"]
    if ir.get("tables"):
        capabilities.append("table_cells")
    if any(f.get("asset_path") for f in (ir.get("figures") or [])):
        capabilities.append("figure_assets")
    if not text.strip():
        state = "EMPTY"
        warnings.append("正文为空（合法空文件需上游给出证明）")
    elif not blocks:
        state = "PARTIAL"
        warnings.append("IR 无块：结构化能力不足，不能当表格/图片解析已完成")
    else:
        state = "COMPLETE"
    return {"state": state, "capabilities": capabilities, "warnings": warnings}


# ─────────────────────────────────────────────────────────────── 构建与提交


def _producer_from(metadata, producer_inputs):
    merged = {
        "name": "doc2md",
        "source_revision": producer_inputs.get("source_revision"),
        "parser_name": producer_inputs.get("parser_name") or metadata.get("parser_name"),
        "parser_profile": producer_inputs.get("parser_profile") or metadata.get("parser_profile"),
        "parser_adapter_version": producer_inputs.get("parser_adapter_version")
        or metadata.get("parser_adapter_version"),
        "runtime_lock_hash": producer_inputs.get("runtime_lock_hash"),
        "config_hash": producer_inputs.get("config_hash"),
        "model_fingerprints": list(producer_inputs.get("model_fingerprints") or []),
    }
    missing = [k for k, v in merged.items() if v in (None, "", []) and k != "model_fingerprints"]
    if missing:
        raise ArtifactRefused("PRODUCER_INCOMPLETE", ", ".join(sorted(missing)))
    for key in ("runtime_lock_hash", "config_hash"):
        if not _SHA256_RE.match(str(merged[key])):
            raise ArtifactRefused("PRODUCER_HASH_INVALID", key)
    for digest in merged["model_fingerprints"]:
        if not _SHA256_RE.match(str(digest)):
            raise ArtifactRefused("PRODUCER_MODEL_FINGERPRINT_INVALID", str(digest))
    return merged


def build_artifact(source_dir, producer_inputs, artifact_id=None, committed_at=None):
    """构建（不落盘）ParseArtifact。返回 dict，可直接用 V2 schema 校验。"""
    parts = collect_parts(source_dir)
    content_uid, _legacy, metadata, ir, text, blocks = _check_source_consistency(source_dir, parts)
    producer = _producer_from(metadata, producer_inputs)
    artifact_id = artifact_id or content_uid
    if not _SAFE_ID_RE.match(str(artifact_id)):
        raise ArtifactRefused("UNSAFE_ARTIFACT_ID", str(artifact_id))
    return {
        "schema_version": COMMIT_SCHEMA,
        "artifact_id": artifact_id,
        "content_uid": content_uid,
        "parser_fingerprint": parser_fingerprint(producer),
        "producer": producer,
        "read_set_digest": read_set_digest(parts),
        "parts": parts,
        "ir_schema": IR_SCHEMA,
        "quality": derive_quality(ir, text, blocks),
        "commit_state": "COMMITTED",
        "committed_at": committed_at or _utc_now(),
    }


def _load_artifact(path):
    return _read_json(path, "COMMITTED_ARTIFACT_INVALID")


def verify_committed(store_root, artifact_id):
    """复核已提交快照：逐件 sha256/size 必须与清单一致，缺失或不符即失败。"""
    if not _SAFE_ID_RE.match(str(artifact_id)):
        raise ArtifactRefused("UNSAFE_ARTIFACT_ID", str(artifact_id))
    target = Path(store_root) / "artifacts" / str(artifact_id)
    manifest = target / "artifact.json"
    if not manifest.is_file():
        raise ArtifactRefused("ARTIFACT_NOT_FOUND", str(target))
    artifact = _load_artifact(manifest)
    for part in artifact.get("parts") or []:
        path = target / part["relative_path"]
        if not path.is_file():
            raise ArtifactRefused("VERIFY_FAILED", f"缺件 {part['relative_path']}")
        if path.stat().st_size != part["size_bytes"] or sha256_file(path) != part["sha256"]:
            raise ArtifactRefused("VERIFY_FAILED", f"字节不符 {part['relative_path']}")
    return artifact


def commit(source_dir, store_root, producer_inputs, artifact_id=None,
           committed_at=None, after_part_copied=None):
    """把源产物提交为不可变快照；返回 (artifact, 目标目录)。

    - 幂等：同 artifact_id 且内容一致 → 直接复核后返回既有快照，不重写；
    - 冲突：同 artifact_id 但 content_uid/parts 不同 → ARTIFACT_CONFLICT（不覆盖）；
    - 源在复制期间变化 → SOURCE_CHANGED，staging 清理，目标不产生。
    """
    artifact = build_artifact(source_dir, producer_inputs,
                              artifact_id=artifact_id, committed_at=committed_at)
    root = Path(store_root)
    target = root / "artifacts" / artifact["artifact_id"]
    if target.exists():
        existing = _load_artifact(target / "artifact.json") if (target / "artifact.json").is_file() else None
        if existing is None:
            raise ArtifactRefused("ARTIFACT_CONFLICT", f"{target} 已存在但无可读清单")
        same_parts = existing.get("parts") == artifact["parts"]
        if existing.get("content_uid") != artifact["content_uid"] or not same_parts:
            raise ArtifactRefused("ARTIFACT_CONFLICT",
                                  f"{artifact['artifact_id']} 已存在且内容不同（不可覆盖）")
        return verify_committed(root, artifact["artifact_id"]), target

    staging = root / ".staging" / f"{artifact['artifact_id']}.{uuid.uuid4().hex}"
    source = Path(source_dir)
    try:
        staging.mkdir(parents=True, exist_ok=False)
        for index, part in enumerate(artifact["parts"]):
            src = source / part["relative_path"]
            dst = staging / part["relative_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            if dst.stat().st_size != part["size_bytes"] or sha256_file(dst) != part["sha256"]:
                raise ArtifactRefused("COPY_MISMATCH", part["relative_path"])
            if after_part_copied is not None:
                after_part_copied(index, part)
        if collect_parts(source) != artifact["parts"]:
            raise ArtifactRefused("SOURCE_CHANGED",
                                  "复制期间源产物发生变化，候选快照已放弃（不混合两次解析）")
        (staging / "artifact.json").write_text(
            json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, target)   # 同文件系统内的原子改名
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        parent = staging.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    return artifact, target
