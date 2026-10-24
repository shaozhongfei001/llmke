#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: version.py  
Time: 2025/11/3 15:29  
"""
import os

from conf import VERSION
from dotenv import load_dotenv
from loguru import logger


def get_version():
    load_dotenv()
    version = os.getenv("VERSION", VERSION)
    logger.info(f"算法代码版本: {version}")
    return {
        "code": 200,
        "msg": "算法代码版本信息",
        "data": {
            "version": version,
        }
    }
