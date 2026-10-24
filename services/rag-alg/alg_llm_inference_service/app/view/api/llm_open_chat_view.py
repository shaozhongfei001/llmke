#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_open_chat_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import BaseResponse, LLMOpenChatConfig
from app.llm_service import llm_open_chat
from app.view.core.base_view import BaseView


class LLMOpenChatView(BaseView):

    async def post(self, payload: LLMOpenChatConfig):
        return await llm_open_chat(payload)

