#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 15:25
# @Author  : yuxj
# @File    : llm_api_start.py
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.middleware import register_middlewares
from app.utils import get_config, return_nacos_model
from app.view.urls import register_routes
from app.operators.common.log import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
server_config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    # 初始化配置管理器
    config_manager = return_nacos_model()
    # 强制刷新一次配置
    config_manager.load_initial_config()
    logger.info(f"init config:{config_manager.get_config()}")
    print("init config:", config_manager.get_config())

    yield


llm_app = FastAPI(lifespan=lifespan)

# 添加请求日志中间件
register_middlewares(llm_app)

register_routes(app=llm_app)


def api_start():
    uvicorn.run(llm_app, host=server_config["server"]["host"], port=server_config["server"]["port"])


if __name__ == '__main__':
    api_start()
