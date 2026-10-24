#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: embed_change.py
Time: 2025/12/1 16:13
"""
import copy
from typing import Dict, Optional

from pymilvus import Collection, DataType

from base import DatabaseConfigModel, InsertDataModel, EmbeddingModelInfo
from milvus_kb_config import (
    MILVUS_FIELDS,
    MILVUS_FIELDS_FAQ,
    MILVUS_FIELDS_GRAPH_ENTITY,
    MILVUS_FIELDS_GRAPH_TRIPLES,
    MILVUS_FIELDS_TABLE_CHUNKS,
    MILVUS_FIELDS_TABLE_SUMMARY,
    get_vector_dim,
)
from utils import return_nacos_model



class EmbedChangeController:
    @staticmethod
    def _clone_mapping_with_vector_dim(mapping_template: dict, vector_dim: Optional[int]) -> dict:
        """
        深拷贝 schema，并根据需要重置所有向量字段的维度
        """
        mapping_copy = copy.deepcopy(mapping_template)
        if vector_dim:
            for field_conf in mapping_copy.values():
                if isinstance(field_conf, dict) and field_conf.get("dtype") == "DataType.FLOAT_VECTOR":
                    field_conf["dim"] = vector_dim
        return mapping_copy

    def resolve_vector_mapping(self, collection_name: str, vector_dim: Optional[int]) -> dict:
        """
        根据集合名与模型配置动态返回schema定义
        """
        coll_name_low = collection_name.lower()
        if "faq_" in coll_name_low:
            base_mapping = copy.deepcopy(MILVUS_FIELDS_FAQ)
            # 动态检查 enable_question_vector 配置，确保 question_vector 字段存在
            server_config = return_nacos_model().get_config()
            enable_question_vector = server_config.get("milvus_conn_config", {}).get("enable_question_vector", False)
            if enable_question_vector and "question_vector" not in base_mapping:
                # 如果配置开启但字段不存在，动态添加 question_vector 字段
                # 使用 vector_dim 如果提供，否则使用默认模型的维度
                question_vector_dim = vector_dim if vector_dim is not None else get_vector_dim()
                base_mapping["question_vector"] = {
                    "dtype": "DataType.FLOAT_VECTOR",
                    "dim": question_vector_dim
                }
        elif "graph_entity" in coll_name_low:
            base_mapping = MILVUS_FIELDS_GRAPH_ENTITY
        elif "graph_triples" in coll_name_low:
            base_mapping = MILVUS_FIELDS_GRAPH_TRIPLES
        elif "table_summary_" in coll_name_low:
            base_mapping = MILVUS_FIELDS_TABLE_SUMMARY
        elif "table_chunks_" in coll_name_low:
            base_mapping = MILVUS_FIELDS_TABLE_CHUNKS
        else:
            base_mapping = MILVUS_FIELDS
        return self._clone_mapping_with_vector_dim(base_mapping, vector_dim)

    @staticmethod
    def resolve_vector_dim(embedding_info: EmbeddingModelInfo = None, nacos_config: dict = None,
                           model_name: str = "") -> Optional[int]:
        """
        优先从请求体 embedding_model_info 中获取向量维度，回落到 nacos 配置
        """
        vector_dim = None
        if embedding_info:
            if hasattr(embedding_info, "dim"):
                vector_dim = getattr(embedding_info, "dim")
            elif isinstance(embedding_info, dict):
                vector_dim = embedding_info.get("dim")
        if not vector_dim:
            try:
                vector_dim = nacos_config["online_embedding_model"][model_name]["dim"]
            except KeyError as e:
                raise Exception(f"未在nacos配置中找到模型 {model_name} 的向量维度") from e
        try:
            vector_dim = int(vector_dim)
        except (TypeError, ValueError) as e:
            raise Exception(f"模型 {model_name} 的向量维度值非法：{vector_dim}") from e
        return vector_dim


embed_change_ctrl = EmbedChangeController()
