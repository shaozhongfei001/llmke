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
from datetime import datetime, timedelta

import requests
# 连接到 Milvus 服务
from elasticsearch import Elasticsearch

milvus_database = "rag_knowledge_base"
host = "10.15.12.13"
port = 19527
es_conn = Elasticsearch([{'host': host, 'port': 9200, 'scheme': "http"}], basic_auth=("elastic", "gientech"), verify_certs=False)


def get_all_index():
    indices = es_conn.cat.indices(h='index', s='index', format='json')
    index_name_list = indices.body
    # index_name_list = [il["index"] for il in index_name_list if il["index"].startswith('faq_')]
    index_name_list = [il["index"] for il in index_name_list]
    return index_name_list


def del_create_index(index_name):
    # del
    es_url = 'http://' + host + ':' + str(port) + '/'
    data = {
        "index_name": index_name,
    }
    response_del = requests.post(es_url + 'del_index', json=data)
    if response_del.json()["code"] == 200:
        # create
        data = {
            "index_name": index_name,
        }
        response_create = requests.post(es_url + 'create_es_index', json=data)
        if response_create.json()["code"] == 200:
            return True, "msg"
        else:
            return False, response_create.text
    else:
        return False, response_del.text


def get_document_chunk(index_name):
    """
    查询chunk数据
    Args:
        query_docu:
        server_config:

    Returns:

    """
    es_documents = []
    index_name = [index_name]
    data = {
        "index_name": index_name
    }
    es_url = 'http://' + host + ':' + str(port) + '/'
    response = requests.post(es_url + 'search_by_custom_param', json=data)
    try:
        if response.status_code == 200:
            try:
                es_data = response.json()['data']['result_data']
            except Exception as e:
                print("es:", e)
                return es_documents
        else:
            print(response.text)
            return es_documents
    except Exception as e:
        print("es:", e)
        return es_documents
    data_dict_list = [ed["_source"] for ed in es_data]
    return data_dict_list


def faq_add_question(index_name, res_list):
    success_flag, msg = del_create_index(index_name)
    if not success_flag:
        print(msg)
    else:
        pred_dict_list = []
        for rl in res_list:
            new_dict = {}
            if "answer" not in rl["metadata"].keys() or "question" in rl["metadata"].keys():
                continue
            new_dict["page_content"] = rl["page_content"] + "@@" + rl["metadata"]["answer"]
            new_dict["metadata"] = rl["metadata"]
            new_dict["metadata"]["question"] = rl["page_content"]
            pred_dict_list.append(new_dict)
        if pred_dict_list:
            es_url = 'http://' + host + ':' + str(port) + '/'
            es_data = {
                "index_name": index_name,
                "document_list": pred_dict_list
            }
            response_m = requests.post(es_url + 'insert_fulltext_documents', json=es_data)
            print(response_m.json())


def faq_type_va(index_name, res_list):
    success_flag, msg = del_create_index(index_name)
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
        if pred_dict_list:
            es_url = 'http://' + host + ':' + str(port) + '/'
            es_data = {
                "index_name": index_name,
                "document_list": pred_dict_list
            }
            response_m = requests.post(es_url + 'insert_fulltext_documents', json=es_data)
            print(response_m.json())


def del_data(index_name):
    settings = es_conn.indices.get_settings(index=index_name)
    count = es_conn.count(index=index_name)
    print(count["count"])
    creation_date_str = settings[index_name]['settings']['index']['creation_date']
    current_time = datetime.now()
    creation_date = datetime.fromtimestamp(int(creation_date_str) / 1000.0)  # 转换为
    time_difference = current_time - creation_date
    if ("test" in index_name or '测试' in index_name) and time_difference > timedelta(days=10):
        print(f'Index: {index_name} | Creation Date: {creation_date} | Older than 10 days')
        es_conn.indices.delete(index=index_name)
    elif count["count"] < 10 and time_difference > timedelta(days=10):
        print(f'Index: {index_name} | count: {count["count"]} | Older than 10 days')
        try:
            es_conn.indices.delete(index=index_name)
        except:
            print(f'Index: {index_name}')
    elif time_difference > timedelta(days=90):
        es_conn.indices.delete(index=index_name)
        print(f'Index: {index_name} | Creation Date: {creation_date} | Older than 90 days')
    else:
        print(f'Index: {index_name} | Creation Date: {creation_date}')


if __name__ == '__main__':
    # index_name_list = ["faq_wsAndy"] # 自定义数据
    index_name_list = get_all_index()  # 全部数据
    for inl in index_name_list:
        # res_list = get_document_chunk(inl)
        # faq_add_question(inl, res_list)
        # faq_type_va(inl, res_list)
        del_data(inl)
