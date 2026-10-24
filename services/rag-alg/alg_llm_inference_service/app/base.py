#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/31 10:04
# @Author  : yuxj
# @File    : base.py

import os
import sys
from typing import Any, List, Optional

import pydantic
from pydantic import BaseModel, ConfigDict

from app.utils import get_config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
server_config = get_config()


class BaseResponse(BaseModel):
    code: int = pydantic.Field(200, description="API status code")
    msg: str = pydantic.Field("success", description="API status message")
    data: Any = pydantic.Field(None, description="API data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": 200,
                "msg": "success",
            }
        }
    )


class LLMBasicConfig(BaseModel):
    model_info: dict
    
    model_config = {"protected_namespaces": ()}


class TestModelInfoConfig(BaseModel):
    test_model_info: dict


class MultiModelConfig(BaseModel):
    multi_model_info: dict
    query: Optional[str] = None
    prompt_msg: Optional[List] = None
    stream: bool = True
    chat_history: Optional[List[dict]] = None
    max_tokens: int = server_config["max_tokens"]
    temperature: float = server_config["temperature"]
    file_paths: List[str] = []  # 附件，redis的参数


class LLMOpenChatConfig(LLMBasicConfig):
    query: Optional[str] = None
    rewritten_query: Optional[str] = None
    prompt_msg: Optional[List] = None
    documents: List = []
    web_documents_list: List = []
    table_selected_list: List = []
    database_documents: List = []
    table_result_data: dict = {}
    top_k: int = server_config.get("llm_top_k", 5)
    stream: bool = True
    top_p: float = 0.8
    chat_history: Optional[List[dict]] = None
    max_tokens: int = server_config.get("max_tokens", 2500)
    temperature: float = server_config.get("temperature", 1.0)
    system_prompt: Optional[str] = None
    reasoning_flag: bool = True
    file_paths: List[str] = []  # 附件，redis的参数
    single_text: dict = {}  # 单文本问答查询 {"knowledge_base_name":"","title":""}
    need_trace_source: bool = True
    trace_by_llm: bool = False
    is_return_prompt: bool = True  # 是否返回prompt
    max_context_length: int = server_config.get("rotate_answer", {}).get("max_char_length", 15000)
    enable_thinking: bool = True
    user_intro: str = ''
    use_user_intro: bool = False
    rerank_model_info: dict = {}  # 在规则溯源中使用


class FAQChatConfig(LLMBasicConfig):
    document_list: List = []
    top_k: int = 20
    to_database: bool = True
    max_context_length: int = server_config.get("rotate_answer", {}).get("max_char_length", 15000)


class FAQSelectConfig(LLMBasicConfig):
    query: Optional[str] = None
    documents: List = []
    top_k: int = server_config.get("faq_select_model", {}).get("top_k", 5)
    max_score: float = server_config.get("faq_select_model", {}).get("max_score", 1.0)
    min_score: float = server_config.get("faq_select_model", {}).get("min_score", 0.2)
    chat_history: Optional[List[dict]] = None
    system_prompt: str = ""

class SqlGenConfig(LLMBasicConfig):
    query: Optional[str] = None
    documents: List = []
    top_k: int = server_config["sql_gen_model"]["top_k"]
    max_score: float = server_config["sql_gen_model"]["max_score"]
    min_score: float = server_config["sql_gen_model"]["min_score"]
    chat_history: Optional[List[dict]] = None
    system_prompt: str = ""


class FAQSimiConfig(LLMBasicConfig):
    source_list: list[dict]
    gen_question_num: int = 4
    gen_k: int = 4


class QuestionRecommendConfig(LLMBasicConfig):
    query: str
    answer: str = ""
    chat_history: List[dict] = None
    enabled_faq: bool = True
    top_k: int = 3

class QuestionRewriteConfig(LLMBasicConfig):
    query: str
    chat_history: List[dict] = None
    user_intro: str = ''
    use_user_intro: bool = False
    max_context_length: int = server_config.get("rotate_answer", {}).get("max_char_length", 15000)