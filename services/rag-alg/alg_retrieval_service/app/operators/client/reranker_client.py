import time
import httpx
from loguru import logger
from typing import Dict, List, Any


class RerankerClient:
    """
    封装重排序服务请求，支持同步和异步，带重试、超时和统一异常处理
    """

    @classmethod
    def request_sync(cls, rerank_url: str, rerank_request: Dict[str, Any], 
                    api_key: str, retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
        """
        同步请求重排序服务
        """
        start = time.time()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': api_key
        }
        
        with httpx.Client(
                transport=httpx.HTTPTransport(retries=retries),
                timeout=httpx.Timeout(timeout)
        ) as client:
            try:
                response = client.post(rerank_url, json=rerank_request, headers=headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"同步请求重排序服务耗时: {time.time() - start:.3f}s, "
                          f"URL: {rerank_url}, 请求参数: {rerank_request}, 重排序结果: {result}")
                return result
            except Exception as e:
                logger.error(f"重排序服务同步请求失败，URL: {rerank_url}, "
                             f"response: {response.text}, "
                             f"请求参数: {rerank_request}")
                raise Exception(f"请求重排序服务失败: {e}")

    @classmethod
    async def request(cls, rerank_url: str, rerank_request: Dict[str, Any], 
                     api_key: str, retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
        """
        异步请求重排序服务
        """
        start = time.time()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': api_key
        }
        
        async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=retries),
                timeout=httpx.Timeout(timeout)
        ) as client:
            try:
                response = await client.post(rerank_url, json=rerank_request, headers=headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"异步请求重排序服务耗时: {time.time() - start:.3f}s, "
                          f"URL: {rerank_url}, 请求参数: {rerank_request}, 重排序结果: {result}")
                return result
            except Exception as e:
                logger.error(f"重排序服务异步请求发生错误，URL: {rerank_url}, "
                                 f"response: {response.text}, "
                               f"请求参数: {rerank_request}")
                raise Exception(f"请求重排序服务失败: {e}")
