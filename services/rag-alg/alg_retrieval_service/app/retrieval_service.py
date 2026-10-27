#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 15:40
# @Author  : yuxj
# @File    : retrieval_service.py
import asyncio
import math
import time

import pandas as pd
from collections import defaultdict as dd
import json
from langchain_core.documents import Document

from app.base import QARetrieveConfig, BaseResponse
from multiple_retrieval import multiple_retrieval, retrieval_graph, retrieval_multi_version_elastic
from operators.common.log import logger
from reranker_service import merge_and_rerank, merge_and_get_rrf_score
from retrieval_fun_tool import query_es_data, og_process, document_version, process_return_results, \
    multiple_retrieval_data_process, filter_tables_by_query, sorted_result, get_multi_version_dict, \
    query_es_file_index, query_max_index
from utils import return_nacos_model, create_uuid



async def retrieval_data(knowledge_base_name, top_k, server_config, verify_queries, enabled_summary=False, enabled_faq=True, es_milvus_enabled=None,
                         query_condition=None, cec_kb_file_list=None, dense_weight=None, condition_symbol='and', enable_web_search=False, enable_database=False, database_name=[]):
    """
    多路召回
    :param knowledge_base_name: 知识库名称
    :param top_k: 返回个数
    :param server_config: 配置
    :param verify_queries: query重改后的结果，COVE
    :param enabled_faq 是否启用faq
    :param es_milvus_enabled 是否启用faq
    :param enabled_summary 是否启用table_summary查询
    :param query_condition 查询条件
    :param cec_kb_file_list cec 查询条件
    :param dense_weight 数据库查询阈值
    :param faq_score_threshold faq阈值
    :param condition_symbol 逻辑运算符
    :param enable_web_search 联网搜索开发
    :param enable_database 数据库检索
    :param database_name 数据库名称
    :return: 多路召回的结果
    """
    knowledge_base_name = [kn for kn in knowledge_base_name if kn.strip()]
    full_knowledge_base_name = knowledge_base_name.copy()
    # 判断faq
    if enabled_faq is True:
        faq_knowledge_base_list = ["faq_" + kn for kn in knowledge_base_name]
        full_knowledge_base_name.extend(faq_knowledge_base_list)
    if enabled_summary:
        table_summary_list = ["table_summary_" + kn for kn in knowledge_base_name]
        full_knowledge_base_name.extend(table_summary_list)
    table_chunks_list = ["table_chunks_" + kn for kn in knowledge_base_name]
    full_knowledge_base_name.extend(table_chunks_list)
    tasks = [multiple_retrieval(query, full_knowledge_base_name, top_k, server_config, es_milvus_enabled=es_milvus_enabled,
                                query_condition=query_condition, cec_kb_file_list=cec_kb_file_list, enabled_faq=enabled_faq, condition_symbol=condition_symbol,
                                dense_weight=dense_weight, enable_web_search=enable_web_search, enable_database=enable_database, database_name=database_name) for
             query in verify_queries]
    results = await asyncio.gather(*tasks)
    multiple_retrieval_data = await asyncio.to_thread(lambda: multiple_retrieval_data_process(results))
    documents, table_summary_data, web_search_list, database_list = multiple_retrieval_data
    return documents, table_summary_data, web_search_list, database_list


async def retrieval_table_chunks(knowledge_base_name, top_k, server_config, table_summary_data):
    # 查询table_chunk
    table_chunk_list = ["table_chunks_" + kn for kn in knowledge_base_name]
    table_query_pk_dict = {}
    for qus, doc_list in table_summary_data.items():
        table_pk_list = []
        for doc in doc_list:
            table_pk_list.append(str(doc.metadata["pk"]))
        table_query_pk_dict[qus] = table_pk_list
    tasks = [multiple_retrieval(query, table_chunk_list, top_k, server_config, table_pk_list=pk_list) for query, pk_list
             in
             table_query_pk_dict.items()]
    results = await asyncio.gather(*tasks)
    return results


async def process_img_result(query, documents_list, knowledge_base_name, server_config):
    doc_pk_list = [ds.metadata["pk"] for ds in documents_list]
    img_pk_set = set()
    new_ds_list = []
    dl_image_dict = {}
    for ds in documents_list:
        if "pic_children_id_list" in ds.metadata.keys() and ds.metadata["pic_children_id_list"]:
            c_pk_list = ds.metadata["pic_children_id_list"]
            for cp in c_pk_list:
                img_pk_set.add(cp)
                dl_image_dict[cp] = (ds.metadata["score"], ds.metadata["rerank_score_rank"], ds.metadata["rrf_score"],
                                     ds.metadata["rrf_score_rank"])
        if "text_parent_id_list" in ds.metadata.keys() and ds.metadata["text_parent_id_list"]:
            f_pk_list = ds.metadata["text_parent_id_list"]
            for f_pk in f_pk_list:
                if f_pk not in doc_pk_list:
                    img_pk_set.add(f_pk)
                    dl_image_dict[f_pk] = (ds.metadata["score"], ds.metadata["rerank_score_rank"],
                                           ds.metadata["rrf_score"], ds.metadata["rrf_score_rank"])
    if img_pk_set:
        img_full_list = await query_es_data(query, list(img_pk_set), knowledge_base_name, server_config)
        if img_full_list:
            for fl in img_full_list:
                fl.metadata["score"] = dl_image_dict[fl.metadata["pk"]][0]
                fl.metadata["rerank_score_rank"] = dl_image_dict[fl.metadata["pk"]][1]
                fl.metadata["rrf_score"] = dl_image_dict[fl.metadata["pk"]][2]
                fl.metadata["rrf_score_rank"] = dl_image_dict[fl.metadata["pk"]][3]
                fl.metadata["search_type"] = ["es"]
                new_ds_list.append(fl)
            documents_list.extend(new_ds_list)
    return documents_list


async def process_table_result(documents, table_summary_data, external_pk, qa_model, server_config, queries,
                               log_pk_dict, ori_query):
    table_summary_data, log_pk_dict = await rerank_cal_fun(qa_model, ori_query, table_summary_data, external_pk,
                                                           server_config, log_pk_dict)
    if table_summary_data and any(bool(v) for v in table_summary_data.values()):
        for ques, doc_list in documents.items():
            for doc in doc_list:
                if "type" in doc.metadata.keys() and doc.metadata["type"] == "table":
                    doc_list.remove(doc)
        # 查询 table chunk
        chunk_results = await retrieval_table_chunks(qa_model.knowledge_base_name, qa_model.top_k, server_config,
                                                     table_summary_data)
        if chunk_results:
            for docs in chunk_results:
                for qus, ds_list in docs.items():
                    if qus in documents:
                        documents[qus].extend(ds_list)
                    else:
                        documents[qus] = ds_list
    return documents, log_pk_dict


async def retrieval_faq_answer(qa_model, external_pk, server_config, log_pk_dict, queries, faq_score_threshold):
    """
    faq 召回
    Args:
        qa_model:
        external_pk:
        server_config:
        log_pk_dict:
        queries:
        faq_score_threshold:
    Returns:

    """
    faq_documents_list = []
    documents, *others = await retrieval_data(qa_model.knowledge_base_name, qa_model.top_k, server_config, verify_queries=queries,
                                        enabled_faq=qa_model.enabled_faq, query_condition=qa_model.condition_json)
    if documents:
        rerank_result = await asyncio.to_thread(
            lambda: rerank_cal_fun(qa_model, qa_model.query, documents, external_pk, server_config, log_pk_dict))
        documents_list, log_pk_dict = rerank_result
        faq_score_threshold = faq_score_threshold if qa_model.rerank else 0.1
        answer_list = [du for du in documents_list if
                       "answer" in du.metadata.keys() and du.metadata["score"] > faq_score_threshold and
                       du.metadata["status"] == 1]
        if answer_list:
            faq_documents_list = [
                {"faq_question": dict(x)["metadata"]["question"], "faq_answer": dict(x)["metadata"]["answer"],
                 "score": dict(x)["metadata"]["score"]} for x in answer_list]
    return faq_documents_list, log_pk_dict


async def rerank_cal_fun(qa_model, query, documents, external_pk, server_config, log_pk_dict):
    t11 = time.time()
    documents = merge_and_get_rrf_score(query, documents)
    log_pk_dict = og_process(external_pk, query, documents, server_config, log_pk_dict)
    enabled_rerank = True
    if hasattr(qa_model, 'enabled_rerank'):
        if not qa_model.enabled_rerank:
            enabled_rerank = False
    elif hasattr(qa_model, 'rerank'):
        if not qa_model.rerank:
            enabled_rerank = False
    if enabled_rerank:
        documents, log_pk_dict = await merge_and_rerank(documents, qa_model.top_n, qa_model.score_threshold,
                                                        server_config, log_pk_dict,
                                                        rerank_model_info=qa_model.rerank_model_info)
    logger.info(f"rerank处理时常：{time.time() - t11}")
    return documents, log_pk_dict

async def rerank_web_search_fun(qa_model, query, documents, external_pk, server_config, log_pk_dict=None, no_rerank_score=False):
    t11 = time.time()
    enabled_rerank = True
    if hasattr(qa_model, 'enabled_rerank'):
        if not qa_model.enabled_rerank:
            enabled_rerank = False
    elif hasattr(qa_model, 'rerank'):
        if not qa_model.rerank:
            enabled_rerank = False
    if enabled_rerank:
        documents, log_pk_dict = await merge_and_rerank(documents, qa_model.top_n, qa_model.score_threshold, server_config, log_pk_dict,
                                                        rerank_model_info=qa_model.rerank_model_info, no_rerank_score=no_rerank_score)
    logger.info(f"rerank处理时常：{time.time() - t11}")
    return documents


def sorted_web_doc_list(documents):
    web_documents = []
    for query in documents:
        for doc in documents[query]:
            web_documents.append({"metadata": doc.metadata, "page_content": doc.page_content, "type": doc.type,
                                  "order_num": doc.order_num, "pic_url_list": doc.pic_url_list, "offset ": doc.offset})
    web_documents = sorted(web_documents, key=lambda x: x['metadata']['score'], reverse=True)
    return web_documents

def sorted_database_list(documents):
    web_documents = []
    for query in documents:
        for doc in documents[query]:
            web_documents.append({"metadata":doc.metadata,"page_content":doc.page_content,"type":"database",
                                  "order_num":"","pic_url_list":[],"offset ":[]})
    web_documents = sorted(web_documents, key=lambda x: x['metadata']['score'], reverse=True)
    return web_documents


async def process_multi_version_documents(documents_result_list, query, multi_version_dict, qa_model, server_config,
                                          log_pk_dict):
    """
    Process multi-version documents by retrieving elastic search results and merging them with existing documents.
    The multi-version results will be reranked and deduplicated like other retrieval results.

    Args:
        documents_result_list: List of existing document results
        query: The search query
        multi_version_dict: Multi-version mapping dictionary
        qa_model: QA model configuration
        server_config: Server configuration
        log_pk_dict: Log tracking dictionary

    Returns:
        Updated documents_result_list with multi-version documents merged and reranked
    """
    new_documents_result_list, pk_id_dict = await retrieval_multi_version_elastic(documents_result_list,
                                                                                  multi_version_dict,
                                                                                  qa_model.simi_top_k,
                                                                                  server_config)
    if len(new_documents_result_list) > 0:
        new_documents_result_dict = [{query: new_documents_result_list}]
        multiple_retrieval_data = await asyncio.to_thread(
            lambda: multiple_retrieval_data_process(new_documents_result_dict))
        documents, table_summary_data, web_search, database_sql  = multiple_retrieval_data

        # R14-C-FIX-11b：该分支的 documents 只在"确有普通文档块"时才会写入 query 键
        # （retrieval_fun_tool.multiple_retrieval_data_process 里 `if documents_list:` 才 set），
        # 若本次召回全是 table_summary/web，直接下标会 KeyError → 整个检索 500。
        # 同时保留小写键兜底（上游召回键可能已被 _add_query_to_queries 归一化成小写）。
        documents_list = (documents.get(query)
                          or documents.get(str(query).lower())
                          or [])
        documents_list = await asyncio.to_thread(lambda: document_version(documents_list, server_config, qa_model.knowledge_base_name))

        document_objects = []
        for doc_dict in documents_list:
            doc_obj = Document(
                page_content=doc_dict["page_content"],
                metadata=doc_dict["metadata"]
            )
            document_objects.append(doc_obj)

        # 对版本召回结果重排序
        multi_version_documents = {query: document_objects}
        multi_version_documents, log_pk_dict = await rerank_cal_fun(qa_model, query, multi_version_documents,
                                                                    create_uuid(), server_config, log_pk_dict)

        reranked_documents_list = multi_version_documents[query]
        for doc in reranked_documents_list:
            doc.metadata["knowledge_base_name"] = doc.metadata.get("knowledge_base_name", "")
            doc.metadata["faq_question"] = None
            doc.metadata["faq_answer"] = None
            doc.metadata["search_type"] = ["es"]

        reranked_documents_dict_list = []
        for doc in reranked_documents_list:
            doc_dict = {
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }
            reranked_documents_dict_list.append(doc_dict)

        add_documents_result_list = await asyncio.to_thread(
            lambda: process_return_results(reranked_documents_dict_list))

        documents_result_list += add_documents_result_list

        all_documents = documents_result_list + add_documents_result_list
        all_documents = sorted_result(all_documents)

        for document in documents_result_list:
            for pk_id in pk_id_dict:
                for id in pk_id_dict[pk_id]:
                    if id == document["pk"]:
                        document["son_pk_id"] = pk_id

    return documents_result_list


async def adjacent_chunk_process(documents_list, adjacent_chunk_num, index_names, server_config):
    index_dict = dd(set)
    additional_list = []

    for document in documents_list:
        index_dict[document['metadata']['source']].add(document['metadata']['chunk_index'])

    for document in documents_list:
        if document['type'] == 'image':
            continue
        file_index = document['metadata']['chunk_index']
        query_index_name = ['table_chunks_' + idx for idx in index_names] if document['type'] == 'table' else index_names
        left_pos, right_pos  = file_index - 1, file_index + 1
        left_part, right_part = [], []
        chunk_num = max((await query_max_index(document['metadata']['source'], index_names, server_config), await query_max_index(document['metadata']['source'], query_index_name, server_config)))
        while left_pos >= 0 and len(left_part) < adjacent_chunk_num  or right_pos <= chunk_num and len(right_part) < adjacent_chunk_num:
            if left_pos >= 0 and len(left_part) < adjacent_chunk_num:
                left_extend = await query_es_file_index(document['metadata']['source'], query_index_name, left_pos, server_config)
                if left_extend and not left_extend[0].metadata['type'] == 'image':
                    left_part += left_extend
                left_pos -= 1
            if right_pos <= chunk_num and len(right_part) < adjacent_chunk_num:
                right_extend = await query_es_file_index(document['metadata']['source'], query_index_name, right_pos, server_config)
                if right_extend and not right_extend[0].metadata['type'] == 'image':
                    right_part += right_extend
                right_pos += 1
        adjacent_chunk_list = [dict(x) for x in left_part+right_part]
        adjacent_chunk_list = await asyncio.to_thread(lambda: process_return_results(adjacent_chunk_list))
        additional_list += adjacent_chunk_list

    final_list = []
    for additional_chunk in additional_list:
        additional_file_name = additional_chunk['metadata']['source']
        additional_chunk_index = additional_chunk['metadata']['chunk_index']
        if additional_chunk_index not in index_dict[additional_file_name]:
            final_list.append(additional_chunk)
            index_dict[additional_file_name].add(additional_chunk_index)

    return final_list


async def multiple_retrieval_documents(qa_model: QARetrieveConfig):
    """
    多路召回检索服务
    :param qa_model:参数对象
    :return: 检索结果
    """
    uuid_test = create_uuid()
    t111 = time.time()
    logger.info(f"参数：{str(qa_model.json())}")
    log_pk_dict = {}
    queries = []
    log_list = []
    faq_result_list = []
    documents_result_list = []
    external_pk = create_uuid()
    logger.info("多路召回检索服务开始召回")
    query = qa_model.query
    server_config = await asyncio.to_thread(return_nacos_model().get_config)
    faq_score_threshold = qa_model.faq_score_threshold
    chunk_num_of_table_select = server_config.get("chunk_num_of_table_select", 30)

    # 回答修正，模型给出其他问题，query扩展和分布
    # if qa_model.query_enrich:
    #     queries = split_query(query, qa_model.model_name, server_config)
    # cove_queries = await factored_chain_of_verification(qa_model.query, qa_model.model_name, server_config)  # 回答修正，模型给出其他问题，query扩展和分布
    # queries.extend(cove_queries)
    # 将原始问题添加问题列表中
    # if any(char.isupper() for char in query):
    #     lower_query = query.lower()
    #     queries.append(lower_query)
    # else:
    #     queries.append(query)

    def _add_query_to_queries(query_str, target_list):
        if not query_str or not isinstance(query_str, str):
            return
        normalized_query = query_str.lower()
        target_list.append(normalized_query)

    # 将原始问题添加问题列表中
    _add_query_to_queries(query, queries)
    # 将改写后的问题添加问题列表中
    _add_query_to_queries(qa_model.rewritten_query, queries)

    # 多路召回 文本(图片),faq,table_summary
    t123 = time.time()
    search_policy_map = {
        1: {"es": True, "milvus": True},
        2: {"es": True, "milvus": False},
        3: {"es": False, "milvus": True}
    }
    documents, table_summary_data, web_search_list, database_list = await retrieval_data(qa_model.knowledge_base_name, qa_model.top_k, server_config, verify_queries=queries,
                                                         enabled_faq=qa_model.enabled_faq, query_condition=qa_model.condition_json, enabled_summary=True,
                                                         es_milvus_enabled=search_policy_map.get(qa_model.search_policy, 1), dense_weight=qa_model.dense_weight,
                                                         condition_symbol=qa_model.condition_logic_operations, enable_web_search=qa_model.enable_web_search,
                                                                          enable_database=qa_model.enable_database, database_name=qa_model.database_name)
    logger.info(f"查询时长：{time.time() - t123}")
    logger.info(f"共查出:{len(documents)}条数据")

    # 单表筛选
    if qa_model.enabled_table_select:  # 筛选表格信息
        if len(table_summary_data) == 0:
            logger.debug("table summary为空，无法进行信息筛选")
        else:
            selected_table_summary_dict = await filter_tables_by_query(query, table_summary_data, qa_model.model_info,
                                                                 server_config)
            if selected_table_summary_dict:
                # # 从es中直接获取全量表格切片
                # table_chunks = await query_es_table_data(query, table_ids, ["table_chunks_" + kn for kn in qa_model.knowledge_base_name], server_config)

                # 检索max_num个表格切片
                table_chunks = await retrieval_table_chunks(qa_model.knowledge_base_name, chunk_num_of_table_select,
                                                            server_config, selected_table_summary_dict)
                documents_list = []
                for search_result in table_chunks:
                    for q, documents in search_result.items():
                        documents_list.extend([d.__dict__ for d in documents])
                    table_chunks = process_return_results(documents_list[:int(chunk_num_of_table_select * 1.5)])

                if qa_model.adjacent_chunk_num > 0:
                    extend_chunks = await adjacent_chunk_process(table_chunks, qa_model.adjacent_chunk_num, qa_model.knowledge_base_name, server_config)
                    table_chunks += extend_chunks
                logger.info(f"表格筛选后，保留{len(table_chunks)}个table_chunks")
                return BaseResponse(code=200,
                                    msg=f'查询成功，指向特定表格,返回特定表格信息。',
                                    data={"faq_result_list": faq_result_list,
                                          "table_selected_list": table_chunks,
                                          "documents_list": [],
                                          "log_list": log_list})
    web_documents_result_list = []
    database_result_list = []
    # 开始处理表格数据
    if table_summary_data:
        documents, log_pk_dict = await process_table_result(documents, table_summary_data, external_pk, qa_model,
                                                            server_config, queries, log_pk_dict, query)
    if not documents and not web_search_list and not database_list:
        logger.info(f'查询成功,数据库并没有对应的文本，请检查知识库名称或问题。')
        return BaseResponse(code=200, msg=f'查询成功,数据库并没有对应的文本，请检查知识库名称或问题。',
                            data={"faq_result_list": faq_result_list,
                                  "documents_list": documents_result_list,
                                  "database_documents": [],
                                  "web_documents_list": [],
                                  "log_list": log_list})
    elif not documents and not database_list and web_search_list:
        web_documents_result_list = await rerank_web_search_fun(qa_model, query, web_search_list, external_pk,
                                                                server_config)
        web_documents_result_list = sorted_web_doc_list(web_documents_result_list)
        logger.info(f'查询成功,数据库并没有对应的文本，请检查知识库名称或问题。')
        return BaseResponse(code=200, msg=f'查询成功,数据库并没有对应的文本，请检查知识库名称或问题。',
                            data={"faq_result_list": faq_result_list,
                                  "documents_list": documents_result_list,
                                  "database_documents": [],
                                  "web_documents_list": web_documents_result_list[:qa_model.top_k],
                                  "log_list": log_list})
    elif not documents and database_list:
        database_result_list = await rerank_web_search_fun(qa_model, query, database_list, external_pk,
                                                                server_config, no_rerank_score=True)
        database_result_list = sorted_database_list(database_result_list)
        """
        判断是否需要进行处理
        """
        logger.info(f'查询成功,数据库并没有对应的文本，请检查知识库名称或问题。')
        for database_result in database_result_list:
            old_columns = database_result["metadata"]['columns']
            new_columns = json.dumps(json.loads(database_result["metadata"]['columns']), ensure_ascii=False)
            database_result["metadata"]['columns'] = new_columns
            database_result['page_content'] = database_result['page_content'].replace(old_columns, new_columns)
        return BaseResponse(code=200, msg=f'查询成功,数据库并没有对应的文本，请检查知识库名称或问题。',
                            data={"faq_result_list": faq_result_list,
                                  "documents_list": [],
                                  "database_documents": database_result_list[:qa_model.top_k],
                                  "web_documents_list": web_documents_result_list[:qa_model.top_k],
                                  "log_list": log_list})

    # 查询图
    if qa_model.enabled_graph:
        graph_documents = await retrieval_graph(query, qa_model.knowledge_base_name, qa_model.top_k, qa_model.model_info,
                                               server_config)
        if graph_documents:
            # R14-C-FIX-11（A/B 定位）：_add_query_to_queries 只把小写串放进 queries，于是 documents
            # 的键都是小写；这里原来直接用**原始大小写**取键 —— 任何含大写 ASCII 的查询
            # （AAA / T-CORE-001 / PRD-CORP-LOAN-2026-01 / 英文缩写）只要开图就 KeyError → 500，
            # Java 侧拿不到 documents_list → 引用必为空（表现为"开图 refs=0、但答案对"）。
            # 修法：按键时做"原始 → 小写"降级，并保证原始键存在（下游还有 documents[query] 的直接取值）。
            if query in documents:
                graph_target_key = query
            elif query.lower() in documents:
                graph_target_key = query.lower()
            else:
                graph_target_key = query
            # R14-C-FIX-18（B 定位 + TL 确认）：这里原来还有一句
            #   documents.setdefault(query, [])
            # 目的是"下游可能用原始串取键"。它制造了一个**空列表键**，而 reranker_service 是
            # `for qus, doc_list in documents.items()` 逐键发 rerank、且单批分支没有 try ——
            # 空列表会被服务端 400 "documents must be a non-empty list" 拒掉，异常冒泡把
            # **整轮 rerank** 变成空 → documents_list 空 → 引用归零 → 模型凭常识编答案
            # （实测编出 "AAA 35个基点"，真值 30）。触发条件：问句含大写 ASCII（AAA/T-CORE-001…）
            # 时 _add_query_to_queries 用小写键，于是 query 与原键不同名，补出来的就是空键。
            # 现改为"不存在就新建并立即填充"（同一条语句内 extend，绝不留下空键），
            # 下游取值一律走 documents.get(query) or documents.get(query.lower()) or []。
            documents.setdefault(graph_target_key, []).extend(graph_documents)

    # 合并数据开始计算排序
    documents, log_pk_dict = await rerank_cal_fun(qa_model, query, documents, external_pk, server_config, log_pk_dict)
    documents_list = [doc for doc_list in documents.values() for doc in doc_list]
    # 开始处理图片数据,数据反查  这个放到rerank之后
    web_documents_result_list = await rerank_web_search_fun(qa_model, query, web_search_list, external_pk,
                                                            server_config)
    web_documents_result_list = sorted_web_doc_list(web_documents_result_list)
    database_result_list = await rerank_web_search_fun(qa_model, query, database_list, external_pk,
                                                            server_config, no_rerank_score=True)
    database_result_list = sorted_database_list(database_result_list)
    documents_list = await process_img_result(qa_model.query, documents_list, qa_model.knowledge_base_name, server_config)
    answer_list = []
    # faq 筛选
    for du in documents_list.copy():
        if "answer" in du.metadata.keys():
            documents_list.remove(du)
            if du.metadata["score"] > faq_score_threshold and du.metadata["status"] == 1:
                answer_list.append(du)
    if answer_list:
        faq_result_list = [{"faq_question": dict(x)["metadata"]["query"], "faq_answer": dict(x)["metadata"]["answer"],
                            "score": dict(x)["metadata"]["score"]} for x in answer_list]
    if not documents_list and not faq_result_list and not web_documents_result_list and len(web_documents_result_list) == 0 and not database_result_list and len(database_result_list) == 0:
        logger.info(f'查询成功,但是经过重拍模型和FAQ筛选后，查询结果皆小于阈值、FAQ状态没有启用或者没有符合的答案，请重新设置阈值或修改问题')
        return BaseResponse(code=200, msg=f'查询成功,但是经过重拍模型后，查询结果皆小于重拍阈值，没有符合的答案，请重新设置阈值或修改问题',
                            data={"faq_result_list": faq_result_list,
                                  "database_documents": [],
                                  "documents_list": documents_list, "log_list": log_list})
    documents_list = await asyncio.to_thread(lambda: document_version(documents_list, server_config, qa_model.knowledge_base_name))
    documents_list = sorted_result(documents_list)
    logger.info(f"{uuid_test}------多路合并排序完成，共查询出{len(documents_list)}条数据")
    documents_result_list = await asyncio.to_thread(lambda: process_return_results(documents_list))

    # 针对有多版本的chunk进行es的扩召回，针对表格或者图片同样进行多版本处理
    multi_version_dict = await get_multi_version_dict(qa_model.knowledge_base_name, server_config)
    if multi_version_dict:
        multi_version_dict = {str(k): str(v) for k, v in multi_version_dict.items()}
        try:
            documents_result_list = await process_multi_version_documents(documents_result_list, query,
                                                                          multi_version_dict, qa_model, server_config,
                                                                          log_pk_dict)
        except Exception as e:
            logger.exception(f"多版本chunks召回出错: {e}")
    if log_pk_dict:
        log_list = list(log_pk_dict.values())
    # todo： 召回结果中 table_name/ text_parent_list 会出现nan 导致返回报错 需排查进一步原因
    for document in documents_result_list:
        for key, value in document["metadata"].items():
            if isinstance(value, float) and math.isnan(value) or key == 'revise_date' and pd.isna(value):
                document["metadata"][key] = None

    final_documents_list = documents_result_list[:qa_model.top_k]

    if 'adjacent_chunk_num' in server_config:
        qa_model.adjacent_chunk_num = server_config['adjacent_chunk_num']

    if qa_model.adjacent_chunk_num > 0:
        extend_documents_list = await adjacent_chunk_process(final_documents_list, qa_model.adjacent_chunk_num, qa_model.knowledge_base_name, server_config)
        final_documents_list += extend_documents_list

    for database_result in database_result_list:
        old_columns = database_result["metadata"]['columns']
        new_columns = json.dumps(json.loads(database_result["metadata"]['columns']), ensure_ascii=False)
        database_result["metadata"]['columns'] = new_columns
        database_result['page_content'] = database_result['page_content'].replace(old_columns, new_columns)
    logger.info(f"{uuid_test}------总时长：{time.time() - t111}")
    return BaseResponse(code=200, msg=f'查询成功',
                        data={"faq_result_list": faq_result_list,
                              "database_documents": database_result_list[:qa_model.top_k],
                              "documents_list": final_documents_list,
                              "web_documents_list": web_documents_result_list[:qa_model.top_k],
                              "log_list": log_list})
