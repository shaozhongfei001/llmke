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

import requests
from pymilvus import connections, utility, Collection

# 连接到 Milvus 服务
from milvus_kb_config import MILVUS_FIELDS_FAQ
from milvus_kb_service import generate_collection_name_uuid

milvus_database = "rag_knowledge_base"
host = "10.15.12.13"
port = 19526
connections.connect(alias=milvus_database, host=host, port=19530, db_name=milvus_database)


def return_all_list_collections():
    collection_list = utility.list_collections(using=milvus_database)
    # 打印集合列表
    new_collection_dict = {}
    for cl in collection_list:
        # 创建集合对象
        collection = Collection(cl, using=milvus_database)

        # 获取集合的元数据信息
        collection_info = collection.describe()
        description_name = collection_info["description"].split('集合名称：')[1]
        if description_name.startswith('faq_'):
            collection_fields = collection_info["fields"]
            field_list = [cf["name"] for cf in collection_fields]
            if "folder_id" not in field_list:
                new_collection_dict[description_name] = cl
        # 输出元数据信息
    print(len(new_collection_dict))
    return new_collection_dict


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


def faq_add_question(collection_name, res_list):
    # 先删除原表
    collection_name_new = generate_collection_name_uuid(collection_name)
    coll = Collection(collection_name_new, using=milvus_database)
    coll.drop()
    # 创建新的数据库
    vector_mapping_body = MILVUS_FIELDS_FAQ
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


def add_folder_id(collection_name, t_c_name, res_list):
    # 先删除原表
    coll = Collection(t_c_name, using=milvus_database)
    coll.drop()
    # 创建新的数据库
    vector_mapping_body = MILVUS_FIELDS_FAQ
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
        milvus_url = 'http://' + host + ':' + str(port) + '/'
        milvus_data = {
            "collection_name": collection_name,
            "document_list": pred_dict_list
        }
        response_m = requests.post(milvus_url + 'insert_vector_documents_custom', json=milvus_data)
        print(response_m.json())


def faq_type_va(collection_name, res_list):
    # 先删除原表
    collection_name_new = generate_collection_name_uuid(collection_name)
    coll = Collection(collection_name_new, using=milvus_database)
    coll.drop()
    # 创建新的数据库
    vector_mapping_body = MILVUS_FIELDS_FAQ
    success_flag, msg = create_collection(collection_name, milvus_database, vector_mapping_body)
    if not success_flag:
        print(msg)
    else:
        pred_dict_list = []
        for rl in res_list:
            new_dict = {}
            new_dict["page_content"] = rl["page_content"]
            new_dict["metadata"] = rl["metadata"]
            new_dict["metadata"]["faq_type"] = 1
            pred_dict_list.append(new_dict)
        milvus_url = 'http://' + host + ':' + str(port) + '/'
        milvus_data = {
            "collection_name": collection_name,
            "document_list": pred_dict_list
        }
        response_m = requests.post(milvus_url + 'insert_vector_documents_custom', json=milvus_data)
        print(response_m.json())


if __name__ == '__main__':
    # collection_name_list = ["faq_JBBtest001"]
    new_collection_dict = return_all_list_collections()
    for c_name, t_c_name in new_collection_dict.items():
        milvus_url = 'http://' + host + ':' + str(port) + '/'
        data = {
            "collection_name": c_name,
        }
        response = requests.post(milvus_url + 'get_doc_by_col', json=data)
        if response.json()["code"] != 200:
            print(str(response.text), c_name)
        else:
            res_list = response.json()["data"]["result_data"]
            # faq schema question
            # faq_add_question(collection_name, res_list)
            #  faq  type
            # faq_type_va(c_name, t_c_name, res_list)
            add_folder_id(c_name, t_c_name, res_list)
