#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
rerank:多个chunk超长，切分多次，以长度4000切分为n等份
filter:单个chunk超长
"""
from typing import List, Dict
from app.operators.reranker.base import Reranker
from app.base import CECRetrieveConfig


class LLMReranker(Reranker):

    def __init__(self, config: CECRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
        self.client = None
    
    def filter(self, query: str, reference: List[Dict]) -> List:
        """
        llm filter
        """
        pass
