# -*- coding: utf-8 -*-

from typing import List, Optional, Dict, Generator
from app.operators.operator import Operator
from app.base import CECTableRetrieveConfig

class LLM(Operator):
    
    def __init__(self, config: CECTableRetrieveConfig, logger: object = None) -> None:
        super().__init__(config, logger)
    
    def generate(self, prompt: str, generate_params: Optional[Dict] = None) -> List:
        NotImplemented
    
    def stream_generate(self, prompt: str, generate_params: Optional[Dict] = None) -> Generator:
        NotImplemented
