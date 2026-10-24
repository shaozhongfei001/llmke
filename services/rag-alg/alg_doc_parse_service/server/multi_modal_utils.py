"""
qwen-vl系列设置参照https://www.alibabacloud.com/help/zh/model-studio/vision?spm=a2c63.p38356.0.i32#6509107523iz2
或者https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
"""
import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests
from requests import ConnectionError, RequestException, Timeout

from deepdoc.config.conf import DEFAULT_MULTIMODAL_TOKEN, MULT_MODAL_MAX_TOKEN_DELTA_DEFAULT
from log import logger, request_id
from .api_param import ModelInfo
from .nacos_utils import DocParseConfig
from deepdoc.util.token_utils import truncate_multimodal_prompt
from server.exception.custom_exception import (
    ModelRequestInternalError,
    ModelTokenExceedError,
)

PROMPT_TEMPLATE = '''以下是图片内的文字内容：
```txt
{{content}}
```'''

MERGE_PROMPT_TEMPLATE = '''以下是文件中同一页面内的文字内容：
```txt
{{content}}
```'''

MERGE_QUERY = (
    '请尽可能的根据文字内容和上传的图片，生成一段描述，描述文字和图片的核心内容，保证核心的文字不要丢失，如果是流程类内容，请主要描述流程，字数在300字以内'
)

RELATIVE_CHUNKS = '''以下是图片附近的上下文：
```txt
{{content}}
```
'''

QUERY = (
    '请尽可能非常准确的描述该图片，包括图片中的文字和图片中可能出现物体的颜色、形状、物体名称等。'
    '如果是图表的话你将给出非常详细的统计指标。'
    '注意不要描述任何图片中不存在的内容，否则我会非常痛苦！！！'
)

failed_image = Path(DocParseConfig().config['log_path']) / 'multi_modal_failed_images'
if not os.path.exists(failed_image):
    os.makedirs(failed_image)


@dataclass
class MultiModalMessage:
    type: Literal['image', 'text'] = 'text'
    content: str | bytes = None

    def __post_init__(self):
        if self.type == 'text' and not isinstance(self.content, str):
            raise TypeError('text类型的content必须是字符串')

        if self.type == 'image' and not isinstance(self.content, bytes):
            raise TypeError('image类型的content必须是字节')

        if isinstance(self.content, bytes):
            self.content = base64.b64encode(self.content).decode()


class MultiModalClient:
    def __init__(self, multi_modal_config: ModelInfo):
        self.model_name = multi_modal_config.model_id
        self.url = multi_modal_config.url
        self.headers = None

        api_key = multi_modal_config.key
        if api_key:
            self.headers = {'Authorization': api_key}

    def chat(self, messages: list[MultiModalMessage], return_meta: bool = False):
        content = []
        image = None
        for message in messages:
            if message.type == 'text':
                # 对文本内容进行token截断
                max_tokens = DocParseConfig().configs.get("alg-common",{}).get('online_multi_modal_model', {}).get(self.model_name, {}).get("max_tokens", DEFAULT_MULTIMODAL_TOKEN)
                max_token_delta = DocParseConfig().configs.get("alg-common",{}).get("multi_modal_max_token_delta", MULT_MODAL_MAX_TOKEN_DELTA_DEFAULT)
                truncated_content = truncate_multimodal_prompt(prompt=message.content, max_tokens=max_tokens, max_token_delta=max_token_delta)
                content.append({'type': 'text', 'text': truncated_content})
            else:
                content.append({'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{message.content}'}})
                image = base64.b64decode(message.content)
        output_max_tokens = DocParseConfig().config.get('online_multi_modal_model', {}).get(self.model_name, {}).get('output_max_tokens', 4096)
        payload = {
            'model': self.model_name,
            'messages': [
                {
                    'role': 'user',
                    'content': content
                }
            ],
            'max_tokens': output_max_tokens
        }

        logger.info(f'[Request]多模态模型请求, URL: {self.url}, model: {self.model_name}, output_max_tokens: {output_max_tokens}')
        # [R12-FIX-PARSE-04] 原实现没有传 timeout，下面的 `except Timeout` 分支实际不可达：
        # 端点挂住/连接半开时 worker 线程会永久阻塞、请求永不返回。此处按配置补超时（默认 600s）。
        request_timeout = DocParseConfig().config.get('multi_modal_timeout', 600)
        try:
            response = requests.post(self.url, json=payload, headers=self.headers, timeout=request_timeout)
        except Timeout as exc:
            err = ModelRequestInternalError('多模态模型请求超时')
            err.kind = 'timeout'
            raise err from exc
        except RequestException as exc:
            err = ModelRequestInternalError(f'多模态模型请求失败：{exc}')
            # 连接被拒/无法建链 = 端点没起来（区别于"端点起来了但返回错误"）
            err.kind = 'unavailable' if isinstance(exc, ConnectionError) else 'failed'
            raise err from exc

        try:
            if response.status_code != 200:
                response_text = response.text
                lower_text = response_text.lower()
                # [R12-FIX-PARSE-04] 两种 500 必须靠 message 区分（状态码相同）：
                #   - Context size has been exceeded / maximum context length → over_budget
                #   - failed to process mtmd chunk                            → kv_starved
                if "context size has been exceeded" in lower_text or "maximum context length" in lower_text:
                    err = ModelTokenExceedError('多模态模型请求超过上下文长度限制：' + response_text)
                    err.kind = 'over_budget'
                    raise err
                if "mtmd chunk" in lower_text:
                    err = ModelRequestInternalError('多模态模型 KV 空间不足（mtmd chunk 处理失败）：' + response_text)
                    err.kind = 'kv_starved'
                    raise err
                err = ModelRequestInternalError('多模态模型响应错误：' + response_text)
                err.kind = 'failed'
                raise err

            try:
                # [R12-FIX-PARSE-05] 采集 finish_reason：'length' 表示输出被 max_tokens 截断，
                # 此时文本不可作为"完整逐字转录"使用（实测 256 token 会把 14 行小字页抄一半）。
                _data = response.json()
                _content = _data['choices'][0]['message']['content']
                if return_meta:
                    return _content, {
                        'finish_reason': _data['choices'][0].get('finish_reason'),
                        'usage': _data.get('usage') or {},
                        # [R12-FIX-PARSE-05] llama-server 自带 timings：prompt_n/cache_n 可判定这次测量是否干净
                        # （cache_n 过大说明命中了 prompt cache，耗时不代表首次开销）
                        'timings': _data.get('timings') or {},
                    }
                return _content
            except Exception as e:
                err = ModelRequestInternalError('多模态模型返回格式错误：' + response.text)
                err.kind = 'failed'
                raise err from e
        except Exception as e:
            if image:
                with open(failed_image / f'{request_id.get()}.jpg', 'wb') as f:
                    f.write(base64.b64decode(image))

            raise e
