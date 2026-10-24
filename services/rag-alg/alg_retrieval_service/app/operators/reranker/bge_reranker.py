# -*- coding: utf-8 -*-

from typing import List
import httpx
import traceback

from app.config.conf import DEFAULT_RERANK_MAX_TOKENS, RERANK_MAX_TOKEN_DELTA_DEFAULT
from app.operators.common.log import logger as g_logger
from app.operators.utils.token_utils import truncate_text_by_tokens


class BGEReranker(object):

    def __init__(self,
                 config: object = None,
                 logger: object = None) -> None:
        self.config = config
        self.logger = logger or g_logger

    async def rerank(self,
               query: str,
               documents: List,
               server_config) -> List:
        model_name = server_config["rerank_model"]["model_name"]
        url = server_config["rerank_server"][model_name]["server_url"]
        
        # 获取模型的最大token限制，从配置文件读取
        max_tokens = server_config["rerank_server"].get(model_name, {}).get("max_tokens", DEFAULT_RERANK_MAX_TOKENS)
        max_token_delta = server_config.get("rerank_max_token_delta", RERANK_MAX_TOKEN_DELTA_DEFAULT)

        # 处理文档内容，确保不超过模型的最大token限制
        processed_documents = []
        for document in documents:
            doc_text = document.page_content
            
            truncated_text = truncate_text_by_tokens(doc_text, max_tokens, max_token_delta=max_token_delta)
            processed_documents.append(truncated_text)

        inputs = {
            "model": model_name,
            "query": query,
            "documents": processed_documents
        }
        if not processed_documents:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                response = await client.post(url, json=inputs, headers={"Content-Type": "application/json"})
                response.raise_for_status()
                index_rerank = list(map(lambda x: x['index'], response.json().get('results')))
        except Exception:
            msg = traceback.format_exc().replace('\n', '\t')
            self.logger.error('RerankerClient completions request error: {}'.format(msg))
            raise
        return index_rerank
