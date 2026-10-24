# -*- coding: utf-8 -*-

from typing import List
from langchain_core.documents import Document
from app.base import CECTableRetrieveConfig
from app.operators.retriever.base import Retriever
from app.operators.retriever.bm25_retriever import BM25Retriever
from app.operators.retriever.embedding_retriever import EmbeddingRetriever

class HybridRetriever(Retriever):
    """
    当前仅支持 query与 embedding两种方式混合检索
    """

    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)

        self.client = None
        self.bm25_retriever = BM25Retriever(config, logger)
        self.embed_retriever = EmbeddingRetriever(config, logger)

    @staticmethod
    def merge_result(documents_bm25, documents_embed) -> List:
        page_contents = set()
        documents = []
        for document in documents_bm25:
            x = Document(page_content=document.page_content, metadata=document.metadata)
            
            if x.page_content not in page_contents:
                page_contents.add(x.page_content)
                documents.append(x)
        for document in documents_embed:
            x = Document(page_content=document.page_content, metadata=document.metadata)
            if x.page_content not in page_contents:
                page_contents.add(x.page_content)
                documents.append(x)
        return documents

    async def retrieve(self, question, knowledge_base_name, es_knowledge_base_list, top_k, 
                       server_config, table_pk_list, cec_kb_file_list, dense_weight, query_condition, condition_symbol) -> list:
        
        documents_bm25 = await self.bm25_retriever.retrieve(question, es_knowledge_base_list, top_k, server_config, table_pk_list, cec_kb_file_list, dense_weight)
        documents_embed = await self.embed_retriever.retrieve(question, knowledge_base_name, top_k, server_config, table_pk_list, 
                 query_condition, cec_kb_file_list, dense_weight, condition_symbol)
        documents_hybrid = self.merge_result(documents_bm25, documents_embed)
        return documents_hybrid
