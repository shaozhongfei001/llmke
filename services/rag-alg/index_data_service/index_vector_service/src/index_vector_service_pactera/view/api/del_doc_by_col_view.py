#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: del_doc_by_col_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, DataParamModel
from view.core.base_view import BaseView
from milvus_kb_service import del_doc_by_col


class DelDocByColView(BaseView):
    def post(self, del_param: DataParamModel) -> BaseResponse:
        return del_doc_by_col(del_param)

