#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: es_query.py  
Time: 2025/12/22 11:28  
"""
from controller.query_type import QueryType


def init_field_body(field, value, queryType: QueryType):
    if (isinstance(value, str)):
        t = "term"
    else:
        t = "terms"
    if queryType != QueryType.PK:
        f = f"metadata.{field}.keyword"
    else:
        f = "_id"
    k = {t: {f: value}}
    return k


def query_es_sql(index, field, value, queryType: QueryType):
    sub_sql = init_field_body(field, value, queryType)
    return sub_sql
