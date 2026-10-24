#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: server.py
Time: 2025-11-03 15:16
"""
from fastapi import FastAPI

from controller.version.version import get_version

app = FastAPI()
app.get('/version', summary='获取算法代码版本')(get_version)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=19525)
