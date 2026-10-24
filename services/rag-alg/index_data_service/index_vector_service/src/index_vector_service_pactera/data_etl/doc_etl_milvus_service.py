#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/26 10:36
# @Author  : yuxj
# @File    : faq_etl_milvus_service.py
# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/12/26 09:41
# @Author  : yuxj
# @File    : faq_etl_milvus_service.py
from datetime import datetime

import requests, re, uuid
from pymilvus import connections, utility, Collection

from index_vector_service.src.index_vector_service_pactera.milvus_kb_config import MILVUS_FIELDS_FAQ, \
    MILVUS_FIELDS_TABLE_SUMMARY, MILVUS_FIELDS_TABLE_CHUNKS, MILVUS_FIELDS

# 连接到 Milvus 服务

# from index_vector_service_pactera.milvus_kb_config import MILVUS_FIELDS_FAQ, MILVUS_FIELDS, \
#     MILVUS_FIELDS_TABLE_SUMMARY, MILVUS_FIELDS_TABLE_CHUNKS

milvus_database = "rag_knowledge_base"
host = "10.15.12.11"
port = 19526
connections.connect(alias=milvus_database, host=host, port=19530, db_name=milvus_database)


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
    collection_name = "_" + collection_name.replace("-", "")
    return collection_name


def return_all_list_collections():
    #save_index_name_list = read_index_name()
    collection_list = utility.list_collections(using=milvus_database)
    # 打印集合列表
    new_collection_dict = {}
    for cl in collection_list:
        # 创建集合对象
        collection = Collection(cl, using=milvus_database)
        # 获取集合的元数据信息
        collection_info = collection.describe()
        description_name = collection_info["description"].split('集合名称：')[1]
        # if description_name not in save_index_name_list:
        #     try:
        #         collection = Collection(cl, using=milvus_database)
        #         collection.drop()
        #     except Exception as e:
        #         print(e)
        #         continue
        new_collection_dict[description_name] = cl
        # print(description_name)
        # elif "test" in description_name or '测试' in description_name:
        #     print(f"{description_name}的数量{total_count}________")
        # collection.drop()
    #     description_name = collection_info["description"].split('集合名称：')[1]
    #     if description_name.startswith('faq_'):
    #         collection_fields = collection_info["fields"]
    #         field_list = [cf["name"] for cf in collection_fields]
    #         if "question" not in field_list:
    #             new_collection_list.append(description_name)
    #     # 输出元数据信息
    print(len(new_collection_dict))
    return new_collection_dict


def time_cal(a):
    now = datetime.now()
    try:
        time_a = datetime.strptime(a, '%Y-%m-%d %H:%M:%S.%f')
    except:
        time_a = datetime.strptime(a, '%Y-%m-%d %H:%M:%S')
    # 计算相差的天数
    difference = (now - time_a).days
    return difference


def del_collection(index_name, res_list):
    collection_name_new = generate_collection_name_uuid(index_name)
    coll = Collection(collection_name_new, using=milvus_database)
    if res_list:
        if "create_time" not in res_list[0]["metadata"].keys():
            coll.drop()
            return
        data_list = sorted(res_list, key=lambda x: x["metadata"]["create_time"], reverse=True)
        create_time = data_list[0]["metadata"]["create_time"]
        if create_time:
            difference = time_cal(create_time)
            if ("test" in index_name or '测试' in index_name) and difference > 10:
                print(f'Index: {index_name} | Creation Date: {create_time} | Older than 10 days')
                coll.drop()
            elif difference > 90:
                coll.drop()
                print(f'Index: {index_name} | Creation Date: {create_time} | Older than 90 days')
        else:
            coll.drop()


def create_collection(collection_name, milvus_database, vector_mapping_body):
    milvus_url = 'http://' + host + ':' + str(port) + '/'
    data = {
        "db_name": milvus_database,
        "collection_name": collection_name,
        "vector_mapping_body": vector_mapping_body
    }
    response_coll = requests.post(milvus_url + 'create_milvus_collection', json=data)
    response_index = requests.post(milvus_url + 'create_milvus_index', json=data)
    if response_coll.json()["code"] == 200 and response_index.json()["code"] == 200:
        return True, "msg"
    else:
        return False, str(response_coll.text) + "||" + str(response_index.text)


def page_num_update(collection_name, res_list):
    # 先删除原表
    collection_name_new = generate_collection_name_uuid(collection_name)
    coll = Collection(collection_name_new, using=milvus_database)
    coll.drop()
    # 创建新的数据库
    vector_mapping_body = MILVUS_FIELDS
    success_flag, msg = create_collection(collection_name, milvus_database, vector_mapping_body)
    if not success_flag:
        print(msg)
    else:
        pred_dict_list = []
        for rl in res_list:
            new_dict = {}
            new_dict["page_content"] = rl["page_content"] + "@@" + rl["metadata"]["answer"]
            new_dict["metadata"] = rl["metadata"]
            new_dict["metadata"]["question"] = rl["page_content"]
            pred_dict_list.append(new_dict)
        milvus_url = 'http://' + host + ':' + str(port) + '/'
        milvus_data = {
            "collection_name": collection_name,
            "document_list": pred_dict_list
        }
        response_m = requests.post(milvus_url + 'insert_vector_documents_custom', json=milvus_data)
        print(response_m.json())


def insert_to_db(collection_name, pred_dict_list):
    milvus_url = 'http://' + host + ':' + str(port) + '/'
    milvus_data = {
        "collection_name": collection_name,
        "document_list": pred_dict_list
    }
    response_m = requests.post(milvus_url + 'insert_vector_documents_custom', json=milvus_data)
    return response_m


def labels_update(collection_name, collection_name_new, res_list):
    # 先删除原表
    coll = Collection(collection_name_new, using=milvus_database)
    coll.drop()
    # 创建新的数据库
    coll_name_low = collection_name.lower()
    if "faq_" in coll_name_low:
        vector_mapping_body = MILVUS_FIELDS_FAQ
    elif "table_summary_" in coll_name_low:
        vector_mapping_body = MILVUS_FIELDS_TABLE_SUMMARY
    elif "table_chunks_" in coll_name_low:
        vector_mapping_body = MILVUS_FIELDS_TABLE_CHUNKS
    else:
        vector_mapping_body = MILVUS_FIELDS
    success_flag, msg = create_collection(collection_name, milvus_database, vector_mapping_body)
    if not success_flag:
        print(msg)
    else:
        pred_dict_list = []
        for rl in res_list:
            new_dict = {}
            new_dict["page_content"] = rl["page_content"]
            new_dict["metadata"] = rl["metadata"]
            pred_dict_list.append(new_dict)
        response_m = insert_to_db(collection_name, pred_dict_list)
        print(response_m.json())


data_types = {
    "NONE": 0,
    "BOOL": 1,
    "INT8": 2,
    "INT16": 3,
    "INT32": 4,
    "INT64": 5,
    "FLOAT": 10,
    "DOUBLE": 11,
    "STRING": 20,
    "VARCHAR": 21,
    "ARRAY": 22,
    "JSON": 23,
    "BINARY_VECTOR": 100,
    "FLOAT_VECTOR": 101,
    "FLOAT16_VECTOR": 102,
    "BFLOAT16_VECTOR": 103,
    "SPARSE_FLOAT_VECTOR": 104,
    "UNKNOWN": 999
}


def read_index_name():
    new_index_list = []
    with open('11环境需要保留的知识库.txt', 'r', encoding='utf-8') as file:
        content = file.read()
        index_list = content.split("\n")
    for index in index_list:
        new_index_list.append(index)
        new_index_list.append("table_chunks_" + index)
        new_index_list.append("table_summary_" + index)
        new_index_list.append("faq_" + index)
    return new_index_list


def sync_mysql_kn(collection_name_dict):
    # check_substrings = {"测试", "ceshi", "test"}
    save_index_name_list = read_index_name()
    for c_name, t_c_name in collection_name_dict.items():
        if c_name not in save_index_name_list:
            try:
                collection = Collection(t_c_name, using=milvus_database)
                collection.drop()
            except Exception as e:
                print(e)
                continue


def del_schema_base(collection_name_dict):
    collection_list = utility.list_collections(using=milvus_database)
    # 打印集合列表
    new_collection_list = []
    for collection_name in collection_list:
        # 创建集合对象
        collection = Collection(collection_name, using=milvus_database)
        # 获取集合的元数据信息
        total_count = collection.num_entities
        collection_info = collection.describe()
        description_name = collection_info["description"].split('集合名称：')[1]
        fields = collection.schema.fields
        fields_type_dict = {f.name: f.dtype for f in fields if not f.name == "pk" or f.auto_id is False}
        i_name = [f.name for f in fields if not f.name == "pk" or f.auto_id is False]
        coll_name_low = description_name.lower()
        if "faq_" in coll_name_low:
            vector_mapping_body = MILVUS_FIELDS_FAQ
        # elif "graph_" in coll_name_low:
        #     vector_mapping_body = MILVUS_FIELDS_GRAPH
        elif "table_summary_" in coll_name_low:
            vector_mapping_body = MILVUS_FIELDS_TABLE_SUMMARY
        elif "table_chunks_" in coll_name_low:
            vector_mapping_body = MILVUS_FIELDS_TABLE_CHUNKS
        else:
            vector_mapping_body = MILVUS_FIELDS
        for field_name, params in vector_mapping_body.items():
            dtype = params["dtype"].replace("DataType.", '')
            if field_name not in i_name:
                print(f"知识库：{description_name},字段缺少{field_name}")
                collection.drop()
                break
            elif data_types[dtype] != fields_type_dict[field_name]:
                print(f"知识库：{description_name},类型错误：原{data_types[dtype]}，表中现：{fields_type_dict[field_name]}")
                collection.drop()
                break
        print(description_name)
        # print(f"留下保存的知识库{description_name}")
        # if data_types[dtype]


def query_es_data(knowledge_base_name):
    """
    查询chunk数据
    Args:
        query_field_value: 搜索条件的值， 默认是列名title
        knowledge_base_name:
        server_config:
    Returns:

    """
    es_documents = []
    data = {
        "index_name": [knowledge_base_name],
    }
    es_url = 'http://10.15.12.11:19527/'
    response = requests.post(es_url + 'search_by_custom_param', json=data)
    try:
        if response.status_code == 200:
            try:
                es_data = response.json()['data']['result_data']
                for ed in es_data:
                    es_documents.append({"page_content": ed['_source']['page_content'], "metadata": ed['_source']['metadata']})
            except Exception as e:
                return es_documents
        else:
            return es_documents
    except Exception as e:
        return es_documents
    es_documents = sorted(es_documents, key=lambda x: x['metadata']["chunk_index"])
    return es_documents


if __name__ == '__main__':
    # es 读取数据插入milvus
    #data_list = query_es_data("table_summary_潍坊银行演示")
    #insert_to_db("table_summary_潍坊银行演示", data_list)
    return_all_list_collections()
    #collection_name_dict = return_all_list_collections()
    #sync_mysql_kn(collection_name_dict)
    # del_schema_base(collection_name_dict)
    # for c_name, t_c_name in collection_name_dict.items():
    #     milvus_url = 'http://' + host + ':' + str(port) + '/'
    #     data = {
    #         "collection_name": c_name,
    #     }
    #     response = requests.post(milvus_url + 'get_doc_by_col', json=data)
    #     if response.json()["code"] != 200:
    #         print(str(response.text), c_name)
    #     else:
    #         res_list = response.json()["data"]["result_data"]
    #         # faq schema question
    #         # page_num_update(c_name, res_list)
    #         labels_update(c_name, t_c_name, res_list)
    #         # del_collection(c_name, res_list)
