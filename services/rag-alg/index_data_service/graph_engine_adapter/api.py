"""V2 图服务的 HTTP 边界（最小切片）。

为什么单独一层：`graph_engine_adapter` 目前只被 `scripts/v2_*` 调用，产品
（Java/前端）没有任何入口能触达 HippoRAG。这里先把"建图结果可查询"暴露成
稳定 HTTP 契约，产品接线才有落点。

边界与限制（明确写出来，避免被当成已交付）：
- 本层只包 `HippoRAGEngine.retrieve`，不做答案生成；
- 返回 `executed_route` 与 `trace`，图是否真的跑过由引擎侧痕迹决定，不由本层猜；
- 引用来源依赖 payload 的 file_id/locator；快照里没有来源映射时返回空数组并置
  `sources_available=false`，不伪造来源。

启动：
    uvicorn graph_engine_adapter.api:app --host 127.0.0.1 --port 18094

环境变量：
    LLMKE_V2_SNAPSHOT       必填，快照目录
    LLMKE_V2_LLM_BASE_URL   默认 http://127.0.0.1:18092/v1
    LLMKE_V2_EMBED_BASE_URL 默认 http://127.0.0.1:18090/v1
"""

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

SCHEMA = "llmke.graph-api.v1"


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


def _load_engine() -> Any:
    from .engine_hipporag import HippoRAGEngine

    snapshot = os.environ.get("LLMKE_V2_SNAPSHOT")
    if not snapshot:
        raise RuntimeError("LLMKE_V2_SNAPSHOT 未设置")
    return HippoRAGEngine(
        save_dir=snapshot,
        llm_base_url=os.environ.get("LLMKE_V2_LLM_BASE_URL", "http://127.0.0.1:18092/v1"),
        embedding_base_url=os.environ.get("LLMKE_V2_EMBED_BASE_URL", "http://127.0.0.1:18090/v1"),
    )


def create_app(engine_factory=None) -> FastAPI:
    """engine_factory 用于测试注入；生产按环境变量加载。"""
    app = FastAPI(title="LLMKE V2 Graph API", version=SCHEMA)
    state: Dict[str, Any] = {"engine": None}

    def engine() -> Any:
        if state["engine"] is None:
            state["engine"] = (engine_factory or _load_engine)()
        return state["engine"]

    @app.get("/health")
    def health() -> Dict[str, Any]:
        eng = engine()
        hp = getattr(eng, "hp", None)
        graph = getattr(hp, "graph", None) if hp is not None else None
        # facts 是三元组条数，不是 openie 文档数——按文档数报会把 69 条说成 10 条。
        facts = None
        if hasattr(eng, "openie_docs"):
            facts = sum(len(d.get("extracted_triples") or []) for d in eng.openie_docs())
        return {
            "schema": SCHEMA,
            "status": "ok",
            "snapshot": getattr(eng, "save_dir", None),
            "nodes": graph.vcount() if graph is not None else None,
            "edges": graph.ecount() if graph is not None else None,
            "facts": facts,
        }

    @app.post("/v2/graph/query")
    def query(req: QueryRequest) -> Dict[str, Any]:
        out = engine().retrieve(req.query, top_k=req.top_k)
        docs = list(out.get("docs") or [])
        return {
            "schema": SCHEMA,
            "query": req.query,
            "executed_route": out.get("executed_route"),
            "reason": out.get("reason"),
            "trace": out.get("trace"),
            "hit_count": len(docs),
            "docs": [{"rank": i + 1, "text": text} for i, text in enumerate(docs)],
            # 来源映射缺失时明确置 false，调用方不得把空数组当"无来源"
            "citations": [],
            "sources_available": False,
        }

    return app


app = create_app()
