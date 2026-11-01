"""合并结果重排：打分、截断、以及失败时必须回退到 RRF 顺序。

这些测试盯的不是"能不能重排"，而是三个容易写错、错了也不报错的判据：
1. 超出 `max_candidates` 的候选**不许打分**（没打分就排序等于编分数）；
2. scorer 出任何问题时**回退且结果非空**（把"重排失败"变成"没结果"是最坏的降级）；
3. 同分按原顺序，两次调用结果一致（可复现）。
"""

import pytest

from graph_engine_adapter import merged_rerank
from graph_engine_adapter.merged_rerank import ScorerError


def hit(text, file_id="f1"):
    return {"text": text, "sources": [{"file_id": file_id}]}


def rrf_hits(*texts):
    """模拟 merged.py 的输出形状：带 rrf_score / scopes_hit。"""
    return [{"text": t, "rrf_score": round(1.0 / (60 + i + 1), 6), "scopes_hit": [0]}
            for i, t in enumerate(texts)]


def by_index(scores_by_index):
    """桩 scorer：按下标给分；`None` 表示该条不打分（模拟模型漏答）。"""
    def scorer(query, candidates):
        return {c["id"]: scores_by_index[c["id"]]
                for c in candidates if scores_by_index.get(c["id"]) is not None}
    return scorer


def test_rerank_promotes_third_candidate():
    hits = rrf_hits("授信台账（两路共识，排第一）", "授信台账附件", "五级分类口径：关注指本金利息逾期")
    out = merged_rerank.rerank("五级分类口径中的关注是什么意思", hits,
                               scorer=by_index({"0": 0.05, "1": 0.1, "2": 0.95}), top_k=3)
    assert out["reranked"] is True and out["reason"] == "RERANKED"
    assert [h["text"] for h in out["hits"]][0] == "五级分类口径：关注指本金利息逾期"
    assert out["hits"][0]["rerank_score"] == 0.95
    assert out["hits"][0]["rrf_score"] == hits[2]["rrf_score"]   # 原 RRF 分数保留，不改写


def test_scorer_exception_falls_back_to_rrf_and_is_not_empty():
    hits = rrf_hits("甲", "乙", "丙")

    def broken(query, candidates):
        raise RuntimeError("端点 500")

    out = merged_rerank.rerank("问题", hits, scorer=broken, top_k=3)
    assert out["reranked"] is False and out["reason"] == "SCORER_ERROR"
    assert "端点 500" in out["detail"]
    assert [h["text"] for h in out["hits"]] == ["甲", "乙", "丙"]   # 顺序回到 RRF
    assert out["hits"] != []                                        # 关键：不是空结果


def test_missing_id_is_kept_after_scored_ones():
    hits = rrf_hits("甲", "乙", "丙")
    out = merged_rerank.rerank("问题", hits,
                               scorer=by_index({"0": 0.1, "1": 0.9, "2": None}), top_k=3)
    assert out["reranked"] is True
    assert [h["text"] for h in out["hits"]] == ["乙", "甲", "丙"]   # 漏答的丙排在后面，不丢
    assert out["unscored"] == 1
    assert "rerank_score" not in out["hits"][-1]


def test_empty_scores_falls_back():
    hits = rrf_hits("甲", "乙")
    out = merged_rerank.rerank("问题", hits, scorer=lambda q, c: {}, top_k=5)
    assert out["reranked"] is False and out["reason"] == "EMPTY_SCORES"
    assert [h["text"] for h in out["hits"]] == ["甲", "乙"]


def test_non_dict_and_unknown_index_are_scorer_errors():
    hits = rrf_hits("甲", "乙")
    out = merged_rerank.rerank("问题", hits, scorer=lambda q, c: [0.9, 0.1])
    assert out["reason"] == "SCORER_ERROR" and out["hits"]

    out2 = merged_rerank.rerank("问题", hits, scorer=lambda q, c: {"7": 0.9})
    assert out2["reason"] == "SCORER_ERROR" and out2["hits"]        # 越界下标 = 不可信

    out3 = merged_rerank.rerank("问题", hits, scorer=lambda q, c: {"0": "高"})
    assert out3["reason"] == "SCORER_ERROR" and out3["hits"]


def test_top_k_truncates_and_counts_dropped():
    hits = rrf_hits("甲", "乙", "丙", "丁")
    out = merged_rerank.rerank("问题", hits,
                               scorer=by_index({"0": 0.1, "1": 0.4, "2": 0.3, "3": 0.9}), top_k=2)
    assert [h["text"] for h in out["hits"]] == ["丁", "乙"]
    assert out["dropped"] == 2


def test_max_candidates_limits_scoring():
    hits = rrf_hits(*[f"文档{i}" for i in range(25)])
    seen = {}

    def scorer(query, candidates):
        seen["ids"] = [c["id"] for c in candidates]
        return {c["id"]: 0.5 for c in candidates}

    out = merged_rerank.rerank("问题", hits, scorer=scorer, top_k=5, max_candidates=20)
    assert len(seen["ids"]) == 20 and "20" not in seen["ids"]       # 第 21 条不参与打分
    assert out["candidates"] == 20
    assert "20" not in out["scores"]
    assert out["dropped"] == 20                                     # 25 条里只有 5 条入选
    assert out["reranked"] is True


def test_equal_scores_keep_rrf_order_and_are_reproducible():
    hits = rrf_hits("甲", "乙", "丙", "丁")
    scorer = by_index({str(i): 0.5 for i in range(4)})
    first = merged_rerank.rerank("问题", hits, scorer=scorer, top_k=4)
    second = merged_rerank.rerank("问题", hits, scorer=scorer, top_k=4)
    assert [h["text"] for h in first["hits"]] == ["甲", "乙", "丙", "丁"]   # 同分不动
    assert [h["text"] for h in first["hits"]] == [h["text"] for h in second["hits"]]


def test_empty_hits_or_no_scorer_returns_as_is():
    empty = merged_rerank.rerank("问题", [], scorer=lambda q, c: {"0": 1.0})
    assert empty["hits"] == [] and empty["reranked"] is False and empty["reason"] == "EMPTY_HITS"

    hits = rrf_hits("甲", "乙")
    plain = merged_rerank.rerank("问题", hits, scorer=None)
    assert [h["text"] for h in plain["hits"]] == ["甲", "乙"]
    assert plain["reranked"] is False and plain["reason"] == "NO_SCORER" and plain["dropped"] == 0

    zero = merged_rerank.rerank("问题", hits, scorer=lambda q, c: {"0": 1.0}, top_k=0)
    assert zero["reranked"] is False and zero["reason"] == "TOP_K_NON_POSITIVE"
    assert len(zero["hits"]) == 2


def test_timeout_falls_back_and_keeps_results():
    import time
    hits = rrf_hits("甲", "乙")

    def slow(query, candidates):
        time.sleep(0.5)
        return {"0": 1.0}

    out = merged_rerank.rerank("问题", hits, scorer=slow, timeout_s=0.05, top_k=2)
    assert out["reranked"] is False and out["reason"] == "TIMEOUT"
    assert [h["text"] for h in out["hits"]] == ["甲", "乙"]          # 超时不能变成没结果


def test_llm_scorer_parses_real_json():
    captured = {}

    def llm_call(messages, **kw):
        captured["messages"] = messages
        captured["kw"] = kw
        return '```json\n{"scores": {"0": 0.9, "1": 0.2}}\n```'

    scorer = merged_rerank.llm_scorer(llm_call, model="deepseek-flash")
    got = scorer("问题", [{"id": "0", "text": "相关段落"}, {"id": "1", "text": "无关段落"}])
    assert got == {"0": 0.9, "1": 0.2}
    assert captured["kw"] == {"model": "deepseek-flash"}             # 没瞎塞 temperature
    prompt = captured["messages"][-1]["content"]
    assert "[0]" in prompt and "[1]" in prompt and "问题" in prompt
    assert '"scores"' in captured["messages"][0]["content"]          # 要求只输出 JSON


def test_llm_scorer_omits_model_when_not_given():
    seen = {}

    def llm_call(messages, **kw):
        seen.update(kw)
        return '{"scores": {"0": 1}}'

    merged_rerank.llm_scorer(llm_call)("q", [{"id": "0", "text": "t"}])
    assert "model" not in seen and "temperature" not in seen


@pytest.mark.parametrize("bad", ["完全不是 JSON", '{"scores": {"5": 0.9}}',
                                 '{"scores": {"0": "高"}}', '{"scores": []}', ""])
def test_llm_scorer_raises_on_bad_output(bad):
    scorer = merged_rerank.llm_scorer(lambda messages, **kw: bad)
    with pytest.raises(ScorerError):
        scorer("q", [{"id": "0", "text": "t"}])


def test_llm_scorer_error_propagates_as_fallback_not_empty():
    """链路级：llm_scorer 抛 ScorerError → rerank 回退且非空。"""
    hits = rrf_hits("甲", "乙")
    scorer = merged_rerank.llm_scorer(lambda messages, **kw: "模型开始胡说八道")
    out = merged_rerank.rerank("问题", hits, scorer=scorer, top_k=2)
    assert out["reason"] == "SCORER_ERROR" and out["hits"]
    assert [h["text"] for h in out["hits"]] == ["甲", "乙"]
