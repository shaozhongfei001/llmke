#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: __init__.py.py  
Time: 2025/9/18 14:39  
"""

# Export view classes for router registration side-effects
from .retrieval_documents_view import RetrievalDocumentsView
from .retrieval_global_view import RetrievalGlobalView
from .retrieval_documents_cec_view import RetrievalDocumentsCecView
from .retrieval_table_cec_view import RetrievalTableCecView
from .retrieval_documents_table_view import RetrievalDocumentsTableView

__all__ = [
    "RetrievalDocumentsView",
    "RetrievalGlobalView",
    "RetrievalDocumentsCecView",
    "RetrievalTableCecView",
    "RetrievalDocumentsTableView",
]
