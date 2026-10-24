#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/2 09:47
# @Author  : yuxj
# @File    : llm_config.py
import os

NACOS_SERVER_ADDRESS = os.getenv('NACOS_SERVER_ADDRESS')
NACOS_AK = os.getenv('NACOS_AK')
NACOS_SK = os.getenv('NACOS_SK')
NACOS_USERNAME = os.getenv('NACOS_USERNAME')
NACOS_PASSWORD = os.getenv('NACOS_PASSWORD')
NAMESPACE = os.getenv('NAMESPACE')
DATA_ID = os.getenv('DATA_ID')
GROUP = os.getenv('GROUP')


# nacos 配置
# NACOS_SERVER_ADDRESS = "http://10.15.12.13:8848"
# NAMESPACE = "rag-ai-dev"
# DATA_ID = "alg_llm_config_py"
# GROUP = "DEFAULT_GROUP"
