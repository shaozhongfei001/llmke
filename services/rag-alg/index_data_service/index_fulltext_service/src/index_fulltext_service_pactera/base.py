#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/31 10:04
# @Author  : yuxj
# @File    : base.py
import os
import sys
from typing import Any, List, Dict

import pydantic
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from es_kb_config import ES_INDEX_MAPPING


class BaseResponse(BaseModel):
    code: int = pydantic.Field(200, description="API status code")
    msg: str = pydantic.Field("success", description="API status message")
    data: Any = pydantic.Field(None, description="API data")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
            }
        }


class IndexModel(BaseModel):
    index_name: str


class CreateIndexModel(IndexModel):
    mapping_body: dict = ES_INDEX_MAPPING


class InsertDataModel(IndexModel):
    document_list: List[Dict]
    type: str = ""
    duplicate_flag: bool = True


class OperateDataModel(IndexModel):
    condition_logic_operations: str = 'and'
    col_name: str = ""
    col_values: List[str] = []
    condition_json: List[dict] = []


class QueryDataModel(IndexModel):
    document_id: List[str]


class QueryParamModel(BaseModel):
    index_name: List[str]
    query_body: dict = {}
    col_name: str = ''
    col_values: List[str] = ['']
    condition_json: List[dict] = []
    document_id: str = ""
    condition_logic_operations: str = 'and'
    page_no: int = 1
    page_num: int = 500
    sort_field: str = 'update_time'
    sort_mode: str = 'desc'


class UpdateParamModel(BaseModel):
    index_name: str
    document_list: List[Dict]


class UpdateColModel(BaseModel):
    index_name: str
    pk: List = []
    file_id: List = []
    col_name: str = ""
    col_value: object = ""
    update_condition_json: Dict = {}  # {39640440551662867: {"labels": [1]}, 54422798307062028: {"labels": [2]}}


class DeleteParamModel(BaseModel):
    index_name: str
    pk_list: List[str]
