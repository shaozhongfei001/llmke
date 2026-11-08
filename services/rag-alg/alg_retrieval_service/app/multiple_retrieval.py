#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 15:55
# @Author  : yuxj
# @File    : multiple_retrieval.py
import asyncio
import json
import re
import traceback

import requests
from langchain_core.documents import Document

# [R12-ADAPT-ALG-03] 原为模块级 `from zhipuai import ZhipuAI`（R12 未安装该依赖，见任务书"不装 zhipuai"）。
# 模块级导入会让整个检索服务在 import 期就崩，即使请求里 enable_web_search=false。
# 改为惰性导入，仅在真正调用智谱联网搜索时导入。

from app.operators.client import es_client
from base import WebSearchResult
from operators.client.es_client import ESClient
from operators.client.milvus_client import MilvusClient
from operators.client.graph_client import GraphClient
from operators.client.web_search_client import WebSearchClient
from operators.common.log import logger
# P2-L8：图召回必须用**原库名**（18094 按库目录组织）；影子名 `v2cand_kb_9` 不是库名。
# 通道名（`table_chunks_*` 等）也统一走投影层映射，避免各调用点各自裸拼。
from projection_read import channel_name as _channel_name
from projection_read import original_kb as _original_kb
from utils import create_uuid



async def multiple_retrieval(question, knowledge_base_name, top_k, server_config, es_milvus_enabled=None, table_pk_list=None,
                             query_condition=None, cec_kb_file_list=None, enabled_faq=False, dense_weight=None, condition_symbol='and', enable_web_search=False, enable_database=False, database_name=[]):
    """
    多路召回
    :param question: 用户问题
    :param knowledge_base_name: 知识库名称
    :param top_k: 返回数据条数
    :param server_config: 配置
    :param es_milvus_enabled: es和milvus 查询开关
    :param table_pk_list: table_summary查询到pk，用于条件查询
    :param query_condition 查询条件
    :param cec_kb_file_list cec 查询条件
    :param enabled_faq faq查询
    :param dense_weight 数据筛选
    :param condition_symbol 逻辑查询符号
    :param enable_web_search 联网搜索
    :param enable_database 数据库问答
    :param database_name 数据库名称
    :return: 多路召回的合并数据
    """
    tasks = []
    # # 判断是否需要执行 FAQ 查询
    if enabled_faq:
        es_knowledge_base_list = [kn for kn in knowledge_base_name if not kn.startswith("faq_")]
        faq_knowledge_base_list = [kn for kn in knowledge_base_name if kn.startswith("faq_")]
        if faq_knowledge_base_list:
            tasks.append(
                retrieval_elastic_faq(question, faq_knowledge_base_list, top_k, query_condition, server_config))
            tasks.append(retrieval_milvus(question, faq_knowledge_base_list, top_k, server_config,
                                          query_condition=query_condition))
    else:
        es_knowledge_base_list = knowledge_base_name  # 不过滤 FAQ

    # 处理 Milvus & Elastic 检索
    use_milvus = es_milvus_enabled.get("milvus", True) if es_milvus_enabled else True
    use_es = es_milvus_enabled.get("es", True) if es_milvus_enabled else True

    if use_milvus:
        tasks.append(
            retrieval_milvus(question, knowledge_base_name, top_k, server_config, table_pk_list, query_condition,
                             cec_kb_file_list, dense_weight=dense_weight,
                             condition_symbol=condition_symbol))
    if use_es:
        elastic_task = retrieval_elastic_cec if cec_kb_file_list else retrieval_elastic
        tasks.append(
            elastic_task(question, es_knowledge_base_list, top_k, server_config, table_pk_list,
                         cec_kb_file_list or query_condition, dense_weight=dense_weight))
    if enable_web_search:
        tasks.append(retrieval_web_search(question, top_k, server_config))
    if enable_database:
        tasks.append(retrieval_database_search(question, database_name, top_k, server_config))
    results = await asyncio.gather(*tasks)

    documents_list = []
    for res in results:
        documents_list.extend(res)
    if not documents_list:
        return {}
    documents_list = {question: documents_list}
    return documents_list


async def es_requests(data, server_config, question, top_k=None, dense_weight=None):
    """
    es 查询接口
    Args:
        data:
        server_config:
        question:
        top_k:
        dense_weight:

    Returns:

    """
    es_documents = []
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    search_url = es_url + 'search_by_custom_param'
    es_response = None

    try:
        # 发起ES查询请求
        es_response = await ESClient.request(es_url=search_url, data=data)
        es_data = es_response["data"]["result_data"]

        # 对结果按分数排序
        es_data = sorted(es_data, key=lambda x: x.get("_score", 0), reverse=True)

    except Exception as e:
        logger.exception(f"index ES服务 查询异常, 错误详情: {e}。 请求URL: {search_url}, 请求参数data: {data}, 返回结果: {es_response}")
        return es_documents
    if es_data:
        scores = [hit["_score"] for hit in es_data]
        threshold = server_config.get("es_threshold", 0.6)
        threshold_score = max(scores) * threshold
        for i, x in enumerate(es_data):
            if x["_score"] < threshold_score:
                continue
            metadata = x['_source'].get('metadata', {})
            metadata["search"] = {
                "type": ["es"],
                "query": question,
                "rank": [i]
            }
            metadata["score"] = x["_score"]
            es_documents.append(Document(page_content=x['_source']['page_content'], metadata=metadata))

    if dense_weight and top_k:
        data_radio = round((1 - dense_weight) * top_k)
        es_documents = es_documents[:data_radio]
    return es_documents


async def retrieval_milvus(question, knowledge_base_name, top_k, server_config, table_pk_list=None,
                           query_condition=None, cec_kb_file_list=None,
                           dense_weight=None, condition_symbol='and'):
    """
    # milvus 查询接口
    Args:
        question:
        knowledge_base_name:
        top_k:
        server_config:
        table_pk_list:
        query_condition:
        cec_kb_file_list:
        dense_weight:
        condition_symbol:

    Returns:

    """
    milvus_documents = []

    # 构造 expr 查询参数
    expr_parts = []
    if table_pk_list:
        expr_parts.append(f"table_summary_id in {table_pk_list}")
    if query_condition:
        for k, v in query_condition.items():
            if k == "labels":
                labels_expr = " || ".join([f"array_contains({k}, '{cv}')" for cv in v])
                expr_parts.append(labels_expr)
            else:
                expr_parts.append(f"{k} in {v}")
    expr = f" {condition_symbol} ".join(expr_parts) if expr_parts else ''

    # todo 缺少embed模型参数
    data = {
        "query": question,
        "collection_name": knowledge_base_name,
        "top_k": top_k or server_config.get("retrieval_top_k", 10),
        "search_param": expr,
        "cec_query_condition": {} if cec_kb_file_list is None else cec_kb_file_list
    }

    milvus_url = f"http://{server_config['milvus_config']['host']}:{server_config['milvus_config']['port']}/milvus_vector_search"
    try:
        response = await MilvusClient.request(milvus_url=milvus_url, data=data)
    except Exception as e:
        logger.exception(f"异步请求 milvus index服务异常: {e}")
        return milvus_documents

    try:
        milvus_data = response.get('data', {}).get('result_data', [])
        milvus_data = sorted(milvus_data, key=lambda x: x['metadata'].get("score", 0), reverse=True)
    except Exception as e:
        logger.error(f"解析 milvus index服务返回数据失败: {e}, 数据: {response}")
        return milvus_documents

    threshold_score = server_config.get("milvus_threshold", 0.5)
    for i, x in enumerate(milvus_data):
        score = x['metadata'].get("score", 0)
        if score < threshold_score:
            continue
        x["metadata"]["search"] = {
            "type": ["milvus"],
            "query": question,
            "rank": [i]
        }

        # 尝试解析 offset
        # R14-C-FIX-09（A/F 联合定位）：原实现遇到一行 offset 不是合法 JSON 就 break，
        # 整批 dense 召回被截断（FAQ 行在 Milvus 里 offset 落成空串 → faq_result_list=0，
        # 表现为"FAQ 直答永远不命中"；同理普通向量召回也会被静默清空）。
        # 坏数据只应降级为"无定位"，绝不允许中断整批。
        try:
            raw_offset = x['metadata'].get('offset')
            if raw_offset in (None, "", b""):
                x['metadata']['offset'] = []
            elif isinstance(raw_offset, str):
                x['metadata']['offset'] = json.loads(raw_offset)
        except Exception as e:
            logger.warning(f"offset 非合法 JSON，按无定位处理并继续: {e}, 数据: {str(x)[:200]}")
            x['metadata']['offset'] = []

        milvus_documents.append(Document(page_content=x['page_content'], metadata=x['metadata']))

    if dense_weight:
        data_radio = round(dense_weight * top_k)
        milvus_documents = milvus_documents[:data_radio]
    return milvus_documents


def es_single_question_query_sql(question, top_k, server_config, knowledge_base_name, query_condition):
    """
    es 针对问题查询，不考虑其他条件，主要用于faq查询
    同时查询page_content和question字段，使用best_fields取最高分值
    Args:
        question:
        top_k:
        server_config:
        knowledge_base_name:
        query_condition:

    Returns:

    """
    data = {
        "query_body": {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": question,
                                "fields": ["page_content", "question"],
                                "type": "best_fields"
                            }
                        }
                    ],
                    "filter": []
                }
            },
            "size": top_k or server_config["retrieval_top_k"]
        },
        "index_name": list(knowledge_base_name),
    }

    if query_condition:
        for k, v in query_condition.items():
            data["query_body"]["query"]["bool"]["filter"].append(
                {"terms": {f"metadata.{k}.keyword": v}}
            )

    return data


async def retrieval_elastic_faq(question, knowledge_base_name, top_k, query_condition, server_config):
    """
    faq  查询 索引字段只需要question
    Args:
        question:
        knowledge_base_name:
        top_k:
        query_condition:
        server_config:

    Returns:

    """
    data = es_single_question_query_sql(question, top_k, server_config, knowledge_base_name, query_condition)
    es_documents = await es_requests(data, server_config, question)
    return es_documents


def es_query_params(knowledge_base_name, top_k, question, server_config):
    data = {
        "query_body": {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "page_content": question
                            }
                        },
                        {
                            "match": {
                                "metadata.source": question
                            }
                        },
                        {
                            "match": {
                                "metadata.title_path": question
                            }
                        }
                    ]
                }
            },
            "size": top_k or server_config["retrieval_top_k"]
        },
        "index_name": knowledge_base_name,
    }
    return data


async def retrieval_elastic_cec(question, knowledge_base_name, top_k, server_config, table_pk_list=None,
                                cec_kb_file_list=None, dense_weight=None):
    condition_knowledge_base_name = []
    full_es_documents = []
    for name in knowledge_base_name:
        if name.replace("table_chunks_", "").replace("table_summary_", "") in cec_kb_file_list:
            condition_knowledge_base_name.append(name)
        elif name in cec_kb_file_list:
            condition_knowledge_base_name.append(name)
    full_knowledge_base_name = list(set(knowledge_base_name) - set(condition_knowledge_base_name))
    if full_knowledge_base_name:
        data = es_query_params(full_knowledge_base_name, top_k, question, server_config)
        if table_pk_list:
            data["query_body"]["query"]["bool"]["filter"] = [
                {"terms": {"metadata.table_summary_id.keyword": table_pk_list}}]
        full_es_documents = await es_requests(data, server_config, question)
    cec_es_documents = []
    if cec_kb_file_list:
        for ckbn in condition_knowledge_base_name:
            cn_p = ckbn.replace("table_chunks_", "").replace("table_summary_", "")
            data = es_query_params([ckbn], top_k, question, server_config)
            if table_pk_list:
                data["query_body"]["query"]["bool"]["filter"] = [
                    {"terms": {"metadata.table_summary_id.keyword": table_pk_list}}]
            filter_param = [
                {"terms": {f"metadata.file_id.keyword": cec_kb_file_list[ckbn if ckbn in cec_kb_file_list else cn_p]}}]
            if "filter" not in data["query_body"]["query"]["bool"].keys():
                data["query_body"]["query"]["bool"]["filter"] = filter_param
            else:
                data["query_body"]["query"]["bool"]["filter"].extend(filter_param)
            condition_es_documents = await es_requests(data, server_config, question)
            cec_es_documents.extend(condition_es_documents)
    full_es_documents.extend(cec_es_documents)
    return full_es_documents


async def retrieval_elastic(question, knowledge_base_name, top_k, server_config, table_pk_list=None,
                            query_condition=None, dense_weight=None):
    data = {
        "query_body": {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "page_content": question
                            }
                        },
                        {
                            "match": {
                                "metadata.source": question
                            }
                        },
                        {
                            "match": {
                                "metadata.title_path": question
                            }
                        }
                    ]
                }
            },
            "size": top_k or server_config["retrieval_top_k"]
        },
        "index_name": [name for name in knowledge_base_name],
    }
    simple_data = es_single_question_query_sql(question, top_k, server_config, knowledge_base_name, query_condition)
    if table_pk_list:
        data["query_body"]["query"]["bool"]["filter"] = [
            {"terms": {"metadata.table_summary_id.keyword": table_pk_list}}]
        # simple_data["query_body"]["query"]["bool"]["filter"] = [{"terms": {"metadata.table_summary_id.keyword": table_pk_list}}]
    elif query_condition:
        filter_param = []
        for k, v in query_condition.items():
            filter_param.append({"terms": {f"metadata.{k}.keyword": v}})
        if "filter" not in data["query_body"]["query"]["bool"].keys():
            data["query_body"]["query"]["bool"]["filter"] = filter_param
            # simple_data["query_body"]["query"]["bool"]["filter"] = filter_param
        else:
            data["query_body"]["query"]["bool"]["filter"].extend(filter_param)
            # simple_data["query_body"]["query"]["bool"]["filter"] = filter_param
    es_documents = await es_requests(data, server_config, question, top_k, dense_weight)
    simple_es_documents = await es_requests(simple_data, server_config, question, top_k, dense_weight)
    es_documents.extend(simple_es_documents)
    return es_documents



async def retrieval_elastic_database(question, database_name, top_k, server_config, dense_weight=None):
    data = {
        "query_body": {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "page_content": question
                            }
                        }
                    ]
                }
            },
            "size": top_k or server_config["retrieval_top_k"]
        },
        "index_name": [name for name in database_name],
    }
    es_documents = await es_requests(data, server_config, question, top_k, dense_weight)
    return es_documents


def _pick_pk(raw):
    """平台 chunk 主键必须是整数：Java 侧 RetrieveDoc.pk 是 Long。

    字符串（如 "chunk-<hash>"）会让 fastjson `parseLong` 抛异常，打挂整个 question_re；
    非法/缺失一律 None，由引用解析兜底，绝不拿字符串充数。
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


async def retrieval_graph(question, knowledge_base_name, top_k, model_info, server_config):
    """图召回：直连 HippoRAG（18094 /v2/graph/query，按库路由）。

    此前调 19529 legacy 图（/query_graph_data），依赖 model_info 做实体识别，且旧 Nebula 图
    与前端"知识图谱"视图（18094 HippoRAG）数据割裂。改为直连 HippoRAG 图检索，与传统 RAG
    （ES/Milvus/FAQ）在同一召回服务内融合，实现真正的混合召回。
    """
    graph_documents = []
    hipporag = server_config.get("hipporag_config") or {}
    host = hipporag.get("host", "127.0.0.1")
    port = hipporag.get("port", 18094)
    for k_name in knowledge_base_name:
        # 只对基础库名做图召回（faq_/table_chunks_/table_summary_ 是索引前缀，不是库）
        if k_name.startswith(("faq_", "table_chunks_", "table_summary_")):
            continue
        data = {
            "query": question,
            # 18094 QueryRequest.top_k 硬约束 [1,20]，越界 422
            "top_k": min(top_k or server_config.get("retrieval_top_k", 10), 20),
            "kb": _original_kb(k_name),
        }
        full_url = f"http://{host}:{port}/v2/graph/query"
        try:
            graph_resp = await GraphClient.request(graph_url=full_url, data=data) or {}
        except Exception as e:
            logger.exception(f"HippoRAG 图检索报错: {e}, URL: {full_url}, space={k_name}")
            continue
        if not isinstance(graph_resp, dict):
            continue
        # fail-closed：executed_route 不是 GRAPH（如 NOT_BUILT / DENSE_FALLBACK）就不冒充图召回
        if graph_resp.get("executed_route") != "GRAPH":
            logger.warning(f"HippoRAG 图检索跳过 space={k_name}: "
                           f"route={graph_resp.get('executed_route')} reason={graph_resp.get('reason')}")
            continue
        for i, item in enumerate(graph_resp.get("docs") or []):
            if not isinstance(item, dict):
                continue
            text = item.get("text") or ""
            if not text:
                continue
            sources = item.get("sources") or []
            primary = sources[0] if sources else {}
            locator = primary.get("locator")
            chunk_index = None
            if isinstance(locator, str):
                m = re.search(r"chunk=(\d+)", locator)
                chunk_index = int(m.group(1)) if m else None
            metadata = {
                # 与其他召回（ES/Milvus）一致：search.type 会由 process_return_results 并入 search_type
                "search": {"type": ["graph"], "query": question, "rank": [i]},
                "search_type": ["graph"],
                # og_process / merge_and_rerank 依赖这两个键（KeyError 会打挂整轮 rerank）
                "knowledge_base_name": k_name,
                # pk 用快照 sources.json 里的**平台真实 chunk 主键**（投影 _chunk_pk 的产物，
                # 是整数）。取不到才置 None —— 绝不能拿 "chunk-<hash>" 字符串充数：
                # Java 侧 RetrieveDoc.pk 是 Long，字符串会触发 parseLong error 打挂 question_re。
                "pk": _pick_pk(primary.get("pk")),
                # file_id 用快照里记录的**平台真实文件 id**（投影时写入），Java 才能反查文件路径
                "file_id": primary.get("file_id"),
                # 不设 source 键：get_reranker_score 对 source 非 None 会 os.path.split(source)，
                # 而 source=None/纯文件名会抛错或让 Java 侧 NPE；缺键则走纯正文 rerank。
                # locator 必须走 position：process_return_results 的白名单不含 locator，
                # 但会原样透出 position（Java RetrieveMetaData.position 是 Object）。
                "position": {"locator": locator, "sources": sources},
                "chunk_index": chunk_index,
                "title": primary.get("title"),
                "locator": locator,
                "score": None,
                "idx": item.get("idx"),
                "sources": sources,
                "page_content": text,
            }
            graph_documents.append(Document(page_content=text, metadata=metadata))
    return graph_documents


def es_multi_version_params(knowledge_base_name, file_id, top_k, question):
    data = {
        "query_body": {
            "query": {
                "bool": {
                    "must": [
                        # 精确匹配 file_id（假设为 keyword 类型）
                        {"term": {"metadata.file_id": int(file_id)}},
                        # 模糊查询 query 字段
                        {
                            "match": {
                                "page_content": question.replace("\xa0", " ")
                            }
                        }
                    ]
                }
            },
            "size": top_k
        },
        "index_name": [knowledge_base_name],
    }
    return data


async def retrieval_multi_version_elastic(documents_result_list, multi_version_dict, top_k, server_config):
    """
    根据内容召回多版本内容，读取documents_result_list中documents_result的内容
    判断是否有多版本文件，以及对应的多版本文件内容
    """
    tasks = []
    new_documents_result_list = []
    pk_id_list = []
    for documents_result in documents_result_list:
        es_knowledge_base_name = documents_result["knowledge_base_name"]
        pk_id = documents_result["pk"]
        file_id = str(documents_result["metadata"]["file_id"])
        if file_id in multi_version_dict:
            father_file_id = multi_version_dict[file_id]
            question = documents_result["page_content"]
            chunk_type = documents_result["metadata"]["chunk_type"]
            if chunk_type == "table":
                # P2-L8：不要再裸拼 `"table_chunks_" + 名字` —— 影子模式下这个名字已是
                # `v2cand_kb_9`，拼出来 `table_chunks_v2cand_kb_9` 与写侧
                # `v2cand_table_chunks_kb_9` 不符。先还原原库名，再走通道名映射。
                es_knowledge_base_name = _channel_name(
                    "table_chunks", _original_kb(es_knowledge_base_name))
            data = es_multi_version_params(es_knowledge_base_name, father_file_id, top_k, question)
            tasks.append(es_requests(data, server_config, question))
            pk_id_list.append(pk_id)
    results = await asyncio.gather(*tasks)
    pk_id_dict = {}
    for res, pk_id in zip(results, pk_id_list):
        if pk_id not in pk_id_dict:
            pk_id_dict[pk_id] = []
        for document in res:
            father_pk_id = document.metadata["pk"]
            pk_id_dict[pk_id].append(father_pk_id)
        new_documents_result_list.extend(res)
    return new_documents_result_list, pk_id_dict


async def retrieval_web_search(question, top_k, server_config):
    web_search_config = server_config.get("web_search_config", {})
    api_key = web_search_config.get("zhipuai_api_key", "")
    max_web_results = web_search_config.get("max_web_results", "")
    api_params = {
        "search_query": question,
        "search_engine": web_search_config.get("search_engine", "search_pro"),
        "count": max_web_results if top_k > max_web_results else top_k,
        "content_size": web_search_config.get("content_size", "medium"),
        "search_domain_filter": web_search_config.get("search_domain_filter"),
        "search_recency_filter": web_search_config.get("search_recency_filter")
    }
    response = await WebSearchClient.request(api_key=api_key, api_params=api_params)
    # 解析搜索结果
    search_results = []
    if hasattr(response, 'search_result') and response.search_result:
        logger.info(f"✅ 开始解析 {len(response.search_result)} 条搜索结果")

        for i, result in enumerate(response.search_result):
            try:
                # 使用getattr安全获取属性
                if len(str(getattr(result, 'link', '') or '')) > 0:
                    search_result = WebSearchResult(
                        type="web_search",
                        page_content=str(getattr(result, 'content', '') or ''),
                        metadata={"title": str(getattr(result, 'title', '') or ''),
                                  "snippet": str(getattr(result, 'content', '') or ''),
                                  "source": str(getattr(result, 'media', '') or ''),
                                  "publish_date": str(getattr(result, 'publish_date', '') or ''),
                                  "refer": str(getattr(result, 'refer', '') or ''),
                                  "link": str(getattr(result, 'link', '') or ''),
                                  "type": "text"
                                  },
                        order_num=str(create_uuid()),
                        offset=[],
                        pic_url_list=[]
                    )
                    title = str(getattr(result, 'title', '') or '')
                    search_results.append(search_result)
                    logger.info(f"✅ 第 {i + 1} 条结果解析成功: {title}")
            except Exception as e:
                logger.error(f"❌ 解析第 {i + 1} 条搜索结果失败: {e}")
                continue
    else:
        logger.warning("⚠️ 没有找到有效的搜索结果")

    logger.info(f"联网搜索完成，获取到 {len(search_results)} 条结果")
    return search_results

async def retrieval_database_search(question, database_name, top_k, server_config):
    """
    召回数据库表
    首先进行es召回
    然后生成sql
    然后拼接返回体
    """
    database_sql = await retrieval_elastic_database(question, database_name, top_k, server_config)
    return database_sql
