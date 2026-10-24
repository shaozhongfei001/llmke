#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
index_vector_service配置文件
包含embedding模型的token映射配置
"""
import os


API_WORKER_COUNT = int(os.getenv("API_WORKER_COUNT", 6))
API_TIME_OUT = int(os.getenv("API_TIME_OUT", 600))

# 默认token限制
DEFAULT_EMBEDDING_MAX_TOKENS = 400
EMBED_MAX_TOKEN_DELTA_DEFAULT = 50