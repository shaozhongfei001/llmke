"""R13 GraphRAG 检索侧入口：global 走社区摘要 reduce，local 走社区命中。"""
import httpx

from app.base import BaseResponse
from app.view.core.base_view import BaseView
from operators.common.log import logger

GRAPH_URL = "http://127.0.0.1:19529"


class RetrievalGlobalView(BaseView):
    async def post(self, payload: dict) -> BaseResponse:
        kb = payload.get("knowledge_base_name") or []
        if isinstance(kb, str):
            kb = [kb]
        if not kb:
            return BaseResponse(code=400, msg="knowledge_base_name 不能为空")
        body = {
            "space_name": kb[0].replace("g_", ""),
            "query": payload.get("query", ""),
            "mode": payload.get("query_mode", "global"),
            "top_k": payload.get("summary_top_k", 5),
            "model_info": payload.get("model_info") or {},
        }
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(f"{GRAPH_URL}/query_community", json=body)
            data = resp.json()
        if data.get("code") != 200:
            logger.error(f"社区摘要查询失败: {data}")
            return BaseResponse(code=500, msg=f"社区摘要查询失败: {data.get('msg')}")
        detail = data.get("data") or {}
        communities = detail.get("communities") or []
        # 转成与 documents_list 兼容的结构，便于 Java 侧复用引用渲染
        docs = []
        for c in communities:
            docs.append({
                "page_content": c.get("summary") or "",
                # R13-GRAPH-08：order_num 是 Java 侧引用/溯源的关联键，缺失会被 filterDocs 过滤成空引用
                "order_num": f"gc-{c.get('community_id')}",
                "type": "text",
                "score": c.get("score") if isinstance(c.get("score"), (int, float)) else 1.0,
                "metadata": {
                    # R13-GRAPH-03：社区摘要本身没有单文件定位，取社区成员的首个来源文件作为可打开的原文，
                    # 这样 Java 侧能沿用既有"引用->原文"链路（点击可打开对应文档）。
                    "file_id": (c.get("file_ids") or [None])[0],
                    "title": c.get("title") or f"社区摘要 L{c.get('level')}-{c.get('community_id')}",
                    "community_id": c.get("community_id"),
                    "level": c.get("level"),
                    "member_entities": c.get("members") or [],
                    "file_ids": c.get("file_ids") or [],
                    # 让溯源分句可处理：社区摘要视作整块文本（offset 覆盖全文）
                    "offset": [[0, len(c.get("summary") or "")]],
                    "chunk_type": "text",
                    "search": {"type": ["graph_community"], "query": body["query"], "rank": [len(docs)]},
                    "search_type": ["graph_community"],
                },
            })
        return BaseResponse(code=200, msg=f"社区摘要 {len(docs)} 条", data={
            "global_answer": detail.get("answer", ""),
            "community_summary_list": communities,
            "documents_list": docs,
            "truncated": detail.get("truncated", False),
        })
