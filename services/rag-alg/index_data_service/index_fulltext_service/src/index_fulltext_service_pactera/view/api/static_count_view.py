#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全文服务的文档计数视图。

[R12-ADAPT-ALG-07] 新增：TL 下发的 Java 契约里 19527 需要 `/static_count`
（Java：`remote.faq-count.url = http://127.0.0.1:19527/static_count`），
但上游源码的全文服务没有该路由（只有向量服务有），R12 实测 `POST /static_count` → 404。
入参见 `base.StaticCountModel`，返回 `{"code":200,"data":{"count":N,"detail":{index: count|None}}}`。
"""
from base import BaseResponse, StaticCountModel
from es_kb_service import static_count
from view.core.base_view import BaseView


class StaticCountView(BaseView):
    def post(self, static_param: StaticCountModel) -> BaseResponse:
        return static_count(static_param)
