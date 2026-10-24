#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/22 16:32
# @Author  : yuxj
# @File    : utils.py
import time
import uuid
from typing import Dict, Any

import nacos
import redis
import yaml

# 初始化Nacos客户端
from app.llm_config import NACOS_SERVER_ADDRESS, NACOS_AK, NACOS_SK, NACOS_USERNAME, NACOS_PASSWORD, NAMESPACE, DATA_ID, \
    GROUP

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


class RedisManager:
    """Redis 连接管理类，支持动态更新 Redis 配置信息"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            cls._instance.client = None  # Redis 连接
            cls._instance.config = {}  # 存储 Redis 配置
        return cls._instance

    def connect(self, host, port, db=0, password=None):
        """连接 Redis"""
        try:
            self.client = redis.StrictRedis(
                host=host, port=int(port), db=int(db),
                password=password, decode_responses=True
            )
            print(f"Redis 连接成功: {host}:{port}, DB: {db}")
        except Exception as e:
            print(f"Redis 连接失败: {e}")

    def update_config(self, redis_config):
        """更新 Redis 配置，并重新建立连接"""
        if redis_config != self.config:  # 只有配置变更才更新连接
            print("更新 Redis 连接配置...")
            self.config = redis_config
            self.connect(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                password=redis_config.get("password", None)
            )


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
            cls._instance.redis_manager = RedisManager()  # Redis 管理实例
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
                self.redis_manager.update_config(self.config_cache["redis_config"])  # redis
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
            self.redis_manager.update_config(self.config_cache["redis_config"])  # redis
        except Exception as e:
            print(f"Error fetching initial config from Nacos: {e}")

    def get_config(self) -> Dict[str, Any]:
        return self.config_cache

    def get_redis_config(self):
        return self.redis_manager.client
