import json
from threading import Lock

import requests
from pdfplumber.page import Page

from log import logger
from server.api_param import ModelInfo
from deepdoc.config.conf import DEFAULT_EMBEDDING_TOKEN, EMBED_MAX_TOKEN_DELTA_DEFAULT
from deepdoc.util.token_utils import truncate_text_by_tokens
from server.nacos_utils import DocParseConfig

ALL_CODECS = [
    'utf-8-sig', 'utf-8', 'gb2312', 'gbk', 'utf_16', 'ascii', 'big5', 'big5hkscs',
    'cp037', 'cp273', 'cp424', 'cp437',
    'cp500', 'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856', 'cp857',
    'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866', 'cp869',
    'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006', 'cp1026', 'cp1125',
    'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255', 'cp1256',
    'cp1257', 'cp1258', 'euc_jp', 'euc_jis_2004', 'euc_jisx0213', 'euc_kr',
    'gb2312', 'gb18030', 'hz', 'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2',
    'iso2022_jp_2004', 'iso2022_jp_3', 'iso2022_jp_ext', 'iso2022_kr', 'latin_1',
    'iso8859_2', 'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6', 'iso8859_7',
    'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_11', 'iso8859_13',
    'iso8859_14', 'iso8859_15', 'iso8859_16', 'johab', 'koi8_r', 'koi8_t', 'koi8_u',
    'kz1048', 'mac_cyrillic', 'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman',
    'mac_turkish', 'ptcp154', 'shift_jis', 'shift_jis_2004', 'shift_jisx0213',
    'utf_32', 'utf_32_be', 'utf_32_le', 'utf_16_be', 'utf_16_le', 'utf_7'
]
lock = Lock()


def find_codec(blob):
    for c in ALL_CODECS:
        try:
            blob.decode(c)
            return c
        except Exception as e:
            logger.debug(f'不是{c}：{e}')

    raise ValueError(f'找不到合法的编码格式，已尝试以下编码：{ALL_CODECS}')


def llm_chat(sys_prompt, user_prompt, model_info):
    """调用大模型"""
    try:
        model_name = model_info.model_id
        url = model_info.url
        api_key = model_info.key

        payload = json.dumps({
            'model': model_name,
            'messages': [
                {
                    'role': "system",
                    'content': sys_prompt
                },
                {
                    'role': "user",
                    'content': user_prompt
                }
            ],
            'max_tokens': 1000,
            'temperature': 0.1,
            'stream': False
        })

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = api_key

        # [R12-FIX-PARSE-04] 补超时：原实现无 timeout，端点挂住会永久占用 worker 线程。
        response = requests.post(url, headers=headers, data=payload,
                                 timeout=DocParseConfig().config.get('llm_timeout', 300))

        try:
            return response.json()['choices'][0]['message']['content']
        except:
            raise Exception(response.text)
    except Exception as e:
        logger.exception(f'大模型报错：{e}')
        raise e

def llm_completions(prompt, model_info):
    """completions方式调用llm"""
    try:
        model_name = model_info.model_id
        url = model_info.url
        api_key = model_info.key
        if '/chat' in url:
            url = url.replace('/chat', '')
        inputs = {
            "model": model_name,
            "prompt": prompt,
            "temperature": 0.02,
            "max_tokens": 30000
        }
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = api_key
        # [R12-FIX-PARSE-04] 补超时（同 llm_chat）
        response = requests.post(url, json=inputs, headers=headers,
                                 timeout=DocParseConfig().config.get('llm_timeout', 300))
        if response.status_code == 200:
            table_abstract = response.json().get("choices")[0]["text"]
        else:
            logger.exception(f'大模型报错：{response.text}')
            table_abstract = ""
        return table_abstract
    except Exception as e:
        logger.exception(f'大模型报错：{e}')
        return ""

def request_table_indicators(table_ch_name, url):
    """请求按表查询指标接口"""
    try:
        inputs = {
            "sourceType": table_ch_name
        }
        response = requests.get(url, params=inputs)
        table_indicators = response.json().get("data")
        return table_indicators
    except Exception as e:
        logger.exception(f'按表查询指标接口报错：{e}')
        table_indicators = []
    return table_indicators


def embedding_func(texts: list[str], embedding_model_info: ModelInfo) -> list[list[float]]:
    try:
        max_tokens = DocParseConfig().configs.get("alg-common", {}).get("online_embedding_model", {}).get(
            embedding_model_info.model_id, {}).get("max_tokens", DEFAULT_EMBEDDING_TOKEN)
        processed_texts = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                continue
                
            max_token_delta = DocParseConfig().configs.get("alg-common", {}).get(
                "embed_max_token_delta", EMBED_MAX_TOKEN_DELTA_DEFAULT)
            truncated_text = truncate_text_by_tokens(text, max_tokens, max_token_delta)

            processed_texts.append(truncated_text)

        payload = json.dumps({
            'model': embedding_model_info.model_id,
            'input': processed_texts
        })

        headers = {'Content-Type': 'application/json'}
        api_key = embedding_model_info.key
        if api_key:
            headers['Authorization'] = api_key

        logger.info(f"发送embedding请求，文本数量: {len(processed_texts)}")
        # [R12-FIX-PARSE-04] 补超时（embedding 更快，默认 60s）
        response = requests.post(embedding_model_info.url, headers=headers, data=payload,
                                 timeout=DocParseConfig().config.get('embedding_timeout', 60))

        try:
            return [embed_item['embedding'] for embed_item in response.json()['data']]
        except:
            raise Exception(response.text)
    except Exception as e:
        logger.exception(f'embedding报错：{e}')
        raise e

def to_image(page: Page, *args, **kwargs):
    with lock:
        return page.to_image(*args, **kwargs)
