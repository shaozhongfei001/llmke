#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: urls.py
Time: 2025-12-04 15:10
"""
from fastapi import FastAPI

from view.api.create_es_index_view import CreateEsIndexView
from view.api.delete_index_view import DeleteIndexView
from view.api.insert_fulltext_documents_view import InsertFulltextDocumentsView
from view.api.delete_by_col_view import DeleteByColView
from view.api.delete_by_id_view import DeleteByIdView
from view.api.search_by_document_id_view import SearchByDocumentIdView
from view.api.search_by_page_view import SearchByPageView
from view.api.search_by_custom_param_view import SearchByCustomParamView
from view.api.update_doc_view import UpdateDocView
from view.api.update_by_id_view import UpdateByIdView

# Instantiate views to register their routes with the shared router.
CreateEsIndexView(path="/create_es_index", tags=["create_es_index"], summary="创建ES索引")
DeleteIndexView(path="/del_index", tags=["delete_index"], summary="删除索引")
InsertFulltextDocumentsView(
    path="/insert_fulltext_documents",
    tags=["insert_fulltext_documents"],
    summary="批量添加数据",
)
DeleteByColView(
    path="/del_doc_by_col",
    tags=["delete_data_by_metadata_col"],
    summary="通过metadata字段和值删除数据",
)
DeleteByIdView(path="/del_by_id", tags=["del_by_id"], summary="根据ID删除数据")
SearchByDocumentIdView(
    path="/search_by_document_id",
    tags=["search_by_document_id"],
    summary="根据document_id查询数据",
)
SearchByPageView(path="/search_by_page", tags=["search_by_page"], summary="分页查询")
SearchByCustomParamView(
    path="/search_by_custom_param",
    tags=["search_by_custom_param"],
    summary="自定义查询全部数据",
)
UpdateDocView(path="/update_doc", tags=["update_doc"], summary="修改数据")
UpdateByIdView(path="/update_by_id", tags=["update_by_id"], summary="根据ID修改数据")


def register_routes(app: FastAPI):
    from view.core.base_view import base_router

    app.include_router(router=base_router)


