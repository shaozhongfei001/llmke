"""引用证据组装器：把检索片段组装成契约允许的 DocumentEvidence。

约束来源（冻结契约，不可改）：
- contracts/evidence/llmke-citation-evidence.yaml: offset_unit=unicode_codepoint
- contracts/schema/llmke-core.json#/$defs/{Evidence,DocumentEvidence,SourceRef,Offset}

设计要点：
1. **禁止伪造 offset**：不信任调用方给的 text_hash，一律用 text[start:end] 重算并比对；
2. 越界即失败（0 <= start < end <= len(text)，Python str 下标即码点，天然满足码点语义）；
3. 输出对象严格裁剪到 schema 允许的字段（additionalProperties=false），不夹带内部字段；
4. 所有失败走 EvidenceError，带机器可读 code，便于上层 fail-closed。
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

CORE_SCHEMA = "contracts/schema/llmke-core.json"
UNIT = "unicode_codepoint"


class EvidenceError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _need_str(value: Any, name: str, maxlen: int = 256) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError("FIELD_MISSING", f"{name} 必须是非空字符串")
    if len(value) > maxlen:
        raise EvidenceError("FIELD_TOO_LONG", f"{name} 超过 {maxlen}")
    return value


def _hex64(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise EvidenceError("HASH_FORMAT", f"{name} 必须是 64 位小写十六进制")
    return value


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_document_evidence(document_text: str, source: dict, evidence_id: str) -> dict:
    """组装 DocumentEvidence；任何不可信输入一律抛错，不返回"部分正确"的对象。"""
    if not isinstance(document_text, str):
        raise EvidenceError("ILLEGAL_INPUT", "document_text 必须是 str")
    _need_str(evidence_id, "evidence_id")

    offset = source.get("offset")
    if not isinstance(offset, dict):
        raise EvidenceError("FIELD_MISSING", "source.offset 缺失")

    start, end = offset.get("start"), offset.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool):
        raise EvidenceError("OFFSET_TYPE", "start/end 必须是整数")
    if start < 0 or end < 1 or start >= end:
        raise EvidenceError("OFFSET_RANGE", f"要求 0 <= start < end，实际 {start}..{end}")
    if end > len(document_text):
        raise EvidenceError("OFFSET_OUT_OF_BOUNDS", f"end={end} 超出文本长度 {len(document_text)}")

    if offset.get("unit") != UNIT:
        raise EvidenceError("OFFSET_UNIT", f"unit 必须是 {UNIT}")

    _need_str(offset.get("parser_version"), "offset.parser_version")

    slice_text = document_text[start:end]
    actual = text_hash(slice_text)
    declared = offset.get("text_hash")
    _hex64(declared, "offset.text_hash")
    if actual != declared:
        # 这是"伪造 offset"的核心防线：声称的区间与声称的哈希对不上
        raise EvidenceError("OFFSET_TEXT_HASH_MISMATCH", f"实际 {actual[:12]}… 与声明不一致")

    _hex64(source.get("content_hash"), "source.content_hash")

    # 严格裁剪，避免把内部字段写进对外契约
    return {
        "evidence_id": evidence_id,
        "type": "document_text",
        "source_ref": {
            "kb_id": _need_str(source.get("kb_id"), "source.kb_id"),
            "file_id": _need_str(source.get("file_id"), "source.file_id"),
            "document_version": _need_str(source.get("document_version"), "source.document_version"),
            "chunk_id": _need_str(source.get("chunk_id"), "source.chunk_id"),
            "content_hash": source["content_hash"],
            "offset": {
                "start": start,
                "end": end,
                "unit": UNIT,
                "text_hash": actual,
                "parser_version": offset["parser_version"],
            },
        },
    }


def _load_core(repo_root: Path) -> dict:
    p = Path(repo_root) / CORE_SCHEMA
    if not p.is_file():
        raise EvidenceError("CONTRACT_MISSING", str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def validate_evidence(evidence: dict, repo_root: Path | str) -> None:
    """用冻结契约本体校验；失败抛 EvidenceError，便于 fail-closed 集成。"""
    from jsonschema import Draft202012Validator, RefResolver

    core = _load_core(Path(repo_root))
    resolver = RefResolver.from_schema(core)
    v = Draft202012Validator({"$ref": "#/$defs/DocumentEvidence"}, resolver=resolver)
    errs = sorted(v.iter_errors(evidence), key=lambda e: list(e.path))
    if errs:
        first = errs[0]
        raise EvidenceError("CONTRACT_VIOLATION", f"{list(first.path)}: {first.message}")


class SupportGate:
    """按契约 `unsupported_policy: [block, annotate]` 过滤声明。

    规则（来自 contracts/evidence/llmke-citation-evidence.yaml）：
    - 有证据的声明：放行，附带证据 id 列表；
    - 无证据的声明：**默认 block**（blocked claims never emitted），不得静默丢弃；
    - 调用方显式要求 annotate 时，才允许作为"未支持标注"返回，并保留原因。
    """

    def __init__(self, mode: str = "block"):
        if mode not in ("block", "annotate"):
            raise EvidenceError("ILLEGAL_MODE", "mode 只能是 block 或 annotate")
        self.mode = mode

    def partition(self, claims: list[dict]) -> dict:
        supported, blocked = [], []
        for c in claims:
            cid = c.get("claim_id")
            if not isinstance(cid, str) or not cid:
                raise EvidenceError("CLAIM_ID", "每个 claim 必须有非空 claim_id")
            ev = c.get("evidence_ids") or []
            if not isinstance(ev, list) or not all(isinstance(x, str) and x for x in ev):
                raise EvidenceError("EVIDENCE_IDS", f"{cid}: evidence_ids 必须是非空字符串数组")
            if ev:
                supported.append({"claim_id": cid, "evidence_ids": ev, "text": c.get("text", "")})
            else:
                blocked.append({"claim_id": cid, "reason": "NO_APPROVED_EVIDENCE",
                                "text": c.get("text", "")})

        out = {"mode": self.mode, "supported": supported, "blocked": blocked,
               "emit": supported, "annotations": []}
        if self.mode == "annotate":
            # annotate 只允许"标注为未支持"，不得把无证据声明当成已支持发出
            out["annotations"] = [{"claim_id": b["claim_id"], "label": "unsupported",
                                   "reason": b["reason"]} for b in blocked]
        if self.mode == "block":
            # 硬约束：blocked 的声明绝不能出现在 emit 里
            assert not any(b["claim_id"] in {s["claim_id"] for s in out["emit"]} for b in blocked)
        return out
