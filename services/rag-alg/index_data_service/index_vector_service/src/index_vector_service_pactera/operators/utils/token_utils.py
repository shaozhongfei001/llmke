# -*- coding: utf-8 -*-

import tiktoken

from config.conf import EMBED_MAX_TOKEN_DELTA_DEFAULT
from operators.common.log import logger


def truncate_text_by_tokens(text, max_tokens, max_token_delta=EMBED_MAX_TOKEN_DELTA_DEFAULT):
    """
    根据token数量截断文本
    Args:
        text: 原始文本
        max_tokens: 最大token数量
        model_name: 模型名称
    Returns:
        截断后的文本
    """
    if not text or max_tokens <= 0:
        return text
    
    # 考虑到tiktoken计算可能不准确，预留更多余量
    safe_max_tokens = max(1, max_tokens-max_token_delta)
    
    # 尝试使用cl100k_base编码器
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        token_count = len(tokens)
        if token_count <= safe_max_tokens:
            return text

        # 截断到安全的最大token数量
        truncated_tokens = tokens[:safe_max_tokens]
        truncated_text = encoding.decode(truncated_tokens)
        # logger.debug(f"文本token数量超过模型限制，已截断：原始token数={token_count}, 最大允许={max_tokens}")
        return truncated_text
    except Exception as e:
        logger.warning(f"无法使用tiktoken截断文本，使用字符长度截断: cl100k_base失败({e})")
        max_chars = int(safe_max_tokens * 0.5)
        if len(text) <= max_chars:
            return text
        truncated_text = text[:max_chars]
        logger.debug(f"使用字符长度预估截断：原始字符数={len(text)}, 截断后字符数={len(truncated_text)}")
        return truncated_text
