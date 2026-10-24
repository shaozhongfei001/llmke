#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/31 10:04
# @Author  : yuxj
# @File    : base.py
import os
import sys
from typing import List, Dict, Any

import pydantic
from pydantic import BaseModel

from milvus_kb_config import MILVUS_FIELDS
from utils import get_config, return_nacos_model

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

server_config = get_config()["milvus_conn_config"]
embedding_model = get_config()["embedding_model"]


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


class DataBaseModel(BaseModel):
    db_name: str = server_config["milvus_database"]


class EmbeddingModelInfo(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: str
    model_name: str
    url: str
    key: str
    dim: int
    max_tokens: int


class DatabaseConfigModel(DataBaseModel):
    model_config = {"protected_namespaces": ()}
    collection_name: str
    vector_field_name: str = 'vector'
    vector_mapping_body: dict = None
    model_name: str = None


class InsertDataModel(DataBaseModel):
    model_config = {"protected_namespaces": ()}
    embedding_model_info: EmbeddingModelInfo = None
    model_name: str = embedding_model
    collection_name: str
    document_list: List[Dict]
    consistency_level: str = 'Bounded'
    duplicate_flag: bool = True


class QueryDataModel(DataBaseModel):
    model_config = {"protected_namespaces": ()}

    query: str
    collection_name: List[str]
    model_name: str = embedding_model
    top_k: int = server_config["vector_search_top_k"]
    search_param: str = ""
    search_config: dict = server_config["milvus_kwargs"]["search_params"]
    cec_query_condition: dict = {}


class UpdateParamModel(DataBaseModel):
    model_config = {"protected_namespaces": ()}

    index_name: str
    model_name: str = embedding_model
    document_list: List[Dict]


class UpdateColModel(DataBaseModel):
    index_name: str
    pk: List[int] = []
    file_id: List[str] = []
    col_name: str = ""
    col_value: object = ""
    update_condition_json: Dict = {}  # {39640440551662867: {"chunk_pk_list": [1]}, 54422798307062028: {"chunk_pk_list": [2]}}


class UpdateBatchModel(DataBaseModel):
    index_name: str
    update_file_name: str = 'pk'
    update_condition_json: Dict = {}  # {39640440551662867: {"labels": [1]}, 54422798307062028: {"labels": [2]}}


class DataParamModel(DataBaseModel):
    collection_name: str = ""
    collection_name_list: List[str] = []
    expr: str = ''
    col_name: str = ''
    col_values: List = []
    condition_json: List[dict] = []
    page_no: int = 1
    page_num: int = 500


class MigrateCollectionModel(DataBaseModel):
    origin_collection: str
    target_collection: str
    filter: Dict = {}
    batch_size: int = 2000
