#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: __init__.py
Time: 2025/11/4 11:26  
"""
from app.middleware.request_logging import request_logging_middleware


def register_middlewares(app):
    app.middleware("http")(request_logging_middleware)
