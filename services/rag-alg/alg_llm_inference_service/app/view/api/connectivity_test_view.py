#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: connectivity_test_view.py  
Time: 2025/1/16 10:00  
"""
import asyncio
import httpx
from typing import Dict, List, Any
from app.base import BaseResponse, TestModelInfoConfig
from app.view.core.base_view import BaseView
from app.utils import return_nacos_model


class ConnectivityTestView(BaseView):
    """连通性测试视图"""

    def post(self, test_model_info: TestModelInfoConfig) -> BaseResponse:
        """
        测试所有API接口的连通性
        返回每个接口的测试结果
        """
        try:
            # 获取nacos配置中的model_info
            config_manager = return_nacos_model()
            config = config_manager.get_config()

            if test_model_info is None:
                return BaseResponse(
                    code=400,
                    msg="""需要测试模型参数，例如: { "test_model_info":{ "model_id": "deepseek-distill-qwen-32b", "model_name": "deepseek-distill-qwen-32b", "url": "http://10.15.12.11:9990/v1/chat/completions", "key": null } } """,
                    data=None
                )
            port = config.get("server", {}).get("port")
            if port is None:
                return BaseResponse(
                    code=500,
                    msg="nacos server的地址端口未成功获取",
                    data=None
                )
            # 定义所有需要测试的API接口
            test_endpoints = [
                # {
                #     "path": "/llm_open_chat",
                #     "method": "POST",
                #     "payload": {
                #         "model_info": test_model_info.test_model_info,
                #         "query": "测试连通性",
                #         "stream": False
                #     }
                # },
                {
                    "path": "/llm_faq_generate",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "document_list": [],
                        "stream": False
                    }
                },
                {
                    "path": "/llm_generate_sync",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试连通性",
                        "stream": False
                    }
                },
                {
                    "path": "/llm_sql_generate",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试SQL生成",
                        "documents": [],
                        "stream": False
                    }
                },
                {
                    "path": "/polish_answer_llm",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试答案润色",
                        "stream": False
                    }
                },
                {
                    "path": "/llm_faq_select",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试FAQ选择",
                        "documents": [],
                        "stream": False
                    }
                },
                {
                    "path": "/llm_simi_question",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "source_list": [{"question": "测试问题", "answer": "测试答案"}],
                        "stream": False
                    }
                },
                {
                    "path": "/llm_check_model",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info
                    }
                },
                {
                    "path": "/llm_multi_model",
                    "method": "POST",
                    "payload": {
                        "multi_model_info": test_model_info.test_model_info,
                        "query": "测试多模态",
                        "stream": False
                    }
                },
                # {
                #     "path": "/llm_question_prompt",
                #     "method": "POST",
                #     "payload": {
                #         "model_info": test_model_info.test_model_info,
                #         "query": "测试问题提示",
                #         "stream": False
                #     }
                # },
                {
                    "path": "/llm_question_recommend",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试问题推荐",
                        "stream": False
                    }
                },
                {
                    "path": "/llm_rotate_answer",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试轮询回答",
                        "stream": False
                    }
                },
                {
                    "path": "/llm_question_rewrite",
                    "method": "POST",
                    "payload": {
                        "model_info": test_model_info.test_model_info,
                        "query": "测试问题改写",
                        "stream": False
                    }
                }
            ]

            # 执行连通性测试
            test_results = asyncio.run(self._test_connectivity(test_endpoints, port))

            # 统计结果
            total_tests = len(test_results)
            successful_tests = len([r for r in test_results if r["status"] == "success"])
            failed_tests = total_tests - successful_tests

            return BaseResponse(
                code=200,
                msg="连通性测试完成",
                data={
                    "summary": {
                        "total_tests": total_tests,
                        "successful_tests": successful_tests,
                        "failed_tests": failed_tests,
                        "success_rate": f"{(successful_tests / total_tests) * 100:.1f}%" if total_tests > 0 else "0%"
                    },
                    "details": test_results,
                    "model_info_used": test_model_info.test_model_info
                }
            )

        except Exception as e:
            return BaseResponse(
                code=500,
                msg=f"连通性测试失败: {str(e)}",
                data=None
            )

    async def _test_connectivity(self, endpoints: List[Dict[str, Any]], port) -> List[Dict[str, Any]]:
        """异步测试所有接口的连通性"""
        results = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in endpoints:
                try:
                    # 构建完整的URL
                    url = f"http://localhost:{port}{endpoint['path']}"

                    # 发送请求
                    response = await client.post(
                        url,
                        json=endpoint["payload"],
                        headers={"Content-Type": "application/json"}
                    )

                    # 判断响应状态
                    if response.status_code == 200:
                        status = "success"
                        message = "接口连通正常"
                    else:
                        status = "failed"
                        message = f"HTTP状态码: {response.status_code}"

                    results.append({
                        "endpoint": endpoint["path"],
                        "method": endpoint["method"],
                        "status": status,
                        "message": message,
                        "status_code": response.status_code,
                        "response_time_s": int(response.elapsed.total_seconds() * 1000) / 1000
                    })

                except httpx.TimeoutException:
                    results.append({
                        "endpoint": endpoint["path"],
                        "method": endpoint["method"],
                        "status": "failed",
                        "message": "请求超时",
                        "status_code": None,
                        "response_time_s": None
                    })
                except httpx.ConnectError:
                    results.append({
                        "endpoint": endpoint["path"],
                        "method": endpoint["method"],
                        "status": "failed",
                        "message": "连接失败",
                        "status_code": None,
                        "response_time_s": None
                    })
                except httpx.RemoteProtocolError as e:
                    if "incomplete chunked read" in str(e):
                        results.append({
                            "endpoint": endpoint["path"],
                            "method": endpoint["method"],
                            "status": "failed",
                            "message": "流式响应连接中断（大模型服务可能不可用）",
                            "status_code": None,
                            "response_time_s": None
                        })
                    else:
                        results.append({
                            "endpoint": endpoint["path"],
                            "method": endpoint["method"],
                            "status": "failed",
                            "message": f"协议错误: {str(e)}",
                            "status_code": None,
                            "response_time_s": None
                        })
                except Exception as e:
                    results.append({
                        "endpoint": endpoint["path"],
                        "method": endpoint["method"],
                        "status": "failed",
                        "message": f"请求异常: {str(e)}",
                        "status_code": None,
                        "response_time_s": None
                    })

        return results
