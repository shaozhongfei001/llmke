#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: query_type.py  
Time: 2025/12/22 11:26  
"""
from enum import Enum


# 定义一个枚举类
class QueryType(Enum):
    PK = 1
    METADATA = 2
