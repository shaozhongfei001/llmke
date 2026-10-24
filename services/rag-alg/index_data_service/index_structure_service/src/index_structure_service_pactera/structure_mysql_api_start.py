#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/30 15:14
# @Author  : yuxj
# @File    : vector_milvus_api_start.py
import uvicorn
from fastapi import FastAPI
import sys
import os
from contextlib import asynccontextmanager

from utils import return_nacos_model, get_config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base import BaseResponse
from mysql_kb_service import crud_router, create_table_endpoint, select_item, insert_item, delete_item,update_item

server_config = get_config()["mysql_server"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    # 初始化配置管理器
    config_manager = return_nacos_model()
    # 强制刷新一次配置
    config_manager.load_initial_config()
    print("init config:", config_manager.get_config())
    
    yield
    
    # 关闭时执行
    config_manager = return_nacos_model()
    config_manager.mysql_engine().dispose()


mysql_app = FastAPI(lifespan=lifespan)


mysql_app.include_router(crud_router)

mysql_app.post("/create_table",
               tags=["create_table"],
               response_model=BaseResponse,
               summary="动态创建mysql表"
               )(create_table_endpoint)

mysql_app.post("/select_data",
               tags=["select_data"],
               response_model=BaseResponse,
               summary="根据sql查询数据"
               )(select_item)

mysql_app.post("/insert_data",
               tags=["insert_data"],
               response_model=BaseResponse,
               summary="添加数据"
               )(insert_item)

mysql_app.post("/update_data",
               tags=["update_data"],
               response_model=BaseResponse,
               summary="修改数据"
               )(update_item)

mysql_app.post("/del_data",
               tags=["del_data"],
               response_model=BaseResponse,
               summary="删除数据"
               )(delete_item)


def api_start():
    uvicorn.run(mysql_app, host=server_config["host"], port=server_config["port"])


if __name__ == '__main__':
    api_start()
