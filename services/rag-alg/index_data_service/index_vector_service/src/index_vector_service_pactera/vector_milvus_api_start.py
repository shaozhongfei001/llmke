#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/30 15:14
# @Author  : yuxj
# @File    : vector_milvus_api_start.py
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from view.urls import register_routes
from middleware import register_middlewares
from utils import get_config, return_nacos_model
from operators.common.log import logger

server_config = get_config()["milvus_server"]
milvus_config = get_config()["milvus_conn_config"]
host = milvus_config["milvus_connect"]["host"]
port = milvus_config["milvus_connect"]["port"]

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

milvus_database = milvus_config["milvus_database"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    # try:
    #     connections.connect(alias=milvus_database, host=host, port=port, db_name=milvus_database)
    # except MilvusException as e:
    #     if e.code == 800:
    #         print(f"未检测到{milvus_database}库，正在创建")
    #         connections.connect(host=host, port=port)
    #         db.create_database(milvus_database)
    #         connections.remove_connection(alias=milvus_database)
    #         print(f"重新链接{milvus_database}")
    #         connections.connect(alias=milvus_database, host=host, port=port, db_name=milvus_database)
    #     else:
    #         raise e
    # 初始化配置管理器
    config_manager = return_nacos_model()
    # 强制刷新一次配置
    config_manager.load_initial_config()
    logger.info(f"init config:{config_manager.get_config()}")
    print("init config:", config_manager.get_config())
    
    yield
    
    # 关闭时执行（如果需要的话）
    pass


vector_app = FastAPI(lifespan=lifespan)

# 添加请求日志中间件
register_middlewares(vector_app)
register_routes(app=vector_app)


def api_start():
    uvicorn.run(vector_app, host=server_config["host"], port=server_config["port"])


if __name__ == '__main__':
    api_start()
