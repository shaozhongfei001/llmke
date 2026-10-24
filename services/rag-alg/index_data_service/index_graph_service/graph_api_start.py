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

from base import BaseResponse
from graph_service import create_space, generate_triple_data, create_attribute, batch_insert_vertex, query_graph_data, del_space_data, create_space_attribute
from middleware import register_middlewares
from utils import get_config, return_nacos_model
from operators.common.log import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    # 初始化配置管理器
    config_manager = return_nacos_model()
    # 强制刷新一次配置
    config_manager.load_initial_config()
    config_manager.session_client()
    logger.info(f"init config:{config_manager.get_config()}")
    print("init config:", config_manager.get_config())
    
    yield

graph_app = FastAPI(lifespan=lifespan)

# 添加请求日志中间件
register_middlewares(graph_app)

# @graph_app.on_event("shutdown")
# async def shutdown_event():
#     """
#     在 FastAPI 关闭时释放资源
#     """
#     config_manager = return_nacos_model()
#     session = config_manager.session_client()
#     if session:
#         session.release()  # 释放 Nebula 会话
#         config_manager.close_pool()


server_config = get_config()["graph_server"]

graph_app.post('/create_space',
               tags=['create_space'],
               response_model=BaseResponse,
               summary='创建graph空间'
               )(create_space)

graph_app.post('/create_attribute',
               tags=['create_attribute'],
               response_model=BaseResponse,
               summary='创建图属性'
               )(create_attribute)

graph_app.post('/batch_insert_vertex',
               tags=['batch_insert_vertex'],
               response_model=BaseResponse,
               summary='插入点数据'
               )(batch_insert_vertex)

graph_app.post('/del_space',
               tags=['del_space_data'],
               response_model=BaseResponse,
               summary='删除'
               )(del_space_data)

graph_app.post('/generate_triple_data',
               tags=['generate_triple_data'],
               response_model=BaseResponse,
               summary='生成图数据'
               )(generate_triple_data)

graph_app.post('/query_graph_data',
               tags=['query_graph_data'],
               response_model=BaseResponse,
               summary='查询数据'
               )(query_graph_data)

graph_app.post('/create_space_attribute',
               tags=['create_space_attribute'],
               response_model=BaseResponse,
               summary='测试接口'
               )(create_space_attribute)


def api_start():
    uvicorn.run(graph_app, host=server_config["host"], port=server_config["port"])


if __name__ == '__main__':
    api_start()
