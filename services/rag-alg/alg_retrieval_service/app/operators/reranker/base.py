# -*- coding: utf-8 -*-


from typing import List
from app.operators.operator import Operator
from app.base import CECTableRetrieveConfig

class Reranker(Operator):
    
    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
    
    def rerank(self, query: str, documents: List) -> List:
        NotImplemented
