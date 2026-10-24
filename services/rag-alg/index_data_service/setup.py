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
    name="index_data_service",
    ext_modules=cythonize(
        ["index_fulltext_service/**/*.py", "index_graph_service/**/*.py", "index_structure_service/**/*.py",
         "index_vector_service/**/*.py"],  # 匹配 app/ 及子目录下所有 .py
        language_level="3",  # Python 3 语法
        build_dir="build"  # 中间 .c 文件放到 build/
    ),
    zip_safe=False,
)
