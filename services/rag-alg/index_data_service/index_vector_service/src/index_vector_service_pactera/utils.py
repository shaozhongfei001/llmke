#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/22 16:32
# @Author  : yuxj
# @File    : utils.py
import logging
import os
import time
import uuid
from typing import Dict, Any

import nacos
# 示例配置
import yaml
from pymilvus import connections, db, MilvusException

# 初始化Nacos客户端
NACOS_SERVER_ADDRESS = os.getenv('NACOS_SERVER_ADDRESS')
NACOS_AK = os.getenv('NACOS_AK')
NACOS_SK = os.getenv('NACOS_SK')
NACOS_USERNAME = os.getenv('NACOS_USERNAME')
NACOS_PASSWORD = os.getenv('NACOS_PASSWORD')
NAMESPACE = os.getenv('NAMESPACE')
DATA_ID = os.getenv('DATA_ID')
GROUP = os.getenv('GROUP')
# NACOS_SERVER_ADDRESS = "http://10.2.22.20:8848"
# NAMESPACE = "rag-ai-dev"
# DATA_ID = "index_data_config_py"
# GROUP = "DEFAULT_GROUP"
client = nacos.NacosClient(
    NACOS_SERVER_ADDRESS,
    namespace=NAMESPACE,
    ak=NACOS_AK,
    sk=NACOS_SK,
    username=NACOS_USERNAME,
    password=NACOS_PASSWORD
)
# 全局变量存储配置
config_cache = None


def return_nacos_model():
    config_manager = ConfigManager(
        server_address=NACOS_SERVER_ADDRESS,
        namespace=NAMESPACE,
        data_id=DATA_ID,
        group=GROUP,
        ak=NACOS_AK,
        sk=NACOS_SK,
        username=NACOS_USERNAME,
        password=NACOS_PASSWORD
    )
    return config_manager


def get_config(data_id=DATA_ID, group=GROUP) -> Dict:
    """
    从 Nacos 获取配置。
    """
    global config_cache
    try:
        config1 = client.get_config(data_id, group)
        config_data1 = yaml.load(config1, Loader=yaml.FullLoader)
        config2 = client.get_config("alg_common_py", group)
        if config2:
            config_data2 = yaml.load(config2, Loader=yaml.FullLoader)
        else:
            config_data2 = {}
        config_cache = {**config_data2, **config_data1}
        return config_cache
    except Exception as e:
        print(f"Error fetching config from Nacos: {e}")
        return config_cache  # 返回缓存的配置


def create_data():
    current_millis = int(round(time.time() * 1000))
    timestamp = time.localtime(current_millis / 1000)
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S.", timestamp) + "{:03d}".format(current_millis % 1000)
    return formatted_time


def create_uuid():
    pk_value = uuid.uuid4().int & ((1 << 63) - 1)  # 取 63 位保证在有符号范围内
    if pk_value > 9223372036854775807:  # INT64 的最大正数
        pk_value = pk_value - (1 << 64)  # 转换为负数范围
    return pk_value


class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.client = nacos.NacosClient(
                kwargs['server_address'],
                ak=kwargs['ak'],
                sk=kwargs['sk'],
                username=kwargs['username'],
                password=kwargs['password'],
                namespace=kwargs['namespace']
            )
            cls._instance.config_cache = {}
            cls._instance._init_watcher()
        return cls._instance

    def conn_milvus(self, milvus_config, milvus_database=None):
        milvus_database = milvus_database or milvus_config["milvus_database"]
        host = milvus_config["milvus_connect"]["host"]
        port = milvus_config["milvus_connect"]["port"]
        # 兼容可选认证参数
        user = milvus_config["milvus_connect"].get("user")
        password = milvus_config["milvus_connect"].get("password")
        secure = milvus_config["milvus_connect"].get("secure")
        connect_kwargs = {"host": host, "port": port}
        if user:
            connect_kwargs["user"] = user
        if password:
            connect_kwargs["password"] = password
        if secure is not None:
            connect_kwargs["secure"] = bool(secure)
        try:
            connections.connect(alias=milvus_database, db_name=milvus_database, **connect_kwargs)
            connections.connect(alias="graph_base", db_name="graph_base", **connect_kwargs)
        except MilvusException as e:
            if e.code == 800:
                print(f"未检测到{milvus_database}库，正在创建")
                connections.connect(**connect_kwargs)
                try:
                    db.create_database(milvus_database)
                except Exception as e:
                    print(e)
                try:
                    db.create_database("graph_base")
                except Exception as e:
                    print(e)
                connections.disconnect(alias=milvus_database)
                connections.disconnect(alias="graph_base")
                print(f"重新链接{milvus_database}")
                connections.connect(alias=milvus_database, db_name=milvus_database, **connect_kwargs)
                connections.connect(alias="graph_base", db_name="graph_base", **connect_kwargs)
            else:
                raise e

    def close_milvus(self, milvus_config):
        milvus_database = milvus_config["milvus_database"]
        try:
            # connections.remove_connection(alias=milvus_database)
            connections.disconnect(alias=milvus_database)
        except Exception as e:
            print(e)

    def _init_watcher(self):
        def config_change_callback(config):
            try:
                if config["data_id"] == DATA_ID:
                    config_data1 = yaml.load(config["content"], Loader=yaml.FullLoader)
                    config2 = self.client.get_config("alg_common_py", GROUP)
                    if config2:
                        config_data2 = yaml.load(config2, Loader=yaml.FullLoader)
                    else:
                        config_data2 = {}
                else:
                    config_data1 = yaml.load(config["content"], Loader=yaml.FullLoader)
                    config2 = self.client.get_config(DATA_ID, GROUP)
                    config_data2 = yaml.load(config2, Loader=yaml.FullLoader)
                self.config_cache = {**config_data2, **config_data1}
                self.close_milvus(self.config_cache["milvus_conn_config"])
                self.conn_milvus(self.config_cache["milvus_conn_config"])
                print("Updated config:", self.config_cache)
            except Exception as e:
                print(f"Error parsing config: {e}")

        self.client.add_config_watcher(DATA_ID, GROUP, config_change_callback)
        self.client.add_config_watcher("alg_common_py", GROUP, config_change_callback)

    def load_initial_config(self):
        try:
            config1 = self.client.get_config(DATA_ID, GROUP)
            config_data1 = yaml.load(config1, Loader=yaml.FullLoader)
            config2 = self.client.get_config("alg_common_py", GROUP)
            if config2:
                config_data2 = yaml.load(config2, Loader=yaml.FullLoader)
            else:
                config_data2 = {}
            self.config_cache = {**config_data2, **config_data1}
            self.close_milvus(self.config_cache["milvus_conn_config"])
            self.conn_milvus(self.config_cache["milvus_conn_config"])
        except Exception as e:
            print(f"Error fetching initial config from Nacos: {e}")

    def get_config(self) -> Dict[str, Any]:
        return self.config_cache

    def conn_milvus_service(self):
        self.conn_milvus(self.config_cache["milvus_conn_config"])

    def ensure_connection(self, using="default"):
        """
        判断milvus的链接是否断开
        Args:
            using:

        Returns:

        """
        try:
            _ = connections.get_connection_addr(using)
        except Exception as e:
            logging.info(f"milvus 链接断开， 重新链接,{e}")
            self.close_milvus(self.config_cache["milvus_conn_config"])
            self.conn_milvus(self.config_cache["milvus_conn_config"])
