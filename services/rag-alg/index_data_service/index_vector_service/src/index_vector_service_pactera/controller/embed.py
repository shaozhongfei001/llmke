#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: embed.py  
Time: 2025/12/11 10:08  
异步向量化相关函数
"""
import asyncio

import httpx

# 复用 httpx AsyncClient，避免每次请求重新建连
_shared_httpx_client: httpx.AsyncClient | None = None
_httpx_client_lock = asyncio.Lock()

from config.conf import DEFAULT_EMBEDDING_MAX_TOKENS, EMBED_MAX_TOKEN_DELTA_DEFAULT
from operators.common.log import logger
from operators.utils.token_utils import truncate_text_by_tokens


def split_array(arr, chunk_size):
    """将数组分割成指定大小的chunks"""
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]


async def xinference_embedding_request_async(model_name, page_content_list, server_config,
                                             client: httpx.AsyncClient = None):
    """
    异步版本的向量化请求函数
    Args:
        model_name: 模型名称
        page_content_list: 待向量化的文本列表
        server_config: 服务器配置
        client: httpx异步客户端，如果为None则创建临时客户端
    Returns:
        向量化结果列表
    """
    compatible_flag = server_config["compatible_flag"] if "compatible_flag" in server_config else False
    try:
        embed_url = server_config["online_embedding_model"][model_name]["server_url"]
        api_key = server_config["online_embedding_model"][model_name].get("key", "")
        model_id = server_config["online_embedding_model"][model_name].get("model_id", "")
    except Exception as e:
        logger.error(
            f"模型获取错误，nacos 没有配置该模型：{model_name},请检查，现在使用默认模型{server_config['embedding_model']}，错误：{e}")
        model_name = server_config["embedding_model"]
        model_id = server_config["online_embedding_model"][model_name].get("model_id", "")
        embed_url = server_config["online_embedding_model"][model_name]["server_url"]
        api_key = server_config["online_embedding_model"][model_name].get("key", "")

    # 获取模型的最大token限制，从配置文件读取
    max_tokens = server_config["online_embedding_model"].get(model_name, {}).get("max_tokens", DEFAULT_EMBEDDING_MAX_TOKENS)
    max_tokens_delta = server_config.get("embed_max_token_delta", EMBED_MAX_TOKEN_DELTA_DEFAULT)

    # 处理文本长度，确保不超过模型的最大token限制
    processed_content_list = []
    for content in page_content_list:
        truncated_content = truncate_text_by_tokens(content, max_tokens, max_tokens_delta)
        processed_content_list.append(truncated_content)

    embed_request = {
        "input": processed_content_list,
    }
    if not compatible_flag:
        embed_request["model"] = model_id

    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = api_key

    embed_result = await client.post(embed_url, json=embed_request, headers=headers)
    if embed_result.status_code == 200:
        result = embed_result.json()
        if not compatible_flag:
            return result.get("data", [])
        else:
            return result
    else:
        raise Exception(f'embed模型返回码: {embed_result.status_code}, result: {embed_result.text}, 请求 embed model_name: {model_name}, model_id: {model_id}, 模型 params: {embed_request}')


async def get_httpx_client(timeout: int, max_connections: int) -> httpx.AsyncClient:
    """
    获取共享的 httpx AsyncClient，减少连接建立开销
    """
    global _shared_httpx_client
    async with _httpx_client_lock:
        if _shared_httpx_client is None or _shared_httpx_client.is_closed:
            _shared_httpx_client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_connections=max_connections)
            )
        return _shared_httpx_client


async def split_embedding_data_async(data_list, model_name, server_config):
    """
    异步分批embed，支持并发调用多个embedding请求
    Args:
        data_list: 待向量化的文本列表
        model_name: 模型名称
        server_config: 服务器配置
    Returns:
        content_embed_dict: {text: embedding} 字典
    """
    compatible_flag = server_config["compatible_flag"] if "compatible_flag" in server_config else False
    content_embed_dict = {}

    if not data_list:
        raise Exception(f"待向量化的文本列表为空, data_list=[]")

    # 获取配置参数
    chunk_size = server_config.get("milvus_conn_config", {}).get("embed_chunk_size", 200)
    # 获取并发度配置，默认100
    embed_concurrency = server_config.get("milvus_conn_config", {}).get("embed_concurrency", 200)
    timeout = server_config.get("milvus_conn_config", {}).get("embed_timeout", 120)

    client = await get_httpx_client(timeout=timeout, max_connections=embed_concurrency * 2)

    if len(data_list) > 1:
        # 分批处理
        chunk_entity_list = split_array(data_list, chunk_size)

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(embed_concurrency)

        async def process_chunk(cel):
            """处理单个chunk的向量化"""
            async with semaphore:
                cel_len = len(cel)
                chunk_embed_data = await xinference_embedding_request_async(
                    model_name, cel, server_config, client
                )

                if not chunk_embed_data:
                    logger.warning(f"向量化返回空结果，chunk大小: {cel_len}")
                    return

                for i, ced in enumerate(chunk_embed_data):
                    if not compatible_flag:
                        if "index" in ced and ced["index"] < cel_len:
                            content_embed_dict[cel[ced["index"]]] = ced["embedding"]
                        else:
                            logger.error(f"Invalid index in embedding data: {ced}")
                    else:
                        if i < cel_len:
                            content_embed_dict[cel[i]] = ced
                        else:
                            logger.error(f"Index {i} out of range for chunk data")

        # 并发处理所有chunks
        tasks = [process_chunk(cel) for cel in chunk_entity_list]
        await asyncio.gather(*tasks)
    else:
        # 单条数据
        chunk_embed_data = await xinference_embedding_request_async(
            model_name, data_list, server_config, client
        )
        for i, ced in enumerate(chunk_embed_data):
            if not compatible_flag:
                if "index" in ced and ced["index"] < len(data_list):
                    content_embed_dict[data_list[ced["index"]]] = ced["embedding"]
                else:
                    logger.error(f"Invalid index in embedding data: {ced}")
            else:
                if i < len(data_list):
                    content_embed_dict[data_list[i]] = ced
                else:
                    logger.error(f"Index {i} out of range for data_list")
    if not content_embed_dict:
        raise Exception(f"向量模型返回向量结果为空")

    return content_embed_dict
