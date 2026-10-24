#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/31 10:04
# @Author  : yuxj
# @File    : base.py
import os
import sys
from typing import Any, List, Optional

import pydantic
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


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


class GraphModel(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    space_name: str
    partition_num: int = 10
    replica_factor: int = 1


class GraphAttributeModel(GraphModel):
    model_config = {"protected_namespaces": ()}
    
    # "CREATE TAG IF NOT EXISTS person(name string, age int);"
    attribute_type: str  # TAG or EDGE
    field_name: str = 'entity'
    # field_dict = {"field_name":"name","field_type":"string"}
    field_dict: dict = {}


class InsertModel(GraphModel):
    model_config = {"protected_namespaces": ()}
    
    # model_name: str
    vertex_name: str = 'entity'
    edge_name: str = 'relationship'
    triples_data: List[tuple]
    entity_attribute: dict
    triples_attribute: dict
    # similar_data: List[tuple] = None


class QueryDocChunk(GraphModel):
    model_config = {"protected_namespaces": ()}
    
    col_name: str = ''  # 条件查询 列
    col_values: List[str] = []  # 条件查询 值
    model_info: dict
    embed_model_name: str = "bge-large-zh-v1.5"  # nacos配置
    top_k: int = 30  # 生成三元组返回数量
    system_prompt: Optional[str] = None  # 默认的prompt
    entity_types: List[str] = ["人", "机构", "位置", "时间", "角色", "疾病", "药品", "项目"]


class QueryGraphData(GraphModel):
    model_config = {"protected_namespaces": ()}
    
    query: str
    model_info: dict
    depth: int = 3
    alpha: float = 0.85
    query_type: str = "hippo"  # light
    embed_model_name: str = "bge-large-zh-v1.5"
    top_k: int = 15


class DelModel(GraphModel):
    model_config = {"protected_namespaces": ()}
    
    condition_json: dict = {}
