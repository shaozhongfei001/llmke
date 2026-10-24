#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: urls.py  
Time: 2025/9/18 14:40  
"""
from fastapi import FastAPI

from app.view.api import RetrievalDocumentsView, RetrievalDocumentsCecView, RetrievalTableCecView, \
    RetrievalDocumentsTableView

# [Retrieval]
RetrievalDocumentsView(path="/retrieval_documents", tags=["retrieval_documents"], summary="多路召回，返回查询结果")
RetrievalDocumentsCecView(path="/retrieval_documents_cec", tags=["retrieval_documents_cec"], summary="多路召回，返回查询结果,cec")
RetrievalTableCecView(path="/retrieval_table_cec", tags=["retrieval_table_cec"], summary="表格检索,cec")
RetrievalDocumentsTableView(path="/retrieval_documents_table", tags=["retrieval_documents_table"],summary="mysql+retrieval_documents_table")


def register_routes(app: FastAPI):
    from app.view.core.base_view import base_router
    app.include_router(router=base_router)
