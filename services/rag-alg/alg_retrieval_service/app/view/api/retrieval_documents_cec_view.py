#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: retrieval_documents_cec_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, CECRetrieveConfig
from app.retrieval_service_cec import retrieval_documents_cec

from app.view.core.base_view import BaseView


class RetrievalDocumentsCecView(BaseView):

    async def post(self, payload: CECRetrieveConfig) -> BaseResponse:
        return await retrieval_documents_cec(payload)
