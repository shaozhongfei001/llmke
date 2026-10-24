#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: migrate_collection.py  
Time: 2025/12/5 10:53  
"""
import asyncio
from typing import List, Dict, Any, Optional

from pymilvus import Collection

from base import BaseResponse, MigrateCollectionModel
from milvus_kb_service import get_collection, generate_collection_name_uuid, is_collection, split_array
from utils import return_nacos_model
from operators.common.log import logger


def build_filter_expr(filter_dict: Dict[str, Any]) -> str:
    """
    构建 Milvus 查询表达式
    
    Args:
        filter_dict: 筛选条件字典，例如 {"file_id": {"_in": ["f001", "f002"]}}
    
    Returns:
        查询表达式字符串
    """
    if not filter_dict:
        return ""
    
    conditions = []
    for field, condition in filter_dict.items():
        if isinstance(condition, dict):
            if "_in" in condition:
                # 处理 in 操作
                values = condition["_in"]
                if isinstance(values, list) and len(values) > 0:
                    # 根据值的类型构建表达式
                    if isinstance(values[0], str):
                        # 字符串类型需要加引号
                        value_list = [f'"{v}"' for v in values]
                    else:
                        value_list = [str(v) for v in values]
                    conditions.append(f"{field} in [{','.join(value_list)}]")
            elif "_eq" in condition:
                # 处理等于操作
                value = condition["_eq"]
                if isinstance(value, str):
                    conditions.append(f'{field} == "{value}"')
                else:
                    conditions.append(f'{field} == {value}')
            elif "_ne" in condition:
                # 处理不等于操作
                value = condition["_ne"]
                if isinstance(value, str):
                    conditions.append(f'{field} != "{value}"')
                else:
                    conditions.append(f'{field} != {value}')
        elif isinstance(condition, (list, tuple)):
            # 直接是列表，当作 in 操作
            if len(condition) > 0:
                if isinstance(condition[0], str):
                    value_list = [f'"{v}"' for v in condition]
                else:
                    value_list = [str(v) for v in condition]
                conditions.append(f"{field} in [{','.join(value_list)}]")
        else:
            # 直接是值，当作等于操作
            if isinstance(condition, str):
                conditions.append(f'{field} == "{condition}"')
            else:
                conditions.append(f'{field} == {condition}')
    
    return " and ".join(conditions) if conditions else ""


async def migrate_collection_data(migrate_param: MigrateCollectionModel) -> BaseResponse:
    """
    迁移 Milvus 集合数据
    
    Args:
        migrate_param: 迁移参数
    
    Returns:
        BaseResponse 对象
    """
    try:
        server_config = return_nacos_model().get_config()
        milvus_conn_config = server_config["milvus_conn_config"]
        db_name = migrate_param.db_name or milvus_conn_config.get("milvus_database", "rag_knowledge_base")
        
        # 处理集合名称（生成 UUID 格式）
        origin_collection_name = generate_collection_name_uuid(migrate_param.origin_collection)
        target_collection_name = generate_collection_name_uuid(migrate_param.target_collection)
        
        # 检查源集合是否存在
        if not is_collection(origin_collection_name, milvus_conn_config, db_name):
            logger.error(f"源集合 {origin_collection_name} 不存在")
            return BaseResponse(
                code=500,
                msg=f"源集合 {migrate_param.origin_collection} 不存在",
                data={"status": "failed", "migrated_vectors": 0}
            )
        
        # 检查目标集合是否存在
        if not is_collection(target_collection_name, milvus_conn_config, db_name):
            logger.error(f"目标集合 {target_collection_name} 不存在")
            return BaseResponse(
                code=500,
                msg=f"目标集合 {migrate_param.target_collection} 不存在",
                data={"status": "failed", "migrated_vectors": 0}
            )
        
        # 获取集合对象
        origin_coll = get_collection(origin_collection_name, milvus_conn_config, db_name)
        target_coll = get_collection(target_collection_name, milvus_conn_config, db_name)
        
        # 构建查询表达式
        filter_expr = build_filter_expr(migrate_param.filter)
        logger.info(f"迁移查询表达式: {filter_expr}")
        
        # 获取所有需要迁移的数据的 pk（用于回滚）
        all_migrated_pks = []
        total_migrated = 0
        batch_size = max(migrate_param.batch_size, 1)  # 确保批次大小至少为1
        
        try:
            # 分批查询和插入
            offset = 0
            query_batch_size = min(batch_size, 1000)  # 查询批次大小，避免一次查询太多
            
            while True:
                # 查询一批数据
                query_results = await asyncio.to_thread(
                    lambda: origin_coll.query(
                        expr=filter_expr if filter_expr else "",
                        offset=offset,
                        limit=query_batch_size,
                        output_fields=["*"]
                    )
                )
                
                if not query_results:
                    break
                
                # 准备插入数据（排除 pk 字段，如果目标集合是 auto_id）
                insert_data = []
                batch_pks = []
                
                # 检查目标集合的 schema，判断是否需要 pk（只检查一次）
                target_schema = target_coll.schema
                pk_field = None
                is_auto_id = False
                for field in target_schema.fields:
                    if field.is_primary:
                        pk_field = field
                        is_auto_id = field.auto_id
                        break
                
                for entity in query_results:
                    # 复制实体数据
                    entity_copy = entity.copy()
                    pk_value = entity_copy.get("pk")
                    
                    # 如果目标集合的 pk 是 auto_id，则移除 pk
                    if is_auto_id:
                        entity_copy.pop("pk", None)
                    
                    insert_data.append(entity_copy)
                    # 记录原始 pk，用于回滚（即使目标集合是 auto_id，我们也需要记录新生成的 pk）
                    if pk_value is not None and not is_auto_id:
                        batch_pks.append(pk_value)
                
                if not insert_data:
                    break
                
                # 分批插入（进一步拆分，避免单次插入过多）
                insert_batches = split_array(insert_data, batch_size)
                
                # 如果目标集合不是 auto_id，也需要相应地拆分 batch_pks
                batch_pks_batches = []
                if not is_auto_id and batch_pks:
                    batch_pks_batches = split_array(batch_pks, batch_size)
                
                for batch_idx, insert_batch in enumerate(insert_batches):
                    try:
                        # 插入数据
                        insert_result = await asyncio.to_thread(target_coll.insert, insert_batch)
                        
                        # 获取插入的 pk（用于回滚）
                        inserted_pks = []
                        if hasattr(insert_result, "primary_keys") and insert_result.primary_keys:
                            # 优先使用插入返回的 pk（适用于 auto_id 和非 auto_id）
                            inserted_pks = insert_result.primary_keys
                        elif not is_auto_id and batch_idx < len(batch_pks_batches):
                            # 如果目标集合不是 auto_id 且没有返回 pk，使用我们记录的原始 pk
                            inserted_pks = batch_pks_batches[batch_idx]
                        
                        # 只有当有有效的 pk 时才记录（用于回滚）
                        if inserted_pks:
                            all_migrated_pks.extend(inserted_pks)
                        
                        total_migrated += len(insert_batch)
                        
                        logger.info(f"成功迁移 {len(insert_batch)} 条数据，累计 {total_migrated} 条")
                        
                    except Exception as e:
                        logger.error(f"插入数据失败: {e}")
                        # 回滚已插入的数据
                        if all_migrated_pks:
                            await rollback_migrated_data(target_coll, all_migrated_pks)
                        return BaseResponse(
                            code=500,
                            msg=f"迁移失败: {e}",
                            data={"status": "failed", "migrated_vectors": total_migrated}
                        )
                
                offset += len(query_results)
                
                # 如果查询结果少于批次大小，说明已经查询完所有数据
                if len(query_results) < query_batch_size:
                    break
            
            # 刷新目标集合，确保数据持久化
            await asyncio.to_thread(target_coll.flush)
            await asyncio.to_thread(target_coll.load)
            
            logger.info(f"迁移完成，共迁移 {total_migrated} 条数据")
            
            return BaseResponse(
                code=200,
                msg="迁移完成",
                data={"status": "success", "migrated_vectors": total_migrated}
            )
            
        except Exception as e:
            logger.error(f"迁移过程中发生错误: {e}")
            # 回滚已插入的数据
            if all_migrated_pks:
                await rollback_migrated_data(target_coll, all_migrated_pks)
            
            return BaseResponse(
                code=500,
                msg=f"迁移失败: {e}",
                data={"status": "failed", "migrated_vectors": total_migrated}
            )
            
    except Exception as e:
        logger.error(f"迁移集合数据失败: {e}")
        return BaseResponse(
            code=500,
            msg=f"迁移失败: {e}",
            data={"status": "failed", "migrated_vectors": 0}
        )


async def rollback_migrated_data(coll: Collection, pks: List[Any]):
    """
    回滚已迁移的数据（分批删除，避免表达式过长）
    
    Args:
        coll: 目标集合对象
        pks: 需要删除的主键列表
    """
    if not pks:
        return
    
    try:
        # 分批删除，每批最多 1000 个 pk
        rollback_batch_size = 1000
        pk_batches = split_array(pks, rollback_batch_size)
        
        total_rolled_back = 0
        for pk_batch in pk_batches:
            try:
                # 构建删除表达式
                pk_expr_values = []
                for pk in pk_batch:
                    if isinstance(pk, str):
                        pk_expr_values.append(f'"{pk}"')
                    else:
                        pk_expr_values.append(str(pk))
                
                if pk_expr_values:
                    expr = f"pk in [{','.join(pk_expr_values)}]"
                    await asyncio.to_thread(coll.delete, expr)
                    total_rolled_back += len(pk_batch)
            except Exception as e:
                logger.error(f"回滚批次数据失败: {e}")
                # 继续尝试下一批
        
        # 刷新集合
        if total_rolled_back > 0:
            await asyncio.to_thread(coll.flush)
            logger.info(f"已回滚 {total_rolled_back} 条数据")
    except Exception as e:
        logger.error(f"回滚数据失败: {e}")
