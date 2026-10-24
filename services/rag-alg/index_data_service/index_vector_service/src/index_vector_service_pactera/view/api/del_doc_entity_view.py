#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: del_doc_entity_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, UpdateBatchModel
from view.core.base_view import BaseView
from milvus_kb_service import del_doc_entity


class DelDocEntityView(BaseView):
    def post(self, up_param: UpdateBatchModel) -> BaseResponse:
        return del_doc_entity(up_param)

