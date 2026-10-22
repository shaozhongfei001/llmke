"""证据链路编排（切片 E）：授权过滤 -> 取分块 -> 产出证据。

为什么要这一层：
    前面三个切片各自成立，但"组合起来是否仍然安全"没人验证过。
    典型翻车方式：检索层过滤了，构造证据时却用外部传入的 chunk_id 直接回表——
    过滤被绕过，而且**不会报错**。

本层做两件事：
    1. 取数只走带授权谓词的 SQL（不信任调用方给的 id 列表）；
    2. **纵深防御**：即使调用方传入越权 chunk_id，也显式拒绝（AuthZError），不静默丢弃——
       静默丢弃会让"越权尝试"在日志里消失，事故复盘时查不到。
"""
from __future__ import annotations

from typing import Any

from modules.authz.context import AuthZError, compile_chunk_predicate, files_for
from modules.chunk_store.chunk_store import build_chunk, to_evidence_source
from modules.citation_evidence.assembler import build_document_evidence


def fetch_chunks_sql(ctx: dict, kb_id: str, chunk_ids: list[str] | None = None,
                     limit: int = 50) -> str:
    """生成取块 SQL：授权谓词恒在，chunk_ids 只是**额外**收窄，永远不能放宽。"""
    pred = compile_chunk_predicate(ctx, kb_id)
    extra = ""
    if chunk_ids:
        quoted = ",".join("'" + c.replace("'", "") + "'" for c in chunk_ids)
        extra = f" AND chunk_id IN ({quoted})"
    return ("SELECT chunk_id,kb_id,file_id,document_version,chunk_index,offset_start,offset_end,"
            "offset_unit,text,text_hash,content_hash,parser_version,chunk_strategy "
            f"FROM document_chunk WHERE {pred}{extra} ORDER BY chunk_index LIMIT {int(limit)}")


def rows_to_chunks(rows: list[list[str]]) -> list[dict]:
    """把 SQL 行还原成 chunk 结构，并**重新校验**偏移与哈希（不信任库里的值）。"""
    out = []
    for r in rows:
        out.append({
            "chunk_id": r[0], "kb_id": r[1], "file_id": r[2], "document_version": r[3],
            "chunk_index": int(r[4]), "text": r[8], "text_hash": r[9],
            "content_hash": r[10], "parser_version": r[11], "chunk_strategy": r[12],
            "offset": {"start": int(r[5]), "end": int(r[6]), "unit": r[7],
                       "text_hash": r[9], "parser_version": r[11]},
        })
    return out


def assert_chunks_in_scope(ctx: dict, kb_id: str, chunks: list[dict]) -> None:
    """纵深防御：任何不在授权范围内的块都必须**拒绝**，而不是跳过。"""
    files = files_for(ctx, kb_id)
    if files == "*":
        return
    allowed = set(files)
    bad = sorted({c["file_id"] for c in chunks if c["file_id"] not in allowed})
    if bad:
        raise AuthZError("CHUNK_OUT_OF_SCOPE", ",".join(bad))


def build_evidences_from_chunks(document_text: str, ctx: dict, kb_id: str,
                                chunks: list[dict], evidence_prefix: str = "ev") -> list[dict]:
    """把（已授权的）分块转成证据对象；每个证据都过契约校验。"""
    assert_chunks_in_scope(ctx, kb_id, chunks)
    out = []
    for c in chunks:
        # 用库里的 text 与原文交叉校验：库被改坏时这里会先炸，而不是把坏证据送进 Prompt
        rebuilt = build_chunk(document_text, chunk_id=c["chunk_id"], kb_id=c["kb_id"],
                              file_id=c["file_id"], document_version=c["document_version"],
                              chunk_index=c["chunk_index"], start=c["offset"]["start"],
                              end=c["offset"]["end"], content_hash=c["content_hash"],
                              parser_version=c["parser_version"],
                              chunk_strategy=c["chunk_strategy"],
                              declared_text_hash=c["text_hash"])
        if rebuilt["text"] != c["text"]:
            raise AuthZError("CHUNK_TEXT_MISMATCH", c["chunk_id"])
        eid = f"{evidence_prefix}-{c['chunk_id']}"
        out.append(build_document_evidence(document_text, to_evidence_source(rebuilt), eid))
    return out
