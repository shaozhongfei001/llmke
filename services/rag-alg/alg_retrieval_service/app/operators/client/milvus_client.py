import time
from json import JSONDecodeError

import httpx
from loguru import logger

from app.exception.custom_exception import ResponseCodeError


class MilvusClient:
    """
    封装 milvus 请求，支持同步和异步，带重试、超时和统一异常处理
    """

    @classmethod
    def request_sync(cls, es_url: str, data: dict, retries: int = 3, timeout: int = 30) -> dict:
        """
        同步请求 milvus
        """
        start = time.time()
        with httpx.Client(
                transport=httpx.HTTPTransport(retries=retries),
                timeout=httpx.Timeout(timeout)
        ) as client:
            try:
                response = client.post(
                    es_url,
                    json=data,
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"同步请求 milvus 耗时: {time.time() - start:.3f}s, 请求 data={data}, 召回结果result={result}")
                return result
            except Exception as e:
                text = getattr(e, 'response', None) and e.response.text or str(e)
                logger.error(f"milvus 同步请求失败: {text}")
                raise Exception(f"请求milvus失败: {e}")

    @classmethod
    async def request(cls, milvus_url: str, data: dict, retries: int = 3, timeout: int = 30) -> dict:
        """
        异步请求 milvus
        """
        start = time.time()
        async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=retries),
                timeout=httpx.Timeout(timeout)
        ) as client:
            response = await client.post(
                milvus_url,
                json=data,
            )
            response.raise_for_status()
            try:
                result = response.json()
            except JSONDecodeError:
                logger.error(
                    f"异步请求 milvus index服务返回结果JSON解析失败: URL={milvus_url}, 数据={data}, 返回内容={response.text}")
                raise

            if result.get('code') != 200:
                raise ResponseCodeError(f"Milvus index服务查询结果错误 [返回码异常]: code: {result.get('code')}, 返回内容: {result}, URL: {milvus_url}, 请求参数: {data}")

            logger.info(f"异步请求 milvus index服务耗时: {time.time() - start:.3f}s, 请求 data={data}, 召回结果result={result}")
            return result
