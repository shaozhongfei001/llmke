import os
from functools import partial

import nacos
import yaml

from log import logger

NACOS_SERVER_ADDRESS = os.environ.get('NACOS_SERVER_ADDRESS', 'http://10.2.22.20:8848')
NACOS_NAMESPACE = os.environ.get('NACOS_NAMESPACE', 'rag-ai-dev')
NACOS_DATA_ID = os.environ.get('NACOS_DATA_ID', 'alg_doc_config_py')
NACOS_GROUP = os.environ.get('NACOS_GROUP', 'DEFAULT_GROUP')
NACOS_AK = os.environ.get('NACOS_AK')
NACOS_SK = os.environ.get('NACOS_SK')
NACOS_USERNAME = os.environ.get('NACOS_USERNAME')
NACOS_PASSWORD = os.environ.get('NACOS_PASSWORD')


class DocParseConfig:
    _instance = None

    @property
    def config(self):
        return self._instance.configs['doc-parse']

    @classmethod
    def create_client(cls, nacos_server_address, nacos_namespace, nacos_data_id, nacos_group):
        # 创建nacos client
        client = nacos.NacosClient(
            nacos_server_address,
            namespace=nacos_namespace,
            ak=NACOS_AK,
            sk=NACOS_SK,
            username=NACOS_USERNAME,
            password=NACOS_PASSWORD
        )

        # 读取nacos配置
        config = client.get_config(nacos_data_id, nacos_group, no_snapshot=True)
        config = yaml.load(config, Loader=yaml.FullLoader)

        # 添加nacos watcher
        client.add_config_watcher(nacos_data_id, nacos_group, cls._instance.config_change_callback)

        cls._instance.clients = {'doc-parse': client}
        cls._instance.configs = {'doc-parse': config}

        other_nacos = config['other-nacos']
        for name, nacos_config in other_nacos.items():
            client = nacos.NacosClient(
                nacos_server_address,
                namespace=nacos_config['namespace'],
                ak=NACOS_AK,
                sk=NACOS_SK,
                username=NACOS_USERNAME,
                password=NACOS_PASSWORD
            )
            data_id = nacos_config['data-id']
            group = nacos_config['group']
            cls._instance.configs[name] = yaml.load(
                client.get_config(data_id, group, no_snapshot=True),
                Loader=yaml.FullLoader
            )
            callback_func = partial(cls._instance.config_change_callback, config_name=name)
            callback_func.__name__ = cls._instance.config_change_callback.__name__
            client.add_config_watcher(
                data_id,
                group,
                callback_func
            )
            cls._instance.clients[name] = client

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DocParseConfig, cls).__new__(cls)
            cls.create_client(NACOS_SERVER_ADDRESS, NACOS_NAMESPACE, NACOS_DATA_ID, NACOS_GROUP)
        return cls._instance

    def config_change_callback(self, config, config_name='doc-parse'):
        try:
            logger.info('监测到配置修改')
            self.configs[config_name] = yaml.load(config['content'], Loader=yaml.FullLoader)
            logger.info(f'{config_name}更新成功')
        except Exception as e:
            logger.warning(f'{config_name}更新失败：{e}')
            if self.configs.get(config_name) is None:
                raise Exception(f'Nacos访问错误：{e}')
