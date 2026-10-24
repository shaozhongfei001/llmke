#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: delete_by_id_view.py
Time: 2025-12-04 14:40
"""
from base import BaseResponse, DeleteParamModel
from es_kb_service import del_by_id
from view.core.base_view import BaseView


class DeleteByIdView(BaseView):
    def post(self, delete_model: DeleteParamModel) -> BaseResponse:
        return del_by_id(delete_model)


