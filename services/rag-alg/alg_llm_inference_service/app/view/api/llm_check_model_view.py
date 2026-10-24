#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_check_model_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, LLMBasicConfig
from app.llm_service import llm_check_model
from app.view.core.base_view import BaseView


class LLMCheckModelView(BaseView):

    def post(self, payload: LLMBasicConfig) -> BaseResponse:
        return llm_check_model(payload)

