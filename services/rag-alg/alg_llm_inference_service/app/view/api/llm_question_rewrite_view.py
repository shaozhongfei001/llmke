#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_question_rewrite_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, QuestionRewriteConfig
from app.llm_service import llm_question_rewrite
from app.view.core.base_view import BaseView


class LLMQuestionRewriteView(BaseView):

    def post(self, payload: QuestionRewriteConfig) -> BaseResponse:
        return llm_question_rewrite(payload)

