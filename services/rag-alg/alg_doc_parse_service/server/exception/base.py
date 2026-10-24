#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: base.py
Time: 2025-11-21 16:23
"""
from server.exception.error_code import UnknownErrorCode


class ApiError(Exception):
    """
    标准API异常
    """
    default_code = UnknownErrorCode

    def __init__(self, message: str | None = None, *, code: int | None = None):
        super().__init__(message)
        self.code = code if code is not None else self.default_code


def get_error_code(exc: Exception, default_code=None) -> int:
    if isinstance(exc, ApiError):
        return getattr(exc, 'code', exc.default_code)
    return default_code if default_code is not None else UnknownErrorCode
