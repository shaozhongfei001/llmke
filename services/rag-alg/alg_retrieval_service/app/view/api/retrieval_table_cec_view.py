#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: retrieval_table_cec_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, CECTableRetrieveConfig
from app.retrieval_service_cec import retrieval_table_cec

from app.view.core.base_view import BaseView


class RetrievalTableCecView(BaseView):

    async def post(self, payload: CECTableRetrieveConfig) -> BaseResponse:
        return await retrieval_table_cec(payload)



