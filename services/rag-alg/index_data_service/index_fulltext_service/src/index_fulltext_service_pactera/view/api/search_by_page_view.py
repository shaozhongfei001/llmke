#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: search_by_page_view.py
Time: 2025-12-04 14:50
"""
from base import BaseResponse, QueryParamModel
from es_kb_service import search_by_page
from view.core.base_view import BaseView


class SearchByPageView(BaseView):
    def post(self, query_params: QueryParamModel) -> BaseResponse:
        return search_by_page(query_params)


