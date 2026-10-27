"""R13 GraphRAG：社区摘要生成、摘要索引读写、global/local 查询。

设计取舍（写清楚，便于评审）：
  - 摘要只依据"社区内实体与关系"生成，prompt 明确禁止编造，模型失败直接返回错误，不塞模板文本；
  - 摘要索引沿用表格摘要惯例：ES index 与 Milvus collection 同名 `community_summary_<kb>`，双写；
  - global 查询用 LLM 在"社区摘要集合"上做 reduce（社区数量级小，先做精确全量，不做近似召回），
    当社区数超过 SUMMARY_SCAN_LIMIT 时在响应里显式告知"已截断"，不假装全量。
"""
import json
import re
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

REDUCE_PROMPT = """你是企业知识库的分析助手。下面是若干"社区摘要"及其"社区内事实三元组"，每条都有 community_id。

硬约束（违反即视为答错）：
1) 只能使用下面列出的事实。**数字、单位、日期、评级、比例必须逐字来自事实**，不得换算、不得补全、不得推测；
2) 每条结论后面必须标注它所依据的 community_id，格式 [L0-xxxxxxxx]；
3) 若某个子问题在事实里找不到答案，就明确写"事实中未提及"，不要用常识补齐；
4) 需要"实体属性 → 规则"对应时（例如某公司的评级 → 加点幅度），先取该实体的属性事实，
   再到事实里找**同名规则行**逐条对应，不得套用其它实体或其它等级那一行；
5) 凡数值来自【代码推导】段落，社区号必须用推导行前标的那个 [L0-xxx]（数值所在规则社区），
   不得改用"实体所属社区"的编号——否则读者按编号回指会找不到该数值；
6) 不要输出格式说明或免责声明，直接给结论。

问题：{question}

社区摘要与事实：
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
    # R14-B（A-IDENTITY §6.0 第 3 条，A-data 收紧本条）：**只有 ES 索引名 lower**。
    # Milvus 允许大写，且 chunk/table/faq 的写入方（alg_doc_parse_service → 19526）传的是原样
    # primitive_name；若社区摘要这类写入方把集合名 lower，同一个大写 KB 会分裂成两个集合
    # （`_KB_17` 与 `_kb_17`），表现为"摘要写进去了但读不到"，两边各自自洽、日志都成功，极难查。
    es_index = f"community_summary_{_idx(kb)}"
    mv_collection = f"community_summary_{kb}"
    es_data = {"index_name": es_index, "document_list": records}
    mv_data = {"db_name": "graph_base", "collection_name": mv_collection, "document_list": records}
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
                  {"index_name": [_idx(kb)],
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


def _idx(kb):
    """ES 索引名 / 派生主键种子用的知识库名——**必须 lower**。

    ES 硬限制：索引名不允许大写（代码里 is_index_lower() 就是为此）；而 Milvus 集合名允许大写。
    一旦有人建了 `KB_17` 这种 primitive_name，就会出现"ES 索引 kb_17 / Milvus 集合 KB_17，
    派生种子若不 lower 则两侧 id 不同"。A-data 已把写侧统一 lower（A-IDENTITY §6.0），
    读侧同样必须 lower，否则表现为"社区摘要突然查不到"，且极难归因。
    注意：Nebula 图空间名（g_<kb>）**不**经过本函数，那边仍用原始名。
    """
    return str(kb or "").strip().lower()


def _es_search(kb, query_body):
    r = _post(ES_PORT, "search_by_custom_param",
              {"index_name": [_idx(kb)], "query_body": query_body})
    return ((r.json() or {}).get("data") or {}).get("result_data") or []


def _sources_from_rows(rows):
    out = []
    for row in rows:
        src = ((row.get("_source") or {}).get("metadata") or {}).get("source")
        if src and src not in out:
            out.append(src)
    return sorted(out)


def resolve_sources_by_entities(kb, members):
    """按"社区成员实体在原文 chunk 里出现"反查当前代次的对象键。

    R14-B（F04 代次漂移）：图里边的 `file_id` 是**抽取时刻**的 ES 文档 id，知识库重新解析后
    全部失效，`file_names` 也就跟着解析不出来——社区摘要于是既没有 source 也没有文件名，
    下游只能回落到 MySQL 的绝对路径（又变回双 host），或者干脆引用点不开。
    这里不依赖任何 id/文件名，直接用实体名在原文 chunk 里做短语匹配，取命中实体最多、
    且**当前代次**仍存在的那份文档的对象键，属于"从内容反推来源"，与重解析无关。
    """
    names = [str(m) for m in (members or [])
             if m and len(str(m)) >= 3 and not _looks_like_value(m)]
    if not names:
        return []
    # 取最"独特"的几个（长名优先），避免 通用词 命中所有文档
    names = sorted(set(names), key=lambda x: -len(x))[:6]
    body = {"query": {"bool": {"should": [
        {"match_phrase": {"page_content": n}} for n in names]}}, "size": 20}
    try:
        rows = _es_search(kb, body)
    except Exception as e:
        logger.error(f"按实体反查来源失败: {e}")
        return []
    scored = []
    for row in rows:
        src = ((row.get("_source") or {}).get("metadata") or {}).get("source")
        text = (row.get("_source") or {}).get("page_content") or ""
        if not src:
            continue
        score = sum(1 for n in names if n in text)
        scored.append((score, src))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = []
    for _sc, src in scored:
        if src not in out:
            out.append(src)
    return out


def resolve_sources(kb, file_ids, file_names):
    """把社区的溯源解析成**原文对象键**（bucket 相对路径，如 `r12-rag/kb_9/x.docx/V0/x.docx`）。

    R14-B：global 引用出现 `http://h/http://h/...` 的根因是两处口径不一致——
      - ES `metadata.source` = bucket 相对对象键（无 scheme），Java 拼一次 endPoint 得到正确 URL；
      - MySQL `knowledge_base_list.converted_file_path` = **绝对 URL**，Java 再拼一次就变双 host。
    社区摘要原本没有 source，Java 只能走 file_id/文件名回落到 MySQL，于是**只有 global 双 host**。
    这里由图谱侧（权威侧）给出相对对象键，下游只拼一次 host，即为单个可解析 URL；
    对象键是**文件级**身份，重新解析不改变，重传会进新版本目录（V1），因此比 chunk id 稳定。

    解析顺序：file_id（精确）→ 文件名（重传后 id 失效的回落）。
    返回 (sources, resolved_by)，resolved_by ∈ {"file_id", "file_name", ""}。
    """
    ids = []
    for fid in file_ids or []:
        try:
            ids.append(int(fid))
        except (TypeError, ValueError):
            continue
    sources, by = [], ""
    if ids:
        try:
            sources = _sources_from_rows(
                _es_search(kb, {"query": {"terms": {"metadata.file_id": ids}}, "size": 200}))
            if sources:
                by = "file_id"
        except Exception as e:
            logger.error(f"按 file_id 解析 source 失败: {e}")
    if not sources and file_names:
        try:
            sources = _sources_from_rows(
                _es_search(kb, {"query": {"terms": {"metadata.title.keyword": list(file_names)[:50]}},
                                "size": 200}))
            if sources:
                by = "file_name"
        except Exception as e:
            logger.error(f"按文件名解析 source 失败: {e}")
    return sources, by


ENTITY_DB = "graph_base"
CHUNK_REFS_LIMIT = 8


def _entity_chunk_pks(kb, members, limit=60):
    """按实体名从向量实体表取 `chunk_pk_list`（实体→出现过的 chunk）。

    为什么不用 Nebula 顶点属性：顶点上只有 `file_id`（逗号串的**文件** id），
    没有 chunk 级引用；chunk_pk_list 是写在向量实体表 `graph_entity_<kb>` 里的。
    直接读图顶点会拿到 file_id 并误当成 pk（早期脚本就踩过）。
    """
    names = [str(m).replace('"', "") for m in (members or []) if m][:limit]
    if not names:
        return {}
    expr = "text in [%s]" % ", ".join('"%s"' % n for n in names)
    try:
        r = _post(MILVUS_PORT, "get_doc_by_col",
                  {"collection_name": f"graph_entity_{kb}", "db_name": ENTITY_DB, "expr": expr},
                  timeout=120)
        rows = ((r.json().get("data") or {}).get("result_data")) or []
    except Exception as e:
        logger.error(f"读取实体 chunk_pk_list 失败: {e}")
        return {}
    out = {}
    for row in rows:
        md = row.get("metadata") or {}
        text = row.get("page_content") or md.get("text")
        pks = md.get("chunk_pk_list") or []
        if text:
            out[str(text)] = [str(p) for p in pks]
    return out


def _es_chunk_meta(kb, pks, limit=200):
    """pk → {source, offset, title, chunk_index}，只返回 ES 里**真实存在**的 pk。

    悬空 pk（抽取时刻的 `_id` 已被重解析覆盖）不会出现在返回里——这正是
    "引用有效性"的判据：`resolved / total` 就是命中率。
    """
    ids = [str(p) for p in pks][:limit]
    if not ids:
        return {}
    try:
        rows = _es_search(kb, {"query": {"ids": {"values": ids}}, "size": len(ids)})
    except Exception as e:
        logger.error(f"按 pk 回查 ES 失败: {e}")
        return {}
    out = {}
    for row in rows:
        md = (row.get("_source") or {}).get("metadata") or {}
        out[str(row.get("_id"))] = {
            "source": md.get("source"),
            "offset": md.get("offset"),
            "title": md.get("title"),
            "chunk_index": md.get("chunk_index"),
        }
    return out


def valid_file_ids(kb, file_ids, file_names=None):
    """把社区的 `file_ids` 收敛到**当前仍存在**的文件 id。

    为什么必须做（实测 500）：社区摘要里的 `file_ids` 是抽取时刻的旧代（如 120/259），
    A 重解析后这些文件行已不存在；Java 拿到 global 结果后会调 `KbClient#getByIds([120,259])`
    → **404** → 抛异常 → 用户侧 **500**。
    表现很有迷惑性：同样的 global 逻辑，引用到"旧代文件全失效"的社区就 500，
    引用到"还有效"的社区就 200（所以 R1 200 / R2 500，看着像随机）。

    处理：按 file_id 回查 ES，只保留存在的；都不存在则按文件名回查；
    仍找不到就返回空列表（宁可不给，也不把不存在的 id 交给下游去 404）。
    """
    ids = []
    for fid in file_ids or []:
        try:
            ids.append(int(fid))
        except (TypeError, ValueError):
            continue
    out = []
    # **仅为容错，主修复在入库侧**（TL 裁定）：台账/表格的 chunk 落在 table_chunks_/table_summary_，
    # 只在 kb 主索引查会漏，导致"台账来源"被当成失效 id 丢掉。
    # 注意：file_id 的归一（旧行 314 -> 当前 329）必须由入库侧重解析完成，
    # 图侧不长期保留 id 映射逻辑，否则是把数据问题固化成代码债务。
    indices = [kb, f"table_chunks_{kb}", f"table_summary_{kb}"]
    if ids:
        for idx in indices:
            try:
                rows = _es_search(idx, {"query": {"terms": {"metadata.file_id": ids}}, "size": 200})
                for row in rows:
                    fid = ((row.get("_source") or {}).get("metadata") or {}).get("file_id")
                    if fid is not None and int(fid) not in out:
                        out.append(int(fid))
            except Exception as e:
                logger.error(f"校验 file_id 失败({idx}): {e}")
    if not out and file_names:
        try:
            rows = _es_search(kb, {"query": {"terms": {"metadata.title.keyword": list(file_names)[:50]}},
                                   "size": 200})
            for row in rows:
                fid = ((row.get("_source") or {}).get("metadata") or {}).get("file_id")
                if fid is not None and int(fid) not in out:
                    out.append(int(fid))
        except Exception as e:
            logger.error(f"按文件名回捞 file_id 失败: {e}")
    return out


def resolve_chunk_refs(kb, members, limit=CHUNK_REFS_LIMIT):
    """社区 → **chunk 级**引用 [{pk, source, offset, title, chunk_index}]。

    C15 要求：global 的每条结论必须能回到具体 chunk，而不只是"某个社区"。
    社区摘要本身没有块定位，这里用成员实体在原文里的出现块（chunk_pk_list）回填：
      1) 实体名 → 向量实体表 `graph_entity_<kb>` 取 chunk_pk_list；
      2) pk → ES `ids` 查当前代次，命中才留（悬空的丢弃并计入 stats）。
    返回 (refs, stats)，stats 里 total/resolved 即引用命中率，可直接做验收指标。
    """
    by_entity = _entity_chunk_pks(kb, members)
    all_pks = []
    for pks in by_entity.values():
        for p in pks:
            if p not in all_pks:
                all_pks.append(p)
    meta = _es_chunk_meta(kb, all_pks)
    refs = []
    for p in all_pks:
        m = meta.get(p)
        if not m:
            continue
        refs.append({"pk": p, "source": m.get("source"), "title": m.get("title"),
                     "offset": m.get("offset"), "chunk_index": m.get("chunk_index")})
    stats = {"entities_with_pk": len(by_entity), "total_pks": len(all_pks),
             "resolved": len(refs), "dangling": len(all_pks) - len(refs)}
    return refs[:limit], stats


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
                                     min_community_size=min_size, max_level=max_level,
                                     namespace=space_name)
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
        # R14-B：同时落"原文对象键"，供 global 引用给出单个可解析 source（见 resolve_sources）
        _sources, _sources_by = resolve_sources(space_name, _file_ids, _file_names)
        if not _sources:
            _sources = resolve_sources_by_entities(space_name, c["members"])
            _sources_by = "entity_content" if _sources else ""
        # C15：同时落 chunk 级引用（pk + source + offset），global 引用卡片取第一条
        _chunk_refs, _chunk_stats = resolve_chunk_refs(space_name, c["members"])
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
                # R14-B：原文对象键（bucket 相对），下游只拼一次 endPoint 即为单个可解析 URL
                "sources": _sources,
                "sources_resolved_by": _sources_by,
                # C15：chunk 级引用（成员实体所在 chunk 的 pk/source/offset），
                # 引用卡片取第一条即为"可打开的具体块"，不再只有社区摘要。
                "chunk_refs": _chunk_refs,
                "chunk_refs_stats": _chunk_stats,
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


def _load_summaries(kb, with_triples=False):
    try:
        r = _post(ES_PORT, "search_by_custom_param",
                  {"index_name": [f"community_summary_{_idx(kb)}"], "page_no": 1, "page_size": SUMMARY_SCAN_LIMIT})
        rows = (r.json().get("data") or {}).get("result_data") or []
    except Exception as e:
        # R14-B5（F 实测 13:10 窗口）：ES 短暂不可用（索引服务重启）时，
        # 原实现把"读不到"当成"没有摘要"，于是 global 对**本可回答**的问题回
        # "现有社区摘要不足以回答" —— 用户看到的是"拒答"，实际是基础设施故障，
        # 属于把故障伪装成结论。这里返回 None 表示"读取失败"，与"确实为空"([]) 区分。
        logger.error(f"读取社区摘要失败: {e}")
        return None
    out = []
    for row in rows:
        md = row.get("_source", {}).get("metadata") or {}
        file_ids = md.get("file_ids") or []
        file_names = md.get("file_names") or []
        sources = md.get("sources") or []
        by = md.get("sources_resolved_by") or ""
        # R14-B：旧摘要没有 sources 字段，读取时就地解析一次
        # （file_id → 文件名 → 实体反查内容），这样不重建社区也能让 global 给出可解析的 source。
        if not sources:
            sources, by = resolve_sources(kb, file_ids, file_names)
        if not sources and md.get("member_entities"):
            sources = resolve_sources_by_entities(kb, md.get("member_entities"))
            by = "entity_content" if sources else ""
        community_id = md.get("community_id")
        members = md.get("member_entities") or []
        # R14-B4：file_ids 必须是"当前仍存在"的，否则 Java 侧 getByIds 会 404 → 用户 500
        _raw_file_ids = list(file_ids)
        file_ids = valid_file_ids(kb, file_ids, file_names)
        # C15：chunk 级引用。旧摘要没有该字段时读取时就地解析一次，
        # 这样不重建社区也能让 global 给出"可打开的具体块"（而非只有社区）。
        chunk_refs = md.get("chunk_refs") or []
        chunk_stats = md.get("chunk_refs_stats") or {}
        if not chunk_refs and members:
            chunk_refs, chunk_stats = resolve_chunk_refs(kb, members)
        triples = []
        if with_triples and members:
            # R14-B2（效果题暴露的真实缺陷）：社区摘要 prompt 只要求"至少 2 条关系"，
            # 数值型关系（如 AAA/AA 各自加点多少）会被摘要丢掉，reduce 阶段只能靠猜，
            # 实测把 AAA 30BP/AA 60BP 编成 15BP/10BP。这里把**社区内全部关系**一并喂给
            # reduce，并配 REDUCE_PROMPT 的"数字逐字来自事实、不得推测"硬约束。
            # 取自 Nebula 实时读取（不依赖摘要落库字段），因此不需要重建社区摘要。
            try:
                triples, _ = community_triples(kb, members)
            except Exception as e:
                logger.error(f"读取社区 {community_id} 三元组失败: {e}")
        out.append({
            "community_id": community_id,
            "level": md.get("level"),
            "members": members,
            "file_ids": file_ids,
            # 审计：原始（可能是旧代）file_ids 一并回传，便于判断"是数据旧"还是"逻辑丢"
            "file_ids_raw": _raw_file_ids,
            # R13-FIX-GRAPH-17：一并向调用方返回文件名（旧摘要没有该字段时为 []）
            "file_names": file_names,
            "sources": sources,
            "sources_resolved_by": by,
            "chunk_refs": chunk_refs,
            "chunk_refs_stats": chunk_stats,
            "edge_count": md.get("edge_count"),
            "triples": triples,
            "summary": row.get("_source", {}).get("page_content"),
        })
    return out


def _ngrams(text, n=2):
    text = str(text or "")
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def _community_score(query, s):
    """社区相关性：问题与"成员实体 + 关系名 + 摘要"的 2-gram 重合度。

    比"实体名整串 in 问题"宽松——问句里常是「加点规则」，而图里是「AAA级加点幅度」。
    """
    hay = " ".join([str(s.get("summary") or "")] +
                   [str(m) for m in (s.get("members") or [])] +
                   [str(r) for _a, r, _b in (s.get("triples") or [])])
    q = _ngrams(query)
    return len(q & _ngrams(hay))


def _select_communities(query, summaries, limit=4):
    """map 阶段的输入面：按相关性挑社区；一个都没命中就退回全部（不静默空转）。"""
    scored = [(c, _community_score(query, c)) for c in summaries]
    hit = [c for c, sc in sorted(scored, key=lambda x: -x[1]) if sc > 0]
    return (hit or [c for c, _ in scored])[:limit]


_VALUE_RE = None


def _looks_like_value(x):
    """判断一个实体名像"取值"（数字/金额/日期/等级）还是像"主体名"。"""
    global _VALUE_RE
    if _VALUE_RE is None:
        import re
        _VALUE_RE = re.compile(
            r"^(加|减)?(人民币)?[\d.,]+(万元|亿元|个基点|%|年|个月|日|天|个工作日)?$"
            r"|^\d{4}-\d{2}-\d{2}$|^[A-Z]{1,4}$")
    return bool(_VALUE_RE.match(str(x or "").strip()))


def _orient(a, r, b):
    """把三元组摆成"主体 -关系-> 取值"的方向。

    图里同一事实两个方向都有（`AA -信用评级-> 华东精密` 与 `华东精密 -信用评级-> AA`），
    小模型读到反向形式会把取值当成主体、把主体当成取值，进而把相邻数字配错。
    """
    if _looks_like_value(a) and not _looks_like_value(b):
        return b, r, a
    return a, r, b


# R14-B3（TL 要求的三问法一致性）：问句与关系名常常**同义不同词**，
# 2-gram 直接比会漏。实测反例：问"…对应多少**基点**"，图里关系是"AAA级**加点**幅度"，
# 二者没有共同 2-gram → 加点事实整批被丢弃 → reduce 只能对评级答"0 基点"。
# 这里做一层**概念归一**（只在图谱投影内部用，不改落库数据），把同义说法收敛到同一概念。
CONCEPT_ALIASES = {
    "加点": ("加点", "基点", "bp", "幅度"),
    "评级": ("评级", "等级", "级别"),
    "额度": ("额度", "限额", "上限"),
    "期限": ("期限", "到期", "有效期"),
    "利率": ("利率", "lpr", "定价"),
    "还款": ("还款", "付息", "还本"),
}


def _concepts(text):
    t = str(text or "").lower()
    return {c for c, aliases in CONCEPT_ALIASES.items() if any(a in t for a in aliases)}


def _project_facts(query, s):
    """单社区的事实投影（map）：只保留与该社区被问到的实体/关系直接相关的事实行。

    为什么是确定性投影而不是再问一次模型：实测本环境的 qwen2.5-7b-instruct 在
    "从事实列表里挑相关内容"这一步会直接输出「无」（即使 AAA 评级事实就在眼前），
    再让它挑一次只会把不确定性叠加。这里用两个可复核的判据：
      ① 实体命中：社区成员实体名**整串出现在问题里**（如"江南装备科技有限公司"）；
      ② 关系命中：关系名与问题有 2-gram 重合（如"加点" ⊂ "AAA级加点幅度"）。
    两条都不命中就丢弃该行——宁可少给，也不把无关数字塞进 reduce 让模型乱配。
    返回 (anchors, facts)。
    """
    members = [str(m) for m in (s.get("members") or []) if m]
    anchors = [m for m in members if len(m) >= 3 and m in query]
    q = _ngrams(query)
    q_concepts = _concepts(query)
    member_hits, rel_hits, seen = [], [], set()
    for a, r, b in (s.get("triples") or []):
        if a in anchors or b in anchors:
            bucket = member_hits
        elif (_ngrams(r) & q) or (q_concepts & _concepts(r)):
            # 关系命中有两条路：字面 2-gram 重合，或**概念归一后重合**
            # （"基点"问句 ↔ "加点幅度"关系）。后者是 R14-B3 修三问法不一致的关键。
            bucket = rel_hits
        else:
            continue
        a, r, b = _orient(a, r, b)
        # 定向后再按"实体|关系|取值"去重：正反两个方向归一成同一行，避免同义重复挤占上下文
        key = (str(a), str(r), str(b))
        if key in seen:
            continue
        seen.add(key)
        bucket.append((a, r, b))
    return anchors, (member_hits + rel_hits)[:40]


GRADE_RE = re.compile(r"^([A-Z]{1,3})级")
BP_RE = re.compile(r"(\d+)\s*个基点")


def _join_grade_rules(map_outputs):
    """在代码里做**确定性连接**：`实体 -信用评级-> 等级` × `规则 -等级级加点幅度-> 数值`。

    为什么不能交给 reduce：实测同一批事实、只换问法，7B 的取值就会错
    （"…对应多少基点" 曾对 AA 答 0；"各自的加点是各多少" 又把 AAA 答成 60）。
    这个连接是图内两条事实的组合，不引入任何外部知识，因此由代码算、模型只负责表述。
    返回 [(fact_line, community_id)]。
    """
    grade_of, rules = {}, []
    for s, facts in map_outputs:
        for f in facts:
            if " -" not in f or "-> " not in f:
                continue
            try:
                a, rest = f.split(" -", 1)
                r, b = rest.split("-> ", 1)
            except ValueError:
                continue
            a, r, b = a.strip(), r.strip(), b.strip()
            if r == "信用评级" and re.fullmatch(r"[A-Z]{1,3}", b):
                grade_of.setdefault(a, b)
            m = GRADE_RE.match(r)
            if m and BP_RE.search(b):
                rules.append((m.group(1), b, a, s["community_id"]))
    derived, seen = [], set()
    for ent, g in grade_of.items():
        for gg, bp, _prod, cid in rules:
            if gg == g:
                key = (ent, g, bp)
                if key in seen:
                    continue
                seen.add(key)
                derived.append((f"{ent} -{g}级加点幅度-> {bp}", cid))
    return derived


DERIVED_RE = re.compile(r"^(?P<ent>.+?) -(?P<grade>[A-Z]{1,3})级加点幅度-> (?P<bp>\d+)\s*个基点$")


def _fix_bp_citations(answer, derived):
    """把"数值引到错社区"的行纠正到**规则所在社区**。

    C15 要求"每条结论可回指"。实测：模型会写"江南…加点是30个基点 [L0-3af0d4bc]"，
    而 L0-3af0d4bc 只有 `江南 -信用评级-> AAA`，30 这个数字在 L0-18625408。
    这里只做**一对一可核对**的纠正：同一行同时出现实体名与推导数值、且数值等于推导值，
    才把它引用的社区号替换成规则社区；其余行不动，并记录纠正明细便于审计。
    """
    if not answer or not derived:
        return answer, []
    want = {}
    for fact, cid in derived:
        m = DERIVED_RE.match(fact)
        if not m:
            continue
        want.setdefault((m.group("ent"), m.group("bp")), cid)
    def _dedupe_cids(text):
        """同一行里重复出现的社区号只保留第一次（模型偶发重复 + 补引用可能叠加）。"""
        seen = []

        def _repl(m):
            cid_ = m.group(1)
            if cid_ in seen:
                return ""
            seen.append(cid_)
            return m.group(0)

        return re.sub(r"\[(L\d-[0-9a-fA-F]+)\]", _repl, text)

    fixes, out_lines = [], []
    for line in (answer or "").split("\n"):
        for (ent, bp), cid in want.items():
            # R14-B4：只**补**规则社区，不覆盖原有社区号。
            # 覆盖会造成两个后果：①评级结论的社区被抹掉（G1 的 refs 从 3 掉到 1）；
            # ②"评级由 A 社区支撑、加点由 B 社区支撑"这种双依据被压成单依据。
            if ent in line and bp in line and "个基点" in line and cid not in line:
                line = re.sub(r"([。；;]?)\s*$", f" [{cid}]\\1", line)
                fixes.append({"entity": ent, "bp": bp, "added": cid, "line": line.strip()[:80]})
        out_lines.append(_dedupe_cids(line))
    return "\n".join(out_lines), fixes


def query_community(payload: dict) -> BaseResponse:
    """mode=global：对社区摘要做 reduce；mode=local：按实体命中的社区返回摘要。"""
    from utils import return_nacos_model
    space_name = str(payload.get("space_name", "")).replace("g_", "")
    query = payload.get("query", "")
    mode = payload.get("mode", "global")
    top_k = int(payload.get("top_k", 5))
    model_info = payload.get("model_info") or {}
    server_config = return_nacos_model().get_config()

    summaries = _load_summaries(space_name, with_triples=(mode != "local"))
    if summaries is None:
        # 读不到 != 没有：明确报错，不伪装成"不足以回答"
        return BaseResponse(code=500, msg="社区摘要读取失败（ES 不可用），请稍后重试",
                            data={"answer": "", "communities": [], "error": "summary_store_unavailable"})
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

    # ---- R14-B2：真正的 map-reduce（原来是把全部摘要塞进一个 prompt 做单次 reduce）----
    # 实测问题：7 个社区 6.6k 字上下文里已经含有 "智造贷 -AAA级加点幅度-> 30个基点"，
    # 单次 reduce 仍把 AAA 答成 100/50 个基点，并把引用标到并不含该事实的社区上。
    # 改成：先按相关性挑社区（map 的输入面），逐社区做"只抄相关事实行"的抽取，
    # 再把各社区的抽取结果（带 community_id）做最终汇总——每步任务都变小，引用可核对。
    selected = _select_communities(query, summaries, limit=max(top_k, 4))
    # 同一事实会同时出现在 L0 社区和上层 L1 超社区里（L1 ⊃ L0）。
    # 若两个都喂给模型，同一行重复两遍且引用可能标到超社区上，核验时对不上原文。
    # 这里按事实去重，并把引用归给**更具体**的社区（level 越小越具体）。
    owner, order = {}, []
    for s in selected:
        anchors, facts = _project_facts(query, s)
        s["anchors"] = anchors
        s["facts"] = [f"{a} -{r}-> {b}" for a, r, b in facts]
        for f in s["facts"]:
            if f not in owner:
                owner[f] = s
                order.append(f)
            elif (owner[f].get("level") or 0) > (s.get("level") or 0):
                owner[f] = s

    map_outputs = []
    for s in selected:
        owned = [f for f in s["facts"] if owner.get(f) is s]
        if owned:
            map_outputs.append((s, owned))

    if not map_outputs:
        return BaseResponse(code=200,
                            msg=f"global：命中的 {len(selected)} 个社区内没有与问题相关的事实",
                            data={"answer": "现有社区摘要不足以回答", "communities": selected,
                                  "truncated": truncated, "map_hit": 0, "map_used": len(selected)})

    lines = []
    for s, facts in map_outputs:
        head = f"[{s['community_id']}] (level={s.get('level')})"
        if s.get("anchors"):
            head += f" 命中实体: {', '.join(s['anchors'])}"
        lines.append(head + "\n" + "\n".join(f"- {f}" for f in facts))
    # R14-B3：评级 → 加点 这类"属性 + 规则"的连接由代码算定，模型只做表述。
    # 实测把它交给 7B：同一批事实换问法会答出 0 基点 / 60 基点 等不一致结果。
    _derived = _join_grade_rules(map_outputs)
    if _derived:
        lines.append("【代码推导：由图内两条事实组合，非外部知识】\n" +
                     "\n".join(f"- [{cid}] {f}" for f, cid in _derived))
    prompt = REDUCE_PROMPT.format(question=query, summaries="\n\n".join(lines))
    # 贪心解码 + 固定 seed：同一问题、同一事实必须可复现，否则"效果好坏"取决于采样运气
    answer = requests_llm(prompt, model_info, server_config, prompt_flag=True,
                          temperature=0.0, seed=42)
    if not answer:
        return BaseResponse(code=500, msg="社区摘要汇总失败（模型未返回内容）", data={"communities": selected})
    answer, _cite_fixes = _fix_bp_citations(answer, _derived)
    cited = [s for s, _e in map_outputs if s["community_id"] and s["community_id"] in answer]
    return BaseResponse(code=200,
                        msg=f"global 汇总完成（社区 {len(summaries)} 个，命中 {len(selected)} 个，"
                            f"有相关事实 {len(map_outputs)} 个）",
                        data={"answer": answer,
                              "communities": cited or [s for s, _e in map_outputs],
                              "truncated": truncated,
                              "map_used": len(selected), "map_hit": len(map_outputs),
                              # 审计：哪些行的社区号被纠正到规则社区（可逐条核对）
                              "cite_fixes": _cite_fixes,
                              "derived_facts": [f for f, _c in _derived]})


def del_community(payload: dict) -> BaseResponse:
    """删除社区摘要索引（补 del_space_data 不联动 Milvus 的缺口）。"""
    kb = str(payload.get("space_name", "")).replace("g_", "")
    # 同 write_summary_indexes：ES 名 lower，Milvus 集合名保持原样。
    # 注意（A-data 2026-10-27）：Milvus 侧 `del_collection` 会自己加前导下划线
    # （`generate_collection_name_uuid()`），所以这里**只能传不带下划线的名字**——
    # 若传 `_community_summary_<kb>`，会被再加一次成 `__community_summary_<kb>`，
    # 名称不匹配 → 幂等返回 dropped=false，**静默不删**（不会误删，但会以为删了）。
    # 另：整 KB 重建/回滚才用它；日常"清干净"走 A 的整代替换（generate_community 先删旧代再写新代），
    # 不要反复 drop+重建（每次要重做 collection+index，约 1.7s）。
    es_index = f"community_summary_{_idx(kb)}"
    mv_collection = f"community_summary_{kb}"
    ok = []
    for port, path, body in [
        (ES_PORT, "del_index", {"index_name": es_index}),
        (MILVUS_PORT, "del_collection", {"db_name": "graph_base", "collection_name": mv_collection}),
    ]:
        try:
            r = _post(port, path, body, timeout=120)
            ok.append({"target": path, "status": r.status_code, "body": r.text[:120]})
        except Exception as e:
            ok.append({"target": path, "error": str(e)})
    return BaseResponse(code=200, msg="社区摘要索引删除已执行（以返回明细为准）", data={"detail": ok})
