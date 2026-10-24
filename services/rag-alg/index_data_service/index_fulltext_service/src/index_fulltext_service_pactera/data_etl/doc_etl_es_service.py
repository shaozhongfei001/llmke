#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/14 13:42
# @Author  : yuxj
# @File    : doc_etl_es_service.py

# 与mysql 的知识库同步 ，  删除不再mysql中的知识库
from elasticsearch import Elasticsearch

host = "10.15.12.11"
port = 19527
es_conn = Elasticsearch([{'host': host, 'port': 9200, 'scheme': "http"}], basic_auth=("elastic", "gientech"), verify_certs=False)


def get_all_index():
    indices = es_conn.cat.indices(h='index', s='index', format='json')
    index_name_list = indices.body
    # index_name_list = [il["index"] for il in index_name_list if il["index"].startswith('faq_')]
    index_name_list = [il["index"] for il in index_name_list]
    return index_name_list


def read_index_name():
    new_index_list = []
    with open('11环境需要保留的知识库.txt', 'r', encoding='utf-8') as file:
        content = file.read()
        index_list = content.split("\n")
    for index in index_list:
        new_index_list.append(index)
        new_index_list.append("table_chunks_"+index)
        new_index_list.append("table_summary_" + index)
    return index_list


def mainStart():
    save_index_name_list = read_index_name()
    print(f"需要保存的index数量:{len(save_index_name_list)}")
    full_index_name_list = get_all_index()
    print(f"es现在共存在的es数量:{len(full_index_name_list)}")
    # for f_index in save_index_name_list:
    #     if f_index not in full_index_name_list:
    #         print(f_index)

    for f_index in full_index_name_list:
        if f_index not in save_index_name_list:
            try:
                print(f_index)
                es_conn.indices.delete(index=f_index)
            except Exception as e:
                print(e)
                continue
        else:
            print(f"{f_index}")


if __name__ == '__main__':
    mainStart()
