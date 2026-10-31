"""回答组装：引用必须逐字可核验；核验不过宁可无答案，不给假引用。"""

import json

from graph_engine_adapter.answer import assemble, build_context, parse_answer, verify_citations
from graph_engine_adapter.assertions import Assertion, AssertionStore, SourceRef


def make_store():
    s = AssertionStore()
    s.register_entity("p_jia", "产品甲")
    s.add(Assertion(subject="p_jia", predicate="额度", object_value=8000, unit="万元", key="额度",
                    sources=[SourceRef("333", "a" * 64)]))
    return s


def retrieval(hits, executed_route="GRAPH"):
    return {"executed_route": executed_route, "hits": hits}


HITS = [{"text": "产品甲 最高额度 8000万元", "sources": [{"file_id": "333"}]}]


def llm_returning(payload):
    def _call(messages, **kw):
        return payload
    return _call


def test_valid_answer_with_verbatim_citation_passes():
    out = assemble("产品甲额度是多少", store=make_store(), retrieval=retrieval(HITS),
                   llm_call=llm_returning(json.dumps({
                       "answer": "8000万元",
                       "citations": [{"file_id": "333", "quote": "最高额度 8000万元"}]})))
    assert out["passed"] is True and out["reason"] == "OK"
    assert out["citations"][0]["file_id"] == "333"


def test_paraphrased_quote_is_rejected():
    """模型改写了原文 → quote 不是子串 → 不算有效引用。"""
    out = assemble("产品甲额度是多少", store=make_store(), retrieval=retrieval(HITS),
                   llm_call=llm_returning(json.dumps({
                       "answer": "8000万元",
                       "citations": [{"file_id": "333", "quote": "产品甲最高额度为8000万元"}]})))
    assert out["passed"] is False
    assert out["reason"] == "INVALID_CITATION"
    assert out["invalid_citations"][0]["reason"] == "QUOTE_NOT_FOUND"


def test_citation_to_unknown_file_is_rejected():
    out = assemble("产品甲额度是多少", store=make_store(), retrieval=retrieval(HITS),
                   llm_call=llm_returning(json.dumps({
                       "answer": "8000万元",
                       "citations": [{"file_id": "999", "quote": "最高额度"}]})))
    assert out["passed"] is False
    assert out["invalid_citations"][0]["reason"] == "FILE_NOT_IN_CONTEXT"


def test_answer_without_citation_fails_when_required():
    out = assemble("产品甲额度是多少", store=make_store(), retrieval=retrieval(HITS),
                   llm_call=llm_returning('{"answer": "8000万元", "citations": []}'))
    assert out["passed"] is False and out["reason"] == "NO_VALID_CITATION"


def test_require_graph_refuses_dense_fallback():
    out = assemble("产品甲额度是多少", store=make_store(),
                   retrieval=retrieval(HITS, executed_route="DENSE_FALLBACK"),
                   llm_call=llm_returning('{"answer": "x", "citations": []}'),
                   require_graph=True)
    assert out["passed"] is False
    assert out["reason"].startswith("GRAPH_ROUTE_REQUIRED")


def test_unparseable_output_is_reported_not_crash():
    out = assemble("q", store=make_store(), retrieval=retrieval(HITS),
                   llm_call=llm_returning("这不是 JSON"))
    assert out["passed"] is False
    assert out["reason"].startswith("UNPARSEABLE_LLM_OUTPUT")


def test_code_fence_is_tolerated():
    raw = '```json\n{"answer":"a","citations":[]}\n```'
    assert parse_answer(raw) == {"answer": "a", "citations": []}


def test_context_includes_passages_and_assertions():
    ctx = build_context(make_store(), HITS, include_derived=True)
    kinds = [c["kind"] for c in ctx]
    assert kinds[0] == "passage"
    assert "assertion" in kinds
    assert all(c["files"] for c in ctx)


def test_triple_return_from_llm_is_supported():
    """本地端点 infer 返回 (text, usage, ...) 三元组，必须取第一个元素。"""
    def _call(messages, **kw):
        return ('{"answer":"8000万元","citations":[{"file_id":"333","quote":"8000万元"}]}',
                {"completion_tokens": 10}, False)

    out = assemble("q", store=make_store(), retrieval=retrieval(HITS), llm_call=_call)
    assert out["passed"] is True


def test_verify_citations_marks_missing_fields():
    res = verify_citations([{"file_id": "", "quote": ""}],
                           [{"files": ["333"], "text": "x"}])
    assert res["invalid"][0]["reason"] == "MISSING_FIELD"


def test_citation_to_derived_assertion_is_rejected():
    """只在本平台渲染出来的断言里出现的"引用"不算原文引用（避免自证循环）。

    这里直接把派生文本塞进上下文模拟"引用断言"的场景，核验必须拒绝。
    """
    ctx = build_context(make_store(), HITS, include_derived=True)
    from graph_engine_adapter.answer import verify_citations
    res = verify_citations([{"file_id": "333", "quote": "产品甲 额度 8000万元"}], ctx)
    assert res["valid"] == []
    assert res["invalid"][0]["reason"] == "QUOTE_IN_DERIVED_ONLY"

    # 走完整 assemble 时，默认上下文里没有派生文本，同样不应该通过
    out = assemble("产品甲额度是多少", store=make_store(), retrieval=retrieval(HITS),
                   llm_call=llm_returning(json.dumps({
                       "answer": "8000万元",
                       "citations": [{"file_id": "333", "quote": "产品甲 额度 8000万元"}]})))
    assert out["passed"] is False
    # 默认上下文里根本没有派生文本，所以这里是 QUOTE_NOT_FOUND；两种都表示"引用不成立"
    assert out["invalid_citations"][0]["reason"] in ("QUOTE_NOT_FOUND", "QUOTE_IN_DERIVED_ONLY")


def test_context_excludes_derived_by_default():
    """默认只喂原文段落：派生物进上下文会诱导模型引用它，引用又必然核验不过。"""
    ctx = build_context(make_store(), HITS)
    assert [c["kind"] for c in ctx] == ["passage"]


def test_assertion_rendered_with_names_not_ids():
    ctx = build_context(make_store(), HITS, include_derived=True)
    assertion_texts = [c["text"] for c in ctx if c["kind"] == "assertion"]
    assert assertion_texts
    assert all("ent:" not in t for t in assertion_texts)
    assert any("产品甲" in t for t in assertion_texts)
