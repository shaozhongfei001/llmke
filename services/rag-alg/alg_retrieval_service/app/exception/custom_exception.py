#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: custom_exception.py.py  
Time: 2025/10/28 14:31  
"""
from app.exception.base import ApiError


class RequestError(Exception):
    """外部api请求错误"""
    pass

class ResponseCodeError(Exception):
    """外部api请求错误"""
    pass

class NotFoundError(ApiError):
    """数据未找到错误"""
    pass


class ParamsCheckError(ApiError):
    """参数检查错误"""
    pass


class InsideServerError(ApiError):
    """内部服务器错误"""
    pass


class DataBaseError(ApiError):
    """数据库错误"""
    pass


class UserError(ApiError):
    """用户相关错误"""
    pass


class PasswordError(ApiError):
    """密码错误"""
    pass


class ExpireTokenError(ApiError):
    """该错误的默认错误码将返回401弹回到登录页"""
    pass


class PermissionDenyError(ApiError):
    """权限拒绝错误"""
    pass


class UserLockError(ApiError):
    """用户锁定错误"""
    pass


class SystemLockError(ApiError):
    """系统锁定错误"""
    pass


class ServiceConnectionError(ApiError):
    """服务连接错误"""
    pass


class AccessDeniedError(ApiError):
    """访问拒绝错误"""
    pass


class AuthDenyError(ApiError):
    """认证拒绝错误"""
    pass


class AlreadyExistsError(ApiError):
    """数据已存在错误"""
    pass


class JsonParseError(ApiError):
    """JSON解析错误"""
    pass


class UploadFileSizeError(ApiError):
    """上传文件大小错误"""
    pass


class FileTypeNotSupportError(ApiError):
    """文件类型不支持错误"""
    pass


class ServiceUnavailableError(ApiError):
    """服务不可用错误"""
    pass
