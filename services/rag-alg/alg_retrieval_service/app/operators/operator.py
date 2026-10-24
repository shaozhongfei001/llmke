# -*- coding: utf-8 -*-

from app.operators.common.log import logger as g_logger
from app.base import CECRetrieveConfig


class Operator:
    
    def __init__(self, config: CECRetrieveConfig, logger: object = None) -> None:
        self.config = config
        self.logger = logger or g_logger