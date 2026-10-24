#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_question_prompt_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, QuestionRecommendConfig
from app.llm_service import llm_question_prompt
from app.view.core.base_view import BaseView


class LLMQuestionPromptView(BaseView):

    def post(self, payload: QuestionRecommendConfig) -> BaseResponse:
        return llm_question_prompt(payload)

