#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: delete_index_view.py
Time: 2025-12-04 14:25
"""
from base import BaseResponse, IndexModel
from es_kb_service import delete_index
from view.core.base_view import BaseView


class DeleteIndexView(BaseView):
    def post(self, index_model: IndexModel) -> BaseResponse:
        return delete_index(index_model)


