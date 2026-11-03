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
    # 查询侧实体种子（平台 `query_seed_recognition` 的结果，形如 ["ent:智造贷"] 或裸名）。
    # 之前 HTTP 层没有这个字段，种子永远到不了引擎 —— 线上 trace 里 seed_hits 恒为 []。
    seeds: List[str] = Field(default_factory=list)
    # D6 禁用图对照：false 时强制走稠密并标 DENSE_FALLBACK/GRAPH_DISABLED，
    # 不允许把稠密命中冒充满图检索。
    enable_graph: bool = True


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
    _ensure_cjk_compat()
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


def _auto_seeds(query: str, snapshot: Optional[str]) -> List[str]:
    """T-A6：调用方没给种子时，从快照 openie 实体里自动识别。

    与服务端 pipeline.find_seeds 同一套匹配口径（唯一实体才算种子），
    认不出就返回空列表，不瞎猜。bare 名由引擎 `_to_engine_key` 换算。
    """
    if not query or not str(query).strip():
        return []
    names: List[str] = []
    for doc in global_report._openie_docs(snapshot):
        for e in doc.get("extracted_entities") or []:
            if isinstance(e, str) and e.strip():
                names.append(e.strip())
        for t in doc.get("extracted_triples") or []:
            if isinstance(t, (list, tuple)):
                for end in (t[0], t[-1]):
                    if isinstance(end, str) and end.strip():
                        names.append(end.strip())
    names = sorted(set(names))
    if not names:
        return []
    from . import seed_match

    result = seed_match.match_seeds(query, names, resolve=lambda n: n)
    return list(result["seeds"])


def _default_build(docs: List[BuildDoc], root: str) -> Dict[str, Any]:
    from .engine_hipporag import HippoRAGEngine
    from .fence import FenceState
    from .rebuild import rebuild

    # 建图前装中文补丁：index() 期就调用 text_processing 做实体键，装晚了中文实体全是空串。
    _ensure_cjk_compat()
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


def _install_cjk_compat() -> Dict[str, Any]:
    """按需安装中文 text_processing 补丁，返回可写进 health/证据的安装报告。

    默认安装（`LLMKE_V2_CJK_COMPAT` 未设或不为 "0"）：不做这件事，产品的图检索在中文
    语料上恒等于空事实，D6/D9 都无从成立。装了必须能在 health 里看见，不许静默偏离上游。
    """
    if os.environ.get("LLMKE_V2_CJK_COMPAT", "1") == "0":
        return {"installed": False, "reason": "disabled_by_env:LLMKE_V2_CJK_COMPAT=0"}
    try:
        from .hipporag_compat import install_cjk_text_processing

        report = install_cjk_text_processing()
        return {"installed": True, **report}
    except Exception as exc:  # noqa: BLE001 - 装不上要带原因出来，不当成没发生
        return {"installed": False, "reason": f"{type(exc).__name__}: {exc}"}


# 进程级安装结果：health 要能读到"这个进程到底装没装"，不能每次查询重装一遍。
_CJK_STATE: Dict[str, Any] = {}


def _ensure_cjk_compat() -> Dict[str, Any]:
    """真正的安装点：只有**构造真实引擎**时才装。

    不能在 `create_app` 里装：本模块尾部就有 `app = create_app()`，一 import 就产生全局副作用，
    测试里"导入补丁模块不应改变上游行为"（tests/test_graph_hipporag_compat.py）会被悄悄破坏。
    装在"要建图/要查询"这一刻，语义也更准：补丁影响的正是 index/retrieve 两条路径。
    """
    if not _CJK_STATE:
        _CJK_STATE.update(_install_cjk_compat())
    return _CJK_STATE


def create_app(engine_factory=None, builder=None) -> FastAPI:
    """engine_factory / builder 用于测试注入；生产按环境变量加载。"""
    app = FastAPI(title="LLMKE V2 Graph API", version=SCHEMA)
    # 中文兼容补丁：产品路径（HTTP）**默认安装**，因为交付要求"中文默认可用"。
    # 之前只有 scripts/v2_* 里显式调用，服务端从不安装 —— 结果 18094 上
    # text_processing 仍把中文清成空串，事实变成 ("","","5000")、种子换算撞空实体。
    # 可用 LLMKE_V2_CJK_COMPAT=0 显式关掉（对照实验用），关掉时 health 必须如实报。
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
            # 中文补丁装没装必须可见：装了是"偏离上游"，没装则中文事实为空。
            "cjk_compat": dict(_CJK_STATE) or {"installed": None, "reason": "engine_not_loaded"},
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
        seeds = list(req.seeds)
        seeds_source = "caller" if seeds else "none"
        if not seeds and req.enable_graph:
            auto = _auto_seeds(req.query, getattr(eng, "save_dir", None))
            if auto:
                seeds, seeds_source = auto, "auto"
        out = eng.retrieve(req.query, seeds=seeds, top_k=req.top_k,
                           use_graph=req.enable_graph)
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
            "seeds": list(seeds),
            "seeds_source": seeds_source,
            "graph_enabled": bool(req.enable_graph),
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
        # 来源元数据：sources.json 里 file_id -> {locator,title}。
        # 报告本身只记 file_id（引用校验的最小集合），但页面/Java 需要 title 才能显示文件名。
        source_meta: Dict[str, Any] = {}
        for items in (global_report.read_sources(snapshot) or {}).values():
            for src in items or []:
                fid = str(src.get("file_id") or "")
                if fid and fid not in source_meta:
                    source_meta[fid] = {"file_id": fid, "locator": src.get("locator"),
                                        "title": src.get("title")}
        return {**base, "status": report.get("status"), "communities": len(sections),
                "answer": answer, "citations": citations, "sections": sections,
                "source_meta": source_meta,
                "used_communities": used, "citation_check": check, "reason": reason,
                # 过滤明细（只增不改既有键）：多少条事实被阈值/上限挡掉，避免静默丢数据。
                "answer_stats": answer_stats}

    return app


app = create_app()
