#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/12 16:01
# @Author  : yuxj
# @File    : init_database.py
from datetime import datetime

from index_structure_service.base import Base, engine
import models

def create_tables():
    Base.metadata.create_all(bind=engine)


def reset_tables():
    Base.metadata.drop_all(bind=engine)
    create_tables()


if __name__ == '__main__':
    create_tables()
    # import argparse
    #
    # parser = argparse.ArgumentParser(description="please specify only one operate method once time.")
    #
    # parser.add_argument(
    #     "--create-tables",
    #     action="store_true",
    #     help=("create empty tables if not existed")
    # )
    # parser.add_argument(
    #     "--clear-tables",
    #     action="store_true",
    #     help=("create empty tables, or drop the database tables before recreate vector stores")
    # )
    #
    # args = parser.parse_args()
    # start_time = datetime.now()
    #
    # if args.create_tables:
    #     create_tables()  # confirm tables exist
    #
    # if args.clear_tables:
    #     reset_tables()
    #     print("database tables reset")
    #
    # end_time = datetime.now()
    # print(f"总计用时： {end_time - start_time}")
