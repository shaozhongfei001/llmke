import time
import asyncio
from loguru import logger
from typing import Dict, Any, List

# [R12-ADAPT-ALG-04] zhipuai 是智谱联网搜索 SDK，R12 无对应凭据与出网通路，按任务书不安装该依赖。
# 原实现为模块级 `from zhipuai import ZhipuAI`，会把"未启用联网搜索"的场景也拖成 import 失败。
# 改为惰性导入：只有真正调用联网搜索时才导入，失败时抛出明确错误（不静默降级为假结果）。


def _load_zhipuai():
    try:
        from zhipuai import ZhipuAI  # noqa: PLC0415 - 惰性导入是本处刻意行为
        return ZhipuAI
    except ImportError as e:
        raise RuntimeError(
            "联网搜索需要 zhipuai SDK，但当前 R12 venv 未安装（见 status/alg.md 依赖处置表）；"
            "请关闭 enable_web_search 或安装 zhipuai 后重启"
        ) from e


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
        client = _load_zhipuai()(api_key=api_key)
        
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
        client = _load_zhipuai()(api_key=api_key)
        
        try:
            # 使用 asyncio.to_thread 包装同步调用
            response = await asyncio.to_thread(client.web_search.web_search, **api_params)
            logger.info(f"异步请求联网搜索服务耗时: {time.time() - start:.3f}s, "
                      f"请求参数: {api_params}, response: {response}")
            return response
        except Exception as e:
            logger.error(f"联网搜索服务异步请求发生错误，请求参数: {api_params}")
            raise Exception(f"请求联网搜索服务失败: {e}")
