#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: retrieval_documents_table_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, CECTableRetrieveConfig
from app.retrieval_service_cec import retrieval_documents_table

from app.view.core.base_view import BaseView


class RetrievalDocumentsTableView(BaseView):

    async def post(self, payload: CECTableRetrieveConfig) -> BaseResponse:
        return await retrieval_documents_table(payload)



