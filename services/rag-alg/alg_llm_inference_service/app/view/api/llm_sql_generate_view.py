#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_sql_generate_view.py  
Time: 2025/9/23 11:33  
"""
from app.base import BaseResponse, SqlGenConfig
from app.llm_service import llm_sql_generate
from app.view.core.base_view import BaseView


class LLMSQLGenerateView(BaseView):

    def post(self, sql_gen_model: SqlGenConfig) -> BaseResponse:
        return llm_sql_generate(sql_gen_model)

