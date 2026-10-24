import logging
import os
import time
import uuid
from typing import Dict, Any

import nacos
# 示例配置
import yaml
from elasticsearch import Elasticsearch, AsyncElasticsearch

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


def create_data():
    current_millis = int(round(time.time() * 1000))
    timestamp = time.localtime(current_millis / 1000)
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S.", timestamp) + "{:03d}".format(current_millis % 1000)
    return formatted_time


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


def create_uuid():
    pk_value = uuid.uuid4().int & ((1 << 63) - 1)  # 取 63 位保证在有符号范围内
    if pk_value > 9223372036854775807:  # INT64 的最大正数
        pk_value = pk_value - (1 << 64)  # 转换为负数范围
    return pk_value


class ClientES:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ClientES, cls).__new__(cls)
            cls._instance.client = nacos.NacosClient(
                kwargs['server_address'],
                ak=kwargs['ak'],
                sk=kwargs['sk'],
                username=kwargs['username'],
                password=kwargs['password'],
                namespace=kwargs['namespace']
            )
        return cls._instance


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
            cls._instance.es_conn = None
            cls._instance.es_conn_async = None
            cls._instance._init_watcher()
        return cls._instance

    def conn_es(self, conn):
        hosts = [{'host': conn['host'], 'port': conn['port'], 'scheme': conn.get('scheme', 'http')}]
        basic_auth = None
        verify_certs = conn.get('verify_certs', True)
        if conn.get("user"):
            basic_auth = (conn['user'], conn['password'])
        # 同时维护同步与异步客户端，避免接口并发时重复创建
        self.es_conn = Elasticsearch(hosts, basic_auth=basic_auth, verify_certs=verify_certs)
        self.es_conn_async = AsyncElasticsearch(hosts, basic_auth=basic_auth, verify_certs=verify_certs)

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
                self.conn_es(self.config_cache["es_conn_config"]["es_connect"])
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
            self.conn_es(self.config_cache["es_conn_config"]["es_connect"])
        except Exception as e:
            print(f"Error fetching initial config from Nacos: {e}")

    def get_config(self) -> Dict[str, Any]:
        return self.config_cache

    def es_client(self):
        return self.es_conn

    def es_client_async(self):
        return self.es_conn_async
