#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Yiyang Feng  
File: llm_question_recommend_view.py  
Time: 2025/9/18 15:25  
"""
from app.base import QuestionRecommendConfig
from app.llm_service import llm_question_recommend
from app.view.core.base_view import BaseView


class LLMQuestionRecommendView(BaseView):

    def post(self, payload: QuestionRecommendConfig):
        return llm_question_recommend(payload)

