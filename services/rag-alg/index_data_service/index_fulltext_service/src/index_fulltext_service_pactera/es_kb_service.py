#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 15:14
# @Author  : yuxj
# @File    : fulltext_es_api_start.py
import asyncio
import copy
import json
import logging
import os
import sys
from datetime import datetime

from elasticsearch import helpers

from base import BaseResponse, InsertDataModel, IndexModel, CreateIndexModel, \
    OperateDataModel, QueryDataModel, QueryParamModel, UpdateParamModel, DeleteParamModel, UpdateColModel
from controller.es import add_documents_async, is_index_lower
from controller.es_query import query_es_sql
from controller.query_type import QueryType
from es_kb_config import ES_INDEX_MAPPING, ES_INDEX_MAPPING_SUMMARY, ES_INDEX_MAPPING_CHUNKS, ES_INDEX_MAPPING_DATABASE
from utils import return_nacos_model, create_uuid
from operators.common.log import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


#
# server_config = get_config()["es_config"]
# conn = server_config["es_connect"]
# """
# 初始化es
# """
# if conn['user']:
#     es = Elasticsearch([{'host': conn['host'], 'port': conn['port'],
#                          'scheme': conn['scheme']}],
#                        basic_auth=(conn['user'], conn['password']),
#                        verify_certs=conn['verify_certs'])
# else:
#     """
#     初始化es无账号密码
#     """
#     es = Elasticsearch([{'host': conn['host'], 'port': conn['port'], 'scheme': 'http'}])
#
# try:
#     es.info()
# except Exception as e:
#     raise ValueError(f'Failed to connect to Elasticsearch: {e}')


def is_index(index_name) -> bool:
    """
    检查index是否存在。

    Args:
       index_name:index名称。
    Returns:
       Bool。
    """
    es = return_nacos_model().es_client()
    return es.indices.exists(index=index_name)


def get_field_type(index, field):
    """获取字段的类型"""
    es = return_nacos_model().es_client()
    if not is_index(index):
        raise ValueError(f"{index} is index_not_found_exception")
    mapping = es.indices.get_mapping(index=index)
    if field == "page_content":
        f_type = mapping[index]['mappings']['properties'].get(field, {}).get('type', None)
    else:
        f_type = mapping[index]['mappings']['properties']["metadata"]['properties'].get(field, {}).get('type', None)
    return f_type


def init_field_sql(index, field, value, condition_logic_operations):
    field_type = get_field_type(index, field)
    if field_type == 'text':
        # 处理文本字段
        if field == "page_content":
            # if condition_logic_operations == "or":
                k = {"wildcard": {f"{field}.keyword": value}}
            # else:
            #     k = {"match": {f"{field}": value}}
        else:
            if condition_logic_operations == "or":
                k = {"wildcard": {f"metadata.{field}.keyword": value}}
            else:
                k = {"term": {f"metadata.{field}.keyword": value}}

    else:
        # 处理日期 数字 bool 字段
        k = {"term": {f"metadata.{field}": value}}
    return k


def query_field_sql(index, field, value, condition_logic_operations):
    full_sql = []
    if isinstance(value, list):
        if field != "page_content":
            sub_sql = {"terms": {f"metadata.{field}.keyword": value}}
        else:
            for vv in value:
                if condition_logic_operations == "or":
                    vv = "*" + str(vv) + "*"
                sub_sql = init_field_sql(index, field, vv, condition_logic_operations)
        full_sql.append(sub_sql)
    else:
        sub_sql = init_field_sql(index, field, value, condition_logic_operations)
        full_sql.append(sub_sql)
    return full_sql


def sort_field_sql(index, field, value):
    field_type = get_field_type(index, field)
    if field_type == 'text':
        return {f"metadata.{field}.keyword": {"order": value}}
    else:
        return {f"metadata.{field}": {"order": value}}


def get_index_mapping_field(index_name):
    """
    获取当前index的mapping中的字段名。

    Args:
        index_name:index名称。
    Returns:
       s_field_names:定义的mappings-properties的顶层字段名
        m_field_names:定义的metadata-properties的字段名
    Notes：
        如果index不存在则根据默认配置的mapping创建index
        目前只支持嵌套2层，如果metadata有多层嵌套需要修改逻辑代码
    """
    s_field_names = []
    m_field_names = []
    index_name = is_index_lower(index_name)
    es = return_nacos_model().es_client()
    if not is_index(index_name):
        index_model = CreateIndexModel(index_name=index_name)
        data = create_index(index_model)
        if data.code == 500:
            raise ValueError(data.msg)
    mapping = es.indices.get_mapping(index=index_name)
    if mapping and index_name in mapping:
        mapping_properties = mapping[index_name]['mappings']['properties']
        for field_name, field_mapping in mapping_properties.items():
            # 这里只提取顶层字段名，metadata字段有嵌套结构，需要递归处理
            s_field_names.append(field_name)
            if field_name == 'metadata':
                for f, v in field_mapping['properties'].items():
                    m_field_names.append(f)
    return s_field_names, m_field_names


def create_index(index_model: CreateIndexModel) -> BaseResponse:
    """
    创建index。

    Args:
        index_model:CreateIndexModel对象
    Returns:
        BaseResponse对象
    Notes：
        如果mapping_body为None，则使用配置文件中的mapping
    """
    # logger.info(f"参数：{str(index_model.json())}")
    index_name = is_index_lower(index_model.index_name)
    if "table_summary_" in index_name:
        body = ES_INDEX_MAPPING_SUMMARY
    elif "table_chunks_" in index_name:
        body = ES_INDEX_MAPPING_CHUNKS
    elif "database_" in index_name:
        body = ES_INDEX_MAPPING_DATABASE
    else:
        body = index_model.mapping_body or ES_INDEX_MAPPING
    es = return_nacos_model().es_client()
    if not is_index(index_name):
        try:
            es.indices.create(index=index_name, body=body)
            logger.info(f'索引{index_name}创建成功')
            return BaseResponse(code=200, msg=f'索引{index_name}创建成功')
        except Exception as ex:
            logger.error(f'索引{index_name}创建失败,{ex}')
            return BaseResponse(code=500, msg=f'索引{index_name}创建失败,{ex}')
    else:
        logger.error(f'索引{index_name}已存在')
        return BaseResponse(code=500, msg=f'索引{index_name}已存在')


def delete_index(index_model: IndexModel) -> BaseResponse:
    """
    删除index。

    Args:
        index_model:IndexModel对象
    Returns:
        BaseResponse对象
    """
    index_name = is_index_lower(index_model.index_name)
    if not is_index(index_name):
        logger.info(f'es索引{index_name}不存在，无需删除')
        return BaseResponse(code=200, msg=f'索引{index_name}不存在，无需删除')

    es = return_nacos_model().es_client()
    try:
        es.indices.delete(index=index_name)
        logger.info(f'索引{index_name}删除成功')
        return BaseResponse(code=200, msg=f'索引{index_name}删除成功')
    except Exception as ex:
        logger.error(f'索引{index_name}删除失败,{ex}')
        return BaseResponse(code=500, msg=f'索引{index_name}删除失败,{ex}')


def update_doc(update_model: UpdateParamModel):
    pk_list = [str(ud["pk"]) for ud in update_model.document_list]
    try:
        del_model = DeleteParamModel(index_name=update_model.index_name, pk_list=pk_list)
        del_by_id(del_model)
    except Exception as e:
        return BaseResponse(code=500, msg=f'修改数据失败:{e}')
    result_list = []
    for rl in update_model.document_list:
        now = datetime.now()
        rl["update_time"] = now.strftime('%Y-%m-%d %H:%M:%S.') + f"{now.microsecond:06d}"
        # rl["update_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        page_content = rl.get("page_content", None)
        if page_content:
            result_list.append({"page_content": page_content, "metadata": rl})
        else:
            page_content = rl.get("question", "") + "@@" + rl.get("answer", "")
            result_list.append({"page_content": page_content, "metadata": rl})
    try:
        insert_model = InsertDataModel(
            index_name=update_model.index_name,
            document_list=result_list,
            duplicate_flag=False,
        )
        insert_res = asyncio.run(add_documents_async(insert_model))
        if insert_res.code == 500:
            return BaseResponse(code=500, msg=f'修改数据失败:{insert_res.msg}')
        return BaseResponse(code=200, msg=f'修改数据成功')
    except Exception as e:
        return BaseResponse(code=500, msg=f'修改数据失败:{e}')


def update_pro_sql(es, update_model, index_name, doc_id_dict=None):
    actions = []
    for doc_id in update_model.pk:
        if not es.exists(index=index_name, id=str(doc_id)):
            continue
        action = {
            '_op_type': 'update',  # 操作类型为更新
            '_index': index_name,
            '_id': str(doc_id),
            'doc': {}
        }
        if update_model.col_name:
            if update_model.col_name == "page_content":
                action['doc']['page_content'] = update_model.col_value
            else:
                action['doc']['metadata'] = {update_model.col_name: update_model.col_value}
            actions.append(action)
        elif update_model.update_condition_json:
            update_condition_json = update_model.update_condition_json
            if doc_id_dict:
                update_field_dict = update_condition_json[doc_id_dict[doc_id]]
                #col_name, col_value = next(iter(update_condition_json[doc_id_dict[doc_id]].items()))
            else:
                update_field_dict = update_condition_json[doc_id]
                #col_name, col_value = next(iter(update_condition_json[doc_id].items()))
            for col_name, col_value in update_field_dict.items():
                action_cp = copy.deepcopy(action)
                if col_name == "page_content":
                    action_cp['doc']['page_content'] = col_value
                else:
                    action_cp['doc']['metadata'] = {col_name: col_value}
                actions.append(action_cp)
    return actions


def update_by_id(update_model: UpdateColModel):
    actions = []
    es = return_nacos_model().es_client()
    if update_model.pk:
        index_name = is_index_lower(update_model.index_name)
        actions = update_pro_sql(es, update_model, index_name)
    elif update_model.file_id:
        index_name_list = ["table_chunks_" + update_model.index_name, "table_summary_" + update_model.index_name, update_model.index_name]
        for index_name in index_name_list:
            index_name = is_index_lower(index_name)
            if not is_index(index_name):
                logger.error(f"该索引：{index_name} 不存在， 请创建后重试")
                continue
            result_data = es.search(
                index=index_name,
                query={"terms": {f"metadata.file_id": update_model.file_id}}
            )
            if not result_data:
                logger.error(f'修改数据失败:{index_name}中file_id={update_model.file_id}并没有查询到数据')
                continue
            doc_id_list = [source_data["_id"] for source_data in result_data["hits"]["hits"]]
            doc_id_dict = {source_data["_id"]: str(source_data["_source"]["metadata"]["file_id"]) for source_data in result_data["hits"]["hits"]}
            update_model.pk = doc_id_list
            actions = update_pro_sql(es, update_model, index_name, doc_id_dict=doc_id_dict)
    if actions:
        try:
            helpers.bulk(es, actions, refresh=True)
            return BaseResponse(code=200, msg=f'修改数据成功')
        except helpers.BulkIndexError as e:
            return BaseResponse(code=500, msg=f'修改数据失败:{e.errors}')
    else:
        log_re = update_model.file_id or update_model.pk
        return BaseResponse(code=200, msg=f'修改数据失败,{update_model.index_name} 表不存在或者这些表中不存在{log_re or update_model.update_condition_json}的数据')


def del_by_id(del_model: DeleteParamModel):
    # logger.info(f"参数：{str(del_model.json())}")
    try:
        pk_list = del_model.pk_list
        index_name = is_index_lower(del_model.index_name)
        es = return_nacos_model().es_client()
        query_param = query_es_sql(index_name, "", pk_list, QueryType.PK)
        logger.info(query_param)
        delete_body = {'query': query_param}
        response = es.delete_by_query(index=index_name, body=delete_body, refresh=True)
        logger.info(f'删除数据成功:共删除{response["deleted"]}条数据')
        return BaseResponse(code=200, msg=f'删除数据成功:共删除{response["deleted"]}条数据')
    except Exception as e:
        logger.error(f'删除数据失败:{e}')
        return BaseResponse(code=500, msg=f'删除数据失败:{e}')


def delete_by_col_documents(operate_data: OperateDataModel) -> BaseResponse:
    """
    根据条件删除数据。

    Args:
        operate_data:OperateDataModel
    Returns:
        BaseResponse对象
    """
    # logger.info(f"参数：{operate_data.json()}")
    es = return_nacos_model().es_client()
    index_name = is_index_lower(operate_data.index_name)
    
    # 检查索引是否存在
    if not is_index(index_name):
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
            response = es.delete_by_query(index=index_name, body=delete_body, refresh=True)
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


def search_by_document_id(query_data: QueryDataModel) -> BaseResponse:
    """
    根据document_id查询数据。

    Args:
        query_data:QueryDataModel
    Returns:
        BaseResponse对象
    Notes：
        该接口仅支持根据document_id查询数据
    """
    # logger.info(f"参数：{query_data.json()}")
    es = return_nacos_model().es_client()
    server_config = return_nacos_model().get_config()["es_conn_config"]
    index_name = is_index_lower(query_data.index_name)
    query_body = {
        'query': {
            'terms': {
                'metadata.document_id.keyword': query_data.document_id
            }
        }, "size": server_config["vector_search_top_k"]
    }
    try:
        response = es.search(index=index_name, body=query_body)
        data_list = response["hits"]["hits"]
        # logger.info(f'查询成功:' + str(data_list))
        return BaseResponse(code=200, msg=f'查询成功', data={"result_data": data_list})
    except Exception as ex:
        logger.error(f'{index_name}查询失败,{ex}')
        return BaseResponse(code=500, msg=f'{index_name}查询失败,{ex}')


def search_by_page(param_query: QueryParamModel) -> BaseResponse:
    """
    根据自定义的body分页查询数据。

    Args:
        param_query:QueryParamModel
    Returns:
        BaseResponse对象
    Notes:
        query_body:自定义的body。 e.g:{"query": {"match": {"page_content": "query"}}, "size": 3}
    """
    # logger.info(f"参数：{param_query.json()}")
    index_name = is_index_lower(param_query.index_name)
    es = return_nacos_model().es_client()
    from_ = (param_query.page_no - 1) * param_query.page_num
    is_index_name = [idx for idx in index_name if is_index(idx)]
    if not is_index_name:
        return BaseResponse(code=200, msg=f'{index_name}不存在')
    if param_query.col_name:
        try:
            query_param = query_field_sql(is_index_name[0], param_query.col_name, param_query.col_values, param_query.condition_logic_operations)
        except Exception as ex:
            logger.error(f'{is_index_name}查询失败,{ex}')
            return BaseResponse(code=500, msg=f'{is_index_name}查询失败,{ex}')
    elif param_query.condition_json:
        must_clauses = []
        for cj_dict in param_query.condition_json:
            for key, value in cj_dict.items():
                try:
                    query_param = query_field_sql(is_index_name[0], key, value, param_query.condition_logic_operations)
                except Exception as ex:
                    logger.error(f'{is_index_name}查询失败,{ex}')
                    return BaseResponse(code=500, msg=f'{is_index_name}查询失败,{ex}')
                must_clauses.extend(query_param)

        if param_query.condition_logic_operations == "and":
            query_param = {
                "bool": {
                    "must": must_clauses
                }
            }
        else:
            if not param_query.document_id:
                query_param = {
                    "bool": {
                        "should": must_clauses,
                    }
                }
            else:
                full_clauses = [{
                    "bool": {
                        "should": must_clauses,
                    }
                }]
                full_clauses.extend([{"term": {"metadata.document_id.keyword": f"{param_query.document_id}"}}])
                query_param = {
                    "bool": {
                        "must": full_clauses,
                    }
                }
    else:
        query_param = {"match_all": {}}
        if param_query.document_id:
            query_param = {"term": {"metadata.document_id.keyword": f"{param_query.document_id}"}}
    init_query_body = {
        "query": query_param,
        "sort": [sort_field_sql(is_index_name[0], param_query.sort_field, param_query.sort_mode)],
        "from": from_,
        "size": param_query.page_num
    }
    query_body = param_query.query_body or init_query_body
    if query_body['sort'] == [{'metadata.chunk_index.keyword': {'order': 'asc'}}]:
        query_body['sort'] = {
            "_script": {
                "type": "number",
                "script":
                    {
                        "lang": "painless",
                        "source": "Integer.parseInt(doc['metadata.chunk_index.keyword'].value)"
                    },
                "order": "asc"
            }
        }
        query_body['sort'] = {
            "_script": {
                "type": "number",
                "script":
                    {
                        "lang": "painless",
                        "source": "Integer.parseInt(doc['metadata.chunk_index.keyword'].value)"
                    },
                "order": "asc"
            }
        }
    try:
        response = es.search(index=','.join(is_index_name), body=query_body)
        data_list = response["hits"]["hits"]
        if param_query.sort_mode == "desc":
            data_list = sorted(data_list, key=lambda x: x["_source"]["metadata"][param_query.sort_field], reverse=True)
        else:
            data_list = sorted(data_list, key=lambda x: x["_source"]["metadata"][param_query.sort_field])
        if param_query.sort_field == "offset":
            data_list = sorted(data_list, key=lambda x: sort_key(x))
        # logger.info(f'查询成功,total_count:{response["hits"]["total"]["value"]}')
        return BaseResponse(code=200, msg=f'查询成功', data={"total_count": response['hits']['total']['value'], 'result_data': data_list})
    except Exception as ex:
        logger.error(f'{is_index_name}查询失败,{ex}')
        return BaseResponse(code=500, msg=f'{is_index_name}查询失败,{ex}')


def sort_key(parsed_text):
    offset = parsed_text["_source"]["metadata"]["offset"]
    return [offset[0][0], offset[-1][-1]]


def search_by_custom_param(param_query: QueryParamModel) -> BaseResponse:
    """
    查询所有数据。

    Args:
        param_query:QueryParamModel
    Returns:
        BaseResponse对象
    Notes:
        query_body:自定义的body。 e.g:{"query": {"match": {"page_content": "query"}}, "size": 3}
    """
    # logger.info(f"参数：{str(param_query.json())}")
    index_list = []
    for name in param_query.index_name:
        name = is_index_lower(name)
        if is_index(name):
            index_list.append(name)
    if index_list:
        es = return_nacos_model().es_client()
        order_sql = [{"_score": {"order": "desc"}}, sort_field_sql(index_list[0], param_query.sort_field, param_query.sort_mode)]
        if param_query.query_body:
            query_body = param_query.query_body
            query_body["sort"] = order_sql
        else:
            query_param = {"query": {"match_all": {}}}
            if param_query.col_name:
                query_param = {"query": {'terms': {f'metadata.{param_query.col_name}.keyword': param_query.col_values}}}
            query_body = {**query_param, "sort": order_sql}
        try:
            if param_query.query_body:
                response = es.search(index=','.join(index_list), body=query_body)
                all_docs = response['hits']['hits']
            else:
                response = es.search(index=','.join(index_list), body=query_body, scroll='2m', size=500)
                all_docs = response['hits']['hits']
                scroll_id = response['_scroll_id']
                while len(response['hits']['hits']) > 0:
                    response = es.scroll(scroll_id=scroll_id, scroll='2m')
                    all_docs.extend(response['hits']['hits'])
            # logger.info(f'查询成功,total_count:{response["hits"]["total"]["value"]}')
            return BaseResponse(code=200, msg=f'查询成功', data={"total_count": response['hits']['total']["value"], "result_data": all_docs})
        except Exception as ex:
            logger.error(f'{param_query.index_name}查询失败,{ex}')
            return BaseResponse(code=500, msg=f'{param_query.index_name}查询失败,{ex}')
    else:
        # logger.error(f'{param_query.index_name}查询失败,index不存在')
        return BaseResponse(code=500, msg=f'{param_query.index_name}查询失败,index不存在')


def create_query(query, k):
    return {"query": {"match": {"page_content": query}}, "size": k}


def static_count(static_param) -> BaseResponse:
    """[R12-ADAPT-ALG-07] 全文侧文档计数（Java 契约要求，上游源码缺失）

    语义与向量服务 /static_count 对齐（返回 data.count），但口径改用 ES `_count`：
    向量侧用的是 `num_entities`，会漏掉尚未 flush 的段（R12 实测出现过 0 vs 1 的差异）。
    索引不存在时不报错、按 0 计（避免 Java 统计空知识库时拿到 500），并在 data.detail 里给出每索引明细。
    """
    names = static_param.index_name
    if isinstance(names, str):
        names = [names]
    es = return_nacos_model().es_client()
    total = 0
    detail = {}
    for name in names:
        index_name = is_index_lower(name)
        if not is_index(index_name):
            detail[index_name] = None          # None = 索引不存在（与"存在但 0 条"区分开）
            continue
        try:
            if static_param.col_name:
                body = {"query": {"terms": {f"metadata.{static_param.col_name}.keyword": static_param.col_values}}}
                resp = es.count(index=index_name, body=body)
            else:
                resp = es.count(index=index_name)
            detail[index_name] = resp["count"]
            total += resp["count"]
        except Exception as ex:
            logger.error(f'{index_name}统计失败,{ex}')
            return BaseResponse(code=500, msg=f'{index_name}统计失败,{ex}')
    return BaseResponse(code=200, msg='成功查询数据', data={"count": total, "detail": detail})

# def get_retriever_documents(index_name, query: str, k=server_config["vector_search_top_k"]) -> BaseResponse:
#     """
#     通过langchain提供方法查询数据。
#
#     Args:
#         index_name:索引名称。
#         query:查询str。
#         k:返回条数。
#     Returns:
#         BaseResponse对象
#     Notes：
#         效果跟search_by_custom_param一样，所以暂时不提供
#     """
#     # 创建 ElasticsearchRetriever 实例，指定 content_field
#     try:
#         es_retriever = ElasticsearchRetriever(
#             es_client=es,
#             index_name=is_index_lower(index_name),
#             body_func=lambda query: create_query(query, k),
#             content_field="page_content"  # 指定 content_field
#         )
#         document_list = es_retriever.get_relevant_documents(query)
#         data_list = [{"page_content": dl.page_content, "metadata": dl.metadata} for dl in document_list]
#         return BaseResponse(code=200, msg=f'查询成功', data={"result_data": data_list})
#     except Exception as ex:
#         return BaseResponse(code=500, msg=f'{index_name}查询失败,{ex}')
