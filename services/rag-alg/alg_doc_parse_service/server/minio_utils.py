from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from langchain_core.document_loaders import Blob
from minio import Minio

from log import logger
from .nacos_utils import DocParseConfig


@dataclass
class MinioConfig:
    endpoint: str
    access_key: str | None = None
    secret_key: str | None = None
    session_token: str | None = None
    secure: bool = True
    region: str | None = None
    cert_check: bool = True


class MinioFile:
    def __init__(self, minio_path: str):
        # 考虑并行效率 每个线程独立使用一个minIO client 而不是复用同一个
        java_config = DocParseConfig().configs['java-common']
        client_config = java_config['minio']
        raw_url = client_config['uri'].replace(
            '${server.host-ip}',
            java_config['server']['host-ip']
        )
        prefix = "https://" if raw_url.startswith("https://") else "http://"
        url = raw_url[len(prefix):]
        client_config = MinioConfig(
            url,
            access_key=client_config['access-key'],
            secret_key=client_config['secret-key'],
            secure='https://' in client_config['uri']
        )
        logger.debug(f'创建minIO client, URL: {url}')
        self.client = Minio(
            **client_config.__dict__
        )
        # self.client = Minio(
        #     endpoint="10.15.12.11:9000", # Minio服务器的IP及端口
        #     access_key="minioadmin", # 访问密钥
        #     secret_key="minioadmin", # 秘钥
        #     secure=False # 是否使用安全连接
        # )

        self.minio_path = Path(minio_path)
        self.bucket_name = self.minio_path.parts[0]
        self.object_name = str(Path(*self.minio_path.parts[1:]))

        self._file_bytes: bytes | None = None

    def get_file_bytes(self) -> bytes:
        if not self._file_bytes:
            self.object_name = self.object_name.replace('\\', '/')
            logger.debug(f'[Request]发送minIO请求, bucket_name: {self.bucket_name}, object_name: {self.object_name}')
            with self.client.get_object(bucket_name=self.bucket_name, object_name=self.object_name) as response:
                self._file_bytes = response.read()
            logger.debug('请求成功')
        return self._file_bytes

    def put_object(self, file_stream: BinaryIO, length: int):
        logger.debug('保存中')
        self.client.put_object(bucket_name=self.bucket_name, object_name=self.object_name, data=file_stream, length=length)
        file_stream.seek(0)
        self._file_bytes = file_stream.read()
        logger.debug('保存成功')

    def get_blob(self) -> Blob:
        return Blob.from_data(self.get_file_bytes(), path=str(self.minio_path))
