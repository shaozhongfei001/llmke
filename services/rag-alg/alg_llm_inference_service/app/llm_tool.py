#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/3/24 10:43
# @Author  : yuxj
# @File    : llm_tool.py
import json

import requests

from operators.common.log import logger
from utils import get_config

server_config = get_config()


def multi_model_message(query, image_data_list, llm_open_model, server_config):
    """
    多模态服务， 已不用
    Args:
        query:
        image_data_list:
        llm_open_model:
        server_config:

    Returns:

    """
    model_id = llm_open_model.model_info["model_id"]
    url = llm_open_model.model_info["url"]
    key = llm_open_model.model_info["key"]
    messages = [{'type': 'text', 'text': query}]
    for image in image_data_list:
        messages.append({'type': 'image_url', 'image_url': {'url': image}})
    payload = json.dumps({
        'model': model_id,
        'messages': [
            {
                'role': 'user',
                'content': messages
            }
        ],
        'max_tokens': 4096,
        'stream': llm_open_model.stream
    })
    logger.info('多模态请求中')
    if not llm_open_model.stream:
        response = request_function(url, payload, server_config, key, stream=llm_open_model.stream)
        if response is not None and response.status_code == 200:
            messages_dict = response.json()["choices"][0]["message"]
            content = messages_dict["content"]
            if content:
                yield json.dumps({"content": content, "finish_flag": False}, ensure_ascii=False)
        else:
            logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
    else:
        response = request_function(url, payload, server_config, key, stream=llm_open_model.stream)
        for data in response.iter_content(chunk_size=4098):
            try:
                data = data.decode('utf8')
                if "DONE" in data:
                    break
                if data.startswith("data: "):
                    data = data[6:]
                data_json = json.loads(data)
                messages_dict = data_json["choices"][0]["delta"]
                if "content" not in messages_dict:
                    continue
                content = messages_dict["content"]
                if content and "DONE" not in content:
                    yield json.dumps({"content": content, "finish_flag": True}, ensure_ascii=False)
            except Exception as e:
                logger.error(f"大模型结果格式错误，请重新尝试，数据：{data}，错误：{e}")
                yield f"大模型结果格式错误，请重新尝试，数据：{data}"


def insert_to_database(server_config, knowledge_base_name, document_list):
    """
    插入es和milvus数据库，通用方法
    Args:
        server_config:
        knowledge_base_name:
        document_list:

    Returns:

    """
    error_msg = ""
    milvus_url = 'http://' + server_config["milvus_config"]["host"] + ':' + str(server_config["milvus_config"]["port"]) + '/'
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    milvus_data = {
        "collection_name": knowledge_base_name,
        "document_list": document_list
    }
    es_data = {
        "index_name": knowledge_base_name,
        "document_list": document_list
    }
    response_m = requests.post(milvus_url + 'insert_vector_documents_custom', json=milvus_data)
    response_e = requests.post(es_url + 'insert_fulltext_documents', json=es_data)
    if response_m.status_code == 200:
        logger.info(f"生成{len(document_list)}条问答对，保存milvus成功")
    else:
        error_msg = str(response_m.text)
        logger.error(f"保存milvus失败，{response_m.text}")
    if response_e.status_code == 200:
        logger.info(f"生成{len(document_list)}条问答对，保存es成功")
    else:
        logger.error(f"保存es失败，{response_e.text}")
        error_msg = error_msg + str(response_e.text)
    return error_msg


def request_function(url, payload, server_config, request_key, stream=False, timeout=60):
    """
    http 请求， 其中proxies  是代理服务， 在nacos中配置
    Args:
        url:
        payload:
        server_config:
        request_key:
        stream:
        timeout:
    Returns:

    """
    authorization_key = request_key if request_key else ""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/122.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Authorization': authorization_key
    }
    proxies = proxies_config(server_config)

    def do_request():
        if proxies:
            return requests.post(url, headers=headers, data=payload, proxies=proxies, stream=stream, timeout=timeout)
        else:
            return requests.post(url, headers=headers, data=payload, stream=stream, timeout=timeout)

    for attempt in range(2):  # 最多尝试2次
        try:
            response = do_request()
            if response.status_code == 200:
                return response
            else:
                logger.error(f"大模型服务请求错误 (状态码: {response.status_code}): {response.text}")
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"大模型服务连接失败（第{attempt + 1}次）: {e}")
            if attempt == 1:
                logger.error("重试失败，放弃请求。")
                return None
        except Exception as e:
            logger.error(f"大模型服务未知错误: {e}")
            return None


def process_history_data(chat_history, len_contents, max_context_length):
    """
    处理历史数据， 拼接上下文
    Args:
        chat_history:
        len_contents:
        max_context_length:

    Returns:

    """
    new_history_list = []
    len_full = len_contents
    for hl in chat_history:
        if "answer" in hl.keys() and hl["answer"]:
            len_his = len(hl["query"] + hl["answer"])
            len_full += len_his
            if len_full > max_context_length:
                break
            new_dict = {"role": "user", "content": hl["query"]}
            new_history_list.append(new_dict)
            new_dict = {"role": "assistant", "content": hl["answer"]}
            new_history_list.append(new_dict)
    return new_history_list


def concat_history_data(new_history_list):
    history_content = ""
    for hl in new_history_list:
        history_content = "question:" +  hl["query"] + "\n"
        history_content = history_content + "answer:" + hl["answer"] + "\n"
    return history_content


def proxies_config(server_config):
    """
    代理处理
    Args:
        server_config:

    Returns:

    """
    proxies = {"http": None, "https": None}
    if "http_proxy" in server_config.keys():
        proxies["http"] = server_config["http_proxy"]
    if "https_proxy" in server_config.keys():
        proxies["https"] = server_config["https_proxy"]
    if not proxies["http"] and not proxies["https"]:
        return None
    return proxies


def ds_data_process(data, incomplete_str):
    """
    模型返回的数据处理
    Args:
        data:
        incomplete_str:

    Returns:

    """
    json_list = []
    data_list = data.split(b'\n\n')
    for dl in data_list:
        try:
            dl = dl.decode('utf8')
            if incomplete_str:
                dl = incomplete_str + dl
                incomplete_str = ""
        except Exception as e:
            logger.error(f"返回数据转码错误，data:{dl},错误：{e}")
            pass
        if not dl or dl == '\r':
            continue
        if dl.startswith("data: "):
            dl = dl[6:]
        try:
            json_data = json.loads(dl)
            json_list.append(json_data)
        except Exception as e:
            if "DONE" in dl:
                logger.info(f"流式输出已经打印完,{dl}")
            else:
                incomplete_str += dl
                # logger.error(f"json 格式解析错误，{e},{dl}")
            continue
    return json_list, incomplete_str


def general_return_data_process(data):
    """
    模型返回的数据处理
    Args:
        data:

    Returns:

    """
    data_list = data.split(b'\n')
    for dl in data_list:
        content = ""
        try:
            dl = dl.decode('utf8')
        except Exception as e:
            logger.error(f"返回结果转码失败：{dl},错误：{e}")
            continue
        if not dl or dl == '\r':
            continue
        if dl.startswith("data: "):
            dl = dl[6:]
        try:
            json_data = json.loads(dl)
        except Exception as e:
            if "DONE" in dl:
                logger.info(f"流式输出已经打印完,{dl}")
                break
            elif "ping -" in dl:
                logger.info(f"大模型错误输出,{dl}")
                continue
            else:
                logger.error(f"json 格式解析错误，{e},{dl}")
            continue
        if 'error' in json_data.keys():
            try:
                content = json_data["error"]["message"]
            except Exception as e:
                content = json_data["error"]
        else:
            try:
                if "content" not in json_data["choices"][0]["delta"].keys():
                    continue
                content = json_data["choices"][0]["delta"]["content"]
                if not content:
                    continue
            except Exception as e:
                continue
        yield content


def save_yield_results(path):
    from datetime import datetime
    t = datetime.now().strftime("%m%d_%H%M%S")

    def decorator(func):
        def wrapper(*args, **kwargs):
            gen = func(*args, **kwargs)
            values = ""
            try:
                for value in gen:
                    res = json.loads(value)
                    if "answer" in res:
                        values += str(res["answer"])
                    elif "content" in res:
                        values += res["content"]

                    with open(f"logs/{t}{path}", 'a') as f:
                        f.write(json.loads(json.dumps(value, ensure_ascii=False)) + "\n")
                    yield value
            finally:
                with open(f"logs/{t}_general{path}", 'a') as f:
                    f.write(values)

        return wrapper

    return decorator


def return_content_process(remain_token):
    start_marker = '```json\n'
    end_marker = '\n```'
    if start_marker in remain_token:
        remain_token = remain_token.split(start_marker)[1]
    if end_marker in remain_token:
        remain_token = remain_token.split(end_marker)[0]
    return remain_token


def check_document_length(document_list, max_length, web_documents_list=None, database_documents=None, table_result_data=None, query=None):
    """
    先检查每个page_content 是否超过最大输入限制，nacos配置的最大值需要减去一些留给prompt+history
    Args:
        document_list:
        web_documents_list:
        database_documents: 数据库问答召回内容
        table_result_data: 表结果数据
        query: 用户问题
        max_length:

    Returns:

    """
    document_list_new = []
    for doc in document_list:
        page_content = doc["page_content"]
        if len(page_content) > max_length:
            split_result = process_length_content(page_content, max_length - 2000)
            document_list_new.extend([{"page_content": sr, "metadata": doc["metadata"]} for sr in split_result])
        else:
            document_list_new.append(doc)
    if web_documents_list:
        for doc in web_documents_list:
            page_content = doc["page_content"]
            if len(page_content) > max_length:
                split_result = process_length_content(page_content, max_length - 2000)
                document_list_new.extend([{"page_content": sr, "metadata": doc["metadata"]} for sr in split_result])
            else:
                document_list_new.append(doc)
    if database_documents:
        for doc in database_documents:
            page_content = doc["page_content"]
            if table_result_data:
                if len(table_result_data) > 0:
                    row_count = table_result_data["row_count"]
                    head_n_row = table_result_data["head_n_row"]
                    have_row = len(head_n_row)
                    head_n_row_content = ""
                    for head_n in head_n_row:
                        for key in head_n:
                            head_n_row_content = head_n_row_content + f"""
                            {key}:{head_n[key]}"""
                    page_content = page_content + f"""
                                        使用数据库查询查到用户问题:{query},结果显示数据见:{head_n_row_content}
                                        使用数据库查询查到用户问题结果显示数据量:{have_row}行
                                        使用数据库查询查到用户问题结果总数据行数:{row_count}行
                                        如果查询数据行数大于显示数据行数，说明数据未展示全，只展示部分数据
                                        """
            if len(page_content) > max_length:
                split_result = process_length_content(page_content, max_length - 2000)
                document_list_new.extend([{"page_content": sr, "metadata": doc["metadata"]} for sr in split_result])
            else:
                doc["page_content"] = page_content
                document_list_new.append(doc)
    return document_list_new


def process_length_content(text, max_len):
    """
    拆分文本块， 通过中文常见句子结束符来截取
    Args:
        text:
        max_len:

    Returns:

    """
    end_punctuations = '。！？'  # 中文常见句子结束符
    result_document = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_len, text_len)
        segment = text[start:end]

        # 如果已经到达末尾或以结束符结尾，直接加入
        if end == text_len or segment[-1] in end_punctuations:
            result_document.append(segment)
            start = end
        else:
            # 向前寻找最近的结束符
            last_punc = max(segment.rfind(p) for p in end_punctuations)
            if last_punc != -1:
                cut_pos = start + last_punc + 1  # +1 保持标点在段尾
                result_document.append(text[start:cut_pos])
                start = cut_pos
            else:
                # 找不到结束符，只能硬拆
                result_document.append(segment)
                start = end
    return result_document


def query_es_data(knowledge_base_name, query_field_value, server_config):
    """
    查询chunk数据
    Args:
        query_field_value: 搜索条件的值， 默认是列名title
        knowledge_base_name:
        server_config:
    Returns:

    """
    es_documents = []
    data = {
        "index_name": [knowledge_base_name, "table_chunks_" + knowledge_base_name],
        "col_name": "title",
        "col_values": [query_field_value]
    }
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    response = requests.post(es_url + 'search_by_custom_param', json=data)
    try:
        if response.status_code == 200:
            try:
                es_data = response.json()['data']['result_data']
                for ed in es_data:
                    es_documents.append({"page_content": ed['_source']['page_content'], "metadata": ed['_source']['metadata']})
            except Exception as e:
                logger.info(f"参数:{data}")
                logger.error(f"es查询报错{e},{response.text}")
                return es_documents
        else:
            logger.error(f"es查询报错,{response.text}")
            return es_documents
    except Exception as e:
        logger.error(f"es查询报错{e},{response.text}")
        return es_documents
    es_documents = sorted(es_documents, key=lambda x: x['metadata']["chunk_index"])
    return es_documents
