#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/31 10:04
# @Author  : yuxj
# @File    : base.py
from typing import Any, List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import pydantic
from pydantic import BaseModel


# from sqlalchemy import create_engine, MetaData
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker, DeclarativeMeta
#
# from mysql_kb_config import MYSQL_SQLALCHEMY_DATABASE_URL
#
# engine = create_engine(MYSQL_SQLALCHEMY_DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# metadata = MetaData()
# Base: DeclarativeMeta = declarative_base(metadata=metadata)
#
#
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


class BaseResponse(BaseModel):
    code: int = pydantic.Field(200, description="API status code")
    msg: str = pydantic.Field("success", description="API status message")
    data: Any = pydantic.Field(None, description="API data")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
            }
        }


class DataModel(BaseModel):
    table_name: str
    data_list: List[Dict]


class QueryModel(BaseModel):
    query_sql: str


class UpdateModel(BaseModel):
    update_sql: str


class DeleteItem(BaseModel):
    table_name: str
    col_name: str
    col_values: List[str]
