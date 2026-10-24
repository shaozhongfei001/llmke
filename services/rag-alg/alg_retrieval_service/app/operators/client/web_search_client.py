import time
import asyncio
from loguru import logger
from typing import Dict, Any, List
from zhipuai import ZhipuAI


class WebSearchClient:
    """
    封装联网搜索服务请求，支持同步和异步，带重试、超时和统一异常处理
    """

    @classmethod
    def request_sync(cls, api_key: str, api_params: Dict[str, Any], 
                     retries: int = 3, timeout: int = 30):
        """
        同步请求联网搜索服务
        """
        start = time.time()
        client = ZhipuAI(api_key=api_key)
        
        try:
            response = client.web_search.web_search(**api_params)
            logger.info(f"同步请求联网搜索服务耗时: {time.time() - start:.3f}s, "
                      f"请求参数: {api_params}")
            return response
        except Exception as e:
            logger.error(f"联网搜索服务同步请求失败: {e}")
            raise Exception(f"请求联网搜索服务失败: {e}")

    @classmethod
    async def request(cls, api_key: str, api_params: Dict[str, Any]):
        """
        异步请求联网搜索服务
        """
        start = time.time()
        client = ZhipuAI(api_key=api_key)
        
        try:
            # 使用 asyncio.to_thread 包装同步调用
            response = await asyncio.to_thread(client.web_search.web_search, **api_params)
            logger.info(f"异步请求联网搜索服务耗时: {time.time() - start:.3f}s, "
                      f"请求参数: {api_params}, response: {response}")
            return response
        except Exception as e:
            logger.error(f"联网搜索服务异步请求发生错误，请求参数: {api_params}")
            raise Exception(f"请求联网搜索服务失败: {e}")
