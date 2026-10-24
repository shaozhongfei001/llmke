#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_rotate_answer_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import LLMOpenChatConfig
from app.llm_service import sync_llm_rounds_generate
from app.view.core.base_view import BaseView


class LLMRotateAnswerView(BaseView):

    def post(self, payload: LLMOpenChatConfig):
        return sync_llm_rounds_generate(payload)

