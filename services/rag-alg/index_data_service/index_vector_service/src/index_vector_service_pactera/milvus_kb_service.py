#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/30 15:14
# @Author  : yuxj
# @File    : milvus_kb_service.py
import asyncio
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime

import requests
from google._upb._message import RepeatedScalarContainer
from pymilvus import (
    utility, db,
    FieldSchema, CollectionSchema, DataType,
    Collection, )
from pymilvus.client.types import LoadState

from base import BaseResponse, DatabaseConfigModel, InsertDataModel, QueryDataModel, DataBaseModel, DataParamModel, \
    UpdateParamModel, UpdateColModel, \
    UpdateBatchModel
from config.conf import DEFAULT_EMBEDDING_MAX_TOKENS, EMBED_MAX_TOKEN_DELTA_DEFAULT
from controller.embed import split_embedding_data_async
from controller.embed_change import embed_change_ctrl
from controller.milvus import batch_insert_async, check_collection_exists_async
from milvus_kb_config import MILVUS_FIELDS
from operators.common.log import logger
from operators.utils.token_utils import truncate_text_by_tokens
from utils import return_nacos_model, create_uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# server_config = return_nacos_config()
# milvus_config = server_config["milvus_conn_config"]
# embedding_model = server_config["embedding_model"]
# milvus_connect = {"host": milvus_config["milvus_connect"]["host"],
#                   "port": milvus_config["milvus_connect"]["port"],
#                   "user": milvus_config["milvus_connect"]["user"],
#                   "password": milvus_config["milvus_connect"]["password"],
#                   "secure": milvus_config["milvus_connect"]["secure"]}

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]


def get_insert_control_config(milvus_conn_config: dict):
    """
    获取插入批次大小与并发度配置
    """
    batch_size = milvus_conn_config.get("insert_batch_size", 500)
    concurrency = milvus_conn_config.get("insert_concurrency", 100)
    try:
        batch_size = int(batch_size)
    except (TypeError, ValueError):
        batch_size = 300
    try:
        concurrency = int(concurrency)
    except (TypeError, ValueError):
        concurrency = 4
    return max(batch_size, 1), max(concurrency, 1)


def split_embedding_data(data_list, model_name, server_config):
    """
    分批embed
    Args:
        data_list:
        model_name:
        server_config:

    Returns:

    """
    compatible_flag = server_config["compatible_flag"] if "compatible_flag" in server_config else False
    content_embed_dict = {}
    # logger.info(f"待向量化的数据集数量：{len(data_list)}条")
    if len(data_list) > 1:
        chunk_size = server_config.get("milvus_conn_config", {}).get("embed_chunk_size", 10)
        chunk_entity_list = split_array(data_list, chunk_size)
        for cel in chunk_entity_list:
            cel_len = len(cel)
            chunk_embed_data = xinference_embedding_request(model_name, cel, server_config)
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
            # logger.info(f"已经完成{cel_len}条数据的向量化")
    else:
        embed_data = xinference_embedding_request(model_name, data_list, server_config)
        for i, ced in enumerate(embed_data):
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
    # logger.info(f"已经完成数据的向量化,{len(data_list)}")
    return content_embed_dict


def xinference_embedding_request(model_name, page_content_list, server_config):
    compatible_flag = server_config["compatible_flag"] if "compatible_flag" in server_config else False
    try:
        embed_url = server_config["online_embedding_model"][model_name]["server_url"]
        api_key = server_config["online_embedding_model"][model_name].get("key", "")
        model_id = server_config["online_embedding_model"][model_name].get("model_id", "")
    except Exception as e:
        logger.error(f"模型获取错误，nacos 没有配置该模型：{model_name},请检查，现在使用默认模型{server_config['embedding_model']}，错误：{e}")
        model_name = server_config["embedding_model"]
        embed_url = server_config["online_embedding_model"][model_name]["server_url"]
        api_key = server_config["online_embedding_model"][model_name].get("key", "")
        model_id = server_config["online_embedding_model"][model_name].get("model_id", "")

    # 获取模型的最大token限制，从配置文件读取
    max_tokens = server_config["online_embedding_model"].get(model_name, {}).get("max_tokens", DEFAULT_EMBEDDING_MAX_TOKENS)
    max_token_delta = server_config.get("embed_max_token_delta", EMBED_MAX_TOKEN_DELTA_DEFAULT)

    # 处理文本长度，确保不超过模型的最大token限制
    processed_content_list = []
    for content in page_content_list:
        truncated_content = truncate_text_by_tokens(content, max_tokens, max_token_delta)
        processed_content_list.append(truncated_content)

    embed_request = {
        "input": processed_content_list,
    }
    if not compatible_flag:
        embed_request["model"] = model_id

    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = api_key

    embed_result = requests.post(embed_url, json=embed_request, headers=headers)
    if embed_result.status_code == 200:
        if not compatible_flag:
            return embed_result.json()["data"]
        else:
            return embed_result.json()
    else:
        logger.error(f'embed参数{embed_request}')
        logger.error(embed_result.text)
    return []


def generate_collection_name_uuid(collection_name: str) -> str:
    """
    如果collection_name为带有汉字字符，需将汉字转成非汉字字符

    Args:
        collection_name (str): 集合名称。
    Returns:
        转换后的collection_name。
    """
    chinese_regex = re.compile(r'[\u4e00-\u9fff]+')

    # 搜索字符串中是否包含汉字
    match = chinese_regex.search(collection_name)
    if match:
        collection_name = str(uuid.uuid5(uuid.NAMESPACE_DNS, collection_name))
    elif re.search(r'[^a-zA-Z0-9_]', collection_name):
        collection_name = str(uuid.uuid5(uuid.NAMESPACE_DNS, collection_name))
    collection_name = "_" + collection_name.replace("-", "_")
    return collection_name


COMMUNITY_COLLECTION_PREFIX = "community_summary_"
DEL_VISIBLE_TIMEOUT = 6.0


def derive_doc_id(*parts) -> int:
    """R14-A：与 index_fulltext_service 同一算法的确定性主键（63 位正整数）。

    两侧必须同源同实现，改这里必须同步 es.py 的 derive_doc_id，否则 ES `_id` 与 Milvus `pk` 会漂移。
    """
    seed = "|".join("" if p is None else str(p) for p in parts)
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15], 16)


def community_doc_id(collection_name, metadata) -> int:
    """R14-A：社区摘要主键 = f(kb, level, community_id)，与 ES 侧 community_doc_id 一致。"""
    metadata = metadata or {}
    return derive_doc_id("community", collection_name, metadata.get("level"),
                         metadata.get("community_id"))


def _visible_count(coll, expr: str):
    """返回当前对查询可见的行数；异常返回 None（调用方按 fail-closed 处理）。"""
    try:
        return len(coll.query(expr=expr, output_fields=["pk"], limit=16384))
    except Exception as e:  # noqa: BLE001
        logger.error(f'统计可见行失败 expr={expr}: {e}')
        return None


def _source_expr(sources):
    return "source in [" + ",".join(json.dumps(str(s), ensure_ascii=False) for s in sources) + "]"


def _wait_until_deleted(coll, expr: str, expected: int = 0, timeout: float = DEL_VISIBLE_TIMEOUT):
    """Milvus 删除是最终一致的：删除后必须确认旧行对查询不可见，否则重复事件会把数据写成两代。

    返回 (ok, 最后可见行数)。ok=False 表示等满 timeout 仍有可见旧行 —— 调用方必须中止写入。
    """
    waited = 0.0
    n = _visible_count(coll, expr)
    while n is None or n > expected:
        if waited >= timeout:
            return False, n
        time.sleep(0.3)
        waited += 0.3
        n = _visible_count(coll, expr)
    return True, n


def check_field_type(data_dict, fields_type_dict):
    for field, value in data_dict.items():
        if field in fields_type_dict:
            if field == "pk" or field == "vector" or field == "text":
                continue
            if fields_type_dict[field] == 5:
                if not isinstance(value, int):
                    raise ValueError(f"该字段：'{field}' 的值是：'{value}',不符合schema中的int类型，请检查解析服务中的数据类型")
            elif fields_type_dict[field] == 22:
                if not isinstance(value, list):
                    raise ValueError(f"该字段：'{field}' 的值是：'{value}',不符合schema中的list类型，请检查解析服务中的数据类型")
            elif fields_type_dict[field] == 21:
                if not isinstance(value, str):
                    raise ValueError(f"该字段：'{field}' 的值是：'{value}',不符合schema中的str类型，请检查解析服务中的数据类型")


def get_collection(collection_name: str, server_config, db_name: str = None):
    """
    获取在指定数据库下的集合。

    Args:
        db_name (str): 数据库别名。
        collection_name (str): 集合名称。
        server_config (dict):配置
    Returns:
        集合对象。
    """
    db_name = db_name or server_config["milvus_database"]
    coll = Collection(collection_name, using=db_name)
    indexes = utility.list_indexes(collection_name, using=db_name)
    if not indexes:
        dc = DatabaseConfigModel(db_name=db_name, collection_name=collection_name)
        do_create_index(dc, is_process=False)
    load_state = utility.load_state(collection_name, using=db_name)
    if load_state != LoadState.Loaded:
        coll.load()
    return coll


# def _load_milvus(collection_name: str, model_name: str = None,
#                  search_config=server_config["milvus_kwargs"]["search_params"]):
#     """
#     使用langchain提供的加载集合。
#
#     Args:
#         model_name (str): embedding模型名称。
#         collection_name (str): 集合名称。
#     Returns:
#         对象。
#     """
#     milvus = Milvus(embedding_function=load_local_embeddings(model_name or embedding_model),
#                     collection_name=collection_name,
#                     connection_args=milvus_connect,
#                     index_params=server_config["milvus_kwargs"]['index_params'],
#                     search_params=search_config
#                     )
#     return milvus


def do_create_database(database: DataBaseModel) -> BaseResponse:
    """
    创建milvus数据库。

    Args:
       database (DataBaseModel): 数据库名称。
    Returns:
       BaseResponse对象。
    """
    server_config = return_nacos_model().get_config()["milvus_conn_config"]
    db_name = database.db_name or server_config["milvus_database"]
    try:
        db.create_database(db_name, using=server_config["milvus_database"])
    except Exception as e:
        logger.error(f'创建{db_name}失败:{e}')
        return BaseResponse(code=500, msg=f'创建失败:{e}')
    logger.info(f'数据库{db_name}创建成功')
    return BaseResponse(code=200, msg=f'数据库{db_name}创建成功', data=db_name)


def do_create_collection(milvus_config_model: DatabaseConfigModel) -> BaseResponse:
    """
    创建milvus集合。

    Args:
       milvus_config_model (DatabaseConfigModel): milvus数据对象。
    Returns:
       BaseResponse对象。
    Notes：
        可在MILVUS_FIELDS中配置milvus中的列属性，通过自定义的方式创建集合，如果dtype缺少可自行添加
    """
    fields = []
    server_config = return_nacos_model().get_config()["milvus_conn_config"]
    if milvus_config_model.vector_mapping_body is None:
        vector_dim = embed_change_ctrl.resolve_vector_dim(nacos_config=return_nacos_model().get_config(), model_name=milvus_config_model.model_name)
        vector_mapping_body = embed_change_ctrl.resolve_vector_mapping(milvus_config_model.collection_name, vector_dim)
    else:
        vector_mapping_body = milvus_config_model.vector_mapping_body
    for field_name, params in vector_mapping_body.items():
        field = ""
        if params["dtype"] == 'DataType.INT64':
            field = FieldSchema(name=field_name, dtype=DataType.INT64, is_primary=params.get('is_primary', False),
                                auto_id=params.get("auto_id", False))
        elif params["dtype"] == 'DataType.VARCHAR':
            field = FieldSchema(name=field_name, dtype=DataType.VARCHAR, max_length=params['max_length'])
        elif field_name == milvus_config_model.vector_field_name:
            field = FieldSchema(name=field_name, dtype=DataType.FLOAT_VECTOR, dim=params['dim'])
        elif params['dtype'] == 'DataType.FLOAT_VECTOR':
            field = FieldSchema(name=field_name, dtype=DataType.FLOAT_VECTOR, dim=params['dim'])
        elif params['dtype'] == 'DataType.INT8':
            field = FieldSchema(name=field_name, dtype=DataType.INT8)
        elif params['dtype'] == 'DataType.DOUBLE':
            field = FieldSchema(name=field_name, dtype=DataType.DOUBLE)
        elif params['dtype'] == 'DataType.ARRAY':
            if params['element_type'] == "DataType.VARCHAR":
                field = FieldSchema(name=field_name, dtype=DataType.ARRAY, element_type=DataType.VARCHAR, max_capacity=params['max_capacity'],
                                    max_length=params['max_length'])
            elif params['element_type'] == "DataType.INT64":
                field = FieldSchema(name=field_name, dtype=DataType.ARRAY, element_type=DataType.INT64, max_capacity=params['max_capacity'],
                                    max_length=params['max_length'])
            elif params['element_type'] == "DataType.DOUBLE":
                field = FieldSchema(name=field_name, dtype=DataType.ARRAY, element_type=DataType.DOUBLE, max_capacity=params['max_capacity'],
                                    max_length=params['max_length'])
        elif params['dtype'] == 'DataType.BOOL':
            field = FieldSchema(name=field_name, dtype=DataType.BOOL)
        else:
            logger.error(f'Unsupported dtype: {params["dtype"]}')
            raise ValueError(f'Unsupported dtype: {params["dtype"]}')
        if field:
            fields.append(field)
    db_name = milvus_config_model.db_name or server_config["milvus_database"]
    schema = CollectionSchema(fields, description=f'集合名称：{milvus_config_model.collection_name}')
    collection_name = generate_collection_name_uuid(milvus_config_model.collection_name)
    docs_data = Collection(collection_name, schema, using=db_name)
    logger.info(f'集合:{milvus_config_model.collection_name}创建成功')
    return BaseResponse(code=200, msg=f'集合:{milvus_config_model.collection_name}创建成功', data={'result_data': str(docs_data)})


def do_create_index(milvus_config_model: DatabaseConfigModel, is_process=True) -> BaseResponse:
    """
    创建集合的索引。

    Args:
       milvus_config_model (DatabaseConfigModel): milvus数据对象。
       is_process: 是否处理集合名称
    Returns:
       BaseResponse对象。
    Notes：
        默认向量列：vector
    """
    server_config = return_nacos_model().get_config()["milvus_conn_config"]
    if is_process:
        collection_name = generate_collection_name_uuid(milvus_config_model.collection_name)
    else:
        collection_name = milvus_config_model.collection_name
    collection = Collection(collection_name, using=milvus_config_model.db_name)
    # 为默认向量列创建索引；当集合名包含 faq_ 前缀且开关开启时，额外创建 question_vector 索引
    try:
        collection.create_index(field_name=milvus_config_model.vector_field_name,
                                index_params=server_config["milvus_kwargs"]['index_params'])
        # 仅当原始集合名包含 faq_ 前缀且开关开启时创建 question_vector 索引
        enable_question_vector = server_config.get("enable_question_vector", False)
        if "faq_" in milvus_config_model.collection_name.lower() and enable_question_vector:
            has_question_vector = any(
                f.name == "question_vector" and f.dtype == DataType.FLOAT_VECTOR for f in collection.schema.fields
            )
            if has_question_vector:
                collection.create_index(field_name="question_vector",
                                        index_params=server_config["milvus_kwargs"]['index_params'])
    except Exception as e:
        logger.error(f"创建索引失败: {e}")
    try:
        collection.load()
        collection.flush()
    except Exception as e:
        logger.error(f"创建index 刷新和加载报错，{e}")
    return BaseResponse(code=200, msg=f'集合:{milvus_config_model.collection_name}的索引创建成功')


async def add_doc_custom(insert_model: InsertDataModel) -> BaseResponse:
    """
    添加数据。

    Args:
       insert_model (InsertDataModel): 数据保存对象。
    Returns:
       BaseResponse对象。
    Notes：
        通过自定义的方式添加数据， 该方法不会自动创建集合和索引，在方法中可自定义逻辑方法后添加数据
        该方法需提前创建好集合和索引。
    """
    coll_name_low = insert_model.collection_name.lower()
    server_config = return_nacos_model().get_config()
    milvus_conn_config = server_config["milvus_conn_config"]
    # todo embed模型还在使用nacos配置，需要修改
    if insert_model.embedding_model_info:
        model_name = insert_model.embedding_model_info.model_name
    else:
        model_name = insert_model.model_name or server_config["embedding_model"]

    collection_name = generate_collection_name_uuid(insert_model.collection_name)

    # 检查集合是否存在
    collection_exists = await check_collection_exists_async(collection_name, milvus_conn_config, insert_model.db_name)
    if not collection_exists:
        vector_dim = embed_change_ctrl.resolve_vector_dim(insert_model.embedding_model_info, server_config, model_name)
        vector_mapping_body = embed_change_ctrl.resolve_vector_mapping(insert_model.collection_name, vector_dim)
        dc = DatabaseConfigModel(db_name=insert_model.db_name, collection_name=insert_model.collection_name,
                                 vector_mapping_body=vector_mapping_body)
        s34 = time.time()
        await asyncio.to_thread(do_create_collection, dc)
        await asyncio.to_thread(do_create_index, dc)
        logger.info(f"创建集合完成, 用时:{time.time() - s34}s")
    try:
        coll = await asyncio.to_thread(get_collection, collection_name, milvus_conn_config, insert_model.db_name)
    except Exception as e:
        logger.error(f'保存数据失败,链接milvus失败，{e}')
        return BaseResponse(code=500, msg=f'保存数据失败，{e}')
    # 检查数据是否已加载
    fields = coll.schema.fields
    fields_type_dict = {f.name: f.dtype for f in fields if not f.name == "pk" or f.auto_id is False}
    # 构建ARRAY字段的element_type映射 (22 = DataType.ARRAY)
    fields_element_type_dict = {}
    for f in fields:
        # 兼容数值和枚举两种比较方式
        if (f.dtype == DataType.ARRAY or f.dtype == 22) and hasattr(f, 'element_type'):
            element_type = f.element_type
            # 将element_type转换为数值以便比较 (DataType.INT64=5, DataType.VARCHAR=21)
            if element_type == DataType.INT64 or element_type == 5:
                fields_element_type_dict[f.name] = 5  # INT64
            elif element_type == DataType.VARCHAR or element_type == 21:
                fields_element_type_dict[f.name] = 21  # VARCHAR
    i_name = [f.name for f in fields if not f.name == "pk" or f.auto_id is False]
    # 获取字段顺序
    fields_order = [f.name for f in fields if not (f.name == "pk" and f.auto_id)]
    add_sources = set()
    # R14-A：社区摘要集合（community_summary_<kb>）走"整代替换 + 确定性主键"，与 ES 侧一致
    is_community_collection = coll_name_low.startswith(COMMUNITY_COLLECTION_PREFIX)
    data_dict_list = []
    text_list = [tt["page_content"] for tt in insert_model.document_list]
    
    # 当为 FAQ 集合时，根据nacos配置决定是否对 question 字段做向量化
    # 从nacos配置中读取question_vector开关，默认为False
    enable_question_vector = server_config.get("milvus_conn_config", {}).get("enable_question_vector", False)
    is_faq_collection = coll_name_low.startswith("faq_")
    
    question_list = []
    question_text_map = {}  # 用于快速查找question对应的text
    if is_faq_collection and enable_question_vector:
        for tt in insert_model.document_list:
            # question 可能在 metadata.question 或 page_content 的前半段（question@@answer）
            q_text = tt.get("metadata", {}).get("question")
            if not q_text and isinstance(tt.get("page_content"), str) and "@@" in tt["page_content"]:
                q_text = tt["page_content"].split("@@", 1)[0]
            if q_text:
                question_list.append(q_text)
                question_text_map[tt["page_content"]] = q_text

    try:
        # 并发执行content和question的向量化
        if is_faq_collection and enable_question_vector and question_list:
            # 并行执行两个向量化任务
            content_task = split_embedding_data_async(text_list, model_name, server_config)
            question_task = split_embedding_data_async(question_list, model_name, server_config)
            content_embed_dict, question_embed_dict = await asyncio.gather(content_task, question_task)

            if not content_embed_dict:
                logger.error(f'保存数据失败，content embed请求失败，请检查配置后重试')
                return BaseResponse(code=500, msg=f'保存数据失败，embed请求失败，请检查配置后重试')
            if not question_embed_dict:
                logger.error(f'保存数据失败，question_vector embed请求失败，请检查配置后重试')
                return BaseResponse(code=500, msg=f'保存数据失败，question_vector embed请求失败，请检查配置后重试')
        else:
            # 非FAQ集合或未启用question_vector，只向量化content
            content_embed_dict = await split_embedding_data_async(text_list, model_name, server_config)
            question_embed_dict = {}

    except Exception as e:
        logger.error(f'保存数据失败，embed请求失败，请检查配置后重试: {e}')
        return BaseResponse(code=500, msg=f'保存数据失败，embed请求失败，请检查配置后重试')

    dict_sizes = []  # 判断文件大小
    for doc in insert_model.document_list:
        data_dict = {}
        for field in i_name:
            if fields_type_dict[field] == 22:
                data_dict.setdefault(field, [])
            elif fields_type_dict[field] == 5 and field != 'pk':
                data_dict.setdefault(field, -1)
            else:
                data_dict.setdefault(field, "")
        text = doc["page_content"]
        vector = content_embed_dict.get(text)
        if not vector:
            continue
        data_dict["text"] = text
        data_dict["vector"] = vector

        # 写入 question_vector（如果已向量化）
        if is_faq_collection and enable_question_vector and question_embed_dict:
            q_text = question_text_map.get(text)
            if q_text and q_text in question_embed_dict:
                data_dict["question_vector"] = question_embed_dict[q_text]

        for k, v in doc["metadata"].items():
            if k not in i_name:
                continue
            # 当 pic_offset_list 字段为 None 时，自动转换为空列表
            if k == "pic_offset_list" and v is None:
                v = []
            if k in ("pk", "status", "faq_type", "chunk_index"):
                data_dict[k] = int(v)
            else:
                # 处理ARRAY类型字段 (22 = DataType.ARRAY)
                field_dtype = fields_type_dict.get(k)
                if field_dtype == DataType.ARRAY or field_dtype == 22:
                    # 如果值是字符串，尝试解析为JSON
                    if isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except (json.JSONDecodeError, TypeError) as e:
                            raise ValueError(f"字段 '{k}' 的值是字符串但无法解析为JSON: {v}，错误: {e}")

                    if v is None:
                        v = []

                    # 确保v是列表类型
                    if not isinstance(v, list):
                        raise ValueError(f"字段 '{k}' 期望ARRAY类型（列表），但收到 {type(v).__name__} 类型，值为: {v}")

                    # 根据element_type转换元素类型 (5 = INT64, 21 = VARCHAR)
                    element_type = fields_element_type_dict.get(k)
                    if element_type == 5:  # INT64
                        # 将元素转换为整数
                        converted_list = []
                        for idx, x in enumerate(v):
                            if x is None:
                                raise ValueError(f"字段 '{k}' 的第 {idx} 个元素为 None，ARRAY类型不允许None值")
                            try:
                                converted_list.append(int(x))
                            except (ValueError, TypeError) as e:
                                raise ValueError(
                                    f"字段 '{k}' 的第 {idx} 个元素 '{x}' (类型: {type(x).__name__}) 无法转换为INT64，错误: {e}")
                        v = converted_list
                    elif element_type == 21:  # VARCHAR
                        # 将元素转换为字符串
                        converted_list = []
                        for idx, x in enumerate(v):
                            if x is None:
                                raise ValueError(f"字段 '{k}' 的第 {idx} 个元素为 None，ARRAY类型不允许None值")
                            converted_list.append(str(x))
                        v = converted_list

                    data_dict[k] = v
                elif isinstance(v, list):
                    if k in ("offset", "position", "page_size"):
                        data_dict[k] = str(v)
                    else:
                        v = [x for x in v if x is not None]
                        if v is not None:
                            data_dict[k] = v
                        else:
                            data_dict[k] = []
                else:
                    if v is not None:
                        data_dict[k] = str(v)
        # R14-A：offset / position / page_size 在读侧会被 json.loads()，写入侧必须落"合法 JSON 字符串"。
        # 历史缺陷：FAQ 抽取没有 offset → 写入落成 ""，检索层 json.loads("") 抛
        #   "Expecting value: line 1 column 1 (char 0)"，而 retrieval_milvus 的 except 是 break（不是 continue），
        #   于是整批 FAQ 命中被丢弃 → faq_result_list=0 → FAQ 直答失效（R14-FAQ 根因之一）。
        for _jf in ("offset", "position", "page_size"):
            if _jf not in i_name:
                continue
            _cur = data_dict.get(_jf)
            if _cur in (None, "", b""):
                data_dict[_jf] = "[]"
            elif isinstance(_cur, str):
                continue          # 已是字符串：保持原样（可能是历史数据回灌的 JSON 文本）
            elif isinstance(_cur, (list, tuple)):
                data_dict[_jf] = json.dumps(list(_cur), ensure_ascii=False)
            else:
                data_dict[_jf] = json.dumps(_cur, ensure_ascii=False)
        if "pk" in data_dict.keys() and not data_dict["pk"]:
            _meta = doc["metadata"]
            if is_community_collection and _meta.get("community_id"):
                data_dict["pk"] = community_doc_id(insert_model.collection_name, _meta)
            elif (not coll_name_low.startswith("faq_") and _meta.get("document_id")
                  and (_meta.get("parsed_chunk_index") is not None or _meta.get("chunk_index") is not None)):
                # R14-A/F04：与 ES 侧同一算法的内容寻址主键，保证 ES `_id` 与 Milvus `pk` 一致。
                # 注意 1：ES 侧 index_name 会先经 is_index_lower() 小写化，这里必须同样小写，否则大小写 KB 名会算出不同 id。
                # 注意 2：序号优先取 parsed_chunk_index（解析全序，:405 赋值、linking 之前即可用），
                #         缺失才退回 chunk_index（解析末尾重编号，:646），与解析服务 pk 派生保持同一字段。
                _seq = _meta.get("parsed_chunk_index")
                if _seq is None:
                    _seq = _meta.get("chunk_index")
                # R14-A-FIX-18：与 es.py 同口径——种子不含 document_id（路径形态会变），
                # 用 file_id（缺失退回 title）+ 序号 + 内容哈希，保证换入口解析 id 不变。
                _fid = _meta.get("file_id")
                if _fid in (None, ""):
                    _fid = _meta.get("title")
                data_dict["pk"] = derive_doc_id("chunk", str(insert_model.collection_name).lower(),
                                                _fid, _seq,
                                                hashlib.sha1(str(doc["page_content"]).encode("utf-8")).hexdigest())
            else:
                data_dict["pk"] = create_uuid()
        if is_community_collection and doc["metadata"].get("community_id"):
            # 社区摘要的 schema 没有 community_id 列（见 milvus_kb_config.MILVUS_FIELDS），
            # 这里用通用列 chunk_doc_id 承载逻辑身份，供对账/删除按 community_id 精确定位。
            if "chunk_doc_id" in i_name:
                data_dict["chunk_doc_id"] = str(doc["metadata"]["community_id"])
            if "knowledge_base_name" in i_name and not data_dict.get("knowledge_base_name"):
                data_dict["knowledge_base_name"] = insert_model.collection_name
        if "source" in doc["metadata"].keys():
            add_sources.add(doc["metadata"]["source"])
        now = datetime.now()
        if "create_time" not in data_dict.keys() or not data_dict["create_time"]:
            data_dict["create_time"] = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
        if "update_time" not in data_dict.keys() or not data_dict["update_time"]:
            data_dict["update_time"] = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
        if "faq_" in coll_name_low:
            # add_query.add(doc["page_content"])
            if "faq_type" not in doc["metadata"].keys():
                data_dict["faq_type"] = 1
            if "status" not in doc["metadata"].keys():
                data_dict["status"] = 0
        item_json = json.dumps(data_dict, ensure_ascii=False)
        dict_sizes.append(sys.getsizeof(item_json.encode("utf-8")))
        try:
            # 检查数据类型是否与schema一致
            check_field_type(data_dict, fields_type_dict)
        except Exception as e:
            logger.error(e)
            return BaseResponse(code=500, msg=f'保存数据失败，{e}')
        data_dict_list.append(data_dict)

    if is_community_collection and data_dict_list:
        # R14-A：社区摘要整代替换——先删旧代（含 R13 遗留的随机 pk 行），确认对查询不可见后再写新代
        try:
            existing = await asyncio.to_thread(_visible_count, coll, "pk >= 0")
            if existing:
                await asyncio.to_thread(coll.delete, expr="pk >= 0")
            ok, remain = await asyncio.to_thread(_wait_until_deleted, coll, "pk >= 0")
            if not ok:
                return BaseResponse(code=500,
                                    msg=f'社区摘要替换失败：删除旧代后仍有 {remain} 条可见，已中止写入以免重复')
            logger.info(f'{insert_model.collection_name} 社区摘要整代替换：清理旧行 {existing} 条，写入 {len(data_dict_list)} 条')
        except Exception as e:
            logger.error(f'社区摘要替换失败，{e}')
            return BaseResponse(code=500, msg=f'社区摘要替换失败: {e}')
    elif "faq_" not in coll_name_low and add_sources and insert_model.duplicate_flag:
        try:
            sources = sorted(str(s) for s in add_sources)
            # R14-F04/F06：原实现没有把 db_name 传下去，删除落到配置默认库（rag_knowledge_base），
            # 实际集合在 graph_base/其它库 → is_collection 查不到 → 删除被静默跳过 → 重解析翻倍。
            del_param = DataParamModel(collection_name=insert_model.collection_name,
                                       db_name=insert_model.db_name,
                                       col_name="source", col_values=sources)
            del_res = await asyncio.to_thread(del_doc_by_col, del_param)
            logger.info(f'{insert_model.collection_name} 入库前按 source 去重: {del_res.msg}')
            # Milvus 删除是最终一致的，必须确认旧行不可见后再插入，否则重复事件仍会写成两代
            ok, remain = await asyncio.to_thread(_wait_until_deleted, coll, _source_expr(sources))
            if not ok:
                return BaseResponse(code=500,
                                    msg=f'删除已入库文件失败：{remain} 条旧数据仍可见，已中止写入以免重复')
        except Exception as e:
            logger.error(f'删除已入库文件失败，{e}')
            return BaseResponse(code=500, msg=f'删除已入库文件失败，{e}')

    total_size = f"{sum(dict_sizes) / (1024 * 1024):.2f}" if dict_sizes else "0.0"
    insert_batch_size, insert_concurrency = get_insert_control_config(milvus_conn_config)
    if float(total_size) < 60 and len(data_dict_list) <= insert_batch_size:
        data_dict_list_batches = [data_dict_list]
    else:
        data_dict_list_batches = split_array(data_dict_list, insert_batch_size)
    # elif 120 > float(total_size) > 60:
    #     mid_index = len(data_dict_list) // 2
    #     data_dict_list = [data_dict_list[:mid_index], data_dict_list[mid_index:]]
    # else:
    #     num_parts = math.ceil(int(total_size) / 40)
    #     part_size = len(data_dict_list) // num_parts
    #     array_parts = [data_dict_list[i * part_size: (i + 1) * part_size] for i in range(num_parts)]
    #     if len(data_dict_list) % num_parts != 0:
    #         # 将剩余的元素加入到最后一个部分
    #         remainder = data_dict_list[num_parts * part_size:]
    #         array_parts[-1].extend(remainder)
    #     data_dict_list = array_parts
    try:
        # 使用异步接口批量插入
        mr = await batch_insert_async(
            collection_name=collection_name,
            data_dict_list=data_dict_list_batches,
            milvus_conn_config=milvus_conn_config,
            concurrency=insert_concurrency,
            fields_order=fields_order,
            db_name=insert_model.db_name
        )
        return BaseResponse(code=200, msg=f'保存数据成功，{mr}')
    except Exception as e:
        logger.error(f'保存数据失败，{e}')
        return BaseResponse(code=500, msg=f'保存数据失败，{e}')


async def batch_insert(data_dict_list, coll, concurrency=4, milvus_conn_config=None):
    """
    异步批量插入 Milvus，同时调整 vector 列维度到 TARGET_DIM
    Args:
        data_dict_list: 待插入的数据列表（已分批）
        coll: Milvus Collection 对象
        concurrency: 插入并发度
        milvus_conn_config: Milvus连接配置
    """
    if not data_dict_list:
        return None

    semaphore = asyncio.Semaphore(max(concurrency, 1))
    inserted_pks = []

    async def insert_chunk(data_chunk):
        async with semaphore:
            result = await asyncio.to_thread(coll.insert, data_chunk)
            inserted_pks.extend(getattr(result, "primary_keys", []) or [])
            # logger.info(f'插入 Milvus 数据成功，批次大小 {len(data_chunk)}')
            return result

    tasks = [asyncio.create_task(insert_chunk(chunk)) for chunk in data_dict_list]
    try:
        results = await asyncio.gather(*tasks)
        async def load_if_needed():
            try:
                db_name = milvus_conn_config.get("milvus_database") if milvus_conn_config else None
                load_state = utility.load_state(coll.name, using=db_name)
                if load_state != LoadState.Loaded:
                    await asyncio.to_thread(coll.load)
            except Exception as e:
                logger.warning(f'milvus后台load失败: {e}')
        asyncio.create_task(load_if_needed())
        
        return results[-1] if results else None
    except Exception as exc:
        logger.error(f'批量插入失败，开始回滚，{exc}')
        if inserted_pks:
            try:
                await asyncio.to_thread(rollback_inserted_rows, coll, inserted_pks)
                logger.info(f'已回滚插入数据，数量 {len(inserted_pks)}')
            except Exception as rollback_err:
                logger.error(f'回滚失败，请手动清理，{rollback_err}')
        raise


def rollback_inserted_rows(coll, inserted_pks):
    pk_expr_values = []
    for pk in inserted_pks:
        if isinstance(pk, str):
            pk_expr_values.append(f'"{pk}"')
        else:
            pk_expr_values.append(str(pk))
    expr = f"pk in [{','.join(pk_expr_values)}]"
    coll.delete(expr)
    coll.flush()


def find_not_included(m_field, s_field):
    m = set(m_field)
    s = set(s_field)
    not_included = s - m
    if not_included:
        return list(not_included)  # 将集合转换回列表并返回
    else:
        return []  # 如果没有元素不在b中，返回空列表


def search_collection(cn, query_model, server_config, embed_data):
    """
    处理单个 collection_name 的搜索逻辑
    """
    search_param = query_model.search_param  # 筛选条件
    cec_query_condition = query_model.cec_query_condition
    cn_p = cn.replace("table_chunks_", "").replace("table_summary_", "")

    if cec_query_condition and (cn in cec_query_condition or cn_p in cec_query_condition):
        file_list = cec_query_condition[cn if cn in cec_query_condition else cn_p]
        search_param = f"file_id in {file_list}"

    hit_dict_list = []
    collection_name = generate_collection_name_uuid(cn)

    if not is_collection(collection_name, server_config["milvus_conn_config"], query_model.db_name):
        # logger.error(f"{collection_name} 不存在")
        return []

    coll = get_collection(collection_name, server_config["milvus_conn_config"], query_model.db_name)
    # coll.load()  # 可选：如果需要加载 collection

    def collect_hits(sr, exclude_fields=("vector", "question_vector")):
        local_hits = []
        for result in sr:
            for hit in result:
                hit_dict = {}
                for field in hit.fields.keys():
                    if field not in exclude_fields:
                        if isinstance(hit.fields.get(field), RepeatedScalarContainer):
                            hit_dict[field] = list(hit.fields.get(field))
                        else:
                            hit_dict[field] = hit.fields.get(field)
                hit_dict["score"] = hit.distance
                local_hits.append(hit_dict)
        return local_hits

    # 1) 默认 vector 字段检索
    # 兼容两种embed_data格式
    compatible_flag = server_config.get("compatible_flag", False)
    if compatible_flag:
        # 兼容格式：embed_data[0] 直接是向量数组
        search_vector = embed_data[0]
    else:
        # 标准格式：embed_data[0]["embedding"] 是向量数组
        search_vector = embed_data[0]["embedding"]

    search_result_main = coll.search(
        data=[search_vector],
        anns_field="vector",
        param=query_model.search_config,
        limit=query_model.top_k,
        timeout=30,
        expr=search_param,
        output_fields=["*"]
    )
    main_hits = collect_hits(search_result_main)

    # 2) 如为 FAQ 集合且存在 question_vector 字段且开关开启，再检索 question_vector，并与 main 合并（同 pk 取最大分）
    merged_by_pk = {}
    for h in main_hits:
        pk_val = h.get("pk")
        if pk_val is not None:
            merged_by_pk[pk_val] = h

    # 从nacos配置中读取question_vector开关，默认为False
    enable_question_vector = server_config.get("enable_question_vector", False)
    if "faq_" in cn.lower() and enable_question_vector:
        has_question_vector = any(f.name == "question_vector" for f in coll.schema.fields)
        if has_question_vector:
            search_result_q = coll.search(
                data=[search_vector],  # 使用相同的search_vector
                anns_field="question_vector",
                param=query_model.search_config,
                limit=query_model.top_k,
                timeout=30,
                expr=search_param,
                output_fields=["*"]
            )
            q_hits = collect_hits(search_result_q)
            logger.info(f"q_hits: {q_hits}")
            for h in q_hits:
                pk_val = h.get("pk")
                if pk_val is None:
                    continue
                if pk_val not in merged_by_pk:
                    merged_by_pk[pk_val] = h
                else:
                    # 取更大分值
                    if h["score"] > merged_by_pk[pk_val]["score"]:
                        merged_by_pk[pk_val] = h

    hit_dict_list = list(merged_by_pk.values()) if merged_by_pk else main_hits

    # FAQ 检索结果按 score 倒序排序
    hit_dict_list.sort(key=lambda d: d.get("score", float("-inf")), reverse=True)


    logger.info(f"milvus 召回结果: {hit_dict_list}")
    return hit_dict_list


def do_search(query_model: QueryDataModel) -> BaseResponse:
    """
    查询数据。

    Args:
       query_model (QueryDataModel): 数据查询对象。
       示例：search_param={"expr": "ids=='1'"}
    Returns:
       BaseResponse对象。
    Notes：
       search_param为查询条件，用户可自定义查询条件
    """
    # logger.info("参数：" + str(query_model.json()))
    server_config = return_nacos_model().get_config()
    collection_name_list = query_model.collection_name
    model_name = query_model.model_name or server_config["embedding_model"]
    full_docs_list = []
    embed_data = xinference_embedding_request(model_name, [query_model.query], server_config)
    error_details = []
    lock = threading.Lock()  # 保护共享变量
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # 10 个线程
        future_to_cn = {executor.submit(search_collection, cn, query_model, server_config, embed_data): cn for cn in collection_name_list}

        for future in concurrent.futures.as_completed(future_to_cn):
            cn = future_to_cn[future]
            try:
                hit_dict_list = future.result()
                if hit_dict_list:
                    with lock:
                        full_docs_list.extend(hit_dict_list)
            except Exception as e:
                logger.error(f"集合 {cn} 查询失败：{e}")
                error_details.append(f"{cn}: {e}")
    # for cn in collection_name_list:
    #     search_param = query_model.search_param  # 筛选条件
    #     cec_query_condition = query_model.cec_query_condition
    #     cn_p = cn.replace("table_chunks_", "").replace("table_summary_", "")
    #     if cec_query_condition and (cn in cec_query_condition or cn_p in cec_query_condition):
    #         file_list = cec_query_condition[cn if cn in cec_query_condition else cn_p]
    #         search_param = f"file_id in {file_list}"
    #     hit_dict_list = []
    #     collection_name = generate_collection_name_uuid(cn)
    #     if not is_collection(collection_name, server_config["milvus_conn_config"], query_model.db_name):
    #         error_num += 1
    #         logger.error(f"{collection_name}不存在")
    #         continue
    #     try:
    #         coll = get_collection(collection_name, server_config["milvus_conn_config"], query_model.db_name)
    #         #coll.load()
    #     except Exception as e:
    #         logger.error(f"{collection_name}链接失败，{e}")
    #         error_num += 1
    #         continue
    #     try:
    #         search_result = coll.search(
    #             data=[embed_data[0]["embedding"]],
    #             anns_field="vector",  # 这是存储向量的字段
    #             param=query_model.search_config,
    #             limit=query_model.top_k,
    #             timeout=30,
    #             expr=search_param,  # 添加过滤条件
    #             output_fields=["*"]
    #         )
    #         for result in search_result:
    #             for hit in result:
    #                 hit_dict = {}
    #                 for field in hit.fields.keys():
    #                     if field not in ["vector"]:
    #                         if isinstance(hit.fields.get(field), RepeatedScalarContainer):
    #                             hit_dict[field] = list(hit.fields.get(field))  # 转换为 list
    #                         else:
    #                             hit_dict[field] = hit.fields.get(field)
    #                 # hit_dict = {field: hit.fields.get(field) for field in hit.fields.keys() if
    #                 #             field not in ("vector")}
    #                 hit_dict["score"] = hit.distance
    #                 hit_dict_list.append(hit_dict)
    #     except Exception as e:
    #         hit_dict_list = []
    #         logger.error(f'查询数据失败，{e}')
    #     full_docs_list.extend(hit_dict_list)
    if not full_docs_list:
        if error_details:
            return BaseResponse(code=500, msg=f'查询失败：{"; ".join(error_details)}')
        return BaseResponse(code=200, msg='查询成功，无匹配结果', data={'result_data': []})
    data_list = [{"page_content": dl.pop("text"), "metadata": dl} for dl in full_docs_list]
    data_list = sorted(data_list, key=lambda x: x["metadata"]["score"], reverse=True)
    return BaseResponse(code=200, msg='查询数据成功', data={'result_data': data_list})


async def update_data(update_model: UpdateParamModel) -> BaseResponse:
    """
    根据pk修改数据
    Args:
        update_model:

    Returns:

    """
    # logger.info("参数：" + str(update_model.json()))
    pk_list = [int(ud["pk"]) for ud in update_model.document_list]
    try:
        del_param = DataParamModel(collection_name=update_model.index_name, col_name="pk", col_values=pk_list)
        del_res = del_doc_by_col(del_param)
    except Exception as e:
        logger.error(f'删除数据失败:{e}')
        return BaseResponse(code=500, msg=f'删除数据失败:{e}')
    result_list = []
    for rl in update_model.document_list:
        now = datetime.now()
        rl["update_time"] = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond:06d}"
        # result_list.append({"page_content": rl.pop("page_content"), "metadata": rl})
        page_content = rl.get("page_content", None)
        if page_content:
            result_list.append({"page_content": page_content, "metadata": rl})
        else:
            page_content = rl.get("question", "") + "@@" + rl.get("answer", "")
            result_list.append({"page_content": page_content, "metadata": rl})

    if del_res.code == 200:
        insert_model = InsertDataModel(collection_name=update_model.index_name,
                                       model_name=update_model.model_name,
                                       document_list=result_list,
                                       duplicate_flag=False)
        response = await add_doc_custom(insert_model)
        if response.code != 200:
            return BaseResponse(code=500, msg=f'修改数据失败:{response.msg}')
    else:
        logger.error(f'删除数据失败:{del_res.msg}')
        return BaseResponse(code=500, msg=f'删除数据失败:{del_res.msg}')
    return BaseResponse(code=200, msg=f'修改数据成功')


def update_by_pk(update_col: UpdateColModel):
    """
    根据pk修改数据
    Args:
        update_col:

    Returns:

    """
    # logger.info("参数：" + str(update_col.json()))
    server_config = return_nacos_model().get_config()
    collection_name_list = [update_col.index_name]
    if update_col.file_id and "faq_" not in update_col.index_name:
        collection_name_list.extend(["table_chunks_" + update_col.index_name, "table_summary_" + update_col.index_name])
    query_res = []
    for collection_name1 in collection_name_list:
        collection_name = generate_collection_name_uuid(collection_name1)
        try:
            coll = get_collection(collection_name, server_config["milvus_conn_config"], update_col.db_name)
        except Exception as e:
            logger.error(f"{collection_name1}链接失败，可能不存在该表，{e}")
            continue

        if update_col.pk:
            query_res = coll.query(
                expr=f"pk in {update_col.pk}",
                output_fields=["*"]
            )
        elif update_col.file_id:
            query_res = coll.query(
                expr=f"file_id in {update_col.file_id}",
                output_fields=["*"]
            )
        if not query_res:
            logger.error(f'修改数据失败:{collection_name1}中{update_col.pk or update_col.file_id}并没有查询到数据')
            continue
        updated_entities = []
        for entity in query_res:
            updated_entity = entity.copy()  # 复制现有数据
            updated_entity[update_col.col_name] = update_col.col_value
            updated_entities.append(updated_entity)
        try:
            coll.upsert(updated_entities)
        except Exception as e:
            logger.error(f'修改数据失败:{e}')
            return BaseResponse(code=500, msg=f'修改数据失败:{e}')
    if query_res:
        return BaseResponse(code=200, msg=f'修改数据成功')
    else:
        return BaseResponse(code=200,
                            msg=f'修改数据失败，{collection_name_list} 表不存在或者这些表中不存在{update_col.pk or update_col.file_id}的数据')


def update_by_pk_batch(update_batch: UpdateBatchModel):
    """
    根据pk修改数据  批量
    Args:
        update_batch:

    Returns:

    """
    # logger.info("参数：" + str(update_batch.json()))
    server_config = return_nacos_model().get_config()
    collection_name_list = [update_batch.index_name]
    if update_batch.update_file_name == 'file_id' and "faq_" not in update_batch.index_name:
        collection_name_list.extend(
            ["table_chunks_" + update_batch.index_name, "table_summary_" + update_batch.index_name])
    query_res = []
    for collection_name1 in collection_name_list:
        collection_name = generate_collection_name_uuid(collection_name1)
        try:
            coll = get_collection(collection_name, server_config["milvus_conn_config"], update_batch.db_name)
        except Exception as e:
            logger.error(f"{collection_name}链接失败，{e}")
            return BaseResponse(code=200, msg=f'修改数据失败:{e}')

        data_dict = update_batch.update_condition_json
        pk_list = [int(pk) for pk in list(data_dict.keys())]

        if update_batch.update_file_name == 'file_id':
            file_id_list = [str(pk) for pk in list(data_dict.keys())]
            query_res = coll.query(
                expr=f"file_id in {file_id_list}",
                output_fields=["*"]
            )
        else:
            query_res = coll.query(
                expr=f"pk in {pk_list}",
                output_fields=["*"]
            )
        updated_entities = []
        if not query_res:
            logger.error(f'修改数据失败:{collection_name1}中{data_dict}并没有查询到数据')
            continue
        for entity in query_res:
            updated_entity = entity.copy()  # 复制现有数据
            source_pk = str(updated_entity[update_batch.update_file_name])
            update_col = list(data_dict[source_pk].keys())[0]
            update_col_value = data_dict[source_pk][update_col]
            updated_entity[update_col] = update_col_value
            updated_entities.append(updated_entity)
        try:
            coll.upsert(updated_entities)
        except Exception as e:
            logger.error(f'修改数据失败:{e}')
            return BaseResponse(code=500, msg=f'修改数据失败:{e}')
    if query_res:
        return BaseResponse(code=200, msg=f'修改数据成功')
    else:
        return BaseResponse(code=200,
                            msg=f'修改数据失败,{collection_name_list} 表不存在或者这些表中不存在{update_batch.update_condition_json}的数据')


def get_doc_by_col(query_param: DataParamModel) -> BaseResponse:
    """
    根据列查询数据。

    Args:
       query_param DataParamModel对象
    Returns:
       BaseResponse对象。
    Notes：

    """
    # logger.info("参数：" + str(query_param.json()))
    server_config = return_nacos_model().get_config()
    collection_name = generate_collection_name_uuid(query_param.collection_name)
    all_results = []
    offset = 0
    batch_size = 500
    try:
        coll = get_collection(collection_name, server_config["milvus_conn_config"], query_param.db_name)
    except Exception as e:
        logger.error(f"{collection_name}链接失败，{e}")
        return BaseResponse(code=200, msg=f'查询数据失败，{e}')
    coll.load()
    fields = coll.schema.fields
    f_type = 0
    for f in fields:
        if f.name == query_param.col_name:
            f_type = f.dtype
    output_fields = [f.name for f in fields if f.name not in ("vector")]
    try:
        expr = query_param.expr
        if not expr:
            if query_param.col_name:
                if f_type == 22:
                    expr = " || ".join([f"array_contains({query_param.col_name}, '{cv}')" for cv in query_param.col_values])
                else:
                    expr = f'{query_param.col_name} in {[cv for cv in query_param.col_values]}'
        while True:
            results = coll.query(
                expr=expr,
                offset=offset,
                limit=batch_size,
                output_fields=output_fields
            )
            if not results:
                break
            result_list = []
            for rl in results:
                # 转换 RepeatedScalarContainer 类型字段为列表
                processed_rl = {}
                for key, value in rl.items():
                    if isinstance(value, RepeatedScalarContainer):
                        processed_rl[key] = list(value)
                    else:
                        processed_rl[key] = value
                result_list.append({"page_content": processed_rl.pop("text"), "metadata": processed_rl})
            all_results.extend(result_list)
            offset += batch_size
    except Exception as e:
        logger.error(f'查询数据失败，{e}')
        return BaseResponse(code=500, msg=f'查询数据失败，{e}')
    return BaseResponse(code=200, msg='查询数据成功', data={'result_data': all_results})


async def get_doc_page(query_param: DataParamModel) -> BaseResponse:
    """
    根据列查询数据。

    Args:
       query_param DataParamModel对象
    Returns:
       BaseResponse对象。
    Notes：

    """
    # logger.info("参数：" + str(query_param.json()))
    server_config = return_nacos_model().get_config()
    collection_names = query_param.collection_name_list or [query_param.collection_name]
    is_multi = len(collection_names) > 1

    all_results = []
    batch_size = query_param.page_num
    offset = (query_param.page_no - 1) * query_param.page_num
    total = 0

    for cn in collection_names:
        collection_name = generate_collection_name_uuid(cn)
        try:
            coll = get_collection(collection_name, server_config["milvus_conn_config"], query_param.db_name)
            await asyncio.to_thread(coll.load)
        except Exception as e:
            logger.error(f"{collection_name}链接失败，{e}")
            # 单集合时直接返回错误
            if not is_multi:
                return BaseResponse(code=200, msg=f'查询数据失败，{e}')
            # 多集合模式下，跳过当前出错的集合，继续查询其他集合
            continue

        fields = coll.schema.fields
        output_fields = [f.name for f in fields if f.name not in ("vector")]
        try:
            expr = query_param.expr
            if not expr:
                if query_param.col_name:
                    expr = f'{query_param.col_name} in {[cv for cv in query_param.col_values]}'
                elif query_param.condition_json:
                    expr_par = ""
                    for cj_dict in query_param.condition_json:
                        for key, value in cj_dict.items():
                            if isinstance(value, list):
                                expr_par += f'{key} in {[cv for cv in value]} and '
                            else:
                                expr_par += f'{key} == {value} and '
                    expr = expr_par[:-4]

            # 先统计当前集合满足条件的总数
            try:
                # 通过分页 query 统计命中数量，确保 total 等于"实际可查询到的记录数"
                count_offset = 0
                count_batch = 1000
                while True:
                    count_res = await asyncio.to_thread(
                        lambda: coll.query(
                            expr=expr or "",
                            offset=count_offset,
                            limit=count_batch,
                            output_fields=["pk"],
                        )
                    )
                    if not count_res:
                        break
                    total += len(count_res)
                    count_offset += count_batch
            except Exception as e:
                logger.error(f'统计数据失败，集合 {collection_name}，错误：{e}')
                if not is_multi:
                    return BaseResponse(code=500, msg=f'统计数据失败，{e}')
                # 多集合模式下，统计失败则跳过该集合
                continue

            # 再按分页查询当前集合的数据
            results = await asyncio.to_thread(
                lambda: coll.query(
                    expr=expr,
                    offset=offset,
                    limit=batch_size,
                    output_fields=output_fields
                )
            )
            result_list = []
            for rl in results:
                # 转换 RepeatedScalarContainer 类型字段为列表
                processed_rl = {}
                for key, value in rl.items():
                    if isinstance(value, RepeatedScalarContainer):
                        processed_rl[key] = list(value)
                    else:
                        processed_rl[key] = value
                result_list.append({"page_content": processed_rl.pop("text"), "metadata": processed_rl})
            all_results.extend(result_list)
        except Exception as e:
            logger.error(f'查询数据失败，集合 {collection_name}，错误：{e}')
            if not is_multi:
                return BaseResponse(code=500, msg=f'查询数据失败，{e}')
            # 多集合时，继续尝试下一个集合
            continue

    if not all_results and is_multi:
        return BaseResponse(code=200, msg='查询数据失败，所有集合均查询失败或无数据',
                            data={'result_data': [], "page": query_param.page_no,
                                  "page_size": batch_size,
                                  "total": total, "count": 0}, )

    return BaseResponse(
        code=200,
        msg=f'查询数据成功,返回第{query_param.page_no}页{batch_size}条数据',
        data={
            'result_data': all_results,
            "page": query_param.page_no,
            "page_size": batch_size,
            "total": total,
            "count": len(all_results)
        }
    )


def del_doc_entity(up_param: UpdateBatchModel):
    """
    专门针对删除实体表开发的删除接口
    Args:
        up_param:
    Returns:

    """
    # logger.info("参数：" + str(up_param.json()))
    server_config = return_nacos_model().get_config()
    collection_name = generate_collection_name_uuid(up_param.index_name)
    try:
        coll = get_collection(collection_name, server_config["milvus_conn_config"], up_param.db_name)
    except Exception as e:
        logger.error(f"{collection_name}链接失败，{e}")
        return BaseResponse(code=200, msg=f'删除数据失败，{e}')
    # {"file_id":["str"],title:["str"]}
    condition_json = up_param.update_condition_json
    if not condition_json:
        coll.drop()
        return BaseResponse(code=200, msg=f'数据删除成功')
    if "file_id" in condition_json.keys():
        par_name = "file_id"
        par_va = condition_json["file_id"]
    elif "title" in condition_json.keys():
        par_name = "title"
        par_va = condition_json["title"]
    elif "type" in condition_json.keys():
        par_name = "type"
        par_va = condition_json["type"]
    else:
        logger.error(f'参数传递错误，暂时支持"file_id，title，type"，不支持其他参数,{condition_json}')
        return BaseResponse(code=500, msg=f'参数传递错误，暂时支持"file_id，title，type"，不支持其他参数')
    query_res = coll.query(
        expr=f'array_contains_any({par_name}, {par_va})',
        # expr=f'array_contains_any(type, ["人"])',
        output_fields=["*"]
    )
    for entity in query_res:
        for key, item in condition_json.items():
            # 转换 RepeatedScalarContainer 为列表（如果存在）
            if isinstance(entity.get(key), RepeatedScalarContainer):
                entity[key] = list(entity[key])
            for im in item:
                if im in entity[key]:
                    entity[key].remove(im)
    try:
        if query_res:
            coll.upsert(query_res)
    except Exception as e:
        logger.error(f'修改数据失败:{e}')
        return BaseResponse(code=500, msg=f'修改数据失败:{e}')
    # 删除为空的数据
    try:
        coll.delete(expr=f'array_length(file_id) == 0')
        coll.load()  # 加载新添加的数据到内存
    except Exception as e:
        logger.error(f'删除数据失败:{e}')
        return BaseResponse(code=500, msg=f'删除数据失败:{e}')
    return BaseResponse(code=200, msg=f'数据删除成功')


def del_doc_by_col(del_param: DataParamModel) -> BaseResponse:
    """
    根据列删除数据。

    Args:
       del_param DataParamModel对象
    Returns:
       BaseResponse对象。
    Notes：

    """
    # logger.info("参数：" + str(del_param.json()))
    server_config = return_nacos_model().get_config()
    collection_name = generate_collection_name_uuid(del_param.collection_name)
    # 如果集合不存在，直接返回未找到
    if not is_collection(collection_name, server_config, del_param.db_name):
        return BaseResponse(code=200, msg=f'未执行删除，milvus未找到集合: {del_param.collection_name}', data={'result_data': del_param.col_values})
    deleted_count = 0
    try:
        coll = get_collection(collection_name, server_config["milvus_conn_config"], del_param.db_name)
        if not del_param.col_name and del_param.collection_name:
            coll.drop()
        elif del_param.col_name:
            delete_res = coll.delete(expr=f'{del_param.col_name} in {del_param.col_values}')
            deleted_count += getattr(delete_res, "delete_count", 0) or 0
            coll.load()  # 加载新添加的数据到内存
        elif del_param.condition_json:
            for con_dict in del_param.condition_json:
                for col_name, col_values in con_dict.items():
                    delete_res = coll.delete(expr=f'{col_name} in {col_values}')
                    deleted_count += getattr(delete_res, "delete_count", 0) or 0
            coll.load()  # 加载新添加的数据到内存
    except Exception as e:
        logger.error(f'删除数据失败，{e}')
        return BaseResponse(code=200, msg=f'删除数据失败，{e}')
    if deleted_count == 0 and (del_param.col_name or del_param.condition_json):
        return BaseResponse(code=200, msg='未执行删除，milvus未找到相应数据', data={'result_data': del_param.col_values})
    return BaseResponse(code=200, msg=f'成功删除数据', data={'result_data': del_param.col_values})


def is_collection(collection_name, server_config, db_name: str = None):
    """
    判断集合是否存在
    """
    db_name = db_name or server_config.get("milvus_database", "rag_knowledge_base")

    # 确保连接
    return_nacos_model().ensure_connection()

    try:
        return utility.has_collection(collection_name, using=db_name)
    except Exception:
        return False


# def list_collection(db_name: str = None):
#     """
#     返回集合
#     """
#     db_name = db_name or server_config["milvus_database"]
#     return utility.list_collections(using=db_name)


def static_count(static_param: DataParamModel):
    """
    统计
    Args:
        static_param:

    Returns:

    """
    # logger.info("参数：" + str(static_param.json()))
    server_config = return_nacos_model().get_config()
    collection_name = generate_collection_name_uuid(static_param.collection_name)
    try:
        coll = get_collection(collection_name, server_config["milvus_conn_config"], static_param.db_name)
        coll.load()
        num = coll.num_entities
    except Exception as e:
        logger.error(f"{collection_name}链接失败，{e}")
        return BaseResponse(code=500, msg=f'查询数据失败，{e}', )
    return BaseResponse(code=200, msg=f'成功查询数据', data={'count': num})


def del_collection(del_param: DataParamModel) -> BaseResponse:
    """R14-A：删除整个 Milvus 集合（补 graph_summary.del_community 依赖、但服务端缺失的路由）。

    R14 实测事实：`GET /openapi.json` 里没有 `/del_collection`，而 `graph_summary.del_community()`
    一直 POST 到这个路由 → 404，且调用方把 404 当"已执行"记录进明细 → **Milvus 侧社区摘要集合
    从未真正被删除过**（ES 侧被 graph-refresh 删索引清掉，所以出现 ES 7 条 / Milvus 65 条）。
    """
    server_config = return_nacos_model().get_config()
    collection_name = generate_collection_name_uuid(del_param.collection_name)
    if not is_collection(collection_name, server_config, del_param.db_name):
        return BaseResponse(code=200,
                            msg=f'未执行删除，milvus未找到集合: {del_param.collection_name}',
                            data={'collection_name': collection_name, 'dropped': False})
    try:
        coll = get_collection(collection_name, server_config["milvus_conn_config"], del_param.db_name)
        coll.drop()
        logger.info(f'集合{collection_name}已删除(db={del_param.db_name})')
        return BaseResponse(code=200, msg=f'集合{collection_name}已删除',
                            data={'collection_name': collection_name, 'dropped': True})
    except Exception as e:  # noqa: BLE001
        logger.error(f'删除集合失败，{e}')
        return BaseResponse(code=500, msg=f'删除集合失败，{e}')
