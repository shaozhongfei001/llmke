"""检索编排：先定路线，再调引擎，最后用断言层收口引用。

设计要点（对应设计 §6.5 与 §5）：
- **路线先判、原因留档**：`decide_route` 给出 GRAPH 或 DENSE_FALLBACK 及原因。
  "返回了结果"不能证明图执行过；强制图验收的查询必须看到 GRAPH，否则算不通过。
- **引擎不直接给答案**：引擎只给候选正文/来源，最终引用由平台断言层与引用校验决定。
- **依赖注入**：retriever 传进来，测试用假实现就能验编排逻辑，不必加载 1.9GB 模型。

`Retriever` 需要提供两个方法：
- `dense(query, top_k)`：稠密召回，返回 [{"text", "sources": [SourceRef-like dict]}]
- `graph(query, seeds, top_k)`：图召回，返回同样结构
两者返回的 `sources` 必须带 `file_id`，否则引用校验无法工作。
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from .assertions import GRAPH, AssertionStore, decide_route
from .fence import FenceState, assert_index_fresh, filter_hits

SCHEMA = "llmke.graph-engine.retrieve.v1"


def _norm_sources(raw: Iterable[Any]) -> List[Dict[str, str]]:
    out = []
    for item in raw or []:
        if isinstance(item, dict):
            out.append({"file_id": str(item.get("file_id", "")),
                        "artifact_id": str(item.get("artifact_id", "")),
                        "channel": str(item.get("channel", "text"))})
        else:  # 允许直接给对象
            out.append({"file_id": str(getattr(item, "file_id", "")),
                        "artifact_id": str(getattr(item, "artifact_id", "")),
                        "channel": str(getattr(item, "channel", "text"))})
    return [s for s in out if s["file_id"]]


def find_seeds(query: str, store: AssertionStore) -> List[str]:
    """从查询里认出已知实体名；认不出就是没有种子，不要瞎猜。"""
    seeds = []
    for name in list(store.entity_names()):
        if name and name in query:
            cid = store.resolve(name)
            if cid and cid not in seeds:
                seeds.append(cid)
    return seeds


def retrieve(query: str, *, store: AssertionStore, retriever: Any,
             graph_enabled: bool = True, seeds: Optional[Sequence[str]] = None,
             top_k: int = 3, scopes: Optional[Set[str]] = None,
             known_files: Optional[Iterable[str]] = None,
             require_graph: bool = False, fence: Optional[FenceState] = None,
             index_generation: Optional[int] = None) -> Dict[str, Any]:
    """返回 {route, reason, hits, citations, invalid_citations, passed}。

    `require_graph=True` 用于强制图验收：一旦回退到稠密，`passed=False`，
    即使拿到了看起来合理的正文。
    """
    seeds = list(seeds) if seeds is not None else find_seeds(query, store)
    decision = decide_route(graph_enabled, seeds, store, scopes)
    route, reason = decision["route"], decision["reason"]

    if route == GRAPH:
        raw = retriever.graph(query, seeds, top_k)
    else:
        raw = retriever.dense(query, top_k)

    # 撤权 fence：先验索引代次，再按来源过滤。顺序不能反——
    # 只过滤不验代次，等于赌引擎一定会把撤权内容吐出来让我们拦。
    fence_info = {"generation": None, "dropped": []}
    if fence is not None:
        assert_index_fresh(index_generation, fence)
        fence_info["generation"] = fence.generation
        filtered = filter_hits(raw or [], fence)
        raw = filtered["hits"]
        fence_info["dropped"] = filtered["dropped"]
        if known_files is not None:
            known_files = {f for f in known_files if not fence.is_revoked(f)}

    hits = []
    for item in raw or []:
        hits.append({"text": item.get("text", ""), "sources": _norm_sources(item.get("sources"))})

    # 引用收口：把命中来源对回断言，再校验这些文件是否仍可见
    cited, invalid = [], []
    known = set(known_files) if known_files is not None else None
    for hit in hits:
        for src in hit["sources"]:
            facts = store.facts_by_source(src["file_id"])
            for fact in facts:
                label = f"{fact.subject}.{fact.predicate}@{src['file_id']}"
                bucket = cited
                if known is not None and src["file_id"] not in known:
                    bucket = invalid
                if label not in [x["label"] for x in bucket]:
                    bucket.append({"label": label, "assertion": fact.content_key()[:4],
                                   "sources": [s.file_id for s in fact.sources]})

    # 引擎自报的**实际**路线优先于我们的计划：计划是意图，执行才是事实
    executed_route = getattr(retriever, "last_executed_route", None)
    route_matches = None if executed_route is None else (executed_route == route)

    passed = bool(hits)
    if require_graph:
        # 强制图验收只认引擎 trace：计划走图但引擎内部回退，同样算不通过
        if executed_route is None:
            passed = False
        elif executed_route != GRAPH:
            passed = False

    return {"schema": SCHEMA, "query": query, "route": route, "reason": reason,
            "executed_route": executed_route, "route_matches": route_matches,
            "seeds": seeds, "hit_count": len(hits), "hits": hits[:top_k],
            "citations": cited, "invalid_citations": invalid,
            "require_graph": require_graph, "fence": fence_info, "passed": passed}
