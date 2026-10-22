"""分块存储：把解析产物落成可复核的块，并能直接产出证据的 source。

设计要点：
1. **不信任调用方给的哈希**：一律用 text[start:end] 重算并与声明比对（与 assembler 同规则）；
2. **码点语义**：Python str 下标即码点，与 contracts 的 `offset_unit=unicode_codepoint` 一致；
3. **与证据打通**：`to_evidence_source()` 直接产出 `build_document_evidence` 需要的 source，
   因为两边用同一套 offset 与 text_hash 规则；
4. 失败一律抛 `ChunkError`，不返回"部分正确"的块。
"""
from __future__ import annotations

import hashlib
from typing import Any

UNIT = "unicode_codepoint"


class ChunkError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _need_str(value: Any, name: str, maxlen: int = 128) -> str:
    if not isinstance(value, str) or not value:
        raise ChunkError("FIELD_MISSING", f"{name} 必须是非空字符串")
    if len(value) > maxlen:
        raise ChunkError("FIELD_TOO_LONG", f"{name} 超过 {maxlen}")
    return value


def build_chunk(document_text: str, *, chunk_id: str, kb_id: str, file_id: str,
                document_version: str, chunk_index: int, start: int, end: int,
                content_hash: str, parser_version: str, chunk_strategy: str,
                declared_text_hash: str | None = None) -> dict:
    """按码点区间切出一个分块；所有不可信输入一律抛错。"""
    if not isinstance(document_text, str):
        raise ChunkError("ILLEGAL_INPUT", "document_text 必须是 str")
    for value, name in ((chunk_id, "chunk_id"), (kb_id, "kb_id"), (file_id, "file_id"),
                        (document_version, "document_version"),
                        (parser_version, "parser_version"),
                        (chunk_strategy, "chunk_strategy")):
        _need_str(value, name)
    if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
        raise ChunkError("CHUNK_INDEX", "chunk_index 必须是 >=0 的整数")
    if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool):
        raise ChunkError("OFFSET_TYPE", "start/end 必须是整数")
    if start < 0 or start >= end:
        raise ChunkError("OFFSET_RANGE", f"要求 0 <= start < end，实际 {start}..{end}")
    if end > len(document_text):
        raise ChunkError("OFFSET_OUT_OF_BOUNDS", f"end={end} 超出文本长度 {len(document_text)}")
    if not isinstance(content_hash, str) or len(content_hash) != 64:
        raise ChunkError("HASH_FORMAT", "content_hash 必须是 64 位十六进制")

    text = document_text[start:end]
    digest = text_hash(text)
    if declared_text_hash is not None and declared_text_hash != digest:
        # 与 assembler 同一道防线：声明与内容不符即拒绝
        raise ChunkError("TEXT_HASH_MISMATCH", f"实际 {digest[:12]}… 与声明不一致")

    return {
        "chunk_id": chunk_id,
        "kb_id": kb_id,
        "file_id": file_id,
        "document_version": document_version,
        "chunk_index": chunk_index,
        "offset": {"start": start, "end": end, "unit": UNIT,
                   "text_hash": digest, "parser_version": parser_version},
        "text": text,
        "text_hash": digest,
        "content_hash": content_hash,
        "parser_version": parser_version,
        "chunk_strategy": chunk_strategy,
    }


def to_evidence_source(chunk: dict) -> dict:
    """转成 assembler.build_document_evidence 需要的 source。

    两边规则一致（码点 + sha256），所以不需要换算——这是刻意的：
    换算层越少，"证据指向的文本"与"分块文本"不一致的机会就越少。
    """
    o = chunk["offset"]
    return {
        "kb_id": chunk["kb_id"], "file_id": chunk["file_id"],
        "document_version": chunk["document_version"], "chunk_id": chunk["chunk_id"],
        "content_hash": chunk["content_hash"],
        "offset": {"start": o["start"], "end": o["end"], "unit": o["unit"],
                   "text_hash": o["text_hash"], "parser_version": o["parser_version"]},
    }


def check_chunk_set(chunks: list[dict]) -> None:
    """同一文档版本内的分块集合校验：序号唯一、区间不重叠、策略与解析器版本一致。"""
    seen_index: dict[int, str] = {}
    seen_id: set[str] = set()
    pv: str | None = None
    strat: str | None = None
    spans = []
    for c in chunks:
        cid = c["chunk_id"]
        if cid in seen_id:
            raise ChunkError("DUPLICATE_CHUNK_ID", cid)
        seen_id.add(cid)
        idx = c["chunk_index"]
        if idx in seen_index:
            raise ChunkError("DUPLICATE_CHUNK_INDEX", f"第 {idx} 块重复：{seen_index[idx]} / {cid}")
        seen_index[idx] = cid
        if pv is None:
            pv = c["parser_version"]
        elif pv != c["parser_version"]:
            raise ChunkError("PARSER_VERSION_MIXED", f"{pv} vs {c['parser_version']}（offset 不可比）")
        if strat is None:
            strat = c["chunk_strategy"]
        elif strat != c["chunk_strategy"]:
            raise ChunkError("CHUNK_STRATEGY_MIXED", f"{strat} vs {c['chunk_strategy']}")
        o = c["offset"]
        spans.append((o["start"], o["end"], cid))

    spans.sort()
    for i in range(1, len(spans)):
        if spans[i][0] < spans[i - 1][1]:
            raise ChunkError("CHUNK_OVERLAP",
                             f"{spans[i-1][2]}[{spans[i-1][0]},{spans[i-1][1]}) 与 "
                             f"{spans[i][2]}[{spans[i][0]},{spans[i][1]}) 重叠")
