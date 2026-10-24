#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/31 10:04
# @Author  : yuxj
# @File    : base.py
import os
import sys
from typing import Any, List, Dict, Union

import pydantic
from pydantic import BaseModel, model_validator

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

    # [R12-ADAPT-ALG-08] 结构校验前置到入口，避免脏 payload 变成不透明的 500。
    # 背景（R12 实测）：传入 {"index_name":..., "type":"text", "document_list":[{"id":..,"content_with_weight":..,"source":..}]}
    # 会在 controller/es.py:169 抛 KeyError: 'metadata' → 500 Internal Server Error，
    # 调用方拿不到任何"缺哪个字段"的信息。契约要求每条文档是 {"page_content": str, "metadata": dict}。
    # 注意：type == "database" 走的是另一套结构（columns 等），不做此校验。
    @model_validator(mode="after")
    def _validate_document_shape(self):
        if self.type == "database":
            return self
        for idx, doc in enumerate(self.document_list):
            ok = isinstance(doc, dict) and isinstance(doc.get("page_content"), str) and isinstance(doc.get("metadata"), dict)
            if not ok:
                keys = list(doc.keys()) if isinstance(doc, dict) else type(doc).__name__
                raise ValueError(
                    f"document_list[{idx}] 结构不合法：每条必须是 {{\"page_content\": str, \"metadata\": object}}，"
                    f"实际 keys={keys}。若你用的是 {{id, content_with_weight, source}} 这类自定义结构，"
                    f"请在调用侧转换为 page_content + metadata 后再提交"
                )
        return self


class OperateDataModel(IndexModel):
    condition_logic_operations: str = 'and'
    col_name: str = ""
    col_values: List[str] = []
    condition_json: List[dict] = []


class StaticCountModel(BaseModel):
    """[R12-ADAPT-ALG-07] 全文侧 /static_count 入参。

    TL 下发的 Java 契约里 19527 需要提供 /static_count（Java 配置 remote.faq-count.url 指向
    19527/static_count），但上游源码的全文服务没有这个路由（只有向量服务有），实测 404。
    为兼容调用方两种写法，index_name 同时接受字符串与字符串数组；未识别的多余字段按 pydantic 默认忽略。
    """
    index_name: Union[str, List[str]]
    col_name: str = ""
    col_values: List[str] = []


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
