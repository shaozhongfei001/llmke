# -*- coding: utf-8 -*-

from typing import Dict, Optional
import httpx
import traceback

from app.operators.common.log import logger as g_logger
from app.base import CECTableRetrieveConfig

class LLMClient(object):

    def __init__(self,
                 config: CECTableRetrieveConfig,
                 logger: object = None,
                 timeout: int = 120) -> None:

        self.url = config.model_info["url"]
        self.model = config.model_name
        self.timout = timeout
        self.logger = logger or g_logger

    async def completions(self,
                         prompt: str,
                         generation_params: Optional[Dict] = None) -> str:
        """
        Sends a completion request to the CZAPIClient with the given prompt and model.

        Args:
            prompt (str): The prompt to be completed.
            generation_params (Optional[Dict], optional): Additional parameters for completion generation. Defaults to None.
            
        Returns:
            str: The completion result..
        """
        params = {
            "model": self.model,
            "prompt": prompt,
        }
        if generation_params is not None:
            params.update(generation_params)
        
        # 处理URL，避免修改原始URL
        request_url = self.url
        if '/chat' in request_url:
            request_url = request_url.replace('/chat', '')
            
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timout)) as client:
                response = await client.post(
                    url=request_url,
                    json=params
                )
                response.raise_for_status()
                result = response.json().get("choices")[0]["text"]
                _char = '</think>'
                if _char in result:
                    result = result[result.index(_char)+len(_char):].strip()
        except Exception:
            msg = traceback.format_exc().replace('\n', '\t')
            self.logger.error('LLMClient completions request error: {}'.format(msg))
            raise
        return result
