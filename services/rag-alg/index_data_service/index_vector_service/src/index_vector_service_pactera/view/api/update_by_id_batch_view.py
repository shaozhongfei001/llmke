#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: update_by_id_batch_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, UpdateBatchModel
from view.core.base_view import BaseView
from milvus_kb_service import update_by_pk_batch


class UpdateByIdBatchView(BaseView):
    def post(self, update_batch: UpdateBatchModel) -> BaseResponse:
        return update_by_pk_batch(update_batch)

