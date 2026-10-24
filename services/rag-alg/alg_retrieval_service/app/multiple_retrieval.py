#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 15:55
# @Author  : yuxj
# @File    : multiple_retrieval.py
import asyncio
import json
import traceback

import requests
from langchain_core.documents import Document
from zhipuai import ZhipuAI

from app.operators.client import es_client
from base import WebSearchResult
from operators.client.es_client import ESClient
from operators.client.milvus_client import MilvusClient
from operators.client.graph_client import GraphClient
from operators.client.web_search_client import WebSearchClient
from operators.common.log import logger
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
        try:
            if "offset" in x['metadata']:
                x['metadata']['offset'] = json.loads(x['metadata']['offset'])
        except Exception as e:
            logger.error(f"解析 offset 失败: {e}, 数据: {x}")
            break

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


async def retrieval_graph(question, knowledge_base_name, top_k, model_info, server_config):
    graph_documents = []
    for k_name in knowledge_base_name:
        data = {
            "space_name": "g_" + k_name,
            "query": question,
            "model_info": model_info,
            "depth": 3,
            "top_k": top_k or server_config["retrieval_top_k"],  # top_k or server_config["retrieval_top_k"]
        }

        graph_url = 'http://' + server_config["graph_config"]["host"] + ':' + str(
            server_config["graph_config"]["port"]) + '/'
        full_url = f'{graph_url}query_graph_data'
        milvus_data = None

        try:
            milvus_data = await GraphClient.request(graph_url=full_url, data=data)
            milvus_data = milvus_data['data']['result_data']
        except Exception as e:
            logger.exception(f"graph查询报错: {e}, 请求 URL: {graph_url}, 请求参数 data: {data}, 图检索结果 response: {milvus_data}")
            return graph_documents

        for i, x in enumerate(milvus_data):
            x["metadata"]["search"] = {
                "type": ["graph"],
                "query": question,
                "rank": [i]
            }
            try:
                x["metadata"]["offset"] = json.loads(x["metadata"]["offset"])
            except Exception as e:
                logger.info(f"查询结果中，数据没有offset字段,{e}")
            graph_documents.append(Document(page_content=x['page_content'], metadata=x['metadata']))
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
                es_knowledge_base_name = "table_chunks_" + es_knowledge_base_name
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
