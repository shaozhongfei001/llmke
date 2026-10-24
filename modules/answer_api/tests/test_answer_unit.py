"""答案层单测：正常路径 1 条，其余全是"必须拒绝"的负例。

为什么负例占多数：
    这一层的价值不在"能拼出答案"，而在**证据不足、越权、库被改坏时会不会闭嘴**。
    每条负例对应一种真实事故：空答案冒充"查无此事"、越权块被静默丢弃、
    报错回显未授权文件名、库里的文本与原文不一致仍被送进答案。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.answer_api import (AnswerError, POLICY_STATE, build_answer, fetch_chunks,
                                to_api_error, to_api_response)

ROOT = Path(__file__).resolve().parents[3]
DOC = "第一段内容。第二段内容。"
CH = hashlib.sha256(DOC.encode()).hexdigest()
FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def ctx(files=("*"), kb="kb-1"):
    return {"request_id": "req-1", "principal_id": "user-1", "service": "answer",
            "kb_scope": [kb], "file_scope": {kb: files},
            "authz_version": 1, "expires_at": FUTURE}


def chunk(chunk_id="k1", file_id="f-1", start=0, end=6, *, text=None,
          idx=0, doc=DOC, pv="p-1", text_hash=None):
    t = DOC[start:end] if text is None else text
    return {"chunk_id": chunk_id, "kb_id": "kb-1", "file_id": file_id,
            "document_version": "v1", "chunk_index": idx, "text": t,
            "text_hash": text_hash or sha(t), "content_hash": sha(doc),
            "parser_version": pv, "chunk_strategy": "S1",
            "offset": {"start": start, "end": end, "unit": "unicode_codepoint",
                       "text_hash": text_hash or sha(t), "parser_version": pv}}


def two_chunks():
    return [chunk("k1", start=0, end=6, idx=0), chunk("k2", start=6, end=12, idx=1)]


def call(**over):
    args = {"query": "第一段讲什么", "ctx": ctx(), "kb_id": "kb-1",
            "chunks": two_chunks(), "document_texts": {"f-1": DOC}}
    args.update(over)
    return build_answer(**args)


# ---------- 正常路径 ----------
def test_answer_ok_with_citations():
    r = call()
    assert r["status"] == "OK"
    assert [c["evidence_id"] for c in r["answer"]["claims"]] == ["ev-k1", "ev-k2"]
    assert r["audit"]["support_ratio"] == 1.0
    assert r["policy_state"] == POLICY_STATE          # 规则未批准，必须一直挂着
    assert {c["file_id"] for c in r["citations"]} == {"f-1"}
    assert "第一段内容" in r["answer"]["text"]


def test_whole_kb_scope_allows_any_file():
    r = call(ctx=ctx(files="*"))
    assert len(r["citations"]) == 2


# ---------- 上下文负例 ----------
def test_missing_context_refused():
    with pytest.raises(AnswerError) as e:
        call(ctx=None)
    assert e.value.code == "CONTEXT_MISSING"


def test_empty_kb_scope_refused():
    c = ctx()
    c["kb_scope"] = []
    c["file_scope"] = {}
    with pytest.raises(AnswerError) as e:
        call(ctx=c)
    assert e.value.code in {"KB_SCOPE_EMPTY", "FILE_SCOPE_EMPTY"}


def test_expired_context_refused():
    c = ctx()
    c["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with pytest.raises(AnswerError) as e:
        call(ctx=c)
    assert e.value.code == "CONTEXT_EXPIRED"


# ---------- 证据负例 ----------
def test_no_chunks_is_refusal_not_empty_answer():
    with pytest.raises(AnswerError) as e:
        call(chunks=[])
    assert e.value.code == "NO_EVIDENCE"


def test_out_of_scope_chunk_refused_and_redacted():
    """越权块必须显式拒绝；报错不得回显文件名，否则报错本身成了越权探测工具。"""
    cs = two_chunks() + [chunk("k9", file_id="f-2", start=0, end=6, idx=2)]
    with pytest.raises(AnswerError) as e:
        call(chunks=cs, ctx=ctx(files=["f-1"]))
    assert e.value.code == "CHUNK_OUT_OF_SCOPE"
    assert "f-2" not in str(e.value)


def test_missing_document_text_refused():
    cs = [chunk("k9", file_id="f-9")]
    with pytest.raises(AnswerError) as e:
        call(chunks=cs, ctx=ctx(files="*"))
    assert e.value.code == "DOCUMENT_TEXT_MISSING"


def test_text_mismatch_refused():
    cs = [chunk("k1", text="被篡改的文本")]
    with pytest.raises(AnswerError) as e:
        call(chunks=cs)
    assert e.value.code in {"CHUNK_TEXT_MISMATCH", "TEXT_HASH_MISMATCH"}


def test_duplicate_chunk_id_refused():
    cs = [chunk("k1", start=0, end=6, idx=0), chunk("k1", start=6, end=12, idx=1)]
    with pytest.raises(AnswerError) as e:
        call(chunks=cs)
    assert e.value.code == "DUPLICATE_EVIDENCE_ID"


def test_overlapping_chunks_refused():
    """同一文件两段区间重叠 = 同一段原文被两个证据认领，支撑率会虚高。"""
    cs = [chunk("k1", start=0, end=6, idx=0), chunk("k2", start=4, end=10, idx=1)]
    with pytest.raises(AnswerError) as e:
        call(chunks=cs)
    assert e.value.code in {"CROSS_CHUNK_OVERLAP", "SAME_CHUNK_OVERLAP"}


def test_mixed_parser_version_refused():
    cs = [chunk("k1", start=0, end=6, idx=0, pv="p-1"),
          chunk("k2", start=6, end=12, idx=1, pv="p-2")]
    with pytest.raises(AnswerError) as e:
        call(chunks=cs)
    assert e.value.code == "PARSER_VERSION_MIXED"


# ---------- 查询负例 ----------
def test_empty_query_refused():
    with pytest.raises(AnswerError) as e:
        call(query="   ")
    assert e.value.code == "QUERY_EMPTY"


def test_too_long_query_refused():
    with pytest.raises(AnswerError) as e:
        call(query="字" * 501)
    assert e.value.code == "QUERY_TOO_LONG"


# ---------- 响应形状 ----------
def test_api_wrappers_are_stable():
    ok = to_api_response(call())
    assert ok["ok"] is True and set(ok) == {"ok", "data"}
    bad = to_api_error(AnswerError("NO_EVIDENCE", "x"))
    assert bad == {"ok": False, "error": {"code": "NO_EVIDENCE", "message": "x"}}


def test_api_error_never_leaks_traceback():
    try:
        call(chunks=[])
    except AnswerError as e:
        payload = json.dumps(to_api_error(e), ensure_ascii=False)
    assert "Traceback" not in payload and ".py" not in payload


# ---------- SQL 适配（不连库） ----------
def test_sql_contains_authz_predicate_and_cannot_be_widened():
    captured = {}

    def runner(sql):
        captured["sql"] = sql
        return []

    fetch_chunks(runner, ctx(files=["f-1"]), "kb-1", chunk_ids=["k2"])
    sql = captured["sql"]
    assert "file_id IN ('f-1')" in sql          # 授权谓词恒在
    assert "chunk_id IN ('k2')" in sql          # 只是额外收窄
    assert "OR " not in sql.upper().split("WHERE", 1)[1]   # 收窄条件不得用 OR 拓宽


# ---------- CLI ----------
def test_cli_ok_and_refusal(tmp_path):
    req = {"query": "第一段", "ctx": ctx(), "kb_id": "kb-1",
           "chunks": two_chunks(), "document_texts": {"f-1": DOC}}
    p = tmp_path / "req.json"
    p.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")

    ok = subprocess.run([sys.executable, "-m", "modules.answer_api.cli", "--input", str(p)],
                        cwd=str(ROOT), capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert json.loads(ok.stdout)["ok"] is True

    req["chunks"] = []
    p.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
    bad = subprocess.run([sys.executable, "-m", "modules.answer_api.cli", "--input", str(p)],
                         cwd=str(ROOT), capture_output=True, text=True)
    assert bad.returncode == 2, bad.stdout + bad.stderr
    assert json.loads(bad.stdout)["error"]["code"] == "NO_EVIDENCE"


# ---------- HTTP 状态映射 ----------
def test_handler_200_on_success():
    from modules.answer_api.handler import handle
    status, body = handle({"query": "第一段", "ctx": ctx(), "kb_id": "kb-1",
                           "chunks": two_chunks(), "document_texts": {"f-1": DOC}})
    assert status == 200 and body["ok"] is True
    assert body["data"]["policy_state"] == POLICY_STATE


def test_handler_400_on_missing_field():
    from modules.answer_api.handler import handle
    status, body = handle({"query": "x"})
    assert status == 400 and body["error"]["code"] == "FIELD_MISSING"


def test_handler_403_on_expired_context():
    from modules.answer_api.handler import handle
    c = ctx()
    c["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    status, body = handle({"query": "第一段", "ctx": c, "kb_id": "kb-1",
                           "chunks": two_chunks(), "document_texts": {"f-1": DOC}})
    assert status == 403 and body["error"]["code"] == "CONTEXT_EXPIRED"


def test_handler_403_on_cross_scope_chunk():
    from modules.answer_api.handler import handle
    cs = two_chunks() + [chunk("k9", file_id="f-2", start=0, end=6, idx=2)]
    status, body = handle({"query": "第一段", "ctx": ctx(files=["f-1"]), "kb_id": "kb-1",
                           "chunks": cs, "document_texts": {"f-1": DOC}})
    assert status == 403
    assert "f-2" not in json.dumps(body, ensure_ascii=False)


def test_handler_422_on_no_evidence():
    from modules.answer_api.handler import handle
    status, body = handle({"query": "第一段", "ctx": ctx(), "kb_id": "kb-1",
                           "chunks": [], "document_texts": {"f-1": DOC}})
    assert status == 422 and body["error"]["code"] == "NO_EVIDENCE"


def test_handler_409_on_overlap():
    from modules.answer_api.handler import handle
    cs = [chunk("k1", start=0, end=6, idx=0), chunk("k2", start=4, end=10, idx=1)]
    status, body = handle({"query": "第一段", "ctx": ctx(), "kb_id": "kb-1",
                           "chunks": cs, "document_texts": {"f-1": DOC}})
    assert status == 409


def test_handler_500_never_leaks_internals():
    from modules.answer_api.handler import handle
    status, body = handle({"query": "x", "ctx": ctx(), "kb_id": "kb-1",
                           "chunks": "不是列表", "document_texts": {}})
    assert status in {400, 409, 422, 500}
    assert "Traceback" not in json.dumps(body) and ".py" not in json.dumps(body)


# ---------- 相关性筛选 ----------
def test_tokenize_cjk_bigram_and_latin_lower():
    from modules.answer_api.ranking import tokenize
    f = tokenize("第一段 Contains")
    assert "第一" in f and "一段" in f and "contains" in f


def test_score_bounds():
    from modules.answer_api.ranking import score
    assert score("第一段", "第一段内容。") == 1.0
    assert score("完全不相关", "第二段内容。") < 0.5
    assert score("", "任何文本") == 0.0


def test_rank_drops_zero_overlap_and_reports_why():
    from modules.answer_api.ranking import rank_chunks
    kept, dropped = rank_chunks("第一段讲什么", two_chunks())
    assert [c["chunk_id"] for c in kept] == ["k1"]
    assert dropped and dropped[0]["reason"] in {"no_overlap", "below_min_score"}
    assert dropped[0]["chunk_id"] == "k2"


def test_rank_min_score_and_top_k():
    from modules.answer_api.ranking import rank_chunks
    kept, _ = rank_chunks("第一段", two_chunks(), min_score=0.99)
    assert [c["chunk_id"] for c in kept] == ["k1"]
    kept2, dropped2 = rank_chunks("第一段 第二段", two_chunks(), top_k=1)
    assert len(kept2) == 1
    assert any(d["reason"] == "top_k_cut" for d in dropped2)


def test_rank_rejects_bad_params():
    from modules.answer_api.ranking import rank_chunks
    with pytest.raises(ValueError):
        rank_chunks("x", two_chunks(), min_score=1.5)
    with pytest.raises(ValueError):
        rank_chunks("x", two_chunks(), top_k=0)


def test_answer_with_rank_cites_only_relevant():
    """开启排序后，无关块不得进答案，且丢弃原因要能被审计看到。"""
    r = call(rank=True)
    assert [c["chunk_id"] for c in r["citations"]] == ["k1"]
    assert r["audit"]["ranked"] is True
    assert r["audit"]["dropped_chunks"][0]["chunk_id"] == "k2"


def test_answer_rank_all_irrelevant_is_refusal():
    with pytest.raises(AnswerError) as e:
        call(query="完全无关的问题", rank=True)
    assert e.value.code == "INSUFFICIENT_RELEVANCE"


def test_mixed_document_versions_refused():
    """同一文件的两个版本同时引用 = 重复计数，且重叠检测看不出来（集合键含版本）。"""
    cs = [chunk("k1", start=0, end=6, idx=0), chunk("k2", start=6, end=12, idx=1)]
    cs[1]["document_version"] = "v2"
    with pytest.raises(AnswerError) as e:
        call(chunks=cs)
    assert e.value.code == "MIXED_DOCUMENT_VERSION"


def test_handler_forwards_rank_options():
    from modules.answer_api.handler import handle
    status, body = handle({"query": "第一段", "ctx": ctx(), "kb_id": "kb-1",
                           "chunks": two_chunks(), "document_texts": {"f-1": DOC},
                           "rank": True, "min_relevance": 0.5})
    assert status == 200
    assert [c["chunk_id"] for c in body["data"]["citations"]] == ["k1"]
    assert body["data"]["audit"]["ranked"] is True


def test_cli_rank_flag_can_refuse(tmp_path):
    req = {"query": "完全无关", "ctx": ctx(), "kb_id": "kb-1",
           "chunks": two_chunks(), "document_texts": {"f-1": DOC}}
    p = tmp_path / "req.json"
    p.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "modules.answer_api.cli", "--input", str(p), "--rank"],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert json.loads(r.stdout)["error"]["code"] == "INSUFFICIENT_RELEVANCE"


def test_status_map_marks_index_not_ready_as_503():
    """索引未就绪是运维问题，不能与"查无结果"(422) 共用一个状态码。"""
    from modules.answer_api.handler import STATUS_BY_CODE
    assert STATUS_BY_CODE["INDEX_NOT_READY"] == 503
    assert STATUS_BY_CODE["NO_EVIDENCE"] == 422
