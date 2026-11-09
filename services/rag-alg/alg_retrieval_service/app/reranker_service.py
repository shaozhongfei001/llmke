#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 17:18
# @Author  : yuxj
# @File    : reranker_service.py
import asyncio
import os.path

from operators.client.reranker_client import RerankerClient

from operators.common.log import logger
from config.conf import DEFAULT_RERANK_MAX_TOKENS, RERANK_MAX_TOKEN_DELTA_DEFAULT
from operators.utils.token_utils import truncate_text_by_tokens
from operators.reranker.qwen3_reranker import Qwen3Reranker


def min_max_normalize(data):
    min_val = min(data)
    max_val = max(data)
    if min_val == max_val:
        return max_val
    data_res = [(x - min_val) / (max_val - min_val) for x in data]
    final_value = sum(data_res) / len(data_res)
    return final_value


def merge_and_get_rrf_score(question: str, documents, rrf_k=60, query_weight=1):
    """
    rrf + 数据合并去重

    HR-06：多路融合去重**按平台 pk**（k=60），禁止按 page_content 精确字符串去重。
    理由：ES/Milvus 的 pk 与图检索 source.pk 已统一为同一个整数 pk（阶段 1），
    按 page_content 去重会把「正文碰巧相同、但 pk 不同」的两个 chunk 错误合并，
    也会把「同一 chunk 在 ES 与图里正文有细微差异（如是否带标题）」拆成两条。

    pk 缺失时（异常数据）用进程内唯一占位，禁止把不同来源错误合并成一条。
    """
    for qus, doc_list in documents.items():
        pk2document = dict()
        for doc in doc_list:
            pk = doc.metadata.get("pk")
            search_params = doc.metadata.pop("search")

            # if question.strip().lower() == search_params["query"].strip().lower():
            #     qw = query_weight
            # else:
            #     qw = 1 - query_weight

            rrf_score = query_weight * (1 / (rrf_k + search_params["rank"][0]))
            key = pk if pk is not None else ("__no_pk__", id(doc))
            if key not in pk2document:
                doc.metadata["score"] = rrf_score
                doc.metadata["rrf_score"] = [rrf_score]
                doc.metadata["query_weight"] = query_weight
                doc.metadata["query"] = search_params["query"]
                doc.metadata["rank"] = search_params["rank"]
                doc.metadata["search_type"] = search_params["type"]
                pk2document[key] = doc
            else:
                pk2document[key].metadata["score"] += rrf_score
                pk2document[key].metadata["rrf_score"].append(rrf_score)
                pk2document[key].metadata["search_type"].extend(search_params["type"])
                pk2document[key].metadata["rank"].extend(search_params["rank"])
        c_documents = list(pk2document.values())
        results = sorted(c_documents, key=lambda x: x.metadata["score"], reverse=True)
        for rank, item in enumerate(results, start=1):
            item.metadata['rrf_score_rank'] = rank
            if item.metadata['rrf_score'] and len(item.metadata['rrf_score']) > 1:
                rrf_score = min_max_normalize(item.metadata['rrf_score'])
            else:
                rrf_score = item.metadata['rrf_score'][0]
            item.metadata['rrf_score'] = rrf_score
        documents[qus] = results
    return documents


async def get_reranker_score(query, document_list, server_config, rerank_model_info=None):
    """
    调用rerank函数，进行rerank计算
    Args:
        query:
        document_list:
        server_config:
        rerank_model_info:
    Notes： compatible_flag 该参数是兼容华为接口所用， 当启动时 则用mindia方式
    Returns:

    """
    async def rerank(q, doc_list):
        compatible_flag = server_config["compatible_flag"] if "compatible_flag" in server_config else False
        if rerank_model_info:
            model_name = rerank_model_info["model_name"]
            rerank_url = rerank_model_info["url"]
            api_key = rerank_model_info.get("key", "")
        else:
            model_name = server_config["rerank_model"]["model_name"]
            rerank_url = server_config["rerank_server"][model_name]["server_url"]
            api_key = rerank_model_info.get("key", "")

        # 获取模型的最大token限制，从配置文件读取
        max_tokens = server_config["rerank_server"].get(model_name, {}).get("max_tokens", DEFAULT_RERANK_MAX_TOKENS)

        # 检查是否为 Qwen3 模型
        is_qwen3_model = "qwen3" in model_name.lower()

        if is_qwen3_model:
            # 使用 Qwen3Reranker 处理
            qwen3_reranker = Qwen3Reranker()
            try:
                # 构建临时 server_config 用于 Qwen3Reranker
                temp_server_config = {
                    "rerank_model": {"model_name": model_name},
                    "rerank_server": {model_name: {"server_url": rerank_url, "api_key": api_key}}
                }
                score_list = await qwen3_reranker.get_scores(q, doc_list, temp_server_config)
                # 转换为标准格式
                results = []
                for i, score in enumerate(score_list):
                    results.append({"index": i, "score": score})
                return results
            except Exception as e:
                logger.error(f"Qwen3 rerank 处理失败: {e}")
                return []

        # 原有的处理逻辑
        # documents = [os.path.split(doc.metadata["source"])[-1] + "\n" + doc.page_content for doc in doc_list]
        documents = []
        for doc in doc_list:
            if "source" in doc.metadata and not str(doc.metadata.get('knowledge_base_name', "")).startswith("faq_"):
                doc_text = os.path.split(doc.metadata["source"])[-1] + "\n" + doc.page_content
            else:
                doc_text = doc.page_content
            max_token_delta = server_config.get("rerank_max_token_delta", RERANK_MAX_TOKEN_DELTA_DEFAULT)
            truncated_text = truncate_text_by_tokens(doc_text, max_tokens, max_token_delta)
            documents.append(truncated_text)

        rerank_request = {
            "query": q
        }
        if not compatible_flag:
            rerank_request["model"] = model_name
            rerank_request["documents"] = documents
        else:
            rerank_request["texts"] = documents
        
        try:
            rerank_result = await RerankerClient.request(
                rerank_url=rerank_url, 
                rerank_request=rerank_request,
                api_key=api_key
            )
        except Exception as e:
            logger.error(f"rerank模型请求异常：{e}")
            return []
        if not compatible_flag:
            score_list = rerank_result['results']
        else:
            score_list = rerank_result
        return score_list

    score_list = await rerank(query, document_list)
    if not score_list:
        score_list = []
        for dl in document_list:
            score_sub_list = await rerank(query, [dl])
            if not score_sub_list:
                break
            score_list.extend(score_sub_list)
    score_dict = {}
    for sl in score_list:
        key = "relevance_score" if "relevance_score" in sl else "score"
        score_dict[sl["index"]] = [sl[key]]
    for k, v in score_dict.items():
        document_list[k].metadata["score"] = max(v)
    return document_list


async def merge_and_rerank(documents, top_n, score_threshold, server_config, log_pk_dict, rerank_model_info=None, no_rerank_score=False):

    """
    拆分数据、rerank后数据筛选
    Args:
        documents:
        top_n:
        score_threshold:
        server_config:
        log_pk_dict:
        rerank_model_info:
        no_rerank_score:

    Returns:

    """

    def split_array(arr, chunk_size):
        return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

    ranked_documents_dict = {}
    for qus, doc_list in documents.items():
        # R14-C-FIX-18（B 定位）：任何来源留下的空键都不该让**整轮** rerank 失败。
        # 服务端对空列表直接 400 "documents must be a non-empty list"，而单批分支没有 try，
        # 异常会冒泡到调用方 → 所有 query 的 rerank 结果一起丢 → 上下文为空 → 模型自答。
        # 这里显式跳过空集合（保留该键、结果为空），把"一条坏数据"限制在它自己身上。
        if not doc_list:
            logger.warning(f"reranker: 跳过空文档集合 query={qus[:40]!r}，避免整轮 rerank 失败")
            continue
        new_ranked_documents = []
        # HR-07：rerank 只做精排。top_n 前先按 RRF score 粗排，只取 top_n×3 候选进入 rerank，
        # 避免对全量召回（尤其开图后三路叠加）做重排，既省算力又减少弱相关噪声进入精排。
        candidate_n = max(int(top_n) * 3, 1)
        if len(doc_list) > candidate_n:
            doc_list = sorted(doc_list, key=lambda d: (d.metadata.get("score") or 0), reverse=True)[:candidate_n]
        if len(doc_list) > server_config["rerank_batch_size"]:
            chunk_document_list = split_array(doc_list, server_config["rerank_batch_size"])
        else:
            chunk_document_list = [doc_list]
        ranked_documents = []
        if len(chunk_document_list) == 1:
            chunk_rerank_list = await get_reranker_score(qus, chunk_document_list[0], server_config, rerank_model_info=rerank_model_info)
            ranked_documents.extend(chunk_rerank_list)
        else:
            tasks = [get_reranker_score(qus, cdl, server_config, rerank_model_info=rerank_model_info) for cdl in chunk_document_list]
            try:
                results = await asyncio.gather(*tasks)
                if results:
                    for chunk_rerank_list in results:
                        ranked_documents.extend(chunk_rerank_list)
            except Exception as e:
                logger.error(f"rerank报错：{e}")
        # HR-07：阈值用**相对阈值**（top 候选最高分 ×0.3），不写死近似 0 的阈值放行弱相关结果。
        # 保留调用方 score_threshold 作为下限兜底：相对阈值低于它时仍以它为下限，避免阈值被
        # 高分候选拉得过高而误杀；但正常情况相对阈值会显著高于近似 0 的写死值。
        ranked_scores = [d.metadata.get("score") or 0 for d in ranked_documents]
        relative_threshold = (max(ranked_scores) * 0.3) if ranked_scores else 0.0
        effective_threshold = max(score_threshold, relative_threshold)
        for docu in ranked_documents:
            rerank_score = docu.metadata["score"] or 0
            if log_pk_dict:
                pk = docu.metadata["pk"]
                log_pk_dict[pk]["rerank_model"] = server_config["rerank_model"]["model_name"]
                log_pk_dict[pk]["rerank_filter_threshold"] = effective_threshold
                log_pk_dict[pk]["rerank_score"] = rerank_score
            if rerank_score >= effective_threshold or no_rerank_score:
                new_ranked_documents.append(docu)
        if new_ranked_documents:
            new_ranked_documents = sorted(new_ranked_documents, key=lambda x: x.metadata["score"], reverse=True)
            for rank, item in enumerate(new_ranked_documents, start=1):
                item.metadata['rerank_score_rank'] = rank
            ranked_documents_dict[qus] = new_ranked_documents[:top_n]
    return ranked_documents_dict, log_pk_dict
