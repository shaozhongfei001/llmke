#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alg_retrieval_service配置文件
包含rerank模型的token映射配置
"""
import os

API_WORKER_COUNT = int(os.getenv("API_WORKER_COUNT", 6))
API_TIME_OUT = int(os.getenv("API_TIME_OUT", 600))

# 默认rerank模型token限制
DEFAULT_RERANK_MAX_TOKENS = 400

RERANK_MAX_TOKEN_DELTA_DEFAULT = 50