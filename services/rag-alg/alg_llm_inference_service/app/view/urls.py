#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: urls.py  
Time: 2025/9/18 14:40  
"""
from fastapi import FastAPI

from app.view.api.llm_check_model_view import LLMCheckModelView
from app.view.api.llm_faq_generate_view import LLMFAQGenerateView
from app.view.api.llm_faq_select_view import LLMFAQSelectView
from app.view.api.llm_generate_sync_view import LLMGenerateSyncView
from app.view.api.llm_multi_model_view import LLMMultiModelView
from app.view.api.llm_open_chat_view import LLMOpenChatView
from app.view.api.llm_question_prompt_view import LLMQuestionPromptView
from app.view.api.llm_question_recommend_view import LLMQuestionRecommendView
from app.view.api.llm_question_rewrite_view import LLMQuestionRewriteView
from app.view.api.llm_rotate_answer_view import LLMRotateAnswerView
from app.view.api.llm_simi_question_view import LLMSimiQuestionView
from app.view.api.llm_sql_generate_view import LLMSQLGenerateView
from app.view.api.polish_answer_llm_view import PolishAnswerLLMView
from app.view.api.connectivity_test_view import ConnectivityTestView

LLMOpenChatView(path="/llm_open_chat", tags=["llm_open_chat"], summary="通过线上大模型回答问题")
LLMFAQGenerateView(path="/llm_faq_generate", tags=["llm_faq_generate"], summary="通过线上大模型生成FAQ问题")
LLMGenerateSyncView(path="/llm_generate_sync", tags=["llm_generate"], summary="同步请求")
LLMSQLGenerateView(path="/llm_sql_generate", tags=["llm_sql_generate"], summary="大模型生成sql")
PolishAnswerLLMView(path="/polish_answer_llm", tags=["polish_answer_llm"], summary="对faq答案进行润色")
LLMFAQSelectView(path="/llm_faq_select", tags=["llm_faq_select"], summary="大模型对top问题进行check")
LLMSimiQuestionView(path="/llm_simi_question", tags=["llm_simi_question"], summary="大模型生成相似问题")
LLMCheckModelView(path="/llm_check_model", tags=["llm_check_model"], summary="检查模型是否可用")
LLMMultiModelView(path="/llm_multi_model", tags=["llm_multi_model"], summary="多模态推理服务")
LLMQuestionPromptView(path="/llm_question_prompt", tags=["llm_question_prompt"], summary="大模型问题提示")
LLMQuestionRecommendView(path="/llm_question_recommend", tags=["llm_question_recommend"], summary="大模型问题推荐")
LLMRotateAnswerView(path="/llm_rotate_answer", tags=["llm_rotate_answer"], summary="以轮询的方式总结回答大信息量内容")
LLMQuestionRewriteView(path="/llm_question_rewrite", tags=["llm_question_rewrite"], summary="大模型问题改写")
ConnectivityTestView(path="/connectivity_test", tags=["connectivity_test"], summary="API接口连通性测试")


def register_routes(app: FastAPI):
    from app.view.core.base_view import base_router
    app.include_router(router=base_router)

