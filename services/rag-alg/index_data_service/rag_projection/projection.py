"""RAG 投影：从**已提交的解析快照**产出召回单元（V2 / VL1-03 第一步）。

定位
----
线上现有分块发生在解析服务内部（`alg_doc_parse_service/server/controller.py::chunk`），
输入是刚解析出来的 Document 列表；本模块把这件事改成"消费快照"：

    ParseArtifact 快照（parsed_text.md + document_ir.json）
        → 确定性窗口分块（段落边界优先）
        → 每个 chunk 带 parse_artifact_id + MD 码点区间
        → ProjectionResult（只在内存/报告里，不写 ES/Milvus）

刻意**不做**的事
----------------
- 不写索引、不改线上分块路径：本模块只产出结果对象，落库由后续适配器负责。
- 不假装语义分块等价：现有 `Splitter` 是语义/模型驱动，这里先用确定性窗口，
  两者差异必须靠 shadow 对照数据说话，不能口头声明"等价"。
- 不碰原件：只读快照内的 `parsed_text.md`，不重新解析。

并存开关
--------
`ingest.projection.mode = legacy | snapshot | shadow`（默认 legacy）：

- `legacy`   ：继续走现有分块，本模块返回 NOT_APPLICABLE（不偷偷接上）；
- `snapshot` ：只用本模块；
- `shadow`   ：本模块产出结果供对照，线上仍用 legacy；差异写进报告。

未知取值一律拒绝（fail-closed），不允许"写错字就默认走新路径"。
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECTION_VERSION = "rag-projection-v2-window/1.0"
MODES = ("legacy", "snapshot", "shadow")
MODE_ENV = "INGEST_PROJECTION_MODE"


class ProjectionRefused(ValueError):
    """投影被拒绝（配置错、快照不合规、覆盖不完整）。"""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class ProjectionPolicy:
    """确定性窗口策略。改任一字段都必须重建，不允许静默变更。"""

    index_name: str
    file_id: str
    chunk_chars: int = 800
    overlap_chars: int = 0
    version: str = PROJECTION_VERSION

    def digest(self):
        core = {"index": self.index_name, "file": str(self.file_id),
                "chunk_chars": self.chunk_chars, "overlap": self.overlap_chars,
                "version": self.version}
        return hashlib.sha256(json.dumps(core, sort_keys=True,
                                         separators=(",", ":")).encode()).hexdigest()


@dataclass
class ProjectionResult:
    status: str
    mode: str
    chunks: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    refusals: list = field(default_factory=list)

    def to_dict(self):
        return {"status": self.status, "mode": self.mode,
                "policy_digest": self.stats.get("policy_digest"),
                "chunks": self.chunks, "stats": self.stats, "refusals": self.refusals}


def mode_from_env(env=None):
    """读并存开关；默认 legacy，未知值直接拒绝。"""
    raw = (env or os.environ).get(MODE_ENV, "legacy")
    mode = str(raw).strip().lower()
    if mode not in MODES:
        raise ProjectionRefused("PROJECTION_MODE_INVALID",
                                f"{MODE_ENV}={raw!r}，允许 {MODES}")
    return mode


def _chunk_pk(index_name, file_id, seq, text):
    """与线上同一套种子规则：chunk|index|file_id|seq|sha1(text)。

    保持一致是为了让 shadow 对照能按主键对齐；本模块另行记录 parse_artifact_id，
    不把 artifact 塞进 seed（否则同一文本换快照就换主键，跨代比对失效）。
    """
    seed = "|".join(["chunk", str(index_name).lower(), str(file_id), str(seq),
                     hashlib.sha1(str(text).encode("utf-8")).hexdigest()])
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15], 16)


def _windows(text, chunk_chars, overlap_chars):
    """按段落边界切窗，返回 [(start, end)]，区间是 MD 的 Unicode 码点左闭右开。"""
    if chunk_chars <= 0:
        raise ProjectionRefused("POLICY_INVALID", "chunk_chars must be > 0")
    if overlap_chars < 0 or overlap_chars >= chunk_chars:
        raise ProjectionRefused("POLICY_INVALID", "overlap must satisfy 0 <= overlap < chunk_chars")
    spans, start, n = [], 0, len(text)
    while start < n:
        end = min(start + chunk_chars, n)
        if end < n:
            # 优先在段落边界收口，避免把一个段落从中间劈开
            split = text.rfind("\n\n", start + 1, end)
            if split != -1 and split > start:
                end = split + 2
        spans.append((start, end))
        if end >= n:
            break
        start = max(end - overlap_chars, start + 1)
    return spans


def _check_coverage(text, spans):
    """非空白字符必须被完整覆盖，且尾部不得丢。"""
    covered = bytearray(len(text))
    for start, end in spans:
        for i in range(start, end):
            covered[i] = 1
    lost = [i for i in range(len(text)) if not covered[i] and not text[i].isspace()]
    if lost:
        raise ProjectionRefused("PROJECTION_COVERAGE_LOST",
                                f"{len(lost)} 个非空白字符未覆盖，首个位置={lost[0]}")


def load_artifact(artifact_dir):
    """读快照内的 artifact.json + parsed_text.md + 可选 IR，做基本一致性检查。"""
    root = Path(artifact_dir)
    manifest_path = root / "artifact.json"
    if not manifest_path.is_file():
        raise ProjectionRefused("ARTIFACT_MANIFEST_MISSING", str(manifest_path))
    artifact = json.loads(manifest_path.read_text(encoding="utf-8"))
    text_path = root / "parsed_text.md"
    if not text_path.is_file():
        raise ProjectionRefused("ARTIFACT_PART_MISSING", "parsed_text.md")
    text = text_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text_path.read_bytes()).hexdigest()
    recorded = next((p["sha256"] for p in artifact.get("parts", [])
                     if p.get("role") == "parsed_text"), None)
    if recorded != digest:
        raise ProjectionRefused("ARTIFACT_TEXT_HASH_MISMATCH",
                                f"清单={recorded} 实际={digest}")
    ir = None
    ir_path = root / "document_ir.json"
    if ir_path.is_file():
        ir = json.loads(ir_path.read_text(encoding="utf-8"))
        if ir.get("content_uid") != artifact.get("content_uid"):
            raise ProjectionRefused("ARTIFACT_IR_UID_MISMATCH",
                                    f"ir={ir.get('content_uid')} artifact={artifact.get('content_uid')}")
    return artifact, text, ir


def project(artifact_dir, policy, mode=None):
    """从快照产出投影结果。不写任何存储。"""
    mode = mode or mode_from_env()
    if mode == "legacy":
        return ProjectionResult(status="NOT_APPLICABLE", mode=mode,
                                stats={"reason": "legacy 模式仍走现有分块，未消费快照"})
    artifact, text, ir = load_artifact(artifact_dir)
    artifact_id = artifact.get("artifact_id")
    if not artifact_id:
        raise ProjectionRefused("ARTIFACT_ID_MISSING", str(artifact_dir))

    spans = _windows(text, policy.chunk_chars, policy.overlap_chars)
    _check_coverage(text, spans)

    blocks = list((ir or {}).get("blocks") or [])
    chunks = []
    for seq, (start, end) in enumerate(spans):
        body = text[start:end]
        if not body.strip():
            raise ProjectionRefused("PROJECTION_EMPTY_CHUNK", f"seq={seq} {start}..{end}")
        if body != text[start:end]:                      # 冗余但显式：内容必须来自 MD
            raise ProjectionRefused("PROJECTION_TEXT_MISMATCH", f"seq={seq}")
        chunks.append({
            "seq": seq,
            "pk": _chunk_pk(policy.index_name, policy.file_id, seq, body),
            "text": body,
            "locator": {"kind": "text_span", "source": "parsed_text.md",
                        "start_offset": start, "end_offset": end},
            "parse_artifact_id": artifact_id,
            "content_uid": artifact.get("content_uid"),
            "block_ids": [b.get("block_id") for b in blocks],
        })

    quality = artifact.get("quality") or {}
    status = "EMPTY" if not text.strip() else ("SHADOW" if mode == "shadow" else "READY")
    return ProjectionResult(
        status=status, mode=mode, chunks=chunks,
        stats={
            "artifact_id": artifact_id,
            "content_uid": artifact.get("content_uid"),
            "artifact_schema": artifact.get("schema_version"),
            "artifact_quality": quality.get("state"),
            "artifact_capabilities": quality.get("capabilities"),
            "ir_present": ir is not None,
            "ir_blocks": len(blocks),
            "chars": len(text),
            "chunks": len(chunks),
            "policy_digest": policy.digest(),
            "chunk_chars": policy.chunk_chars,
            "overlap_chars": policy.overlap_chars,
        })
