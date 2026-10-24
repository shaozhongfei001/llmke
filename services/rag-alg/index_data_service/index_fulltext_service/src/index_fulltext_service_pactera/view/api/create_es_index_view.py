#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: create_es_index_view.py
Time: 2025-12-04 14:20
"""
from base import BaseResponse, CreateIndexModel
from es_kb_service import create_index
from view.core.base_view import BaseView


class CreateEsIndexView(BaseView):
    def post(self, create_model: CreateIndexModel) -> BaseResponse:
        return create_index(create_model)


