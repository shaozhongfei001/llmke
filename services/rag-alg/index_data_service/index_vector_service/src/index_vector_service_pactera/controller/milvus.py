#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: milvus.py  
Time: 2025/12/11 13:56  
异步Milvus客户端工具类
"""
import asyncio
from typing import Optional, List, Dict, Any

from pymilvus import AsyncMilvusClient
from operators.common.log import logger

# 全局异步客户端缓存
_async_client_cache = {}
_client_lock = asyncio.Lock()


async def get_async_milvus_client(milvus_config: dict, db_name: str) -> AsyncMilvusClient:
    """
    获取或创建异步Milvus客户端（带连接池）
    
    Args:
        milvus_config: Milvus连接配置
        db_name: 数据库名称
    
    Returns:
        AsyncMilvusClient实例
    """
    host = milvus_config["milvus_connect"]["host"]
    port = milvus_config["milvus_connect"]["port"]
    user = milvus_config["milvus_connect"].get("user")
    password = milvus_config["milvus_connect"].get("password")
    secure = milvus_config["milvus_connect"].get("secure", False)
    
    # 使用host:port:db_name作为缓存key
    cache_key = f"{host}:{port}:{db_name}"
    
    async with _client_lock:
        if cache_key not in _async_client_cache:
            uri = f"http://{host}:{port}"
            client = AsyncMilvusClient(
                uri=uri,
                user=user,
                password=password,
                secure=secure,
                db_name=db_name
            )
            _async_client_cache[cache_key] = client
            logger.info(f"创建异步Milvus客户端: {cache_key}")
        
        return _async_client_cache[cache_key]


def prepare_insert_data(data_dict_list: List[Dict[str, Any]], fields_order: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    准备插入数据，确保字段顺序正确
    
    Args:
        data_dict_list: 数据字典列表，每个字典包含字段名和值的映射
        fields_order: 字段顺序列表，如果提供则按此顺序排列字段
    
    Returns:
        准备好的数据字典列表
    """
    if not data_dict_list:
        return []
    
    # 如果没有提供字段顺序，直接返回原数据
    if fields_order is None:
        return data_dict_list
    
    # 按照字段顺序重新排列数据
    result = []
    for data_dict in data_dict_list:
        ordered_dict = {}
        # 先添加有序字段
        for field_name in fields_order:
            if field_name in data_dict:
                ordered_dict[field_name] = data_dict[field_name]
        # 添加其他字段
        for key, value in data_dict.items():
            if key not in ordered_dict:
                ordered_dict[key] = value
        result.append(ordered_dict)
    
    return result


async def batch_insert_async(
    collection_name: str,
    data_dict_list: List[List[Dict[str, Any]]],
    milvus_conn_config: dict,
    db_name: str,
    concurrency: int = 4,
    fields_order: Optional[List[str]] = None
) -> Any:
    """
    使用异步客户端批量插入Milvus
    
    Args:
        collection_name: 集合名称
        data_dict_list: 待插入的数据列表（已分批），每个元素是一个批次的数据字典列表
        milvus_conn_config: Milvus连接配置
        concurrency: 插入并发度
        fields_order: 字段顺序列表，如果为None则从第一条数据中获取
        db_name: 数据库名称
    
    Returns:
        最后一个插入操作的结果
    """
    if not data_dict_list:
        return None
    
    client = await get_async_milvus_client(milvus_conn_config, db_name)
    
    semaphore = asyncio.Semaphore(max(concurrency, 1))
    inserted_pks = []
    
    async def insert_chunk(data_chunk: List[Dict[str, Any]]):
        """插入单个批次的数据"""
        async with semaphore:
            try:
                insert_data = prepare_insert_data(data_chunk, fields_order)
                
                # 异步插入
                result = await client.insert(
                    collection_name=collection_name,
                    data=insert_data
                )
                
                # 提取主键
                if result and hasattr(result, "primary_keys"):
                    inserted_pks.extend(result.primary_keys or [])
                elif isinstance(result, dict) and "ids" in result:
                    inserted_pks.extend(result["ids"] or [])
                
                # logger.debug(f'异步插入Milvus数据成功，批次大小: {len(data_chunk)}')
                return result
            except Exception as e:
                logger.error(f'异步插入批次失败: {e}')
                raise
    
    tasks = [asyncio.create_task(insert_chunk(chunk)) for chunk in data_dict_list]
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有异常
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f'批次 {i} 插入失败: {result}')
                raise result
        
        # 异步加载集合
        try:
            await client.load_collection(collection_name=collection_name)
            # logger.debug(f'集合 {collection_name} 已加载')
        except Exception as e:
            # 如果已经加载或加载失败，记录警告但不影响插入结果
            logger.warning(f'milvus后台load失败（可能已加载）: {e}')
        
        return results[-1] if results else None
        
    except Exception as exc:
        logger.error(f'批量插入失败，开始回滚，{exc}')
        if inserted_pks:
            try:
                await rollback_inserted_rows_async(
                    client, collection_name, inserted_pks
                )
                logger.info(f'已回滚插入数据，数量: {len(inserted_pks)}')
            except Exception as rollback_err:
                logger.error(f'回滚失败，请手动清理，{rollback_err}')
        raise


async def rollback_inserted_rows_async(
    client: AsyncMilvusClient,
    collection_name: str,
    inserted_pks: List[Any]
):
    """
    异步回滚已插入的数据
    
    Args:
        client: 异步Milvus客户端
        collection_name: 集合名称
        inserted_pks: 要删除的主键列表
    """
    if not inserted_pks:
        return
    
    try:
        # 构建删除表达式
        pk_expr_values = []
        for pk in inserted_pks:
            if isinstance(pk, str):
                pk_expr_values.append(f'"{pk}"')
            else:
                pk_expr_values.append(str(pk))
        
        expr = f"pk in [{','.join(pk_expr_values)}]"
        
        # 异步删除
        await client.delete(
            collection_name=collection_name,
            filter=expr
        )
        
        # 刷新数据
        await client.flush(collection_name=collection_name)
        
        logger.info(f'回滚成功，删除 {len(inserted_pks)} 条数据')
    except Exception as e:
        logger.error(f'回滚删除失败: {e}')
        raise


async def check_collection_exists_async(
    collection_name: str,
    milvus_conn_config: dict,
    db_name: Optional[str] = None
) -> bool:
    """
    异步检查集合是否存在
    
    Args:
        collection_name: 集合名称
        milvus_conn_config: Milvus连接配置
        db_name: 数据库名称
    
    Returns:
        集合是否存在
    """
    try:
        client = await get_async_milvus_client(milvus_conn_config, db_name)
        collections = await client.list_collections()
        return collection_name in collections
    except Exception as e:
        logger.error(f'检查集合是否存在失败: {e}')
        return False


async def get_collection_schema_async(
    collection_name: str,
    milvus_conn_config: dict,
    db_name: Optional[str] = None
) -> Optional[Dict]:
    """
    异步获取集合的schema信息
    
    Args:
        collection_name: 集合名称
        milvus_conn_config: Milvus连接配置
        db_name: 数据库名称
    
    Returns:
        schema信息字典，包含fields等信息
    """
    try:
        client = await get_async_milvus_client(milvus_conn_config, db_name)
        schema = await client.describe_collection(collection_name=collection_name)
        return schema
    except Exception as e:
        logger.error(f'获取集合schema失败: {e}')
        return None
