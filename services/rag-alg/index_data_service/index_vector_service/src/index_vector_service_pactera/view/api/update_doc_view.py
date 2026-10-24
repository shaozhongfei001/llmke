#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: update_doc_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, UpdateParamModel
from view.core.base_view import BaseView
from milvus_kb_service import update_data


class UpdateDocView(BaseView):
    async def post(self, update_model: UpdateParamModel) -> BaseResponse:
        return await update_data(update_model)

