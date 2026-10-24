# -*- coding: utf-8 -*-

import tiktoken

from deepdoc.config.conf import EMBED_MAX_TOKEN_DELTA_DEFAULT, MULT_MODAL_MAX_TOKEN_DELTA_DEFAULT
from log import logger


def truncate_text_by_tokens(text, max_tokens, max_token_delta=EMBED_MAX_TOKEN_DELTA_DEFAULT):
    """
    根据token数量截断文本
    Args:
        text: 原始文本
        max_tokens: 最大token数量
    Returns:
        截断后的文本
    """
    # 考虑到tiktoken计算可能不准确，预留更多余量
    safe_max_tokens = max(1, max_tokens - max_token_delta)
    
    # 尝试使用cl100k_base编码器
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        if len(tokens) <= safe_max_tokens:
            return text
        
        # 截断到安全的最大token数量
        truncated_tokens = tokens[:safe_max_tokens]
        truncated_text = encoding.decode(truncated_tokens)
        logger.info(f"文本已截断：原始token数={len(tokens)}, 截断后token数={len(truncated_tokens)}, 安全限制={safe_max_tokens}")
        return truncated_text
    except Exception as e:
        logger.warning(f"无法使用tiktoken截断文本: cl100k_base失败({e})")
        # 如果tiktoken完全失败，使用更保守的字符长度截断
        max_chars = int(safe_max_tokens * 0.5)
        if len(text) <= max_chars:
            return text
        truncated_text = text[:max_chars]
        logger.warning(f"使用字符长度估算截断：原始字符数={len(text)}, 截断后字符数={len(truncated_text)}")
        return truncated_text


def truncate_multimodal_prompt(prompt: str, max_tokens: int = None, max_token_delta: int = MULT_MODAL_MAX_TOKEN_DELTA_DEFAULT) -> str:
    """
    截断多模态模型的文本提示，确保不超过token限制
    Args:
        prompt: 原始提示文本
        max_tokens: 最大token数量，如果为None则从配置获取
    Returns:
        截断后的提示文本
    """
    # 为图像预留更多token空间，通常图像占用约1000-2000个token
    text_max_tokens = max_tokens - max_token_delta
    
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(prompt)
        token_count  = len(tokens)
        if token_count <= text_max_tokens:
            return prompt
        
        # 使用精确的token截断
        truncated_tokens = tokens[:text_max_tokens]
        truncated_prompt = encoding.decode(truncated_tokens)
        logger.warning(f"多模态提示文本已截断：原始token数={token_count}, 截断后token数={text_max_tokens}")
        return truncated_prompt
    except Exception as e:
        logger.warning(f"无法使用tiktoken截断文本: cl100k_base失败({e})")
        # 如果tiktoken失败，使用字符长度截断
        max_chars = int(text_max_tokens * 0.5)
        if max_chars <= text_max_tokens:
            return prompt
        truncated_text = prompt[:max_chars]
        logger.warning(f"使用字符长度估算截断：原始字符数={len(prompt)}, 截断后字符数={len(truncated_text)}")
        return truncated_text
