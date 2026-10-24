#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: update_by_id_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, UpdateColModel
from view.core.base_view import BaseView
from milvus_kb_service import update_by_pk


class UpdateByIdView(BaseView):
    def post(self, update_col: UpdateColModel) -> BaseResponse:
        return update_by_pk(update_col)

