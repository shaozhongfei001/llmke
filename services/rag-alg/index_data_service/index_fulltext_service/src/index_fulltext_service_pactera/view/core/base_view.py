#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: base_view.py
Time: 2025-12-04 14:15
"""
import inspect
from typing import Optional, List

from fastapi import APIRouter

from base import BaseResponse

base_router = APIRouter()


class BaseView:
    path: Optional[str] = None

    def __init__(self, path: str, tags: List[str], summary: str):
        self.path = path or getattr(self, "path")
        self.tags = tags or getattr(self, "tags", None)
        self.summary = summary or getattr(self, "summary", "")
        self.register_routes()

    def register_routes(self):
        method_map = {
            "get": {"path": self.path, "methods": ["GET"]},
            "post": {"path": self.path, "methods": ["POST"]},
            "put": {"path": self.path, "methods": ["PUT"]},
            "delete": {"path": self.path, "methods": ["DELETE"]},
        }
        for method_name, router_info in method_map.items():
            method = getattr(self, method_name, None)
            if self.is_method_overridden(method_name):
                extra_params = getattr(method, "_extra_params", {})
                base_router.add_api_route(
                    router_info["path"],
                    method,
                    methods=router_info["methods"],
                    tags=self.tags,
                    summary=self.summary,
                    response_model=BaseResponse,
                    **extra_params,
                )

    def is_method_overridden(self, method_name: str) -> bool:
        subclass_method = getattr(self, method_name, None)
        base_method = getattr(BaseView, method_name, None)
        if not subclass_method or not base_method:
            return False
        return inspect.getmodule(subclass_method) != inspect.getmodule(base_method)

    def get(self, *args, **kwargs):
        raise ImportError("Not implemented")

    def post(self, *args, **kwargs):
        raise ImportError("Not implemented")

    def put(self, *args, **kwargs):
        raise ImportError("Not implemented")

    def delete(self, *args, **kwargs):
        raise ImportError("Not implemented")


