"""包导出：答案层的对外契约只有四个符号。

`build_answer` 是纯逻辑（无 IO）；`fetch_chunks` 把 SQL 与执行器分开；
`to_api_*` 固定响应形状，避免调用方各自拼 JSON。
"""
from modules.answer_api.service import (AnswerError, POLICY_STATE, build_answer,
                                        to_api_error, to_api_response)
from modules.answer_api.sql_adapter import fetch_chunks, fetch_chunks_active

__all__ = ["AnswerError", "POLICY_STATE", "build_answer", "fetch_chunks",
           "to_api_error", "to_api_response", "fetch_chunks_active"]
