# -*- coding: utf-8 -*-


from typing import List

from app.operators.retriever.base import Retriever
from app.base import CECTableRetrieveConfig
from app.multiple_retrieval import retrieval_elastic_cec

class BM25Retriever(Retriever):

    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
        
        # [暂使用retrieval_elastic_cec]
        self.client = None
        
    async def retrieve(self, question, es_knowledge_base_list, top_k, server_config, table_pk_list, cec_kb_file_list, dense_weight) -> List:
        result = await retrieval_elastic_cec(question, es_knowledge_base_list, top_k, server_config, table_pk_list, cec_kb_file_list, dense_weight=dense_weight)
        return result
