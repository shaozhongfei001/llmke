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
    # R15 W03 / F05：代次（V0/V1…）。契约把 generation 列为 required，
    # 但实现此前完全没有这一维，导致新旧文档的实体/关系混在同一张图里、
    # 无法按代次回滚或审计。默认空串表示"未标注"，行为与旧版本一致。
    generation: str = ""


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
    # R14-LIVE-15：默认值必须是"未指定"，不能是通用 NER 8 类。
    # 原实现把 8 类写死在模型字段上，导致 graph_service._resolve_entity_types 里
    # "请求为空 -> 升级为业务类型表" 的分支**永远走不到**（请求永远看起来带了类型）。
    # 实测日志：抽取类型表（source=request）：['人','机构','位置','时间','角色','疾病','药品','项目']
    # 一个贷款产品知识库里出现"疾病/药品"这种类型，模型只能把业务实体判成"未分类"或被过滤。
    entity_types: Optional[List[str]] = None


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
