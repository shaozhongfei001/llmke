#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: get_doc_by_col_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, DataParamModel
from view.core.base_view import BaseView
from milvus_kb_service import get_doc_by_col


class GetDocByColView(BaseView):
    def post(self, query_param: DataParamModel) -> BaseResponse:
        return get_doc_by_col(query_param)

