"""HybridRetrieval 阶段 3：RRF 按 pk 去重（HR-06）+ k=60。

验证 `alg_retrieval_service.app.reranker_service.merge_and_get_rrf_score` 的去重 key
从 `page_content` 精确字符串改为**平台整数 pk**：

1. 相同 pk、不同正文（ES 带标题 / 图无标题）→ 必须合并为 1 条，search_type 合并；
2. 不同 pk、相同正文 → 必须保留 2 条（禁止按正文精确字符串去重）；
3. pk 缺失 → 不错误合并（用进程内唯一占位）；
4. rrf_k 默认 60（rank=0 → 1/60）。

依赖说明：`reranker_service` 依赖 alg_retrieval_service 运行环境（langchain/httpx 等），
项目根测试环境若缺依赖则 `importorskip` 跳过，不伪装成通过。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/rag-alg/alg_retrieval_service/app"))

reranker_service = pytest.importorskip("reranker_service")
Document = pytest.importorskip("langchain_core.documents").Document


def mk(pk, text, search_type, rank=0):
    return Document(page_content=text, metadata={
        "pk": pk, "search": {"type": [search_type], "query": "q", "rank": [rank]}})


def test_same_pk_different_content_merges():
    d1 = mk(111, "正文A（ES 版，带标题）", "es", 0)
    d2 = mk(111, "正文A（图版，无标题）", "graph", 1)
    out = reranker_service.merge_and_get_rrf_score("q", {"q": [d1, d2]})["q"]
    assert len(out) == 1
    assert set(out[0].metadata["search_type"]) == {"es", "graph"}


def test_different_pk_same_content_keeps_both():
    d1 = mk(222, "相同正文", "es", 0)
    d2 = mk(333, "相同正文", "graph", 1)
    out = reranker_service.merge_and_get_rrf_score("q", {"q": [d1, d2]})["q"]
    assert len(out) == 2
    assert sorted(d.metadata["pk"] for d in out) == [222, 333]


def test_missing_pk_does_not_merge():
    d1 = mk(None, "无pkA", "es", 0)
    d2 = mk(None, "无pkB", "graph", 1)
    out = reranker_service.merge_and_get_rrf_score("q", {"q": [d1, d2]})["q"]
    assert len(out) == 2


def test_rrf_k_defaults_to_60():
    d = mk(444, "rank0", "es", 0)
    out = reranker_service.merge_and_get_rrf_score("q", {"q": [d]})["q"]
    assert out[0].metadata["score"] == pytest.approx(1 / 60)
