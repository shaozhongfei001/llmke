"""R13 GraphRAG 检索侧入口：global 走社区摘要 reduce，local 走社区命中。"""
import httpx

from app.base import BaseResponse
from app.view.core.base_view import BaseView
from operators.common.log import logger

GRAPH_URL = "http://127.0.0.1:19529"
# V2 图服务（HippoRAG）。V2 建图不写 Nebula / community_summary_<kb>，
# 所以 global 模式在 V2 库上必须能回退到它，否则恒返回 0 条。
V2_GRAPH_URL = "http://127.0.0.1:18094"
ES_URL = "http://127.0.0.1:19200"


class RetrievalGlobalView(BaseView):
    async def post(self, payload: dict) -> BaseResponse:
        kb = payload.get("knowledge_base_name") or []
        if isinstance(kb, str):
            kb = [kb]
        if not kb:
            return BaseResponse(code=400, msg="knowledge_base_name 不能为空")
        space_name = kb[0].replace("g_", "")
        query = payload.get("query", "")
        top_k = payload.get("summary_top_k", 5)

        # HR-10（阶段 4）：global 主链路切到 18094 community.json，不再走 19529→Nebula Louvain。
        # 18094 的答案只由 community.json 的社区事实拼装、逐条带来源；不命中时回退图检索。
        data = None
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(f"{V2_GRAPH_URL}/v2/graph/global",
                                         json={"query": query, "max_communities": top_k,
                                               "kb": space_name})
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - 上游不可达时走图检索回退
            logger.error(f"V2 global 查询失败，转图检索回退: {exc}")

        answer = (data or {}).get("answer") or ""
        if data and answer:
            # 命中社区事实：把 citations（answer 实际用到的 fact）转成可回指的 documents_list
            docs = await self._convert_global_citations(space_name, query, data)
            # 社区 fact 是 HippoRAG 抽取的关系事实，对「过程型/如何做」问题常零散（丢失步骤
            # 细节与数值）；图检索返回的原文 chunk 才含具体步骤。这里补充图检索原文一起生成，
            # 避免英文「How should I grow tomatoes」只给零散原则、不给具体种植步骤。
            graph_docs = await self._fallback_v2_query(space_name, query, top_k)
            combined = (graph_docs or []) + docs
            # 18094 的 answer 是「事实+来源」碎片拼接（assemble_answer），直接返回会让
            # 英文/事实型 query 变成零散列表（用户实测退化）。这里用 LLM 基于事实+原文生成
            # 连贯回答，对齐旧 19529 query_community 的 requests_llm 行为；LLM 失败时回退碎片。
            coherent = await self._summarize_v2_docs(combined, query, payload.get("model_info") or {})
            return BaseResponse(code=200, msg=f"社区摘要命中 {len(docs)} 条", data={
                "global_answer": coherent or answer,
                "community_summary_list": [],
                "documents_list": docs,
                "truncated": False,
            })

        # 回退：community.json 没命中该问句时，走 18094 图检索给出可回指 chunk 的原文块。
        fallback_docs = await self._fallback_v2_query(space_name, query, top_k)
        if fallback_docs:
            # Java 侧 global 分支只看 global_answer，不看 documents（AiServiceImpl：
            # "现有社区摘要不足以回答该问题" = global_answer 为空、且禁止回落二次生成的产物）。
            # 所以回退必须自己产出答案，否则前端仍显示"抱歉，未能找到您要的答案"。
            answer = await self._summarize_v2_docs(
                fallback_docs, query, payload.get("model_info") or {})
            return BaseResponse(
                code=200, msg=f"社区摘要 0 条，已回退图检索 {len(fallback_docs)} 条",
                data={
                    "global_answer": answer,
                    "community_summary_list": [],
                    "documents_list": fallback_docs,
                    "truncated": False,
                    "fallback": "v2_graph_query",
                })

        return BaseResponse(code=200, msg="无相关社区事实", data={
            "global_answer": "",
            "community_summary_list": [],
            "documents_list": [],
            "truncated": False,
        })

    async def _convert_global_citations(self, kb: str, query: str, data: dict) -> list:
        """把 18094 global 的 citations（answer 实际用到的 fact）转成 documents_list。

        citation = {community, text, sources:[file_id,...]}；source_meta 提供 file_id→title/locator。
        反查 ES 拿 MinIO 对象键（source），Java 侧拼 endPoint + source 才能打开原文。
        """
        citations = data.get("citations") or []
        source_meta = data.get("source_meta") or {}
        file_ids = [str(s) for c in citations for s in (c.get("sources") or []) if s]
        source_map = await self._resolve_sources(kb, file_ids)
        docs = []
        for i, c in enumerate(citations):
            sources = [str(s) for s in (c.get("sources") or []) if s]
            first = sources[0] if sources else None
            meta = source_meta.get(first, {}) if first else {}
            docs.append({
                "page_content": c.get("text") or "",
                "order_num": f"gc-{c.get('community')}-{i}",
                "type": "text",
                "score": 1.0,
                "metadata": {
                    "file_id": first,
                    "title": meta.get("title"),
                    "community_id": c.get("community"),
                    "file_ids": sources,
                    "source": source_map.get(first, "") if first else "",
                    "locator": meta.get("locator"),
                    "chunk_type": "text",
                    "search": {"type": ["graph_community"], "query": query, "rank": [i]},
                    "search_type": ["graph_community"],
                },
            })
        return docs

    async def _fallback_v2_query(self, kb: str, query: str, top_k) -> list:
        """V2 图检索回退：返回可回指到 chunk 的原文块。"""
        try:
            limit = max(1, min(int(top_k or 5), 20))
        except (TypeError, ValueError):
            limit = 5
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(f"{V2_GRAPH_URL}/v2/graph/query",
                                         json={"query": query, "top_k": limit, "kb": kb})
                d = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"V2 图检索回退失败: {exc}")
            return []
        if d.get("executed_route") != "GRAPH":
            logger.warning(f"V2 图检索未走 GRAPH 路由: {d.get('executed_route')} {d.get('reason')}")
            return []
        items = [x for x in (d.get("docs") or []) if (x.get("text") or "").strip()]
        source_map = await self._resolve_sources(kb, [
            (x.get("sources") or [{}])[0].get("file_id") for x in items])
        docs = []
        for i, item in enumerate(items):
            src = (item.get("sources") or [{}])[0]
            text = item.get("text") or ""
            fid = src.get("file_id")
            docs.append({
                "page_content": text,
                "order_num": f"v2-{item.get('idx') or i}",
                "type": "text",
                "score": 1.0,
                "metadata": {
                    "file_id": fid,
                    "title": src.get("title"),
                    # Java 侧用 endPoint + "/" + source 拼原文地址；缺失会导致引用打不开
                    "source": source_map.get(str(fid), ""),
                    "locator": src.get("locator"),
                    "chunk_pk": src.get("pk"),
                    "offset": [[0, len(text)]],
                    "chunk_type": "text",
                    "search": {"type": ["graph"], "query": query, "rank": [i]},
                    "search_type": ["graph"],
                },
            })
        return docs

    async def _summarize_v2_docs(self, docs: list, query: str, model_info: dict) -> str:
        """用检索到的 V2 原文块生成答案（global 分支要求非空 global_answer）。"""
        if not docs:
            return ""
        ctx = "\n".join(
            f"[{i + 1}] {(d.get('page_content') or '')[:600]}"
            for i, d in enumerate(docs[:8])
        )
        # 语言跟随：qwen 对英文 query 常回落中文（用户实测），显式指定输出语言
        is_zh = any('\u4e00' <= c <= '\u9fff' for c in query)
        lang_hint = "必须用中文回答" if is_zh else "必须用英文回答（Answer in English only）"
        messages = [
            {"role": "system",
             "content": "你是知识库问答助手。严格只依据给定资料作答，禁止编造、推测或补充资料中没有的信息；"
                        "若资料中没有直接相关内容，必须明确回答「资料中未提及」，不得猜测或发挥。"
                        f"简明扼要。输出语言要求：{lang_hint}。"},
            {"role": "user", "content": f"资料：\n{ctx}\n\n问题：{query}"},
        ]
        try:
            from app.base import server_config
            llm = (server_config or {}).get("llm_server") or {}
            host = llm.get("host", "127.0.0.1")
            port = llm.get("port", 18092)
            api = str(llm.get("api_name") or "v1/chat/completions").lstrip("/")
            # 注意：不能走 retrieval_fun_tool.requests_llm —— 它发的是 {"prompt_msg": ...}
            # 私有协议，当前 LLM 网关（OpenAI 兼容，18092）只认 {"messages": [...]}，
            # 实测直接返回 400 "'messages' is required"。
            headers = {"Content-Type": "application/json"}
            if model_info.get("key"):
                headers["Authorization"] = f"Bearer {model_info['key']}"
            payload = {
                "model": model_info.get("model_name") or "qwen2.5-7b-instruct",
                "messages": messages,
                "stream": False,
                "temperature": 0.2,
                "max_tokens": 800,
            }
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(f"http://{host}:{port}/{api}",
                                         json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            choices = data.get("choices") or []
            text = ((choices[0].get("message") or {}).get("content") if choices else "") or ""
            return text.strip()
        except Exception as exc:  # noqa: BLE001 - 生成失败就退回原文摘录，不阻断回答
            logger.warning(f"V2 回退答案生成失败，改用原文摘录: {exc}")
            return "\n".join(
                f"- {(d.get('page_content') or '').strip()[:200]}" for d in docs[:5])

    async def _resolve_sources(self, kb: str, file_ids) -> dict:
        """按 file_id 反查 ES 里的 MinIO 对象键，供引用打开原文。"""
        ids = sorted({str(x) for x in file_ids if x})
        if not ids:
            return {}
        body = {
            "size": 0,
            "query": {"terms": {"metadata.file_id": ids}},
            "aggs": {"by_file": {
                # file_id 映射是 text + keyword 子字段；聚合必须落到 .keyword，
                # 用 text 字段会因 fielddata 关闭而报错（或拿到空桶）。
                "terms": {"field": "metadata.file_id.keyword", "size": 50},
                "aggs": {"first": {"top_hits": {"size": 1, "_source": ["metadata.source"]}}},
            }},
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{ES_URL}/{kb}/_search", json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - 取不到就不带 source，引用降级但不阻断回答
            logger.warning(f"反查 source 失败 kb={kb}: {exc}")
            return {}
        out = {}
        for bucket in ((data.get("aggregations") or {}).get("by_file") or {}).get("buckets") or []:
            hits = ((bucket.get("first") or {}).get("hits") or {}).get("hits") or []
            if hits:
                meta = hits[0].get("_source", {}).get("metadata") or {}
                if meta.get("source"):
                    out[str(bucket.get("key"))] = meta["source"]
        return out
