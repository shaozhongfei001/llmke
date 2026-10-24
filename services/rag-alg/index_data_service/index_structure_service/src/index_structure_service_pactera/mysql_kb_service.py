#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/30 16:44
# @Author  : yuxj
# @File    : mysql_kb_service.py
from fastapi import APIRouter
from sqlalchemy import Table, Column, Integer, String, text, TIMESTAMP
import sys
import os

from utils import return_nacos_model

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base import BaseResponse, DeleteItem, DataModel, QueryModel, UpdateModel

crud_router = APIRouter()


def create_table(column_dict_list):
    """
    创建表的函数。

    Args:
        column_dict_list:创建表中的列名
    Returns:
        return_true_list：创建成功的列表
        return_failed_list:创建失败的列表
    Notes：

    """
    metadata = return_nacos_model().mysql_metadata()
    engine = return_nacos_model().mysql_engine()
    return_true_list = []
    return_failed_list = []
    for tc in column_dict_list:
        for table_name, column_list in tc.items():
            columns = [
                Column("id", Integer, primary_key=True, index=True),
                Column("create_time", TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
            ]
            for cl in column_list:
                columns.append(Column(cl, String(255)))
            Table(table_name, metadata, *columns,
                  extend_existing=True)  # extend_existing=True： 重新定义表结构，只能扩展，不能删除列，不会删除数据
            try:
                metadata.create_all(engine)
                return_true_list.append(table_name)
            except:
                return_failed_list.append(table_name)
    return return_true_list, return_failed_list


def process_structure(item):
    """
    处理数据结构。
    Args:
        item:数据
    Returns:
        table_dict：{表名:列名}
    Notes：

    """
    fields = []
    table_info = item["table"][0]
    metadata_info = item["metadata"]
    table_name = metadata_info["table_name"]
    del metadata_info["table_name"]
    fields.extend(table_info.keys())
    fields.extend(metadata_info.keys())
    table_dict = {table_name: fields}
    return table_dict


def create_table_endpoint(data_model: DataModel) -> BaseResponse:
    """
    创建表的接口函数。
    Args:
        data_model:DataModel数据对象
    Returns:
        BaseResponse对象
    Notes：
        数据结构[{"table_name":["col1","col2","col3"]}]
    """
    try:
        return_true_list, return_failed_list = create_table(data_model.data_list)
        return BaseResponse(code=200, msg=f'创建成功',
                            data={"success_table": {"table_name": return_true_list},
                                  "failed_table": {"table_name": return_failed_list}})
    except Exception as ex:
        return BaseResponse(code=500, msg=f'创建失败,{ex}')


def select_item(query_model: QueryModel) -> BaseResponse:
    """
    查询接口函数。
    Args:
        query_model:QueryModel查询对象
        db:Session对象，获取查询链接
    Returns:
        BaseResponse对象，data：返回List[Dict]
    Notes：
        通过自定义的sql查询数据
    """
    db = return_nacos_model().mysql_client()
    try:
        result = db.execute(text(query_model.query_sql))
        # 获取列名
        columns = result.keys()
        # 将结果转换为字典列表
        result_dicts = [dict(zip(columns, row)) for row in result.fetchall()]
        return BaseResponse(code=200, msg=f'查询成功',
                            data={"result_data": result_dicts})
    except Exception as ex:
        return BaseResponse(code=500, msg=f'查询失败,{ex}')


def insert_item(data_model: DataModel) -> BaseResponse:
    """
    保存数据接口函数。
    Args:
        data_model:DataModel数据对象
        db:Session对象，获取查询链接
    Returns:
        BaseResponse对象
    Notes：
        通过自定义的sql查询数据
    """
    db = return_nacos_model().mysql_client()
    engine = return_nacos_model().mysql_engine()
    metadata = return_nacos_model().mysql_metadata()
    # inspector = inspect(engine)
    table_name = data_model.table_name
    insert_data_list = []
    table = Table(table_name, metadata, autoload_with=engine)
    for item in data_model.data_list:
        # table_data_list = item["table"]
        # count += len(table_data_list)
        # metadata_info = item["metadata"]
        # table_name = item["metadata"]["table_name"]
        # # 检查表是否存在,如果不存在，则创建表
        # if not inspector.has_table(table_name):
        #     column_dict_list = [process_structure(item)]
        #     create_table(column_dict_list)
        m_columns = table.columns.keys()
        data_keys = list(item.keys())
        for tk in data_keys:
            if tk not in m_columns:
                data_keys.remove(tk)
        insert_data_list.append(item)
    try:
        insert_stmt = table.insert()
        db.execute(insert_stmt, insert_data_list)
        db.commit()
        return BaseResponse(code=200, msg=f'保存成功，表{table_name}共保存了{len(insert_data_list)}条数据')
    except Exception as e:
        return BaseResponse(code=500, msg=f'保存失败，{e}')


def update_item(update_model: UpdateModel):
    db = return_nacos_model().mysql_client()
    try:
        db.execute(update_model.update_sql)
        db.commit()
        return BaseResponse(code=200, msg=f'修改成功')
    except Exception as ex:
        return BaseResponse(code=500, msg=f'修改失败,{ex}')


def delete_item(del_item: DeleteItem) -> BaseResponse:
    """
    保存数据接口函数。
    Args:
        del_item:DeleteItem删除对象
        db:Session对象，获取查询链接
    Returns:
        BaseResponse对象
    Notes：
        通过自定义的列删除数据
    """
    db = return_nacos_model().mysql_client()
    joined_col_value = ', '.join(f'"{va}"' for va in del_item.col_values)
    sql = f"DELETE FROM {del_item.table_name} WHERE {del_item.col_name} IN ({joined_col_value});"
    try:
        db.execute(text(sql))
        db.commit()
        return BaseResponse(code=200, msg=f'删除成功')
    except Exception as ex:
        return BaseResponse(code=500, msg=f'删除失败,{ex}')
