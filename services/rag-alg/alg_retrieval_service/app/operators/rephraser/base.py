# -*- coding: utf-8 -*-

from typing import List, Optional
from app.operators.operator import Operator
from app.base import CECTableRetrieveConfig


class Rephraser(Operator):
    
    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
    
    def rephrase(self, query: str, history_chat: Optional[List] = None) -> List:
        NotImplemented
