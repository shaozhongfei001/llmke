#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: search_by_document_id_view.py
Time: 2025-12-04 14:45
"""
from base import BaseResponse, QueryDataModel
from es_kb_service import search_by_document_id
from view.core.base_view import BaseView


class SearchByDocumentIdView(BaseView):
    def post(self, query_data: QueryDataModel) -> BaseResponse:
        return search_by_document_id(query_data)


