import time
import httpx
from loguru import logger
from typing import Dict, Any
from json import JSONDecodeError


class GraphClient:
    """
    封装图检索服务请求，支持同步和异步，带重试、超时和统一异常处理
    """

    @classmethod
    def request_sync(cls, graph_url: str, data: Dict[str, Any], 
                    retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
        """
        同步请求图检索服务
        """
        start = time.time()

        with httpx.Client(
                transport=httpx.HTTPTransport(retries=retries),
                timeout=httpx.Timeout(timeout)
        ) as client:
            try:
                response = client.post(graph_url, json=data)
                response.raise_for_status()
                result = response.json()
                logger.info(f"同步请求图检索服务耗时: {time.time() - start:.3f}s, "
                          f"请求数据: {data}, 图检索结果: {result}")
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"图检索服务同步请求失败，状态码: {e.response.status_code}, "
                           f"响应内容: {e.response.text}")
                raise Exception(f"请求图检索服务失败: {e}")
            except Exception as e:
                text = getattr(e, 'response', None) and e.response.text or str(e)
                logger.error(f"图检索服务同步请求失败: {text}")
                raise Exception(f"请求图检索服务失败: {e}")

    @classmethod
    async def request(cls, graph_url: str, data: Dict[str, Any],
                     retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
        """
        异步请求图检索服务
        """
        start = time.time()
        
        async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=retries),
                timeout=httpx.Timeout(timeout)
        ) as client:
            response = await client.post(graph_url, json=data)
            response.raise_for_status()
            try:
                result = response.json()
            except JSONDecodeError:
                logger.error(f"异步请求图检索服务返回结果JSON解析失败: URL={graph_url}, 数据={data}, 返回内容={response.text}")
                raise
            logger.info(f"异步请求图检索服务耗时: {time.time() - start:.3f}s, URL: {graph_url}, 请求数据: {data}, 图检索结果: {result}")
            return result
