"""V2 图服务的 HTTP 边界（最小切片）。

为什么单独一层：`graph_engine_adapter` 目前只被 `scripts/v2_*` 调用，产品
（Java/前端）没有任何入口能触达 HippoRAG。这里先把"建图 + 可查询"暴露成
稳定 HTTP 契约，产品接线才有落点。

边界与限制（明确写出来，避免被当成已交付）：
- 只包 `HippoRAGEngine` 的 build/retrieve，不做答案生成；
- 返回 `executed_route` 与 `trace`，图是否真的跑过由引擎侧痕迹决定，不由本层猜；
- 来源映射由 build 时写入快照的 `sources.json` 提供；没有映射时
  `sources_available=false` 且 citations 为空，不伪造来源。

启动：
    uvicorn graph_engine_adapter.api:app --host 127.0.0.1 --port 18094

环境变量：
    LLMKE_V2_SNAPSHOT       查询用快照目录（build 后可指向新快照）
    LLMKE_V2_ROOT           build 的根目录，默认 .artifacts/api-root
    LLMKE_V2_LLM_BASE_URL   默认 http://127.0.0.1:18092/v1
    LLMKE_V2_EMBED_BASE_URL 默认 http://127.0.0.1:18090/v1
"""

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import global_report

SCHEMA = "llmke.graph-api.v1"


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class GlobalRequest(BaseModel):
    """global 问答：只读建图时落盘的 community.json，不现场改图、不另做检索。"""
    query: str = ""
    max_communities: int = Field(default=3, ge=1, le=20)


class BuildDoc(BaseModel):
    file_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    locator: Optional[str] = None
    title: Optional[str] = None


class BuildRequest(BaseModel):
    docs: List[BuildDoc] = Field(default_factory=list)
    root: Optional[str] = None
    # 同一份 ParseArtifact 的绑定信息；给了就必须通过校验，否则 400，不允许"降级成裸文本"。
    artifact: Optional[Dict[str, Any]] = None


def _urls() -> Dict[str, str]:
    return {
        "llm": os.environ.get("LLMKE_V2_LLM_BASE_URL", "http://127.0.0.1:18092/v1"),
        "embed": os.environ.get("LLMKE_V2_EMBED_BASE_URL", "http://127.0.0.1:18090/v1"),
    }


def _load_engine(snapshot: Optional[str] = None) -> Any:
    from .engine_hipporag import HippoRAGEngine

    snapshot = snapshot or os.environ.get("LLMKE_V2_SNAPSHOT")
    if not snapshot:
        raise RuntimeError("LLMKE_V2_SNAPSHOT 未设置")
    urls = _urls()
    return HippoRAGEngine(save_dir=snapshot, llm_base_url=urls["llm"],
                          embedding_base_url=urls["embed"])


def _load_sources(snapshot: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    if not snapshot:
        return {}
    path = os.path.join(snapshot, "sources.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def _text_to_idx(engine: Any) -> Dict[str, str]:
    """块文本 → openie idx。块 id 是文本哈希，passage 就是原文，可精确对上。"""
    out: Dict[str, str] = {}
    for doc in engine.openie_docs():
        passage, idx = doc.get("passage"), doc.get("idx")
        if passage and idx:
            out.setdefault(passage, idx)
    return out


def _default_build(docs: List[BuildDoc], root: str) -> Dict[str, Any]:
    from .engine_hipporag import HippoRAGEngine
    from .fence import FenceState
    from .rebuild import rebuild

    urls = _urls()
    live = [{"file_id": d.file_id, "text": d.text, "locator": d.locator,
             "title": d.title} for d in docs]
    fence = FenceState()

    def full_build(items, target):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=urls["llm"],
                                embedding_base_url=urls["embed"])
        return engine.build([x["text"] for x in items])

    result = rebuild(root, fence, live, full_build, fencing=1)
    target = result["current"]["dir"]

    # 写来源映射：idx → [{file_id, locator}]。不写的话查询层只能返回空引用。
    engine = HippoRAGEngine(save_dir=target)
    by_text = _text_to_idx(engine)
    sources: Dict[str, List[Dict[str, Any]]] = {}
    for item in live:
        idx = by_text.get(item["text"])
        if not idx:
            continue
        sources.setdefault(idx, []).append(
            {k: v for k, v in (("file_id", item["file_id"]), ("locator", item["locator"]),
                               ("title", item.get("title"))) if v}
        )
    with open(os.path.join(target, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(sources, fh, ensure_ascii=False, indent=1)

    # 真实计数供 legacy 兼容层回填 edges_total/edges_written：
    # 不返回就会出现"建图成功但 Java 判 0 边失败"的假阴性。
    facts = sum(len(d.get("extracted_triples") or []) for d in engine.openie_docs())
    graph = getattr(getattr(engine, "hp", None), "graph", None)
    return {
        "snapshot": target,
        "generation": result["current"].get("generation"),
        "documents": result["current"].get("documents"),
        "chunks": (result.get("build_result") or {}).get("chunks"),
        "sources": len(sources),
        "facts": facts,
        "edges": graph.ecount() if graph is not None else None,
    }


def create_app(engine_factory=None, builder=None) -> FastAPI:
    """engine_factory / builder 用于测试注入；生产按环境变量加载。"""
    app = FastAPI(title="LLMKE V2 Graph API", version=SCHEMA)
    state: Dict[str, Any] = {"engine": None, "text_to_idx": None, "snapshot": None}

    def engine() -> Any:
        if state["engine"] is None:
            state["engine"] = (engine_factory or (lambda: _load_engine(state["snapshot"])))()
        return state["engine"]

    def idx_map() -> Dict[str, str]:
        if state["text_to_idx"] is None:
            state["text_to_idx"] = _text_to_idx(engine())
        return state["text_to_idx"]

    @app.get("/health")
    def health() -> Dict[str, Any]:
        eng = engine()
        hp = getattr(eng, "hp", None)
        graph = getattr(hp, "graph", None) if hp is not None else None
        # facts 是三元组条数，不是 openie 文档数——按文档数报会把 76 条说成 10 条。
        facts = None
        if hasattr(eng, "openie_docs"):
            facts = sum(len(d.get("extracted_triples") or []) for d in eng.openie_docs())
        snapshot = getattr(eng, "save_dir", None)
        return {
            "schema": SCHEMA,
            "status": "ok",
            "snapshot": snapshot,
            "nodes": graph.vcount() if graph is not None else None,
            "edges": graph.ecount() if graph is not None else None,
            "facts": facts,
            # 数字全部来自快照里的 community.json；没有报告就说没接上，不填 0 冒充。
            "community": global_report.stats(snapshot),
        }

    @app.post("/v2/graph/build")
    def build(req: BuildRequest) -> Dict[str, Any]:
        docs = req.docs
        bound: Optional[Dict[str, Any]] = None
        if req.artifact is not None:
            from .artifact_binding import ArtifactBindingError, bind_artifact

            try:
                bound = bind_artifact(req.artifact)
            except ArtifactBindingError as exc:
                raise HTTPException(status_code=400, detail=f"artifact invalid: {exc}") from exc
            docs = [BuildDoc(**d) for d in bound["docs"]]
        if not docs:
            raise HTTPException(status_code=400,
                                detail="docs 与 artifact 至少给一个（空请求不能建图）")
        root = req.root or os.environ.get("LLMKE_V2_ROOT") or ".artifacts/api-root"
        try:
            out = (builder or _default_build)(docs, root)
        except Exception as exc:  # noqa: BLE001 - 失败要带原因回到调用方
            raise HTTPException(status_code=500,
                                detail=f"build failed: {type(exc).__name__}: {exc}") from exc
        # 新快照可以立刻被查询：重置缓存，指向新目录（不改进程环境变量）
        state["engine"] = None
        state["text_to_idx"] = None
        state["snapshot"] = str(out.get("snapshot") or "")
        # 构建后立刻预热：否则首次查询要现场加载图与向量，实测会空响应/超时。
        # 预热失败不影响构建结果，查询时会再报真实错误。
        try:
            hp = getattr(engine(), "hp", None)
            if hp is not None and hasattr(hp, "prepare_retrieval_objects"):
                hp.prepare_retrieval_objects()
        except Exception:  # noqa: BLE001
            pass
        if bound is not None:
            out = {**out, "artifact_id": bound["artifact_id"],
                   "content_hash": bound["content_hash"]}
        # 建图成功即产社区报告（global 的前提）：报告读的是刚落盘快照里的 openie 结果与
        # sources.json，所以和查询用的是同一份数据，不存在"报告说 A、检索给 B"。
        # 报告失败不影响建图结果（图已经建好了），但必须在响应里写明失败原因，不能装作没这回事。
        snapshot = str(state["snapshot"] or "")
        try:
            community = global_report.write(snapshot, [d.file_id for d in docs])
        except Exception as exc:  # noqa: BLE001 - 报告失败要带原因回调用方
            community = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}",
                         "snapshot": snapshot}
        return {"schema": SCHEMA, "status": "BUILT", **out, "community": community}

    @app.post("/v2/graph/query")
    def query(req: QueryRequest) -> Dict[str, Any]:
        eng = engine()
        out = eng.retrieve(req.query, top_k=req.top_k)
        docs = list(out.get("docs") or [])
        mapping = idx_map()
        sources = _load_sources(getattr(eng, "save_dir", None))
        items = []
        for i, text in enumerate(docs):
            idx = mapping.get(text)
            items.append({"rank": i + 1, "text": text, "idx": idx,
                          "sources": sources.get(idx, []) if idx else []})
        return {
            "schema": SCHEMA,
            "query": req.query,
            "executed_route": out.get("executed_route"),
            "reason": out.get("reason"),
            "trace": out.get("trace"),
            "hit_count": len(items),
            "docs": items,
            "citations": [s for it in items for s in it["sources"]],
            "sources_available": bool(sources),
        }

    @app.post("/v2/graph/global")
    def graph_global(req: GlobalRequest) -> Dict[str, Any]:
        """global 问答：答案只能由 community.json 里的社区事实拼装，逐条带来源。

        三种"不给答案"的情形都返回 200 + 空答案 + 原因，不用普通检索顶替：
        报告不存在（NOT_READY）、没有社区（NO_COMMUNITIES）、引用校验不过（CITATION_INVALID）。
        """
        eng = engine()
        snapshot = getattr(eng, "save_dir", None) or state["snapshot"]
        report = global_report.load(snapshot)
        base = {"schema": SCHEMA, "snapshot": snapshot, "query": req.query}
        if report is None:
            return {**base, "status": "NOT_READY", "communities": 0, "answer": "",
                    "citations": [], "sections": [],
                    "citation_check": {"ok": False, "checked": 0, "valid": [], "invalid": [],
                                       "sources_available": False,
                                       "reason": "NO_COMMUNITY_REPORT",
                                       "detail": "该快照没有 community.json（重建图后才会生成）"},
                    "reason": "NO_COMMUNITY_REPORT"}

        check = dict(report.get("citation_check") or {})
        sections = list(report.get("communities") or [])
        answer, citations, answer_stats = global_report.assemble_answer(
            sections, max_communities=req.max_communities, query=req.query)

        reason = None
        if not check.get("ok"):
            # 引用失效比"没有社区"更能解释问题（幽灵来源会把事实全挡在导出阶段，
            # 只报 NO_COMMUNITIES 就等于把"引用坏了"说成"语料没社区"）。
            reason = check.get("reason") or "CITATION_INVALID"
            if reason == "NO_FACTS" and not sections:
                reason = "NO_COMMUNITIES"
        elif not sections:
            reason = "NO_COMMUNITIES"
        elif not answer:
            # 社区在、但按 query 过滤后一条相关事实都不剩：如实说"没有相关事实"，
            # 不拿无关条款拼一个看起来能答的答案（也不要静默返回 200 + 空串 + reason=null）。
            reason = "NO_RELEVANT_FACTS"
        if reason and reason != "NO_RELEVANT_FACTS":
            # 引用不过或没有社区时，答案与引用一律留空：宁可说不可用，不给无来源结论。
            answer, citations = "", []

        # 只有答案真正用到的那几个社区要出去，别把 34 个社区整包塞给调用方。
        used: List[str] = []
        for item in citations:
            cid = item.get("community")
            if cid not in used:
                used.append(cid)
        return {**base, "status": report.get("status"), "communities": len(sections),
                "answer": answer, "citations": citations, "sections": sections,
                "used_communities": used, "citation_check": check, "reason": reason,
                # 过滤明细（只增不改既有键）：多少条事实被阈值/上限挡掉，避免静默丢数据。
                "answer_stats": answer_stats}

    return app


app = create_app()
