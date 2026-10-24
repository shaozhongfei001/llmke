"""HTTP 形状的适配：把 `build_answer` 的结果映射成 (状态码, 响应体)。

为什么单独一层：
    "答案对不对"和"该回 400 还是 403"是两件事。混在 service 里会让纯逻辑依赖 HTTP，
    也会让状态码散落在各处、彼此不一致。这里集中一张表，改一处即可审计。

映射原则：
    - 输入形状错误 → 400（调用方写错了）；
    - 授权/上下文问题 → 403（无权限或凭据过期，**不是**"没找到"）；
    - 证据不足 → 422（请求合法，但无法给出有引用的答案）；
    - 数据自相矛盾（重复 id、区间重叠、文本与原文不符）→ 409；
    - 其余内部错误 → 500，且**不回显栈**。

刻意不做：不解析 HTTP 报文、不读 body 流。入参是已解析的 dict，出参是 (int, dict)，
这样单测无需起服务，将来套任何框架都只是搬运。
"""
from __future__ import annotations

from modules.answer_api.service import AnswerError, build_answer, to_api_error, to_api_response

# 状态码表：新增错误码必须在这里登记，否则按 500 处理（fail-closed）
STATUS_BY_CODE: dict[str, int] = {
    "INVALID_REQUEST": 400,
    "FIELD_MISSING": 400,
    "QUERY_EMPTY": 400,
    "QUERY_TOO_LONG": 400,
    "ILLEGAL_INPUT": 400,
    "BAD_KB_ID": 400,
    "BAD_FILE_ID": 400,
    "BAD_VERSION": 400,
    "BAD_TIMESTAMP": 400,

    "CONTEXT_MISSING": 403,
    "CONTEXT_EXPIRED": 403,
    "KB_SCOPE_EMPTY": 403,
    "FILE_SCOPE_EMPTY": 403,
    "KB_NOT_AUTHORIZED": 403,
    "KB_SCOPE_MISSING": 403,
    "CHUNK_OUT_OF_SCOPE": 403,

    "NO_EVIDENCE": 422,
    "DOCUMENT_TEXT_MISSING": 422,

    "DUPLICATE_EVIDENCE_ID": 409,
    "SAME_CHUNK_OVERLAP": 409,
    "CROSS_CHUNK_OVERLAP": 409,
    "PARSER_VERSION_MIXED": 409,
    "CHUNK_TEXT_MISMATCH": 409,
    "TEXT_HASH_MISMATCH": 409,
    "OFFSET_UNIT": 409,
    "OFFSET_RANGE": 409,
    "OFFSET_OUT_OF_BOUNDS": 409,
    "OFFSET_TYPE": 409,
}

REQUIRED_FIELDS = ("query", "ctx", "kb_id", "chunks", "document_texts")


def handle(payload: dict) -> tuple[int, dict]:
    """一次请求 → (状态码, 响应体)。任何异常都不得以栈形式外泄。"""
    if not isinstance(payload, dict):
        return 400, {"ok": False, "error": {"code": "INVALID_REQUEST", "message": "请求体必须是对象"}}

    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        return 400, {"ok": False, "error": {"code": "FIELD_MISSING", "message": ",".join(missing)}}

    opts = {}
    if "rank" in payload:
        opts["rank"] = bool(payload["rank"])
    if "min_relevance" in payload:
        opts["min_relevance"] = payload["min_relevance"]
    if "top_k" in payload:
        opts["top_k"] = payload["top_k"]

    try:
        result = build_answer(payload["query"], payload["ctx"], payload["kb_id"],
                              payload["chunks"], payload["document_texts"], **opts)
    except AnswerError as e:
        return STATUS_BY_CODE.get(e.code, 500), to_api_error(e)
    except Exception:                      # noqa: BLE001 —— 兜底：绝不把内部细节回给调用方
        return 500, {"ok": False, "error": {"code": "INTERNAL", "message": "内部错误"}}

    return 200, to_api_response(result)
