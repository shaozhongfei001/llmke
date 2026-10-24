#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright DataGrand Tech Inc. All Rights Reserved.
Author: Wangzihao
File: embedding_retriever.py
Time: 20240722
"""


from typing import List
from app.base import CECTableRetrieveConfig
from app.operators.retriever.base import Retriever
from app.multiple_retrieval import retrieval_milvus


class EmbeddingRetriever(Retriever):

    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
        
        # [暂使用retrieval_elastic_cec]
        self.client = None

    async def retrieve(self, question, knowledge_base_name, top_k, server_config, table_pk_list, 
                 query_condition, cec_kb_file_list, dense_weight, condition_symbol) -> List:
        
        result = await retrieval_milvus(question, knowledge_base_name, top_k, server_config, 
                                  table_pk_list, query_condition, cec_kb_file_list, 
                                  dense_weight=dense_weight, condition_symbol=condition_symbol)
        return result
