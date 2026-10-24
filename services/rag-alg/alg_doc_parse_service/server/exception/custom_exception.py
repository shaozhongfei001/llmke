#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: custom_exception.py
Time: 2025-11-21 16:21
"""
from server.exception.base import ApiError
from server.exception.error_code import (
    FILE_PARSE_FAILED,
    INDEX_INTERNAL_ERROR,
    INDEX_MILVUS_DIMENSION_MISMATCH,
    INDEX_MILVUS_INSERT_FAILED,
    MINERU_REQUEST_TIMEOUT,
    MINERU_RESOURCE_INSUFFICIENT,
    MINERU_SERVICE_UNAVAILABLE,
    MODEL_REQUEST_INTERNAL,
    MODEL_TOKEN_TOO_LONG,
    UnknownErrorCode, INDEX_ES_INSERT_FAILED,
)


class UnknownError(ApiError):
    """1000 未知错误"""
    default_code = UnknownErrorCode


class FileParseFailedError(ApiError):
    """1100 文件解析内部错误"""
    default_code = FILE_PARSE_FAILED


class ModelRequestInternalError(ApiError):
    """1300 模型请求内部错误"""
    default_code = MODEL_REQUEST_INTERNAL


class MineruServiceUnavailableError(ApiError):
    """1301 mineru 模型服务挂"""
    default_code = MINERU_SERVICE_UNAVAILABLE


class MineruResourceInsufficientError(ApiError):
    """1302 mineru 模型显存不足"""
    default_code = MINERU_RESOURCE_INSUFFICIENT


class ModelTokenExceedError(ApiError):
    """1303 请求大模型 token 超长"""
    default_code = MODEL_TOKEN_TOO_LONG


class MineruRequestTimeoutError(ApiError):
    """1304 mineru 模型超时"""
    default_code = MINERU_REQUEST_TIMEOUT


class IndexInternalError(ApiError):
    """1400 index 服务请求内部错误"""
    default_code = INDEX_INTERNAL_ERROR


class IndexMilvusInsertFailedError(ApiError):
    """1401 index milvus 服务向量插入失败"""
    default_code = INDEX_MILVUS_INSERT_FAILED


class IndexMilvusDimensionMismatchError(ApiError):
    """1402 index milvus 服务插入向量维度不符合要求"""
    default_code = INDEX_MILVUS_DIMENSION_MISMATCH


class IndexESInsertFailedError(ApiError):
    """1403 index es 服务插入失败"""
    default_code = INDEX_ES_INSERT_FAILED
