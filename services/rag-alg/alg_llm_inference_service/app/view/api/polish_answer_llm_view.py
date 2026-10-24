#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: polish_answer_llm_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, FAQChatConfig
from app.llm_service import llm_polish_answer
from app.view.core.base_view import BaseView


class PolishAnswerLLMView(BaseView):

    def post(self, payload: FAQChatConfig) -> BaseResponse:
        return llm_polish_answer(payload)

