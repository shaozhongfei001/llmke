#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: request_logging.py
Time: 2025/11/4
"""
import json
from fastapi import Request
from operators.common.log import logger


async def request_logging_middleware(request: Request, call_next):
    """请求日志中间件"""
    url = request.url
    method = request.method
    params = {}

    # 跳过文件上传
    if "multipart/form-data" in request.headers.get("content-type", ""):
        return await call_next(request)

    # 获取查询参数
    if request.query_params:
        params.update(request.query_params)

    # 获取请求体
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_json = json.loads(body_bytes.decode("utf-8"))
                    params.update(body_json)
                except Exception:
                    params["raw_body"] = body_bytes[:500].decode("utf-8", errors="ignore")

            # 重新构造 Request，以便下游依然能读取 body
            async def receive():
                return {"type": "http.request", "body": body_bytes}

            request = Request(request.scope, receive=receive)

        except Exception as e:
            logger.warning(f"读取请求体失败: {e}")

    logger.info(f"[API] {method} {url}, request params: {params}")

    response = await call_next(request)
    return response
