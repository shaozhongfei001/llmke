#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng
File: gunicorn_conf.py
Time: 2025-10-31 16:56
"""
from app.config.conf import API_WORKER_COUNT, API_TIME_OUT

# 绑定端口 注意0.0.0.0的配置在docker网络中是关键配置
bind = "0.0.0.0:19995"
# 工作进程数 常规使用Docker横向扩容，故按项目实际情况配置
workers = API_WORKER_COUNT
# 允许pending状态最大连接数 推荐64-2048
backlog = 2048
# 超时时间 根据实际情况配置 推荐30/60
timeout = API_TIME_OUT
# 是否使用debug模式
# debug = True
# 是否重定向错误到日志文件
capture_output = True
# 不使用sync的最大问题在于sync虽然在短连接中网络模式最为简单干净,但不支持长连接,在高并发任务中的TCP效率会非常低
worker_class = "uvicorn.workers.UvicornWorker"
# 客户端最大同时连接数 在极高并发根据服务器和实例数根据情况修改
# 仅适用于eventlet/gevent
worker_connections = 5000
