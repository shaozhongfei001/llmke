#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: static_count_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, DataParamModel
from view.core.base_view import BaseView
from milvus_kb_service import static_count


class StaticCountView(BaseView):
    def post(self, static_param: DataParamModel) -> BaseResponse:
        return static_count(static_param)

