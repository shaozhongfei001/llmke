#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: delete_by_col_view.py
Time: 2025-12-04 14:35
"""
from base import BaseResponse, OperateDataModel
from es_kb_service import delete_by_col_documents
from view.core.base_view import BaseView


class DeleteByColView(BaseView):
    def post(self, operate_data: OperateDataModel) -> BaseResponse:
        return delete_by_col_documents(operate_data)


