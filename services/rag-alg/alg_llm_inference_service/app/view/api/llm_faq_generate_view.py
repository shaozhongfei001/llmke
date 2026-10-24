#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_faq_generate_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, FAQChatConfig
from app.llm_service import llm_faq_generate
from app.view.core.base_view import BaseView


class LLMFAQGenerateView(BaseView):

    def post(self, payload: FAQChatConfig) -> BaseResponse:
        return llm_faq_generate(payload)

