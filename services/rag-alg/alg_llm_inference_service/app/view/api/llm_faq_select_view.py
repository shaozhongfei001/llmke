#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_faq_select_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, FAQSelectConfig
from app.llm_service import llm_faq_select
from app.view.core.base_view import BaseView


class LLMFAQSelectView(BaseView):

    def post(self, payload: FAQSelectConfig) -> BaseResponse:
        return llm_faq_select(payload)

