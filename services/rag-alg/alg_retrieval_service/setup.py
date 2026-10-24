#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: setup.py  
Time: 2025/9/18 15:02  
"""
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="alg_retrieval_service",
    ext_modules=cythonize(
        "app/**/*.py",       # 匹配 app/ 及子目录下所有 .py
        language_level="3",  # Python 3 语法
        build_dir="build"    # 中间 .c 文件放到 build/
    ),
    zip_safe=False,
)
