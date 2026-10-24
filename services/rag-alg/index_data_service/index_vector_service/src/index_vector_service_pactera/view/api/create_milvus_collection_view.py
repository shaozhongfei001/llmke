#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: create_milvus_collection_view.py  
Time: 2025/11/28
"""
from base import BaseResponse, DatabaseConfigModel
from view.core.base_view import BaseView
from milvus_kb_service import do_create_collection


class CreateMilvusCollectionView(BaseView):
    def post(self, milvus_config_model: DatabaseConfigModel) -> BaseResponse:
        return do_create_collection(milvus_config_model)

