import logging
import os
import time
import uuid
from typing import Dict, Any

import nacos
# 示例配置
import yaml
from nebula3.Config import Config
from nebula3.Exception import IOErrorException, AuthFailedException
from nebula3.gclient.net import ConnectionPool

# 初始化Nacos客户端
NACOS_SERVER_ADDRESS = os.getenv('NACOS_SERVER_ADDRESS')
NACOS_AK = os.getenv('NACOS_AK')
NACOS_SK = os.getenv('NACOS_SK')
NACOS_USERNAME = os.getenv('NACOS_USERNAME')
NACOS_PASSWORD = os.getenv('NACOS_PASSWORD')
NAMESPACE = os.getenv('NAMESPACE')
DATA_ID = os.getenv('DATA_ID')
GROUP = os.getenv('GROUP')
# NACOS_SERVER_ADDRESS = "http://10.15.12.11:8848"
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
            cls._instance._last_check_time = None
            cls._instance.pool = None
            cls._instance.session = None
            cls._instance._init_watcher()
        return cls._instance

    def create_connection_pool(self, config_data):
        config = Config()
        config.idle_time = 3600  # 允许的最大空闲时间（秒）
        config.timeout = 30000  # 请求超时时间（毫秒）
        config.max_connection_pool_size = 10  # 最大连接池大小
        config.min_connection_pool_size = 1  # 最小连接池大小
        # 连接 Nebula Graph 的地址和端口
        pool = ConnectionPool()
        if not pool.init([(config_data["host"], config_data["port"])], config):
            raise Exception("Failed to initialize connection pool")
        return pool

    def open_session(self, pool, config_data):
        # 用户名和密码，使用自己配置的 NebulaGraph 用户信息
        session = pool.get_session(config_data["user"], config_data["user"])
        if session is None:
            raise Exception("Failed to create session")
        return session

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
                self.pool = self.create_connection_pool(self.config_cache["graph_connect"])
                self.session = self.open_session(self.pool, self.config_cache["graph_connect"])
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
            self.pool = self.create_connection_pool(self.config_cache["graph_connect"])
            self.session = self.open_session(self.pool, self.config_cache["graph_connect"])
        except Exception as e:
            print(f"Error fetching initial config from Nacos: {e}")

    def get_config(self) -> Dict[str, Any]:
        return self.config_cache

    @property
    def last_check_time(self):
        if self._last_check_time is None:
            self._last_check_time = 0  # 默认值
        return self._last_check_time

    @last_check_time.setter
    def last_check_time(self, value):
        self._last_check_time = value

    def session_client(self, release_flag=False):
        """

        Args:
            release_flag:  是否释放

        Returns:

        """
        current_time = time.time()
        if release_flag:
            self.session.release()  # 释放旧 Session
            return_nacos_model().load_initial_config()
            return self.session
        elif self.session and current_time - self.last_check_time < 300:  # 5 分钟内无需重新检查
            try:
                self.session.execute('SHOW SPACES;')
            except:
                self.session.release()  # 释放旧 Session
                return_nacos_model().load_initial_config()
            return self.session
        try:
            self.session.release()  # 释放旧 Session
            return_nacos_model().load_initial_config()
            self.last_check_time = current_time  # 更新检查时间
        except (IOErrorException, AuthFailedException) as e:
            print(f"会话失效，需要重新连接: {e}")
            return_nacos_model().load_initial_config()
        except Exception as e:
            print(f"未知错误，需要重新连接: {e}")
            return_nacos_model().load_initial_config()

        return self.session

    def close_session(self, session=None):
        if session:
            session.release()
        else:
            self.session.release()  # 释放旧 Session

    def close_pool(self):
        if self.pool:
            self.pool.close()
