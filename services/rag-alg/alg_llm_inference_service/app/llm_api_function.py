#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/21 14:17
# @Author  : yuxj
# @File    : llm_api_function.py
import ast
import base64
import json
import re
from collections import defaultdict
import random
import aiohttp
import httpx
import requests

# [R12-ADAPT-ALG-05] 原为模块级 `from dashscope import Generation`（阿里百炼 SDK）。
# R12 的 LLM 通路由本机 18092（OpenAI 兼容）承担，按任务书不安装 dashscope；
# 模块级导入会拖垮整个 LLM 服务（即使只走 async_general_service）。
# 改为惰性导入，只在 model_name 命中 "qwen_api" 分支（requests_qwen_llm）时才需要该 SDK。

def _load_dashscope_generation():
    try:
        from dashscope import Generation  # noqa: PLC0415 - 惰性导入是本处刻意行为
        return Generation
    except ImportError as e:
        raise RuntimeError(
            "model_name 命中 qwen_api 分支，需要 dashscope SDK，但 R12 venv 未安装"
            "（见 status/alg.md 依赖处置表）；请改用 OpenAI 兼容端点或安装 dashscope"
        ) from e

from base import LLMOpenChatConfig, FAQChatConfig, FAQSelectConfig, FAQSimiConfig, LLMBasicConfig, \
    QuestionRecommendConfig, QuestionRewriteConfig, SqlGenConfig
from llm_tool import request_function, ds_data_process, general_return_data_process, insert_to_database, \
    process_history_data
from prompt_config import PROMPT_TEMPLATES
from prompt_service import get_prompt_value, build_chat_message, get_system_prompt
from operators.common.log import logger
from utils import create_uuid


async def async_general_service(llm_open_model: LLMOpenChatConfig, server_config):
    """
    异步请求xinference
    Args:
        llm_open_model:
        server_config:

    Returns:

    """
    messages = build_chat_message(llm_open_model)
    model_name = llm_open_model.model_info["model_name"]
    model_id = llm_open_model.model_info["model_id"]
    if model_name == "FinGienModel-32B":
        payload = json.dumps({
            "model": model_id,
            "messages": messages,
            "repetition_penalty": 1.1,  # 避免重复输出
            "temperature": llm_open_model.temperature,
            "stream": llm_open_model.stream,
            "max_tokens": llm_open_model.max_tokens or server_config["MAX_TOKENS"]
        })
    else:
        payload = json.dumps({
            "model": model_id,
            "messages": messages,
            "temperature": llm_open_model.temperature,
            "stream": llm_open_model.stream,
            "max_tokens": llm_open_model.max_tokens or server_config["MAX_TOKENS"]
        })
    request_key = llm_open_model.model_info["key"]
    authorization_key = request_key if request_key else ""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/122.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Authorization': authorization_key
    }
    if llm_open_model.stream:
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(1000)
            async with client.stream("POST", llm_open_model.model_info["url"], headers=headers, timeout=timeout, data=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            json_data = json.loads(data)
                            content = json_data["choices"][0]["delta"]["content"]
                            yield content
                        except (json.JSONDecodeError, KeyError):
                            continue
    else:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(llm_open_model.model_info["url"], headers=headers, data=payload) as response:
                    if response.status == 200:
                        json_response = await response.json()
                        yield json_response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error Occurred in Inference! ErrorMessage: {e}")
            yield {}


async def requests_qwen_llm(llm_open_model: LLMOpenChatConfig, server_config):
    """
    qwen api 函数请求方式
    Args:
        llm_open_model:
        server_config:

    Returns:

    """
    messages = build_chat_message(llm_open_model)
    model_id = llm_open_model.model_info["model_id"]
    incremental_output = True
    if not llm_open_model.stream:
        incremental_output = False
    max_tokens = llm_open_model.max_tokens or server_config["MAX_TOKENS"]
    if max_tokens > 2000:
        max_tokens = 1999
    Generation = _load_dashscope_generation()  # [R12-ADAPT-ALG-05] 惰性导入
    responses = Generation.call(model=model_id,
                                messages=messages,
                                top_p=llm_open_model.top_p,
                                result_format='message',  # 设置输出为'message'格式
                                stream=llm_open_model.stream,  # 设置输出方式为流式输出
                                incremental_output=incremental_output,  # 增量式流式输出
                                max_tokens=max_tokens,
                                api_key=llm_open_model.model_info["key"]
                                )
    if llm_open_model.stream:
        for response in responses:
            if response.status_code == 200:
                yield response.output.choices[0]['message']['content']
            else:
                logger.error('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                    responses.request_id, responses.status_code,
                    responses.code, responses.message
                ))
    else:
        if responses.status_code == 200:
            yield responses.output.choices[0].message.content
        else:
            logger.error('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                responses.request_id, responses.status_code,
                responses.code, responses.message
            ))


# def loop_llm_function(message_list, llm_open_model, full_document, num, answer_all, server_config, query):
#     """
#     多轮问答， 已不用
#     Args:
#         message_list:
#         llm_open_model:
#         full_document:
#         num:
#         answer_all:
#         server_config:
#         query:
#
#     Returns:
#
#     """
#     messages = [{"role": "system", "content": llm_open_model.system_prompt + "\n" + LOOP_DOCUMENT_PROMPT_TEMPLATES},
#                 {"role": "user", "content": USER_PROMPT.format(passage=full_document, question=query, title='文本数据')}]
#     response_message = {"role": "assistant", "content": ""}
#     continue_message = {'role': "user", "content": CONTINUE_PROMPT}
#     if message_list:
#         messages = messages + message_list
#     llm_open_model.stream = False
#     llm_open_model.prompt_msg = messages
#     llm_open_model.return_prompt = False
#     llm_open_model.query = ""
#     content_iterator = list(sync_general_service(llm_open_model, server_config))
#     check_substrings = ["无法提供答案", "无法回答", "无答案", "无参考回答"]
#     for token in content_iterator:
#         token = token.strip()
#         if "########\nF" not in token and token != 'F' and all(substring not in token for substring in check_substrings):
#             if "</think>" in token:
#                 token = token.split("</think>")[-1]
#             response_message["content"] = token
#             answer_all = answer_all + f"answer{num}:" + token + "\n"
#             message_list.append(response_message)
#             message_list.append(continue_message)
#     return answer_all, message_list


# def sync_annex_service(llm_open_model: LLMOpenChatConfig, server_config, redis_client):
#     """
#     附件问答请求函数，已不用
#     Args:
#         llm_open_model:
#         server_config:
#         redis_client:
#
#     Returns:
#
#     """
#     logger.info(f"单文本参数：{llm_open_model.json()}")
#
#     def _split_text(text, length=10000):
#         return [text[i:i + length] for i in range(0, len(text), length)]
#
#     redis_file_paths = llm_open_model.file_paths
#     stream_flag = llm_open_model.stream
#     query = llm_open_model.query
#     answer_all = ""
#     full_all_document = "\n".join(document for key in redis_file_paths if (document := redis_client.get(key)) is not None)
#     if not full_all_document:
#         logger.info(f"redis中没有数据，请检查后重试,{redis_file_paths}")
#         yield json.dumps({"content": "redis中没有数据，请检查后重试", "finish_flag": True}, ensure_ascii=False)
#     if len(full_all_document) < llm_open_model.max_context_length:
#         # 直接调用推理服务
#         messages = [{"role": "system", "content": llm_open_model.system_prompt + "\n" + DOCUMENT_PROMPT_TEMPLATES},
#                     {"role": "user", "content": USER_PROMPT.format(passage=full_all_document, question=query, title='文本数据')}]
#         llm_open_model.stream = stream_flag
#         llm_open_model.prompt_msg = messages
#         llm_open_model.return_prompt = False
#         llm_open_model.query = ""
#         yield from sync_general_service(llm_open_model, server_config)
#     else:
#         message_list = []
#         global_num = 1
#         document_list = _split_text(full_all_document, length=llm_open_model.max_context_length)
#         for document in document_list:
#             answer_all, message_list = loop_llm_function(message_list, llm_open_model, document, global_num, answer_all, server_config, query)
#             global_num += 1
#         messages = [{"role": "system", "content": llm_open_model.system_prompt + "\n" + FINALLY_PROMPT},
#                     {"role": "user", "content": USER_PROMPT.format(passage=answer_all, question=query, title='参考答案')}]
#         llm_open_model.stream = stream_flag
#         llm_open_model.prompt_msg = messages
#         llm_open_model.return_prompt = False
#         llm_open_model.query = ""
#         yield from sync_general_service(llm_open_model, server_config)


def sync_general_service(llm_open_model: LLMOpenChatConfig, server_config):
    """
    同步请求xinference 和 符合openai格式
    Args:
        llm_open_model:
        server_config:
    Returns:

    """
    # logger.info(f"问答服务参数：{llm_open_model.json()}")
    model_id = llm_open_model.model_info["model_id"]
    model_name = llm_open_model.model_info["model_name"]
    lower_model_name = model_name.lower()
    key = llm_open_model.model_info["key"]
    if llm_open_model.query:
        messages = build_chat_message(llm_open_model)
    elif llm_open_model.prompt_msg:
        messages = llm_open_model.prompt_msg
    else:
        llm_open_model.query = ""
        messages = build_chat_message(llm_open_model)
    payload = json.dumps({
        "model": model_id,
        "messages": messages,
        "top_p": llm_open_model.top_p,
        "repetition_penalty": 1.1 if model_name == "FinGienModel-32B" else 1.0,  # 避免重复输出
        "temperature": llm_open_model.temperature,
        "stream": llm_open_model.stream,
        "max_tokens": llm_open_model.max_tokens,
        "chat_template_kwargs": {"enable_thinking": llm_open_model.enable_thinking}
    })
    if llm_open_model.stream:
        response = request_function(llm_open_model.model_info["url"], payload, server_config, llm_open_model.model_info["key"], stream=llm_open_model.stream)
        if response is not None and response.status_code == 200:
            # 使用 iter_content 迭代处理响应内容
            data_iterator = response.iter_content(chunk_size=1024)
            distill_flag_num = 1
            distill_content = ""
            incomplete_str = ""
            finish_flag = True
            while True:
                data = next(data_iterator, None)  # 获取下一个数据块
                if not data:
                    break
                try:
                    check_substrings = {"deepseek-distill", "deepseek-r1-distill", "qwq", "deepseek"}
                    if model_name == "deepseek-r1":
                        json_data_list, incomplete_str = ds_data_process(data, incomplete_str)
                        for jl in json_data_list:
                            delta_data = jl["choices"][0]["delta"]
                            if finish_flag and "reasoning_content" in delta_data.keys():
                                content = delta_data["reasoning_content"]
                            elif finish_flag and "reasoning_content" not in delta_data.keys():
                                content = "\n</think>\n"
                                finish_flag = False
                            else:
                                content = delta_data["content"]
                                finish_flag = False
                            if content:
                                yield json.dumps({"content": content, "finish_flag": False}, ensure_ascii=False)
                    elif any(substring in lower_model_name for substring in check_substrings):
                        content_general = general_return_data_process(data)
                        for ct in content_general:
                            if not ct:
                                continue
                            else:
                                if "<" not in ct and distill_flag_num == 1:
                                    content = "<think>" + ct
                                    distill_flag_num = 2
                                    yield json.dumps({"content": content, "finish_flag": False}, ensure_ascii=False)
                                elif "<" in ct:
                                    distill_content += ct
                                    distill_flag = True
                                    while distill_flag:
                                        data_s = next(data_iterator, None)
                                        if data_s is None:
                                            break
                                        content_general_s = general_return_data_process(data_s)
                                        for ct_s in content_general_s:
                                            if not ct_s:
                                                continue
                                            for cs in ct_s:
                                                if cs in ["<", "/", "t", "h", "i", "n", "k", ">", "\n"]:
                                                    distill_content += cs
                                                else:
                                                    distill_content += cs
                                                    distill_flag = False
                                    yield json.dumps({"content": distill_content, "finish_flag": False}, ensure_ascii=False)
                                    distill_content = ""
                                    distill_flag_num = 3
                                else:
                                    yield json.dumps({"content": ct, "finish_flag": False}, ensure_ascii=False)
                    else:
                        content_general = general_return_data_process(data)
                        if any(substring not in model_name for substring in check_substrings):
                            for content in content_general:
                                if content and isinstance(content, str):
                                    yield json.dumps({"content": content, "finish_flag": False}, ensure_ascii=False)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"解析错误:{e},{data}")
                    continue
            # yield json.dumps({"content": "", "finish_flag": True}, ensure_ascii=False)
        else:
            logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
    else:
        try:
            response = request_function(llm_open_model.model_info["url"], payload, server_config, key, stream=llm_open_model.stream, timeout=600)
            if response is not None and response.status_code == 200:
                return_content = ""
                messages_dict = response.json()["choices"][0]["message"]
                if "reasoning_content" in messages_dict.keys() and messages_dict["reasoning_content"]:
                    return_content += "<think>"
                    reasoning_content = messages_dict["reasoning_content"]
                    return_content += reasoning_content + "</think>"
                content = messages_dict["content"]
                if content:
                    if "</think>" in content and "<think>" not in content and not return_content:
                        return_content += "<think>"
                    yield json.dumps({"content": return_content + content, "finish_flag": True}, ensure_ascii=False)
                else:
                    yield json.dumps({"content": return_content, "finish_flag": True}, ensure_ascii=False)
            else:
                logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
        except Exception as e:
            logger.error(f"Error Occurred in Inference! ErrorMessage: {e}")
            yield json.dumps({"content": "", "finish_flag": False}, ensure_ascii=False)
    if llm_open_model.is_return_prompt:
        yield json.dumps({"prompt_content": messages[-1]["content"]}, ensure_ascii=False)


def polish_answer_llm(faq_model: FAQChatConfig, server_config):
    """
    faq或其他答案的润色接口
    Args:
        faq_model:
        server_config:

    Returns:

    """
    logger.info(f"润色大模型参数：{faq_model.json()}")
    model_id = faq_model.model_info["model_id"]
    messages = []
    count = 0
    pred_dict_list = []
    faq_knowledge_base_name = ""
    for doc in faq_model.document_list:
        question = doc["metadata"]["question"]
        answer = doc["metadata"]["answer"]
        faq_knowledge_base_name = doc["metadata"]["knowledge_base_name"]
        top_k = faq_model.top_k
        prompt_value = get_prompt_value(question=question, page_contents=answer, prompt_type="polish_llm_chat", top_k=top_k)
        messages.append({'role': 'user', 'content': prompt_value.text})
        # 支持api接口生成和本地xinference生成
        if faq_model.model_info["key"]:
            payload = json.dumps({
                "model": model_id,
                "input": {"messages": messages},
                "messages": messages,
                "stream": False
            })
        else:
            payload = json.dumps({
                "model": model_id,
                "messages": messages,
                "stream": False
            })
        response = request_function(faq_model.model_info["url"], payload, server_config, faq_model.model_info["key"], stream=False)
        if response is not None and response.status_code == 200:
            res_answer = response.json()["choices"][0]["message"]["content"].strip()
            if "</think>" in res_answer:
                res_answer = res_answer.split("</think>")[-1].strip()
            doc["page_content"] = doc["metadata"]["question"] + "@@" + res_answer
            doc["metadata"]["answer"] = res_answer
        else:
            logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
            return count, f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确", []
        if "pk" not in doc["metadata"].keys():
            doc["metadata"]["pk"] = str(create_uuid())
        if "related_pk" not in doc["metadata"].keys():
            doc["metadata"]["related_pk"] = str(create_uuid())
        pred_dict_list.append({**doc["metadata"], "page_content": doc["page_content"]})
    count += len(pred_dict_list)
    if pred_dict_list and faq_model.to_database:
        milvus_url = 'http://' + server_config["milvus_config"]["host"] + ':' + str(server_config["milvus_config"]["port"]) + '/'
        es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
        milvus_data = {
            "index_name": faq_knowledge_base_name,
            "document_list": pred_dict_list
        }
        es_data = {
            "index_name": faq_knowledge_base_name,
            "document_list": pred_dict_list
        }
        response_m = requests.post(milvus_url + 'update_doc', json=milvus_data)
        response_e = requests.post(es_url + 'update_doc', json=es_data)
        if response_m.status_code == 200:
            logger.info(f"润色{len(pred_dict_list)}条问答对，保存milvus成功")
        if response_e.status_code == 200:
            logger.info(f"润色{len(pred_dict_list)}条问答对，保存es成功")
    else:
        return count, f"润色成功", pred_dict_list
    return count, f"润色成功", pred_dict_list


def requests_faq_llm(faq_model: FAQChatConfig, server_config):
    """
    faq生成接口
    Args:
        faq_model:
        server_config:

    Returns:

    """
    logger.info(f"faq生成参数：{faq_model.json()}")
    model_id = faq_model.model_info["model_id"]
    messages = []
    pred_dict_list = []
    top_k = faq_model.top_k
    faq_knowledge_base_name = ""
    # 同一个是知识库下file_id是唯一的，在faq数据中，metadata是相同的，如果后期有改变则改代码
    grouped_dict = defaultdict(list)
    # 根据file_id来合并文本数据
    for item in faq_model.document_list:
        grouped_dict[item["metadata"]["file_id"]].append(item)
    new_document_list = []
    for file_id, item_list in grouped_dict.items():
        page_content_join = ""
        meta_data = None
        for il in item_list:
            meta_data = il["metadata"]
            if len(page_content_join) < faq_model.max_context_length - 1000:  # 留一些prompt
                page_content_join += il["page_content"]
            else:
                new_document_list.append({"page_content": page_content_join, "metadata": meta_data})
                page_content_join = ''
        if page_content_join:
            new_document_list.append({"page_content": page_content_join, "metadata": meta_data})
    for doc in new_document_list:
        meta_data = doc["metadata"]
        page_content = doc["page_content"]
        file_id = meta_data.get("file_id", "")
        folder_id = meta_data.get("folder_id", "")
        if len(page_content) > faq_model.max_context_length:
            page_content = page_content[:faq_model.max_context_length]
        faq_knowledge_base_name = "faq_" + meta_data["knowledge_base_name"]
        if top_k <= 0:
            top_k = random.randint(10, 20)
        prompt_value = get_prompt_value(page_contents=page_content, prompt_type="faq_llm_chat" , top_k=top_k)
        # messages.append({'role': 'user', 'content': prompt_value.text})
        messages = [{'role': 'user', 'content': prompt_value.text}]
        if not faq_model.model_info.get("key"):
            faq_model.model_info["key"] = ""
        # 支持api接口生成和本地xinference生成
        if faq_model.model_info["key"]:
            payload = json.dumps({
                "model": model_id,
                "input": {"messages": messages},
                "messages": messages,
                "stream": False
            })
        else:
            payload = json.dumps({
                "model": model_id,
                "messages": messages,
                "stream": False
            })
        response = request_function(faq_model.model_info["url"], payload, server_config, faq_model.model_info["key"], timeout=300)
        if response is not None and response.status_code == 200:
            try:
                res = response.json()["choices"][0]["message"]["content"]
                if "</think>" in res:
                    res = res.split("</think>")[-1]
                res = res.replace("'", '\"').replace("\n", "").replace("\r", "")
            except Exception as e:
                logger.warning(f"faq 解析json格式失败，尝试其他解析方法，{e}")
                res = response.json()["output"]["text"]
            try:
                res_json = json.loads(res)
                res_json["question"] = res_json["question"]
                res_json["answer"] = res_json["answer"]
                res_json["file_id"] = int(file_id)
                res_json["folder_id"] = int(folder_id)
                js_res_list = [res_json]
            except Exception as e:
                logger.warning(f"faq 解析json格式失败，尝试json解析，{e}")
                try:
                    js_res_list = json.loads('[' + res.replace('}, {', '},{') + ']')
                except json.JSONDecodeError:
                    logger.warning(f"faq 解析json格式失败，尝试正则匹配，{e}")
                    # logger.error(f"faq抽取请求大模型返回内容: {response.text}")
                    js_res_list = []
                    patterns = [
                        r'"question":\s*"(.*?)",\s*"answer":\s*"(.*?)"',
                        r"\['question': '(.*?)','answer': '(.*?)'\]",
                        r"\['问题': '(.*?)','答案': '(.*?)'\]",
                        r"\['问题1': '(.*?)','答案': '(.*?)'\]",
                        r"问题[:：](.*?)答案[:：](.*)",
                        r'"question":\s*(.*?)\s*"answer":\s*(.*)'
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, res)
                        if matches:
                            js_res_list = [{"question": match[0].strip(), "answer": match[1].strip(), "folder_id": folder_id, "file_id": file_id} for match in
                                           matches]
                            break
            for num in range(0, len(js_res_list)):
                new_dict = {}
                error_msg = ['未知', '无答案', '本题无答案', '']
                if not js_res_list[num]["answer"]:
                    continue
                if js_res_list[num]["answer"] in error_msg:
                    continue
                if not any(em in js_res_list[num]["answer"] for em in error_msg):
                    continue
                new_dict["page_content"] = js_res_list[num]["question"] + "@@" + js_res_list[num]["answer"]
                new_dict["metadata"] = meta_data.copy()
                new_dict["metadata"]["pk"] = str(create_uuid())
                new_dict["metadata"]["related_pk"] = str(create_uuid())
                new_dict["metadata"]["knowledge_base_name"] = faq_knowledge_base_name
                new_dict["metadata"]["question"] = js_res_list[num]["question"]
                new_dict["metadata"]["answer"] = js_res_list[num]["answer"]
                new_dict["metadata"]["labels"] = js_res_list[num].get("labels", None)
                new_dict["metadata"]["file_id"] = int(file_id)
                new_dict["metadata"]["folder_id"] = int(folder_id)
                new_dict["metadata"]["order_num"] = new_dict["metadata"]["pk"]
                new_dict["metadata"]["status"] = 0
                new_dict["metadata"]["faq_type"] = 1
                pred_dict_list.append(new_dict)
            # 文本超过数量则跳出
            if 0 < top_k < len(pred_dict_list):
                pred_dict_list = pred_dict_list[:top_k]
                break
        else:
            logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
            return 0, f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确"
    insert_error_msg = ""
    if pred_dict_list:
        insert_error_msg = insert_to_database(server_config, faq_knowledge_base_name, pred_dict_list)
    return len(pred_dict_list), insert_error_msg


def requests_faq_select_llm(faq_select_model: FAQSelectConfig, server_config):
    """
    faq答案选择接口
    Args:
        faq_select_model:
        server_config:
    Returns:
    """
    id_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U"]
    query = faq_select_model.query
    question_answer = ""
    id_answer_dict = {}
    i = 0
    select_doc = None
    # document_list 进行排序
    if faq_select_model.documents and len(faq_select_model.documents) > 0:
        sort_document_list = sorted(faq_select_model.documents, key=lambda x: x["rerank_score"], reverse=True)
        top_1_doc = sort_document_list[0]
        top_1_rerank_score = top_1_doc["rerank_score"]
        if top_1_rerank_score >= faq_select_model.max_score:
            return top_1_doc
        elif top_1_rerank_score <= faq_select_model.min_score:
            return select_doc
        else:
            for doc in sort_document_list[0:faq_select_model.top_k]:
                meta_data = doc["metadata"]
                bq = meta_data["question"]
                answer = meta_data["answer"]
                question_answer = question_answer + "问题" + str(id_list[i]) + ":" + str(bq) + ", 问题" + str(
                    id_list[i]) + "对应的答案:" + answer
                id_answer_dict[id_list[i]] = doc
                i = i + 1
            # content = faq_select_model.system_prompt.format(query, question_answer)
            content = "客人的问题是:" + query + (".请根据下面的问题和答案, {}，根据上述问题和答案选择最合适的答案对应的问题的编号,如果没有合适回答，请输出:无合适答案，"
                                           "例如:"
                                           "input: 客人问题:加班餐费.请根据下面的问题和答案, 问题A:加班餐费报销的注意事项有哪些？, 问题A对应的答案:同事，加班餐费报销时需注意：<br/>"
                                           "1、加班费报销需要按照发生日期逐条填写，不能合并填写一条。<br/>"
                                           "2、不同交易日期的加班餐费开在一张发票上报销时，可以修改每条加班费用项上发票的\"本次报销金额\"，使得多日加班费合并不超过发票的票面总额即可。<br/>"
                                           "3、涉及多人加班餐费报销时，需要按发票日期添加参与人。"
                                           "问题B:加班餐费, 问题B对应的答案:同事，加班餐费报销时需注意：<br/>"
                                           "1、加班费报销需要按照发生日期逐条填写，不能合并填写一条。<br/>"
                                           "2、不同交易日期的加班餐费开在一张发票上报销时，可以修改每条加班费用项上发票的\"本次报销金额\"，使得多日加班费合并不超过发票的票面总额即可。<br/>"
                                           "3、涉及多人加班餐费报销时，需要按发票日期添加参与人。"
                                           "问题C:加班餐费和加班交通费如何报销？, 问题C对应的答案:同事，加班餐费及交通费需要您在汇联易系统提交报销流程，具体费用标准如下：<br/>"
                                           "1、加班时间在晚上20:00后可享受加班餐费，人均不超过25元，周末加班，可报销午晚二餐，每人每餐不能超过25元，具体标准以部门内部为准。<br/>"
                                           "2、加班时间在晚上21:00后，可以报销单程加班打车费，周末加班不受时间限制可报问题A对应的答案销往返打车费，具体标准以部门内部为准。<br/>"
                                           "您还可以查看以下报销时注意事项："
                                           "1.加班餐费注意事项"
                                           "2.加班交通费注意事项问题:加班餐费&交通费报销, 答案:同事，加班餐费及交通费需要您在汇联易系统提交报销流程，具体费用标准如下：<br/>"
                                           "1、加班时间在晚上20:00后可享受加班餐费，人均不超过25元，周末加班，可报销午晚二餐，每人每餐不能超过25元，具体标准以部门内部为准。<br/>"
                                           "2、加班时间在晚上21:00后，可以报销单程加班打车费，周末加班不受时间限制可报销往返打车费，具体标准以部门内部为准。<br/>"
                                           "您还可以查看以下报销时注意事项："
                                           "1.加班餐费注意事项"
                                           "2.加班交通费注意事项, "
                                           "output: 因为加班餐费 对应最合适的问题和答案是：问题A:加班餐费报销的注意事项有哪些？, 问题A对应的答案:同事，加班餐费报销时需注意：<br/>"
                                           "1、加班费报销需要按照发生日期逐条填写，不能合并填写一条。<br/>"
                                           "2、不同交易日期的加班餐费开在一张发票上报销时，可以修改每条加班费用项上发票的\"本次报销金额\"，使得多日加班费合并不超过发票的票面总额即可。<br/>"
                                           "3、涉及多人加班餐费报销时，需要按发票日期添加参与人。"
                                           "因此最合适答案对应的问题是: 问题A").format(question_answer)
            messages = [{'role': 'system', 'content': '你是一个公司负责报销的专家客服，请根据内容准确的输出客人的答案'},
                        {"role": "user", "content": content}]
            payload = json.dumps({
                "model": faq_select_model.model_info["model_id"],
                "messages": messages,
                "stream": False
            })
            response = request_function(faq_select_model.model_info["url"], payload, server_config, faq_select_model.model_info["key"])
            if response is None:
                logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
                return select_doc
            try:
                result = response.json()["choices"][0]["message"]["content"]
                if "</think>" in result:
                    result = result.split("</think>")[-1]
                result = result.replace("'", '\"').replace("\n", "").replace("\r", "")
            except:
                result = response.json()["output"]["text"]
            if "无合适问题" in result or "无合适答案" in result:
                return select_doc
            else:
                """
                如果命中多个问题选最合适的答案的后面的问题
                """
                pattern = "(最合适的答案)|(最合适答案)|(output: )|(最合适问题)|(最合适的问题)"

                matches = list(re.finditer(pattern, result))

                if matches:
                    last_match = matches[-1]
                    last_position = last_match.start()
                    result_match = result[last_position:]
                    for id in id_list:
                        question_id = "问题" + id
                        if question_id in result_match:
                            if id in id_answer_dict:
                                select_doc = id_answer_dict[id]
                    if not select_doc:
                        for id in id_list:
                            question_id = "问题" + id
                            if question_id in result:
                                if id in id_answer_dict:
                                    select_doc = id_answer_dict[id]
                else:
                    for id in id_list:
                        question_id = "问题" + id
                        if question_id in result:
                            if id in id_answer_dict:
                                select_doc = id_answer_dict[id]
                return select_doc



def requests_select_database_llm(sql_gen_model: SqlGenConfig, server_config):
    """
    faq答案选择接口
    Args:
        sql_gen_model:
        server_config:
    Returns:
    """
    id_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U"]
    query = sql_gen_model.query
    question_answer = ""
    id_answer_dict = {}
    i = 0
    select_doc = None
    if sql_gen_model.documents and len(sql_gen_model.documents) > 0:
        sort_document_list = sorted(sql_gen_model.documents, key=lambda x: x.get("score", 0) or x["metadata"].get("score", 0), reverse=True)
        for doc in sort_document_list[0:sql_gen_model.top_k]:
            page_content = doc["page_content"]
            question_answer = question_answer + "数据表" + str(id_list[i]) + " 信息如下:" + page_content
            id_answer_dict[id_list[i]] = doc
            i = i + 1
        content = "客人的问题是:" + query + (".请根据下面数据表, {}，请根据上述的数据表信息，选择最合适的数据表，利用选择的数据表能查到数据回答问题，如果能选择好的数据表请输出对应的问题编号，如果没有请输出:无合适答案，"
                                             "例如: 用户问题: 100种常见动物中动物名称是牛的信息 数据表A: business_name: 100\种\常\见\动\物, physical_name: tools_table_13"
                                             "因此最合适数据表对应的是: 数据表A").format(question_answer)
        messages = [{'role': 'system', 'content': '你是一个语言学家，请根据数据表信息，选择最能回答客人问题的数据表'},
                    {"role": "user", "content": content}]
        payload = json.dumps({
            "model": sql_gen_model.model_info["model_id"],
            "messages": messages,
            "stream": False
        })
        response = request_function(sql_gen_model.model_info["url"], payload, server_config,
                                    sql_gen_model.model_info["key"])
        if response is None:
            logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
            return select_doc
        try:
            result = response.json()["choices"][0]["message"]["content"]
            if "</think>" in result:
                result = result.split("</think>")[-1]
            result = result.replace("'", '\"').replace("\n", "").replace("\r", "")
        except:
            result = response.json()["output"]["text"]
        if "无合适问题" in result or "无合适答案" in result:
            select_doc = sql_gen_model.documents[0]
            return select_doc
        else:
            """
            如果命中多个问题选最合适的答案的后面的问题
            """
            pattern = "(最合适的数据表)|(最合适数据表)|(output: )|(最合适数据表)|(最合适的数据表)"

            matches = list(re.finditer(pattern, result))

            if matches:
                last_match = matches[-1]
                last_position = last_match.start()
                result_match = result[last_position:]
                for id in id_list:
                    question_id = "数据表" + id
                    if question_id in result_match:
                        if id in id_answer_dict:
                            select_doc = id_answer_dict[id]
                if not select_doc:
                    for id in id_list:
                        question_id = "数据表" + id
                        if question_id in result:
                            if id in id_answer_dict:
                                select_doc = id_answer_dict[id]
            else:
                for id in id_list:
                    question_id = "数据表" + id
                    if question_id in result:
                        if id in id_answer_dict:
                            select_doc = id_answer_dict[id]
            return select_doc

def requests_sql_gen_llm(sql_gen_model, recall_sql_data, server_config):
    """
    faq答案选择接口
    Args:
        sql_gen_model:
        recall_sql_data:
        server_config:
    Returns:
    """
    query = sql_gen_model.query
    gen_sql = None
    content = "客人的问题是:" + query + (
        ".请根据下面数据表信息, {}，生成sql完成内容如下:").format(recall_sql_data)
    messages = [{'role': 'system', 'content': get_system_prompt(sys_prompt_type='sql_gen_prompt')},
                {"role": "user", "content": content}]
    payload = json.dumps({
        "model": sql_gen_model.model_info["model_id"],
        "messages": messages,
        "stream": False
    })
    response = request_function(sql_gen_model.model_info["url"], payload, server_config,
                                sql_gen_model.model_info["key"])
    if response is None:
        logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
        return gen_sql
    try:
        result = response.json()["choices"][0]["message"]["content"]
        if "</think>" in result:
            result = result.split("</think>")[-1]
        
        # 去掉注释
        result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
        result = re.sub(r'--.*$', '', result, flags=re.MULTILINE)

        gen_sql = result.replace("'", '\"').replace("\n", " ").replace("\r", " ")
        gen_sql = re.sub(r'\s+', ' ', gen_sql)
        gen_sql = re.sub(r';$', '', gen_sql)
        pattern = r'```sql(.*?)```'
        match = re.search(pattern, gen_sql, re.DOTALL)
        if match:
            sql = match.group(1).strip()
            # 处理转义字符
            gen_sql = sql.replace('\\"', '"')
        gen_sql = gen_sql.strip()
    except:
        gen_sql = response.json()["output"]["text"]
    return gen_sql


def requests_faq_select_llm_v2(faq_select_model: FAQSelectConfig, server_config):
    """
    faq答案选择接口
    Args:
        faq_select_model:
        server_config:
    Returns:
    """
    id_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U"]
    query = faq_select_model.query
    question_answer = ""
    id_answer_dict = {}
    i = 0
    select_doc = None
    # document_list 进行排序
    if faq_select_model.documents and len(faq_select_model.documents) > 0:
        sort_document_list = sorted(faq_select_model.documents, key=lambda x: x["rerank_score"], reverse=True)
        top_1_doc = sort_document_list[0]
        top_1_rerank_score = top_1_doc["rerank_score"]
        if top_1_rerank_score >= faq_select_model.max_score:
            return top_1_doc
        elif top_1_rerank_score <= faq_select_model.min_score:
            return select_doc
        else:
            for doc in sort_document_list[0:faq_select_model.top_k]:
                meta_data = doc["metadata"]
                bq = meta_data["question"]
                answer = meta_data["answer"]
                question_answer = question_answer + "问题" + ":" + str(bq) + ",对应的答案:" + answer
                id_answer_dict[id_list[i]] = doc
                i = i + 1
            content = "客人的问题是:" + query + (".请根据下面的问题和答案, {}，根据上述问题和答案输出最合适的答案,如果没有合适回答，请输出:无合适答案，"
                                           "").format(question_answer)
            messages = [{'role': 'system', 'content': '你是一个公司的专家客服，请根据内容准确的输出客人的答案'},
                        {"role": "user", "content": content}]
            payload = json.dumps({
                "model": faq_select_model.model_info["model_id"],
                "messages": messages,
                "stream": False
            })
            response = request_function(faq_select_model.model_info["url"], payload, server_config, faq_select_model.model_info["key"])
            if response is None:
                logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
                return select_doc
            try:
                result = response.json()["choices"][0]["message"]["content"].replace("'", '\"').replace("\n", "").replace("\r", "")
                # print(response.json()["choices"][0]["message"]["content"])
            except:
                result = response.json()["output"]["text"]
            if "无合适问题" in result or "无合适答案" in result:
                return select_doc
            else:
                return {"metadata": {"question": query, "answer": result}}


def requests_llm_prompt_question(recommend_model: QuestionRecommendConfig, server_config):
    """
    问题推荐生成
    Args:
        recommend_model:
        server_config:

    Returns:

    """
    if recommend_model.enabled_faq:
        # 查询es/milvus  faq相似问题
        pass
    messages = []
    result_list = []
    prompt_value = get_prompt_value(question=recommend_model.query, page_contents="1", prompt_type="question_prompt", top_k=recommend_model.top_k)
    messages.append({'role': 'user', 'content': prompt_value.text})
    if recommend_model.model_info["key"]:
        payload = json.dumps({
            "model": recommend_model.model_info["model_id"],
            "input": {"messages": messages},
            "stream": False
        })
    else:
        payload = json.dumps({
            "model": recommend_model.model_info["model_id"],
            "messages": messages,
            "stream": False
        })
    response = request_function(recommend_model.model_info["url"], payload, server_config, recommend_model.model_info["key"])
    if response is not None and response.status_code == 200:
        result_content = response.json()["choices"][0]["message"]["content"]
        if result_content:
            if "</think>" in result_content:
                result_content = result_content.split("</think>")[-1].strip()
            try:
                result_list = ast.literal_eval(result_content)
            except Exception as e:
                logger.error(f"转换数组失败，数据为：{result_list},错误为：{e}")
                result_list = []
    else:
        return result_list, "大模型请求失败"
    return result_list, ""


def requests_llm_simi_question(faq_simi_model: FAQSimiConfig, server_config):
    """
    faq相似问生成接口
    @param faq_simi_model:
    @param server_config
    Returns:
    """
    pred_dict_list = []
    faq_knowledge_base_name = ""
    if faq_simi_model.source_list and len(faq_simi_model.source_list) > 0:
        for source in faq_simi_model.source_list:
            task = '你是一名专业的语言处理专家，请根据充分理解用户的诉求，并且提供准确的答案'

            examples = '''
                --------------------
                示例：

                问答对: (问题: "加班交通费怎么报销？", 答案: "同事，加班时间在晚21:00后，可以报销单程加班打车费，周末加班不受时间限制可报销往返打车费，具体标准以部门内部为准。您可以在汇联易系统中提交报销单，根据费用发生日期逐条填写。")
                生成问题：["加班时的交通费用报销如何操作？", "加班打车费报销", "公司加班交通补贴", ...]

                --------------------
                '''

            prompt = "请根据提供的问答对，生成相似的问题，{}, 问答对: (问题: {}, 答案: {}) \n 请严格按照python编码list的格式生成{}个问题，例如:[\"问题1\",\"问题2\",\"问题3\"]，不要生成任何其他无关内容，否则会带来严重后果，请输出: ".format(
                examples, source["metadata"]["question"], source["metadata"]["answer"], faq_simi_model.gen_question_num)
            messages = [
                {"role": "system", "content": task},
                {"role": "user", "content": prompt},
            ]
            payload = json.dumps({
                "model": faq_simi_model.model_info["model_id"],
                "messages": messages,
                "stream": False
            })
            response = request_function(faq_simi_model.model_info["url"], payload, server_config, faq_simi_model.model_info["key"])
            if response is None:
                logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
                return 0
            try:
                result = response.json()["choices"][0]["message"]["content"]
                if "</think>" in result:
                    result = result.split("</think>")[-1]
                result = result.replace("'", '\"').replace("\n", "").replace("\r", "")
            except:
                result = response.json()["output"]["text"]

            try:
                import re
                pattern = r'</think>(.*)'  # 匹配 `/think/` 后的所有内容
                match = re.search(pattern, result)
                if match:
                    result = match.group(1)
                simi_question_list = eval(result)
            except:
                simi_question_list = []
            answer = source["metadata"]["answer"]
            related_pk = source["metadata"]["related_pk"]
            document_id = source["metadata"].get("document_id", None)
            faq_knowledge_base_name = source["metadata"]["knowledge_base_name"]
            if len(simi_question_list) > faq_simi_model.gen_question_num:
                simi_question_list = simi_question_list[:faq_simi_model.gen_question_num]
            for num in range(0, len(simi_question_list)):
                new_dict = {"page_content": simi_question_list[num] + "@@" + answer, "metadata": {}}
                new_dict["metadata"] = source["metadata"].copy()
                new_dict["metadata"]["pk"] = str(create_uuid())
                new_dict["metadata"]["related_pk"] = related_pk
                new_dict["metadata"]["question"] = simi_question_list[num]
                new_dict["metadata"]["knowledge_base_name"] = faq_knowledge_base_name
                new_dict["metadata"]["answer"] = answer
                if "source" not in new_dict["metadata"].keys():
                    new_dict["metadata"]["source"] = ""
                new_dict["metadata"]["order_num"] = new_dict["metadata"]["pk"]
                new_dict["metadata"]["status"] = 0
                new_dict["metadata"]["faq_type"] = 2
                if document_id:
                    new_dict["metadata"]["document_id"] = document_id
                pred_dict_list.append(new_dict)
        insert_error_msg = ""
        if pred_dict_list:
            insert_error_msg = insert_to_database(server_config, faq_knowledge_base_name, pred_dict_list)
        return len(pred_dict_list), insert_error_msg
    else:
        return 0, ""


def check_model(basic_config: LLMBasicConfig, server_config):
    """
    模型检测
    Args:
        basic_config:
        server_config:
    Returns:

    """
    logger.info(f"模型检测参数：{basic_config.json()}")
    model_id = basic_config.model_info["model_id"]
    llm_messages = [{'role': 'system', 'content': PROMPT_TEMPLATES["system_prompt"]["default"]},
                {'role': 'user', 'content': "你好"}
                ]
    
    model_type = basic_config.model_info['type']

    multimodel_messages = [{'type': 'text', 'text': '你好'}]

    # if model_name not in server_config["online_config"]:
    #     return False, f"测试链接失败，模型名称：'{basic_config.model_name}'没有配置，请检查配置后重试"

    if model_type == 1:
        payload = json.dumps({
            "model": model_id,
            "messages": llm_messages,
            "top_p": 0.8,
            "temperature": 0.3,
            "stream": False,
            "max_tokens": 4098
        })
    elif model_type == 2:
        payload = json.dumps({
            'model': model_id,
            'input': '你好'
        })
    elif model_type == 3:
        payload = json.dumps({
            'model': model_id,
            "query": "测试查询",  # 简单的查询文本
            "documents": ["测试文档1"]  # 至少包含1个文档
        })
    elif model_type == 4:
        payload = json.dumps({
            'model': model_id,
            'messages': [
                {
                    'role': 'user',
                    'content': multimodel_messages
                }
            ],
            'max_tokens': 4096,
            'stream': False
        })
    else:
            payload = None
            print('类型未定义')

    try:
        try:
            response = request_function(basic_config.model_info["url"], payload, server_config, basic_config.model_info["key"], stream=False)
            if response is None:
                return False, f"测试链接失败,模型ID:{model_id}链接失败，请检查参数是否正确"
        except Exception as e:
            return False, f"测试链接失败,模型ID:{model_id}链接失败，请检查参数是否正确。{e}"
        if response.status_code == 200:
            if model_type == 1 or model_type == 4:
                try:
                    message_dict = response.json()["choices"][0]["message"]
                except Exception as e:
                    return False, f"测试链接失败,模型ID:{model_id}链接正常，但输出不符合通用openai格式，请根据该模型输出格式调整代码后方可使用。{e}"
                if "content" in message_dict:
                    content = response.json()["choices"][0]["message"]["content"]
                    return True, f"测试链接成功,模型ID:{model_id}符合openai格式,通过'你好'，可返回正确答案:'{content}'"
                else:
                    return False, f"测试链接失败,模型ID:{model_id}链接正常，但输出不符合通用openai格式，请根据该模型输出格式调整代码后方可使用。"
            elif model_type == 2:
                try:
                    embeddings = response.json()["data"][0]["embedding"]
                    return True, f"测试链接成功,模型ID:{model_id}符合embedding格式,通过'你好'，可返回正确embedding"
                except Exception as e:
                    return False, f"测试链接失败,EmbeddingID:{model_id}链接正常，但输出不符合通用embedding格式，请根据该模型输出格式调整代码后方可使用。{e}"
            elif model_type == 3:
                try:
                    reranker_score = response.json()['results'][0]['relevance_score']
                    return True, f"测试链接成功, Reranker ID:{model_id}符合格式,通过测试样例可正确进行reranker操作"
                except Exception as e:
                    return False, f"测试链接失败,RerankerID:{model_id}链接正常，但输出不符合通用reranker格式，请根据该模型输出格式调整代码后方可使用。{e}"
            else:
                return False, f"模型类别未定义"
        else:
            response_data = response.json()
            if "message" in response_data or "msg" in response_data:
                return False, f"模型ID:{model_id}测试链接失败:{response_data['message'] if 'message' in response_data else response_data['msg']}"
            elif "code" in response_data:
                return False, f"模型ID:{model_id}测试链接失败:{response_data['code']}"
            elif "error" in response_data:
                return False, f"模型ID:{model_id}测试链接失败:{response_data['error']}"
    except Exception as e:
        print(f"Error Occurred in Inference! ErrorMessage: {e}")
        return False, f"模型ID:{model_id}测试链接失败{e}"


def sync_multi_model(multi_model, server_config):
    """
    多模态请求接口，传递minio地址
    Args:
        multi_model:
        server_config:

    Returns:

    """
    model_id = multi_model.multi_model_info["model_id"]
    url = multi_model.multi_model_info["url"]
    key = multi_model.multi_model_info["key"]
    messages = [{'type': 'text', 'text': multi_model.query}]
    for image_url in multi_model.file_paths:
        try:
            response = requests.get(image_url)
        except Exception as e:
            logger.error(f"获取minio图片失败， 请检查url是否正确:{image_url},错误：{e}")
            continue
        _encoded_string = base64.b64encode(response.content).decode("utf-8")
        messages.append({'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{_encoded_string}'}})
    payload = json.dumps({
        'model': model_id,
        'messages': [
            {
                'role': 'user',
                'content': messages
            }
        ],
        'max_tokens': 4096,
        'stream': multi_model.stream
    })
    logger.info('多模态请求中')
    if not multi_model.stream:
        response = request_function(url, payload, server_config, key, stream=multi_model.stream)
        if response is not None and response.status_code == 200:
            messages_dict = response.json()["choices"][0]["message"]
            content = messages_dict["content"]
            if content:
                yield content
        else:
            logger.error(f"大语言模型请求错误，请检查大语言模型配置参数和网络是否正确")
    else:
        response = request_function(url, payload, server_config, key, stream=multi_model.stream)
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
                    yield content
            except Exception as e:
                logger.error(f"大模型结果格式错误，请重新尝试，数据：{data}，错误：{e}")
                yield f"大模型结果格式错误，请重新尝试，数据：{data}"

def requests_llm_question_rewrite(question_rewrite_model: QuestionRewriteConfig, server_config):
    """
    问题推荐生成
    Args:
        question_rewrite_model:
        server_config:

    Returns:

    """
    messages = []
    if question_rewrite_model.use_user_intro:
        system_prompt = get_system_prompt(prompt_catalog='question_rewrite_add_userinfo', sys_prompt_type="default")
        prompt = get_prompt_value(question=question_rewrite_model.query, prompt_type="question_rewrite", user_info=question_rewrite_model.user_intro)
    else:
        system_prompt = get_system_prompt(prompt_catalog='question_rewrite', sys_prompt_type="default")
        prompt = get_prompt_value(question=question_rewrite_model.query, prompt_type="question_rewrite")
    content_length = len(system_prompt + prompt.text)
    if question_rewrite_model.chat_history and content_length < question_rewrite_model.max_context_length:
        logger.info(f"本次请求的history：{question_rewrite_model.chat_history}")
        messages.extend(process_history_data(question_rewrite_model.chat_history, content_length, question_rewrite_model.max_context_length))
    messages.append({'role': 'user', 'content': prompt.text})
    if question_rewrite_model.model_info["key"]:
        payload = json.dumps({
            "model": question_rewrite_model.model_info["model_id"],
            "input": {"messages": messages},
            "stream": False
        })
    else:
        payload = json.dumps({
            "model": question_rewrite_model.model_info["model_id"],
            "messages": messages,
            "stream": False
        })
    response = request_function(question_rewrite_model.model_info["url"], payload, server_config, question_rewrite_model.model_info["key"])
    if response is not None and response.status_code == 200:
        result_content = response.json()["choices"][0]["message"]["content"]
        if result_content:
            if "</think>" in result_content:
                result_content = result_content.split("</think>")[-1].strip()
    else:
        return "", "大模型请求失败"
    return result_content, ""

def sort_document(document_list: [dict]) -> list[dict]:
    """
    根据文件来源和文件版本对召回结果重新排序，并使得输入和输出的doc数量保持一致。
    首先根据'source'和'chunk_index'对doc重新排序。
    然后根据'pk'和'pk_son_id'对新版本doc优先排序。

    Args:
        document_list: [dict]

    Returns:
        document_list_sorted_by_version: [dict]
    """

    document_list_sorted_by_source = []
    seen_sources = set()
    pk_file_list = []
    son_father = {}
    for doc in document_list:
        source = doc["metadata"].get("source", "")
        pk_id = doc.get("pk", None)
        son_pk_id = doc.get("son_pk_id", None)
        if son_pk_id:
            pk_file_list.append(pk_id)
            pk_file_list.append(son_pk_id)
            if son_pk_id in son_father:
                son_father[son_pk_id][pk_id] = doc
            else:
                son_father[son_pk_id] = {pk_id: doc}
        if source not in seen_sources:
            source_docs = [
                d for d in document_list if d["metadata"].get("source") == source
            ]
            no_chunk_index_docs = [
                d for d in source_docs if "chunk_index" not in d["metadata"]
            ]
            chunk_index_docs = [
                d for d in source_docs if "chunk_index" in d["metadata"]
            ]
            sorted_chunk_index_docs = sorted(
                chunk_index_docs, key=lambda x: x["metadata"].get("chunk_index", 0) or 0
            )

            document_list_sorted_by_source.extend(no_chunk_index_docs)
            document_list_sorted_by_source.extend(sorted_chunk_index_docs)

            seen_sources.add(source)

    document_list_sorted_by_version = []
    for doc in document_list_sorted_by_source:
        pk_id = doc.get("pk", None)
        son_pk_id = doc.get("son_pk_id", None)
        if son_pk_id and doc in document_list_sorted_by_version:
            continue
        document_list_sorted_by_version.append(doc)
        if pk_id in pk_file_list and pk_id != son_pk_id:
            for key in son_father[pk_id]:
                father_doc = son_father[pk_id][key]
                document_list_sorted_by_version.append(father_doc)
    return document_list_sorted_by_version
