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
            # R14-B：引用来源统一给**原文对象键**（bucket 相对路径，如 r12-rag/kb_9/x.docx/V0/x.docx）。
            # 背景：Java 侧对 metadata.source 一律 `endPoint + "/" + source`；
            #   给相对键 → 单个可解析 URL；给绝对 URL（旧路径来自 MySQL converted_file_path）
            #   → `http://h/http://h/...` 双 host，浏览器无法解析。
            src = (c.get("sources") or [None])[0] or ""
            # C15：优先用 chunk 级引用（具体块），没有再退回文件级 source。
            # 社区摘要本身不是原文，只有落到 chunk 才算"可回指"。
            chunk_refs = c.get("chunk_refs") or []
            first_ref = chunk_refs[0] if chunk_refs else None
            if first_ref and first_ref.get("source"):
                src = first_ref["source"]
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
                    # R14-B：community_id 本身已带 L<level>- 前缀，再拼一次会出 "L1-L1-xxxx"
                    "title": c.get("title") or f"社区摘要 {c.get('community_id')}",
                    "community_id": c.get("community_id"),
                    "level": c.get("level"),
                    "member_entities": c.get("members") or [],
                    "file_ids": c.get("file_ids") or [],
                    # R13-GRAPH-18：file_id 会随文档重传失效，带上文件名供 Java 侧按名回落
                    "file_names": c.get("file_names") or [],
                    # R14-B：非空时 Java 直接用它拼 endPoint（不再走 MySQL 绝对路径回落）
                    "source": src,
                    "sources_resolved_by": c.get("sources_resolved_by") or "",
                    # C15：chunk 级引用（pk + source + offset），前端引用卡片取第一条
                    "chunk_refs": chunk_refs,
                    "chunk_refs_stats": c.get("chunk_refs_stats") or {},
                    "chunk_pk": (first_ref or {}).get("pk"),
                    "chunk_index": (first_ref or {}).get("chunk_index"),
                    # 有 chunk 级 offset 就用它（能定位到具体块），否则整块文本覆盖全文
                    "offset": ((first_ref or {}).get("offset")
                               or [[0, len(c.get("summary") or "")]]),
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
