"""答案接口（第九轮切片）：query → 授权取块 → 证据 → 答案 + 引用。

存在理由
    仓库里"检索 → 证据"这段已经成立（`modules/citation_flow`），但真实请求到这里就断了：
    没有一层把证据变成**可返回的答案**，也没有一层规定"证据不足时该返回什么"。
    真实翻车往往不在检索，而在这一层的三个决定：
      1. 没证据时返回空答案（等于告诉调用方"查无此事"，但事实是"我们没查到"）；
      2. 答案里出现没有引用的句子（模型自由发挥）；
      3. 出错时把未授权的 file_id 回显在错误里（用报错做越权探测）。

三条不变式（违反即拒绝，不降级）
    A. 授权过滤发生在取数（SQL WHERE），本层只做二次校验，不做"取回后再滤"；
    B. 任何缺失（上下文/证据/正文）一律 fail-closed，不返回"空答案成功"；
    C. 答案中每个断言都必须有 evidence_id；无引用不得输出。

刻意不做
    - 不调用真实模型：本轮答案是证据的确定性拼装，可复现、可断言；
      将来接入模型时，响应契约（`answer/claims/citations/audit`）不变。
    - 不实现权限判定规则本身：规则属 P0-03，未获 security-owner 批准，
      因此结果里恒带 `policy_state=CANDIDATE_NOT_RELEASEABLE`。
"""
from __future__ import annotations

from modules.authz.context import AuthZError, validate_context
from modules.chunk_store.chunk_store import ChunkError, build_chunk, to_evidence_source
from modules.citation_evidence.assembler import (EvidenceError, build_document_evidence,
                                                 check_evidence_set)
from modules.citation_flow.service import assert_chunks_in_scope

MAX_QUERY_LEN = 500
POLICY_STATE = "CANDIDATE_NOT_RELEASEABLE"


class AnswerError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _as_answer_error(exc: Exception) -> AnswerError:
    code = getattr(exc, "code", "INTERNAL")
    detail = getattr(exc, "detail", str(exc))
    return AnswerError(code, detail)


def build_answer(query: str, ctx: dict, kb_id: str, chunks: list[dict],
                 document_texts: dict[str, str], *, evidence_prefix: str = "ev",
                 now=None) -> dict:
    """把已授权的分块变成答案；任何不确定都抛 `AnswerError`，绝不返回半成品。

    `document_texts` 按 file_id 提供原文：跨文件检索时，不同文件的码点坐标系互不相干，
    用一份"全文"去切所有文件会静默产生错位证据，因此这里**要求逐文件提供**，缺就拒绝。
    """
    # 1) 授权上下文：结构、时效、范围；缺字段直接拒绝（匿名不得继续）
    try:
        ctx = validate_context(ctx, now=now)
    except AuthZError as e:
        raise _as_answer_error(e) from e

    # 2) 查询本身
    if not isinstance(query, str) or not query.strip():
        raise AnswerError("QUERY_EMPTY", "查询为空")
    q = query.strip()
    if len(q) > MAX_QUERY_LEN:
        raise AnswerError("QUERY_TOO_LONG", f"{len(q)} > {MAX_QUERY_LEN}")

    # 3) 证据必须存在：0 条不是"成功但没答案"，而是无法回答
    if not isinstance(chunks, list) or not chunks:
        raise AnswerError("NO_EVIDENCE", "未取到任何分块，拒绝生成空答案")

    # 4) 纵深防御：调用方可能塞入越权块。显式拒绝，且**不回显**越权 file_id
    try:
        assert_chunks_in_scope(ctx, kb_id, chunks)
    except AuthZError as e:
        if e.code == "CHUNK_OUT_OF_SCOPE":
            raise AnswerError("CHUNK_OUT_OF_SCOPE",
                              "存在不在授权范围内的分块，已拒绝（明细不回显）") from e
        raise _as_answer_error(e) from e

    # 5) 逐块重建（用库里的 text 与原文交叉校验），再产出证据
    built: list[dict] = []
    claims: list[dict] = []
    for c in chunks:
        fid = c.get("file_id")
        if not isinstance(fid, str) or fid not in document_texts:
            raise AnswerError("DOCUMENT_TEXT_MISSING", str(fid))
        try:
            rebuilt = build_chunk(document_texts[fid], chunk_id=c["chunk_id"], kb_id=c["kb_id"],
                                  file_id=c["file_id"], document_version=c["document_version"],
                                  chunk_index=c["chunk_index"], start=c["offset"]["start"],
                                  end=c["offset"]["end"], content_hash=c["content_hash"],
                                  parser_version=c["parser_version"],
                                  chunk_strategy=c["chunk_strategy"],
                                  declared_text_hash=c["text_hash"])
        except (ChunkError, KeyError) as e:
            raise _as_answer_error(e) from e
        if rebuilt["text"] != c.get("text"):
            # 库被改坏时在这里先炸，而不是把坏证据送进答案
            raise AnswerError("CHUNK_TEXT_MISMATCH", str(c.get("chunk_id")))

        eid = f"{evidence_prefix}-{c['chunk_id']}"
        try:
            built.append(build_document_evidence(document_texts[fid],
                                                 to_evidence_source(rebuilt), eid))
        except EvidenceError as e:
            raise _as_answer_error(e) from e
        claims.append({"claim_id": f"c-{len(claims) + 1}", "text": rebuilt["text"],
                       "evidence_id": eid, "chunk_index": c["chunk_index"]})

    # 6) 集合级校验：重复 id / 重叠 / 解析器版本混用
    try:
        check_evidence_set(built)
    except EvidenceError as e:
        raise _as_answer_error(e) from e

    # 7) 断言必须有引用；由本层构造，但显式再查一次（防将来改坏）
    claims.sort(key=lambda x: (x["chunk_index"], x["claim_id"]))
    cited = [c for c in claims if c.get("evidence_id")]
    if len(cited) != len(claims):
        raise AnswerError("UNCITED_CLAIM", f"{len(claims) - len(cited)} 条断言无引用")

    text = "\n".join(f"[{c['evidence_id']}] {c['text']}" for c in claims)
    citations = [{
        "evidence_id": ev["evidence_id"],
        "chunk_id": ev["source_ref"]["chunk_id"],
        "file_id": ev["source_ref"]["file_id"],
        "document_version": ev["source_ref"]["document_version"],
        "offset": dict(ev["source_ref"]["offset"]),
    } for ev in built]
    citations.sort(key=lambda x: x["evidence_id"])

    return {
        "status": "OK",
        "query": q,
        "kb_id": kb_id,
        "answer": {"text": text, "claims": claims},
        "citations": citations,
        "audit": {
            "request_id": ctx["request_id"],
            "principal_id": ctx["principal_id"],
            "authz_version": ctx["authz_version"],
            "chunk_count": len(chunks),
            "evidence_count": len(built),
            "claim_count": len(claims),
            "cited_claim_count": len(cited),
            "support_ratio": len(cited) / len(claims),
        },
        # 规则未获 security-owner 批准：状态必须一直挂在结果上，防止被当成生产策略
        "policy_state": POLICY_STATE,
    }


def to_api_response(result: dict) -> dict:
    """成功响应包装。调用方拿到的永远是 `ok/data` 或 `ok/error` 两种形状之一。"""
    return {"ok": True, "data": result}


def to_api_error(exc: Exception) -> dict:
    """失败响应包装：只回错误码与说明，不回栈、不回内部路径。"""
    code = getattr(exc, "code", "INTERNAL")
    detail = getattr(exc, "detail", "")
    return {"ok": False, "error": {"code": code, "message": detail}}
