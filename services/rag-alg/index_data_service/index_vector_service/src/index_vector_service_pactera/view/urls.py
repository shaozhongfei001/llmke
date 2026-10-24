#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: urls.py  
Time: 2025/11/28 11:25  
"""
from fastapi import FastAPI

from view.api.create_milvus_db_view import CreateMilvusDbView
from view.api.create_milvus_collection_view import CreateMilvusCollectionView
from view.api.create_milvus_index_view import CreateMilvusIndexView
from view.api.insert_vector_documents_custom_view import InsertVectorDocumentsCustomView
from view.api.milvus_vector_search_view import MilvusVectorSearchView
from view.api.get_doc_by_col_view import GetDocByColView
from view.api.del_doc_by_col_view import DelDocByColView
from view.api.del_doc_entity_view import DelDocEntityView
from view.api.update_doc_view import UpdateDocView
from view.api.update_by_id_view import UpdateByIdView
from view.api.update_by_id_batch_view import UpdateByIdBatchView
from view.api.get_doc_page_view import GetDocPageView
from view.api.static_count_view import StaticCountView
from view.api.migrate_collection_view import MigrateCollectionView

CreateMilvusDbView(path="/create_milvus_db", tags=["create_milvus_db"], summary="创建milvus数据库")
CreateMilvusCollectionView(path="/create_milvus_collection", tags=["create_milvus_collection"], summary="创建milvus的collection")
CreateMilvusIndexView(path="/create_milvus_index", tags=["create_milvus_index"], summary="创建milvus索引")
InsertVectorDocumentsCustomView(path="/insert_vector_documents_custom", tags=["insert_vector_documents_custom"], summary="通过自定义的方式插入数据，可在代码处修改逻辑，需自己创建集合和索引")
MilvusVectorSearchView(path="/milvus_vector_search", tags=["milvus_vector_search"], summary="查询数据")
GetDocByColView(path="/get_doc_by_col", tags=["get_doc_by_ids"], summary="根据列名查询数据")
DelDocByColView(path="/del_doc_by_col", tags=["del_doc_by_col"], summary="根据列值，删除数据")
DelDocEntityView(path="/del_doc_entity", tags=["del_doc_entity"], summary="实体表删除接口")
UpdateDocView(path="/update_doc", tags=["update_doc"], summary="修改数据")
UpdateByIdView(path="/update_by_id", tags=["update_by_pk"], summary="根据pk修改数据")
UpdateByIdBatchView(path="/update_by_id_batch", tags=["update_by_pk_batch"], summary="根据pk修改数据_batch")
GetDocPageView(path="/get_doc_page", tags=["get_doc_page"], summary="分页查询")
StaticCountView(path="/static_count", tags=["static_count"], summary="统计总量")
MigrateCollectionView(path="/migrate_milvus_collection", tags=["migrate_milvus_collection"], summary="迁移milvus集合数据")


def register_routes(app: FastAPI):
    from view.core.base_view import base_router
    app.include_router(router=base_router)
