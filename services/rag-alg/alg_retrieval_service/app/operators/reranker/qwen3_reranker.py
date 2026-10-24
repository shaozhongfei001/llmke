# -*- coding: utf-8 -*-

from typing import List
import httpx
import traceback
import json

from app.operators.common.log import logger


class Qwen3Reranker(object):
    """
    Qwen3 Rerank 模型适配器
    支持 Qwen3 系列 rerank 模型服务
    """

    def __init__(self,
                 config: object = None,
                 logger: object = None) -> None:
        self.config = config
        self.logger = logger

    async def rerank(self,
               query: str,
               documents: List,
               server_config) -> List:
        """
        Qwen3 rerank 模型调用
        Args:
            query: 查询文本
            documents: 文档列表
            server_config: 服务器配置
        Returns:
            List: 重排序后的文档索引列表
        """
        model_name = server_config["rerank_model"]["model_name"]
        url = server_config["rerank_server"][model_name]["server_url"]
        api_key = server_config["rerank_server"][model_name].get("api_key", "")
        
        # 提取文档内容
        documents_text = [document.page_content for document in documents]
        
        if not documents_text:
            return []
        
        # 构建 Qwen3 rerank 请求格式
        inputs = {
            "model": model_name,
            "query": query,
            "documents": documents_text
        }
        logger.info(f'inputs: {inputs}')
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            self.logger.info(f"调用 Qwen3 rerank 模型: {model_name}, URL: {url}")
            self.logger.debug(f"Rerank 请求参数: {inputs}")
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                response = await client.post(
                    url, 
                    json=inputs, 
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Qwen3 rerank 请求失败: {response.status_code}, {response.text}")
                    return []

                result = response.json()
                self.logger.debug(f"Qwen3 rerank 响应: {result}")

            # 解析 Qwen3 rerank 响应格式
            if "results" in result:
                # 标准格式: {"results": [{"index": 0, "score": 0.95}, ...]}
                index_rerank = [item['index'] for item in result['results']]
            elif "data" in result:
                # 备用格式: {"data": [{"index": 0, "score": 0.95}, ...]}
                index_rerank = [item['index'] for item in result['data']]
            else:
                # 直接返回索引列表格式
                index_rerank = result if isinstance(result, list) else []

            self.logger.info(f"Qwen3 rerank 完成，返回 {len(index_rerank)} 个结果")
            return index_rerank
            
        except httpx.TimeoutException:
            self.logger.error("Qwen3 rerank 请求超时")
            return []
        except httpx.ConnectError:
            self.logger.error("Qwen3 rerank 连接错误")
            return []
        except json.JSONDecodeError:
            self.logger.error(f"Qwen3 rerank 响应解析失败: {response.text}")
            return []
        except Exception as e:
            msg = traceback.format_exc().replace('\n', '\t')
            self.logger.error(f'Qwen3 Reranker 请求错误: {msg}')
            return []

    async def get_scores(self,
                   query: str,
                   documents: List,
                   server_config) -> List[float]:
        """
        获取 Qwen3 rerank 模型的详细分数
        Args:
            query: 查询文本
            documents: 文档列表
            server_config: 服务器配置
        Returns:
            List[float]: 每个文档的分数列表
        """
        model_name = server_config["rerank_model"]["model_name"]
        url = server_config["rerank_server"][model_name]["server_url"]
        api_key = server_config["rerank_server"][model_name].get("api_key", "")
        
        documents_text = [document.page_content for document in documents]
        
        if not documents_text:
            return []
        
        inputs = {
            "model": model_name,
            "query": query,
            "documents": documents_text,
            "return_scores": True  # 请求返回详细分数
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                response = await client.post(url, json=inputs, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"Qwen3 rerank 分数请求失败: {response.status_code}")
                    return []

                result = response.json()

            # 提取分数
            scores = []
            if "results" in result:
                scores = [item.get('relevance_score', 0.0) for item in result['results']]
            elif "data" in result:
                scores = [item.get('relevance_score', 0.0) for item in result['data']]
            
            return scores
            
        except Exception as e:
            self.logger.error(f"获取 Qwen3 rerank 分数失败: {e}")
            return []
