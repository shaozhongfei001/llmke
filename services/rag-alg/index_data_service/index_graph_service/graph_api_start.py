#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 15:14
# @Author  : yuxj
# @File    : es_kb_service.py
import functools
import os
import sys
import traceback
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from base import BaseResponse
from graph_summary import generate_community, query_community, del_community
from graph_service import create_space, generate_triple_data, create_attribute, batch_insert_vertex, query_graph_data, del_space_data, create_space_attribute
from middleware import register_middlewares
from utils import get_config, return_nacos_model
from operators.common.log import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def _safe_entry(fn, name):
    """R15-A17/D-A17-1：接口级异常兜底。

    原来函数体抛异常时 FastAPI 直接回 HTTP 500 且 body 为空，
    调用方（Java 侧）只能记下 "500 Internal Server Error"，失败原因彻底丢失。
    实测 file 999008 就是这样：既没有可读原因，也没有结构化返回，
    排查只能靠翻 Python 栈——而 loguru 的 sink 在相对路径 logs/graph_service/ 下，
    不看代码根本找不到。

    这里统一转成 BaseResponse(code=500, msg=异常类型+摘要)，
    同时把堆栈写进服务日志（含文件名/行号），失败必须可定位。
    """
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"{name} 未捕获异常 {type(e).__name__}: {e}\n{tb[-1500:]}")
            return BaseResponse(code=500, msg=f"{name} 执行异常 {type(e).__name__}: {str(e)[:180]}")
    return wrapper

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
               )(_safe_entry(generate_triple_data, "generate_triple_data"))

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

# ===== R13 GraphRAG：社区检测 / 分级摘要 / global-local 查询 =====
graph_app.post('/generate_community',
               tags=['GraphRAG'],
               response_model=BaseResponse,
               summary='社区检测并生成社区摘要（LLM），双写 ES/Milvus community_summary_<kb>'
               )(generate_community)

graph_app.post('/query_community',
               tags=['GraphRAG'],
               response_model=BaseResponse,
               summary='global：社区摘要 reduce 汇总；local：按实体命中社区'
               )(query_community)

graph_app.post('/del_community',
               tags=['GraphRAG'],
               response_model=BaseResponse,
               summary='删除社区摘要索引（ES+Milvus）'
               )(del_community)
