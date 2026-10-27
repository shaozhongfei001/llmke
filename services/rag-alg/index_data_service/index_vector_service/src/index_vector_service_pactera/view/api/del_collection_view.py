#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R14-A：删除整个 Milvus 集合（graph_summary.del_community 依赖的路由）。"""
from base import BaseResponse, DataParamModel
from view.core.base_view import BaseView
from milvus_kb_service import del_collection


class DelCollectionView(BaseView):
    def post(self, del_param: DataParamModel) -> BaseResponse:
        return del_collection(del_param)
