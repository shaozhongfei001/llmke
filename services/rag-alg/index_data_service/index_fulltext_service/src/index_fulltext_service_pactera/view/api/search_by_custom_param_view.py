#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: search_by_custom_param_view.py
Time: 2025-12-04 14:55
"""
from base import BaseResponse, QueryParamModel
from es_kb_service import search_by_custom_param
from view.core.base_view import BaseView


class SearchByCustomParamView(BaseView):
    def post(self, query_params: QueryParamModel) -> BaseResponse:
        return search_by_custom_param(query_params)


