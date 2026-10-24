#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: es.py
Time: 2025/12/16 15:23

ES 相关的异步控制逻辑：
- 异步批量插入文档
- 分批、并发控制
- 限流与重试
"""

import asyncio
import json
from datetime import datetime
from typing import List, Tuple, Set

from elasticsearch.helpers import async_bulk

from base import BaseResponse, InsertDataModel, CreateIndexModel, OperateDataModel
from controller.es_query import query_es_sql
from controller.query_type import QueryType
from es_kb_config import (
    ES_INDEX_MAPPING,
    ES_INDEX_MAPPING_SUMMARY,
    ES_INDEX_MAPPING_CHUNKS,
    ES_INDEX_MAPPING_DATABASE,
)
from operators.common.log import logger
from utils import return_nacos_model, create_uuid


def is_index_lower(index_name):
    """将大写索引名转小写"""
    if isinstance(index_name, list):
        index_name = [name.lower() for name in index_name]
    else:
        if any(name.isupper() for name in index_name):
            index_name = index_name.lower()
    return index_name


async def is_index_async(index_name) -> bool:
    es = return_nacos_model().es_client_async()
    return await es.indices.exists(index=index_name)


async def create_index_async(index_model: CreateIndexModel) -> BaseResponse:
    index_name = is_index_lower(index_model.index_name)
    if "table_summary_" in index_name:
        body = ES_INDEX_MAPPING_SUMMARY
    elif "table_chunks_" in index_name:
        body = ES_INDEX_MAPPING_CHUNKS
    elif "database_" in index_name:
        body = ES_INDEX_MAPPING_DATABASE
    else:
        body = index_model.mapping_body or ES_INDEX_MAPPING
    es = return_nacos_model().es_client_async()
    if not await is_index_async(index_name):
        try:
            await es.indices.create(index=index_name, body=body)
            logger.info(f'索引{index_name}创建成功')
            return BaseResponse(code=200, msg=f'索引{index_name}创建成功')
        except Exception as ex:
            logger.error(f'索引{index_name}创建失败,{ex}')
            return BaseResponse(code=500, msg=f'索引{index_name}创建失败,{ex}')
    else:
        logger.error(f'索引{index_name}已存在')
        return BaseResponse(code=500, msg=f'索引{index_name}已存在')


async def get_index_mapping_field_async(index_name) -> Tuple[List[str], List[str]]:
    """
    获取当前 index 的 mapping 字段，如果索引不存在则按配置自动创建。
    返回:
        s_field_names: mappings-properties 顶层字段
        m_field_names: metadata-properties 字段
    """
    s_field_names: List[str] = []
    m_field_names: List[str] = []
    index_name = is_index_lower(index_name)
    es = return_nacos_model().es_client_async()
    if not await is_index_async(index_name):
        index_model = CreateIndexModel(index_name=index_name)
        data = await create_index_async(index_model)
        if data.code == 500:
            raise ValueError(data.msg)
    mapping = await es.indices.get_mapping(index=index_name)
    if mapping and index_name in mapping:
        mapping_properties = mapping[index_name]['mappings']['properties']
        for field_name, field_mapping in mapping_properties.items():
            s_field_names.append(field_name)
            if field_name == 'metadata':
                for f, v in field_mapping['properties'].items():
                    m_field_names.append(f)
    return s_field_names, m_field_names


def build_actions(insert_model: InsertDataModel, s_field_names, index_name) -> Tuple[list, Set[str]]:
    """
    构造文档逻辑，生成 bulk action 列表和 source 去重集合。
    """
    data_list = []
    source_paths: Set[str] = set()

    def build_columns_data(columns):
        columns_page_content = ""
        for column in columns:
            sample_values = " ".join(column.get("sample_values"))
            columns_page_content = columns_page_content + f"""
                                字段中文名称:{column.get("business_name", "")}
                                字段:{column.get("physical_name", "")}
                                字段描述:{column.get("description", "")}
                                字段采样值:{sample_values}
                                字段类型:{column.get("data_type", "")}
                                """
        return columns_page_content

    def build_database_content():
        if len(insert_model.document_list) > 0:
            data_dict = insert_model.document_list[0]
            columns = build_columns_data(data_dict.get("columns", []))
            columns_json = json.dumps(data_dict)
            page_content = f"""
                    表中文名称:{data_dict.get("database_name", "")}
                    表名称:{data_dict.get("physical_name", "")}
                    表描述:{data_dict.get("database_description", "")}
                    表字段信息:{columns}
                    """
            return page_content, columns_json
        else:
            return None, None

    if insert_model.type == "database":
        if len(insert_model.document_list) > 0:
            doc_dict = insert_model.document_list[0]
            doc_keys = doc_dict.keys()
            ids = create_uuid()
            actions_dict = {
                '_index': index_name,
                "_id": ids,
                '_source': {"page_content": "", "metadata": {}}
            }
            page_content, columns_json = build_database_content()
            for sf in s_field_names:
                if sf == 'page_content':
                    actions_dict['_source'][sf] = page_content
                elif sf == 'metadata':
                    for f, v in doc_dict.items():
                        if f == "columns":
                            actions_dict['_source'][sf][f] = columns_json
                        else:
                            actions_dict['_source'][sf][f] = v
                else:
                    if sf in doc_keys:
                        actions_dict['_source'][sf] = doc_dict[sf]
            now = datetime.now()
            if "create_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["create_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            if "update_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["update_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            data_list.append(actions_dict)
    else:
        for doc_dict in insert_model.document_list:
            doc_keys = doc_dict.keys()
            if "pk" in doc_dict["metadata"].keys() and doc_dict["metadata"]["pk"]:
                ids = doc_dict["metadata"]["pk"]
            else:
                ids = create_uuid()
            actions_dict = {
                '_index': index_name,
                "_id": ids,
                '_source': {"page_content": "", "metadata": {}}
            }
            for sf in s_field_names:
                if sf == 'page_content':
                    actions_dict['_source'][sf] = doc_dict['page_content']
                elif sf == 'metadata':
                    for f, v in doc_dict['metadata'].items():
                        if f in ('order_num', "status"):
                            actions_dict['_source'][sf][f] = int(v)
                        else:
                            actions_dict['_source'][sf][f] = v
                else:
                    if sf in doc_keys:
                        actions_dict['_source'][sf] = doc_dict[sf]
            meta_q = doc_dict.get('metadata', {}).get('question')
            if meta_q:
                actions_dict['_source']['question'] = meta_q
            if "status" not in doc_dict['metadata'].keys():
                actions_dict['_source']['metadata']["status"] = 0
            if "pk" not in doc_dict['metadata'].keys():
                actions_dict['_source']['metadata']["pk"] = ids
            now = datetime.now()
            if "create_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["create_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            if "update_time" not in actions_dict['_source']['metadata'].keys():
                actions_dict['_source']['metadata']["update_time"] = now.strftime(
                    "%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
            source_path = actions_dict["_source"]["metadata"].get("source")
            if source_path:
                source_paths.add(source_path)
            data_list.append(actions_dict)
    return data_list, source_paths


async def delete_by_col_documents_async(operate_data: OperateDataModel) -> BaseResponse:
    """
    根据条件删除数据，供大批量写入前去重使用。
    """
    es = return_nacos_model().es_client_async()
    index_name = is_index_lower(operate_data.index_name)

    if not await is_index_async(index_name):
        logger.info(f'es索引{index_name}不存在，无需删除数据')
        return BaseResponse(code=200, msg=f'索引{index_name}不存在，无需删除数据')

    query_param_list = []
    try:
        if operate_data.col_name:
            query_param = query_es_sql(index_name, operate_data.col_name, operate_data.col_values, QueryType.METADATA)
            query_param_list.append(query_param)
        elif operate_data.condition_json:
            for con_dict in operate_data.condition_json:
                for col_name in con_dict:
                    col_values = con_dict[col_name]
                    query_param = query_es_sql(index_name, col_name, col_values, QueryType.METADATA)
                    query_param_list.append(query_param)
        else:
            return BaseResponse(code=500, msg=f'并没有传入删除条件，如果想删除该index，请调用删除index接口')
    except Exception as ex:
        logger.info(f'索引{index_name}构建查询条件失败,没有查到该条件下的数据,{ex}')
        return BaseResponse(code=500, msg=f'索引{index_name}构建查询条件失败, 没有查到该条件下的数据,{ex}')

    total_deleted = 0
    for query_param in query_param_list:
        delete_body = {'query': query_param}
        try:
            response = await es.delete_by_query(index=index_name, body=delete_body, refresh=True)
            deleted_count = response["deleted"]
            total_deleted += deleted_count
            logger.info(f'Deleted {deleted_count} documents.')
        except Exception as ex:
            logger.error(f'索引{index_name}删除失败,{ex}')
            return BaseResponse(code=500, msg=f'索引{index_name}删除失败,{ex}')

    if query_param_list:
        if total_deleted == 0:
            logger.info(f'索引{index_name}没有查到要删除的数据')
            return BaseResponse(code=200, msg=f'索引{index_name}没有查到要删除的数据',
                                data={"result_data": operate_data.col_values})
        else:
            return BaseResponse(code=200, msg=f'成功删除{total_deleted}条数据',
                                data={"result_data": operate_data.col_values})


async def _insert_batch_with_retry(
        es,
        batch,
        sem: asyncio.Semaphore,
        index_name: str,
        batch_no: int,
        max_retries: int,
) -> List[str]:
    attempt = 0
    last_err = None
    while attempt < max_retries:
        attempt += 1
        try:
            async with sem:
                success_count, errors = await async_bulk(
                    es, batch, refresh=False, raise_on_error=False
                )
            if errors:
                last_err = errors
                logger.error(f"{index_name} batch {batch_no} partial failure on attempt {attempt}: {errors}")
                await asyncio.sleep(0.2 * attempt)
                continue
            # 返回已插入的文档 id，便于上层失败时回滚
            return [str(action.get("_id")) for action in batch if action.get("_id")]
        except Exception as ex:
            last_err = ex
            logger.error(f"{index_name} batch {batch_no} failed on attempt {attempt}: {ex}")
            await asyncio.sleep(0.2 * attempt)
    raise RuntimeError(f"{index_name} batch {batch_no} failed after retries: {last_err}")


async def _rollback_documents_by_ids(es, index_name: str, doc_ids: List[str]) -> bool:
    """
    回滚已插入的文档，按 _id 批量删除。
    """
    if not doc_ids:
        return True

    actions = [
        {"_op_type": "delete", "_index": index_name, "_id": str(doc_id)}
        for doc_id in doc_ids
    ]
    try:
        _, errors = await async_bulk(es, actions, refresh=True, raise_on_error=False)
        if errors:
            logger.error(f"{index_name} rollback encountered errors: {errors}")
            return False
        return True
    except Exception as ex:
        logger.error(f"{index_name} rollback failed: {ex}")
        return False


async def add_documents_async(insert_model: InsertDataModel) -> BaseResponse:
    """
    批量添加数据（异步），带分批、并发与重试。
    """
    es_conn_config = return_nacos_model().get_config()["es_conn_config"]
    batch_size = es_conn_config.get("insert_batch_size", 500)
    max_concurrency = es_conn_config.get("insert_concurrency", 100)
    max_retries = es_conn_config.get("insert_max_retries", 3)

    es = return_nacos_model().es_client_async()
    index_name = is_index_lower(insert_model.index_name)
    try:
        s_field_names, _ = await get_index_mapping_field_async(index_name)
    except Exception as ex:
        logger.error(f'创建索引失败,{ex}')
        return BaseResponse(code=500, msg=f'创建索引失败,{ex}')
    if not s_field_names:
        logger.error(f'保存失败，没有获取对应的mapping字段，请检查index是否正确')
        return BaseResponse(code=500, msg=f'保存失败，没有获取对应的mapping字段，请检查index是否正确')

    data_list, source_paths = build_actions(insert_model, s_field_names, index_name)

    # 入库前按 source 去重
    if insert_model.type != "database":
        try:
            if "faq_" not in index_name and source_paths and insert_model.duplicate_flag:
                operate_data = OperateDataModel(index_name=index_name, col_name="source", col_values=list(source_paths))
                await delete_by_col_documents_async(operate_data)
        except Exception as ex:
            logger.error(f'{index_name}删除已入库文件失败,{ex}')
            return BaseResponse(code=500, msg=f'{index_name}删除已入库文件失败,{ex}')

    if not data_list:
        return BaseResponse(code=200, msg=f'{index_name}保存数据成功，共保存0条数据')

    batches = [data_list[i:i + batch_size] for i in range(0, len(data_list), batch_size)]
    semaphore = asyncio.Semaphore(max_concurrency)

    tasks = []
    for idx, batch in enumerate(batches):
        tasks.append(
            _insert_batch_with_retry(
                es,
                batch,
                semaphore,
                index_name,
                idx + 1,
                max_retries,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        # 收集本次任务中已提交的 _id，以及失败批次的 _id 以便幂等回滚
        success_ids: List[str] = []
        failed_batch_ids: List[str] = []
        for idx, res in enumerate(results):
            batch_ids = [str(action.get("_id")) for action in batches[idx] if action.get("_id")]
            if isinstance(res, Exception):
                failed_batch_ids.extend(batch_ids)
            else:
                success_ids.extend(res or [])

        rollback_ids = list({*success_ids, *failed_batch_ids})
        rollback_ok = await _rollback_documents_by_ids(es, index_name, rollback_ids)
        logger.error(
            f'{index_name}存在失败批次，errors={errors}; rollback_ids={len(rollback_ids)}, rollback_ok={rollback_ok}'
        )
        msg_suffix = "（已回滚）" if rollback_ok else "（回滚可能不完全，请检查日志）"
        return BaseResponse(code=500, msg=f'{index_name}部分批次保存失败{msg_suffix}')

    try:
        await es.indices.refresh(index=index_name)
    except Exception as ex:
        logger.warning(f'{index_name}刷新索引失败，但插入结果已提交: {ex}')

    total_saved = len(data_list)
    return BaseResponse(code=200, msg=f'{index_name}保存数据成功，共保存{total_saved}条数据')
