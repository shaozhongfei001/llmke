#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: create_milvus_db_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, DataBaseModel
from view.core.base_view import BaseView
from milvus_kb_service import do_create_database


class CreateMilvusDbView(BaseView):
    def post(self, database: DataBaseModel) -> BaseResponse:
        return do_create_database(database)

