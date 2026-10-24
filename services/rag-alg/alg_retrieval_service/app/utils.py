#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/22 16:32
# @Author  : yuxj
# @File    : utils.py
import base64
import datetime
import logging
import os
import time
import uuid
from typing import Dict, Any

import nacos
import yaml

from app.operators.common.log import logger
# 初始化Nacos客户端
from app.retrieval_config import NACOS_SERVER_ADDRESS, NACOS_AK, NACOS_SK, NACOS_USERNAME, NACOS_PASSWORD, NAMESPACE, \
    DATA_ID, GROUP

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
        data_id1=DATA_ID,
        data_id2="alg_common_py",
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


def create_base64(query):
    now = datetime.datetime.now()
    timestamp_ms = int(now.timestamp() * 1000) + now.microsecond // 1000
    original_string = f"{query}_{timestamp_ms}"
    encoded_string = base64.b64encode(original_string.encode('utf-8')).decode('utf-8')
    return encoded_string


def create_uuid():
    pk_value = uuid.uuid4().int & ((1 << 63) - 1)  # 取 63 位保证在有符号范围内
    if pk_value > 9223372036854775807:  # INT64 的最大正数
        pk_value = pk_value - (1 << 64)  # 转换为负数范围
    return pk_value


def create_data():
    current_millis = int(round(time.time() * 1000))
    timestamp = time.localtime(current_millis / 1000)
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S.", timestamp) + "{:03d}".format(current_millis % 1000)
    return formatted_time


class LoggerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._setup_logging()
        return cls._instance

    def _setup_logging(self):
        log_path = "../logs"
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        handler1 = logging.StreamHandler()
        create_time_str = create_data().split(" ")[0]
        handler2 = logging.FileHandler(filename=f'{log_path}/retrieval_data_{create_time_str}.log')
        formatter = logging.Formatter(f'[PID: {os.getpid()}] %(levelname)s [%(asctime)s] '
                                      f'[%(name)s:%(filename)s:%(lineno)s:%(funcName)s] %(message)s')
        handler1.setFormatter(formatter)
        handler2.setFormatter(formatter)
        logger.addHandler(handler1)  # 将日志输出至屏幕
        logger.addHandler(handler2)  # 将日志输出至文件

    @staticmethod
    def get_logger(name="app"):
        return logging.getLogger(name)


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
            cls._instance.logger = logger
            cls._instance.logger.info("Initializing ConfigManager...")
            cls._instance.config_cache = {}
            cls._instance._init_watcher()
        return cls._instance

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
        except Exception as e:
            print(f"Error fetching initial config from Nacos: {e}")

    def get_config(self) -> Dict[str, Any]:
        # 懒加载：若缓存为空，尝试加载一次初始配置
        if not self.config_cache:
            try:
                self.load_initial_config()
            except Exception as e:
                logger.error(f"Error on lazy loading config: {e}")
        return self.config_cache
