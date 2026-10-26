"""R13 GraphRAG：社区摘要生成、摘要索引读写、global/local 查询。

设计取舍（写清楚，便于评审）：
  - 摘要只依据"社区内实体与关系"生成，prompt 明确禁止编造，模型失败直接返回错误，不塞模板文本；
  - 摘要索引沿用表格摘要惯例：ES index 与 Milvus collection 同名 `community_summary_<kb>`，双写；
  - global 查询用 LLM 在"社区摘要集合"上做 reduce（社区数量级小，先做精确全量，不做近似召回），
    当社区数超过 SUMMARY_SCAN_LIMIT 时在响应里显式告知"已截断"，不假装全量。
"""
import json
import time

import requests

from base import BaseResponse
from graph_community import detect_communities, load_graph, community_triples, community_file_ids
from graph_fun_tool import requests_llm
from operators.common.log import logger

ES_PORT = 19527
MILVUS_PORT = 19526
SUMMARY_SCAN_LIMIT = 200

SUMMARY_PROMPT = """你是企业知识库的图谱分析助手。下面是一个知识图谱社区内的**全部事实**（实体与关系）。
请仅依据给定事实，用中文写一段 3-6 句的社区摘要，要求：
1) 说明这个社区围绕什么主题聚集；
2) 列出关键实体及其关系（用「A -关系-> B」的形式至少 2 条）；
3) 不要引入任何未在事实中出现的信息；不确定就写"信息不足"。

社区成员实体：{members}
社区内关系：
{triples}
"""

REDUCE_PROMPT = """你是企业知识库的分析助手。下面是若干"社区摘要"，每条都有 community_id。
请仅依据这些摘要回答问题，输出两段：
第一段：结论（3-5 句，明确引用你依据的 community_id，格式如 [L0-xxxxxxxx]）；
第二段：如果摘要不足以回答，直接写"现有社区摘要不足以回答"，不要猜测。

问题：{question}

社区摘要：
{summaries}
"""


def _post(port, path, payload, timeout=120):
    return requests.post(f"http://127.0.0.1:{port}/{path}", json=payload, timeout=timeout)


def summarize_community(space_name, community, model_info, server_config):
    triples, file_ids = community_triples(space_name, community["members"])
    if not triples:
        return None, "no_triples"
    triple_text = "\n".join([f"- {s} -{r}-> {d}" for s, r, d in triples[:60]])
    member_text = "、".join(community["members"][:40])
    prompt = SUMMARY_PROMPT.format(members=member_text, triples=triple_text)
    text = requests_llm(prompt, model_info, server_config, prompt_flag=True)
    if not text or len(text.strip()) < 10:
        return None, "llm_empty_or_failed"
    return text.strip(), triple_text


def write_summary_indexes(kb, records, server_config):
    """ES/Milvus 双写；返回 (es_ok, milvus_ok, err)。"""
    if not records:
        return True, True, ""
    index_name = f"community_summary_{kb}"
    es_data = {"index_name": index_name, "document_list": records}
    mv_data = {"db_name": "graph_base", "collection_name": index_name, "document_list": records}
    es_ok = mv_ok = False
    err = ""
    try:
        r = _post(ES_PORT, "insert_fulltext_documents", es_data)
        es_ok = r.status_code == 200 and (r.json().get("code") in (None, 200))
        if not es_ok:
            err += f" es:{r.text[:160]}"
    except Exception as e:
        err += f" es_exc:{e}"
    try:
        r = _post(MILVUS_PORT, "insert_vector_documents_custom", mv_data, timeout=300)
        mv_ok = r.status_code == 200 and (r.json().get("code") in (None, 200))
        if not mv_ok:
            err += f" milvus:{r.text[:160]}"
    except Exception as e:
        err += f" milvus_exc:{e}"
    return es_ok, mv_ok, err.strip()


def file_id_to_names(kb, file_ids):
    """file_id → 文件名（ES `metadata.title`）。

    R13-FIX-GRAPH-17：社区摘要原来只存 file_ids，而文档重传后旧 file_id 指向已删文件，
    global 引用会出现"摘要能显示、source 点不开"。这里额外把文件名落到 `file_names`，
    让下游（Java）在 file_id 失效时按文件名回落到当前文件。
    """
    ids = []
    for fid in file_ids or []:
        try:
            ids.append(int(fid))
        except (TypeError, ValueError):
            continue
    if not ids:
        return []
    try:
        r = _post(ES_PORT, "search_by_custom_param",
                  {"index_name": [kb],
                   "query_body": {"query": {"terms": {"metadata.file_id": ids}}, "size": 200}})
        rows = (r.json().get("data") or {}).get("result_data") or []
    except Exception as e:
        logger.error(f"按 file_id 查文件名失败: {e}")
        return []
    names = []
    for row in rows:
        title = ((row.get("_source") or {}).get("metadata") or {}).get("title")
        if title and title not in names:
            names.append(title)
    return names


def generate_community(payload: dict) -> BaseResponse:
    """检测社区 → 生成摘要 → 双写索引。"""
    from utils import return_nacos_model
    space_name = str(payload.get("space_name", "")).replace("g_", "")
    model_info = payload.get("model_info") or {}
    max_level = int(payload.get("max_level", 1))
    min_size = int(payload.get("min_community_size", 3))
    resolution = float(payload.get("resolution", 1.0))
    with_summary = bool(payload.get("with_summary", True))
    server_config = return_nacos_model().get_config()

    g = load_graph(space_name)
    communities = detect_communities(g, resolution=resolution,
                                     min_community_size=min_size, max_level=max_level)
    if not communities:
        return BaseResponse(code=200, msg="未检测到满足条件的社区（图可能过小）",
                            data={"communities": 0, "summaries": 0})

    records, failures = [], []
    for c in communities:
        if not with_summary:
            continue
        text, info = summarize_community(space_name, c, model_info, server_config)
        _triples, _edge_file_ids = community_triples(space_name, c["members"])
        _file_ids = sorted(set(_edge_file_ids) | set(community_file_ids(space_name, c["members"])))
        _file_names = file_id_to_names(space_name, _file_ids)
        if text is None:
            failures.append({"community_id": c["community_id"], "reason": info})
            continue
        records.append({
            "page_content": text,
            "metadata": {
                "community_id": c["community_id"],
                "level": c["level"],
                "member_entities": c["members"],
                "size": c["size"],
                "edge_count": c["edge_count"],
                "kb": space_name,
                # 溯源：社区涉及的文件 id（来自关系属性 file_id），供引用回落到授权原文
                "file_ids": _file_ids,
                # R13-FIX-GRAPH-17：文件重传后 file_ids 会失效，同时存文件名，供下游按名回落
                "file_names": _file_names,
                "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        })

    es_ok, mv_ok, err = write_summary_indexes(space_name, records, server_config) if with_summary else (True, True, "")
    return BaseResponse(code=200 if (es_ok and mv_ok) else 500,
                        msg=(f"社区 {len(communities)} 个，摘要 {len(records)} 条，失败 {len(failures)} 条"
                             + ("" if es_ok and mv_ok else f"；索引写入异常 {err}")),
                        data={"communities": len(communities), "summaries": len(records),
                              "failures": failures, "es_ok": es_ok, "milvus_ok": mv_ok,
                              "community_detail": [{"community_id": c["community_id"], "level": c["level"],
                                                    "size": c["size"], "edge_count": c["edge_count"]}
                                                   for c in communities]})


def _load_summaries(kb):
    try:
        r = _post(ES_PORT, "search_by_custom_param",
                  {"index_name": [f"community_summary_{kb}"], "page_no": 1, "page_size": SUMMARY_SCAN_LIMIT})
        rows = (r.json().get("data") or {}).get("result_data") or []
        # R13-GRAPH-04：原实现只回 community_id/level/members/summary，把 file_ids 丢了，
        # 导致 global 检索返回的社区摘要无法落到"可打开的原文"，引用为空。
        return [{"community_id": (row.get("_source", {}).get("metadata") or {}).get("community_id"),
                 "level": (row.get("_source", {}).get("metadata") or {}).get("level"),
                 "members": (row.get("_source", {}).get("metadata") or {}).get("member_entities"),
                 "file_ids": (row.get("_source", {}).get("metadata") or {}).get("file_ids") or [],
                 # R13-FIX-GRAPH-17：一并向调用方返回文件名（旧摘要没有该字段时为 []）
                 "file_names": (row.get("_source", {}).get("metadata") or {}).get("file_names") or [],
                 "edge_count": (row.get("_source", {}).get("metadata") or {}).get("edge_count"),
                 "summary": row.get("_source", {}).get("page_content")}
                for row in rows]
    except Exception as e:
        logger.error(f"读取社区摘要失败: {e}")
        return []


def query_community(payload: dict) -> BaseResponse:
    """mode=global：对社区摘要做 reduce；mode=local：按实体命中的社区返回摘要。"""
    from utils import return_nacos_model
    space_name = str(payload.get("space_name", "")).replace("g_", "")
    query = payload.get("query", "")
    mode = payload.get("mode", "global")
    top_k = int(payload.get("top_k", 5))
    model_info = payload.get("model_info") or {}
    server_config = return_nacos_model().get_config()

    summaries = _load_summaries(space_name)
    if not summaries:
        return BaseResponse(code=200, msg="该知识库还没有社区摘要，请先调用 /generate_community",
                            data={"answer": "", "communities": []})

    truncated = len(summaries) >= SUMMARY_SCAN_LIMIT

    if mode == "local":
        hit = []
        for s in summaries:
            members = s.get("members") or []
            score = sum(1 for m in members if m and str(m) in query)
            if score:
                hit.append({**s, "score": score})
        hit.sort(key=lambda x: -x["score"])
        return BaseResponse(code=200, msg=f"命中 {len(hit[:top_k])} 个社区",
                            data={"answer": "", "communities": hit[:top_k], "truncated": truncated})

    lines = []
    for s in summaries:
        lines.append(f"[{s['community_id']}] (level={s.get('level')}, 成员: {', '.join((s.get('members') or [])[:12])})\n{s['summary']}")
    prompt = REDUCE_PROMPT.format(question=query, summaries="\n\n".join(lines))
    answer = requests_llm(prompt, model_info, server_config, prompt_flag=True)
    if not answer:
        return BaseResponse(code=500, msg="社区摘要汇总失败（模型未返回内容）", data={"communities": summaries})
    cited = [s for s in summaries if s["community_id"] and s["community_id"] in answer]
    return BaseResponse(code=200, msg=f"global 汇总完成，社区 {len(summaries)} 条",
                        data={"answer": answer,
                              "communities": cited or summaries[:top_k],
                              "truncated": truncated})


def del_community(payload: dict) -> BaseResponse:
    """删除社区摘要索引（补 del_space_data 不联动 Milvus 的缺口）。"""
    kb = str(payload.get("space_name", "")).replace("g_", "")
    index_name = f"community_summary_{kb}"
    ok = []
    for port, path, body in [
        (ES_PORT, "del_index", {"index_name": index_name}),
        (MILVUS_PORT, "del_collection", {"db_name": "graph_base", "collection_name": index_name}),
    ]:
        try:
            r = _post(port, path, body, timeout=120)
            ok.append({"target": path, "status": r.status_code, "body": r.text[:120]})
        except Exception as e:
            ok.append({"target": path, "error": str(e)})
    return BaseResponse(code=200, msg="社区摘要索引删除已执行（以返回明细为准）", data={"detail": ok})
