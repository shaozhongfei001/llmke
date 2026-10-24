#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_simi_question_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, FAQSimiConfig
from app.llm_service import llm_simi_question
from app.view.core.base_view import BaseView


class LLMSimiQuestionView(BaseView):

    def post(self, payload: FAQSimiConfig) -> BaseResponse:
        return llm_simi_question(payload)

