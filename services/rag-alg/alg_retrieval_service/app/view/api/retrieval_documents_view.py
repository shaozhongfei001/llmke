#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: retrieval_documents_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, QARetrieveConfig
from app.retrieval_service import multiple_retrieval_documents

from app.view.core.base_view import BaseView


class RetrievalDocumentsView(BaseView):

    async def post(self, payload: QARetrieveConfig) -> BaseResponse:
        return await multiple_retrieval_documents(payload)


