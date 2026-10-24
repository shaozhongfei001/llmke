#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: insert_fulltext_documents_view.py
Time: 2025-12-04 14:30
"""
from base import BaseResponse, InsertDataModel
from controller.es import add_documents_async
from view.core.base_view import BaseView


class InsertFulltextDocumentsView(BaseView):
    async def post(self, insert_model: InsertDataModel) -> BaseResponse:
        return await add_documents_async(insert_model)


