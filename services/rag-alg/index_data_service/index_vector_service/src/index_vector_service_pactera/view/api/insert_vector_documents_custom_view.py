#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: insert_vector_documents_custom_view.py
Time: 2025/11/28 11:23
"""
from base import BaseResponse, InsertDataModel
from milvus_kb_service import add_doc_custom, generate_collection_name_uuid
from view.core.base_view import BaseView


class InsertVectorDocumentsCustomView(BaseView):
    async def post(self, insert_model: InsertDataModel) -> BaseResponse:
        return await add_doc_custom(insert_model)