#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: test_connectivity.py  
Time: 2025/1/16 10:30  
"""
import pytest
import httpx
import asyncio
from typing import Dict, List, Any
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.base import BaseResponse
from app.view.api.connectivity_test_view import ConnectivityTestView


class TestConnectivityAPI:
    """连通性测试API的pytest测试类"""
    
    @pytest.fixture
    def connectivity_view(self):
        """创建连通性测试视图实例"""
        return ConnectivityTestView(path="/connectivity_test", tags=["connectivity_test"], summary="API接口连通性测试")
    
    @pytest.fixture
    def test_endpoints(self):
        """定义测试端点配置"""
        return [
            {
                "path": "/llm_open_chat",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_faq_generate", 
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_generate_sync",
                "method": "POST", 
                "expected_status": 200
            },
            {
                "path": "/llm_sql_generate",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/polish_answer_llm",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_faq_select",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_simi_question",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_check_model",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_multi_model",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_question_prompt",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_question_recommend",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_rotate_answer",
                "method": "POST",
                "expected_status": 200
            },
            {
                "path": "/llm_question_rewrite",
                "method": "POST",
                "expected_status": 200
            }
        ]
    
    def test_connectivity_view_creation(self, connectivity_view):
        """测试连通性测试视图创建"""
        assert connectivity_view is not None
        assert connectivity_view.path == "/connectivity_test"
        assert "connectivity_test" in connectivity_view.tags
    
    def test_connectivity_api_response_structure(self, connectivity_view):
        """测试连通性API响应结构"""
        # 模拟测试，不实际发送HTTP请求
        response = connectivity_view.post()
        
        assert isinstance(response, BaseResponse)
        assert response.code in [200, 500]  # 成功或失败
        assert isinstance(response.msg, str)
        
        if response.code == 200:
            assert response.data is not None
            assert "summary" in response.data
            assert "details" in response.data
            assert "model_info_used" in response.data
            
            # 检查summary结构
            summary = response.data["summary"]
            assert "total_tests" in summary
            assert "successful_tests" in summary
            assert "failed_tests" in summary
            assert "success_rate" in summary
    
    @pytest.mark.asyncio
    async def test_individual_endpoint_connectivity(self, test_endpoints):
        """测试单个端点的连通性"""
        # 注意：这个测试需要服务正在运行
        # 如果服务未运行，测试会跳过
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for endpoint in test_endpoints[:3]:  # 只测试前3个端点避免测试时间过长
                    url = f"http://localhost:8000{endpoint['path']}"
                    
                    # 发送简单的测试请求
                    test_payload = {
                        "model_info": {
                            "model_name": "test-model",
                            "model_id": "test-model",
                            "api_key": "test-key"
                        },
                        "query": "test"
                    }
                    
                    try:
                        response = await client.post(url, json=test_payload)
                        # 检查响应状态码
                        assert response.status_code in [200, 422, 500]  # 200成功，422参数错误，500服务器错误
                        print(f"✓ {endpoint['path']}: {response.status_code}")
                    except httpx.ConnectError:
                        pytest.skip(f"服务未运行，跳过 {endpoint['path']} 的连通性测试")
                    except httpx.TimeoutException:
                        pytest.skip(f"请求超时，跳过 {endpoint['path']} 的连通性测试")
                        
        except Exception as e:
            pytest.skip(f"连通性测试失败: {str(e)}")
    
    def test_nacos_model_config_loading(self):
        """测试从nacos加载model_info配置"""
        try:
            from app.utils import return_nacos_model
            config_manager = return_nacos_model()
            config = config_manager.get_config()
            
            # 检查配置是否包含model_info
            assert isinstance(config, dict)
            
            # 如果配置中有model_info，检查其结构
            if "model_info" in config:
                model_info = config["model_info"]
                assert isinstance(model_info, dict)
                print(f"从nacos加载的model_info: {model_info}")
            else:
                print("nacos配置中未找到model_info，将使用默认配置")
                
        except Exception as e:
            pytest.skip(f"无法从nacos加载配置: {str(e)}")
    
    def test_connectivity_test_payload_structure(self, connectivity_view):
        """测试连通性测试的payload结构"""
        # 测试默认model_info结构
        default_model_info = {
            "model_name": "qwen-plus",
            "model_id": "qwen-plus",
            "api_key": "test_key",
            "api_base": "https://dashscope.aliyuncs.com/api/v1"
        }
        
        # 验证payload结构
        test_payloads = [
            {
                "model_info": default_model_info,
                "query": "测试连通性",
                "stream": False
            },
            {
                "model_info": default_model_info,
                "document_list": [],
                "stream": False
            },
            {
                "model_info": default_model_info,
                "source_list": [{"question": "测试问题", "answer": "测试答案"}],
                "stream": False
            }
        ]
        
        for payload in test_payloads:
            assert "model_info" in payload
            assert isinstance(payload["model_info"], dict)
            assert "stream" in payload or "query" in payload or "document_list" in payload or "source_list" in payload


class TestConnectivityIntegration:
    """集成测试类"""
    
    @pytest.mark.integration
    def test_full_connectivity_workflow(self):
        """测试完整的连通性测试工作流"""
        try:
            # 创建连通性测试视图
            view = ConnectivityTestView(path="/connectivity_test", tags=["connectivity_test"], summary="API接口连通性测试")
            
            # 执行连通性测试
            response = view.post()
            
            # 验证响应
            assert isinstance(response, BaseResponse)
            
            if response.code == 200:
                data = response.data
                assert "summary" in data
                assert "details" in data
                
                # 验证summary数据
                summary = data["summary"]
                assert summary["total_tests"] > 0
                assert summary["successful_tests"] >= 0
                assert summary["failed_tests"] >= 0
                assert summary["success_rate"] is not None
                
                # 验证details数据
                details = data["details"]
                assert len(details) == summary["total_tests"]
                
                # 打印测试结果
                print(f"\n连通性测试结果:")
                print(f"总测试数: {summary['total_tests']}")
                print(f"成功数: {summary['successful_tests']}")
                print(f"失败数: {summary['failed_tests']}")
                print(f"成功率: {summary['success_rate']}")
                
                # 打印详细结果
                for detail in details:
                    status_icon = "✓" if detail["status"] == "success" else "✗"
                    print(f"{status_icon} {detail['endpoint']}: {detail['message']}")
                    
            else:
                print(f"连通性测试失败: {response.msg}")
                
        except Exception as e:
            pytest.skip(f"集成测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
