import os
import uuid
from typing import Dict, Any
from urllib import parse

import nacos
# 示例配置
import yaml
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, DeclarativeMeta

# 初始化Nacos客户端
# NACOS_SERVER_ADDRESS = os.getenv('NACOS_SERVER_ADDRESS')
# NAMESPACE = os.getenv('NAMESPACE')
# DATA_ID = os.getenv('DATA_ID')
# GROUP = os.getenv('GROUP')
NACOS_SERVER_ADDRESS = "http://10.15.12.12:8848"
NACOS_AK = os.getenv('NACOS_AK')
NACOS_SK = os.getenv('NACOS_SK')
NACOS_USERNAME = os.getenv('NACOS_USERNAME')
NACOS_PASSWORD = os.getenv('NACOS_PASSWORD')
NAMESPACE = "rag-ai-dev"
DATA_ID = "index_data_config_py"
GROUP = "DEFAULT_GROUP"
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
        config = client.get_config(data_id, group)
        config_data = yaml.load(config, Loader=yaml.FullLoader)
        config_cache = config
        return config_data
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
            cls._instance.sessionLocal = None
            cls._instance.base = None
            cls._instance.metadata = None
            cls._instance.engine = None
            cls._instance._init_watcher()
        return cls._instance

    def conn_mysql(self, conn):
        if conn["user"]:
            pwd = parse.quote_plus(conn['passwd'])
            mysql_sqlalchemy_database_url = f"mysql+pymysql://{conn['user']}:{pwd}@{conn['host']}:{conn['port']}/{conn['db_base']}"
            self.engine = create_engine(mysql_sqlalchemy_database_url)
            self.sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.metadata = MetaData()
            self.base: DeclarativeMeta = declarative_base(metadata=self.metadata)

    def _init_watcher(self):
        def config_change_callback(config):
            try:
                config_data = yaml.load(config["content"], Loader=yaml.FullLoader)
                self.conn_mysql(config_data["mysql_connect"])
                print("Updated config:", self.config_cache)
            except Exception as e:
                print(f"Error parsing config: {e}")

        self.client.add_config_watcher(DATA_ID, GROUP, config_change_callback)

    def load_initial_config(self):
        try:
            config = self.client.get_config(DATA_ID, GROUP)
            config_data = yaml.load(config, Loader=yaml.FullLoader)
            self.conn_mysql(config_data["mysql_connect"])
            self.config_cache = config_data
        except Exception as e:
            print(f"Error fetching initial config from Nacos: {e}")

    def get_config(self) -> Dict[str, Any]:
        return self.config_cache

    def mysql_client(self):
        db = self.sessionLocal()
        try:
            return db
        finally:
            db.close()

    def mysql_base(self):
        return self.base

    def mysql_engine(self):
        return self.engine

    def mysql_metadata(self):
        return self.metadata
