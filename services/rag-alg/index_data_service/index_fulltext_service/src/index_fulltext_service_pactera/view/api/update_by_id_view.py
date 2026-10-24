#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: update_by_id_view.py
Time: 2025-12-04 15:05
"""
from base import BaseResponse, UpdateColModel
from es_kb_service import update_by_id
from view.core.base_view import BaseView


class UpdateByIdView(BaseView):
    def post(self, update_model: UpdateColModel) -> BaseResponse:
        return update_by_id(update_model)


