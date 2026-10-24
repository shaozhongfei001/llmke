#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: update_doc_view.py
Time: 2025-12-04 15:00
"""
from base import BaseResponse, UpdateParamModel
from es_kb_service import update_doc
from view.core.base_view import BaseView


class UpdateDocView(BaseView):
    def post(self, update_model: UpdateParamModel) -> BaseResponse:
        return update_doc(update_model)


