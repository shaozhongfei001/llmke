#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_multi_model_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import MultiModelConfig
from app.llm_service import llm_multi_model
from app.view.core.base_view import BaseView


class LLMMultiModelView(BaseView):

    def post(self, payload: MultiModelConfig):
        return llm_multi_model(payload)

