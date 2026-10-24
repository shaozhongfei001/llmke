#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: migrate_collection_view.py  
Time: 2025/12/5
"""
from base import BaseResponse, MigrateCollectionModel
from view.core.base_view import BaseView
from controller.migrate_collection import migrate_collection_data


class MigrateCollectionView(BaseView):
    async def post(self, migrate_param: MigrateCollectionModel) -> BaseResponse:
        return await migrate_collection_data(migrate_param)

