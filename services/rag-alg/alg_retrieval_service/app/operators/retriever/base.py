# -*- coding: utf-8 -*-


from typing import List
from app.operators.operator import Operator
from app.base import CECTableRetrieveConfig


class Retriever(Operator):
    
    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
    
    async def retrieve(self, *args, **kwargs) -> List:
        NotImplemented
