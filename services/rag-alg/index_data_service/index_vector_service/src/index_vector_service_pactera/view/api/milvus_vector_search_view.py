#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: milvus_vector_search_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, QueryDataModel
from view.core.base_view import BaseView
from milvus_kb_service import do_search


class MilvusVectorSearchView(BaseView):
    def post(self, query_model: QueryDataModel) -> BaseResponse:
        return do_search(query_model)

