#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 15:14
# @Author  : yuxj
# @File    : es_kb_service.py
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from view.urls import register_routes
from middleware import register_middlewares
from operators.common.log import logger
from utils import get_config, return_nacos_model

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


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


es_app = FastAPI(lifespan=lifespan)

# 添加请求日志中间件
register_middlewares(es_app)
register_routes(app=es_app)

server_config = get_config()["es_server"]


# es_app.post('/get_retriever_documents',
#             tags=['get_retriever_documents'],
#             response_model=BaseResponse,
#             summary='通过langchain方式查询数据，与search_by_custom_param相同，暂时不提供，后续有需要可以开启'
#             )(get_retriever_documents)

def api_start():
    uvicorn.run(es_app, host=server_config["host"], port=server_config["port"])


if __name__ == '__main__':
    api_start()
