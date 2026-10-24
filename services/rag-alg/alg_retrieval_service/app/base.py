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

from app.utils import get_config

server_config = get_config()

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


class CECRetrieveConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    query: str = ""
    query_list: List[str] = []
    query_enrich: bool = True
    model_name: str = server_config["default_model_name"]
    model_info: dict = {"key": "", "model_id": "deepseekr1-qwen", "model_name": "deepseek-distill-qwen32b",
                        "url": "http://10.15.12.11:9982/v1/chat/completions"}
    rerank_model_info: dict = {}
    knowledge_base_name: List[str]
    enabled_es: bool = True
    enabled_milvus: bool = True
    enabled_faq: bool = False
    rerank: bool = True
    score_threshold: float = server_config["score_threshold"]
    top_k: int = 2
    top_n: int = 5  # rerank返回条数
    retrieval_top_k: int = 5
    enabled_summary: bool = False
    kb_file_list: dict = {}
    es_threshold: float = 0.6
    milvus_threshold: float = 0.5
class CECTableRetrieveConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    query: str = ""
    query_list: List[str] = []
    query_indicators: List[dict] = []
    query_enrich: bool = True
    model_name: str = server_config["default_model_name"]
    model_info: dict = {"key": "", "model_id": "deepseekr1-qwen", "model_name": "deepseek-distill-qwen32b",
                        "url": "http://10.15.12.11:9982/v1/chat/completions"}
    rerank_model_info: dict = {}
    knowledge_base_name: List[str]
    enabled_es: bool = True
    enabled_milvus: bool = True
    enabled_faq: bool = False
    rerank: bool = True
    score_threshold: float = server_config["score_threshold"]
    top_k: int = 2
    top_n: int = 5  # rerank返回条数
    retrieval_top_k: int = 5
    enabled_summary: bool = False
    kb_file_list: dict = {}
    es_threshold: float = 0.6
    milvus_threshold: float = 0.5

class QARetrieveConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    query: str
    rewritten_query: str = ""
    query_enrich: bool = False
    rerank_model_info: dict = {}  # 服务端传递，如果是空则去nacos 找默认  "model_name": "bge-reranker-v2-m3_xinference", "url": "http://10.15.12.11:9982/v1/rerank"
    dense_weight: float = 0.5  # 检索权重，0-0.5偏向语义检索结果（es），0.5-1 偏向向量检索结果（milvus）
    model_info: dict = {}  # "key": "", "model_id": "deepseekr1-qwen", "model_name": "deepseek-distill-qwen32b","url": "http://10.15.12.11:9982/v1/chat/completions"
    knowledge_base_name: List[str]
    database_name: List[str] = []
    enabled_rerank: bool = True
    enabled_faq: bool = True
    condition_json: dict = {}  # {"title":["国家金融监督管理总局发布《固定资产贷款管理办法》.pdf"]}
    condition_logic_operations: str = 'and'  # 条件运算
    score_threshold: float = server_config["score_threshold"]
    faq_score_threshold: float = 0.3
    search_policy: int = 1  # 1.混合检索(默认) ，2.文本检索(es), 3. 语义检索(milvus)
    top_k: int = 10
    top_n: int = 10  # rerank返回条数
    enabled_graph: bool = False
    enabled_table_select: bool = False  # 表格筛选
    multi_version_dict: dict = {}
    simi_top_k: int = 1
    enable_web_search: bool = False  # 是否开启联网搜索
    adjacent_chunk_num: int = 0 # 拼接邻近文本片数量
    enable_database: bool = False  # 是否开启数据库查询

class WebSearchResult(BaseModel):
    """搜索结果数据结构"""
    type: str = pydantic.Field(..., description="标签")
    page_content: str = pydantic.Field(..., description="网页内容")
    metadata: dict = {}
    order_num: str
    offset: List[str] = []
    pic_url_list: List[str] = []

class DataBaseResult(BaseModel):
    """搜索结果数据结构"""
    type: str = pydantic.Field(..., description="标签")
    page_content: str = pydantic.Field(..., description="数据库内容")
    metadata: dict = {}
    order_num: str
    offset: List[str] = []
    pic_url_list: List[str] = []