#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 18:03
# @Author  : yuxj
# @File    : llm_service.py
import ast
import asyncio
import json
import re
import time
import traceback

from fastapi.responses import StreamingResponse
from tqdm import tqdm

from attribute_function.attribute import attribute, attribute_by_llm, last_attribute, AttributeParameter
from attribute_function.trigger import TriggerConfig, trigger_by_rule, trigger_by_llm
from base import LLMOpenChatConfig, FAQChatConfig, BaseResponse, FAQSelectConfig, FAQSimiConfig, LLMBasicConfig, \
    MultiModelConfig, QuestionRecommendConfig, QuestionRewriteConfig, SqlGenConfig
from llm_api_function import requests_qwen_llm, requests_faq_llm, polish_answer_llm, requests_faq_select_llm, \
    requests_llm_simi_question, \
    requests_llm_prompt_question, async_general_service, sync_general_service, check_model, sync_multi_model, \
    requests_llm_question_rewrite, requests_sql_gen_llm, requests_select_database_llm, sort_document
from llm_tool import check_document_length, query_es_data
from prompt_service import get_document_context, build_chat_message, build_chat_prompt, build_message
from prompt_service import get_prompt_value
from operators.common.log import logger
from utils import return_nacos_model


# [R12-ADAPT-ALG-09] 流式端点改为标准 SSE 分帧。
# 背景（TL 实测）：Java `AiServiceImpl:917-928` 用 WebClient `.accept(TEXT_EVENT_STREAM)`
# + `.bodyToFlux(String.class)`，Spring 会走 `ServerSentEventHttpMessageReader`；
# 而本服务原来返回 `media_type="text/plain"` + `{"answer":"银行"}\r\n` 的单换行帧，
# 没有 `data:` 前缀 → Java 侧 `WebClientResponseException: 200 OK`（解码层失败），前端拿兜底文案。
# 改法：只改分帧，不改 JSON 内容 —— 每帧变成 `data: <原 JSON>\n\n`，结束帧 `data: {"end": ""}\n\n`，
# 并把 media_type 改为 `text/event-stream`，使 Spring SSE reader 与前端 fetch-event-source 都能直接消费。
SSE_MEDIA_TYPE = "text/event-stream"
SSE_HEADERS = {
    "Cache-Control": "no-cache",      # 禁缓存，避免中间层合并帧
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",        # 网关/nginx 不缓冲，保证逐帧下发
}


def _sse_frames(chunk):
    """把内部 "json\r\n" 帧拆成若干 `data: json\n\n` SSE 事件（JSON 内容一字不改）。"""
    if chunk is None:
        return
    text = chunk if isinstance(chunk, str) else str(chunk)
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip()
        if line:
            yield f"data: {line}\n\n"


def sse_response(generator) -> StreamingResponse:
    """统一包装同步/异步帧生成器为标准 SSE 响应。"""
    if hasattr(generator, "__aiter__"):
        async def _aiter():
            async for chunk in generator:
                for frame in _sse_frames(chunk):
                    yield frame
        body = _aiter()
    else:
        def _iter():
            for chunk in generator:
                for frame in _sse_frames(chunk):
                    yield frame
        body = _iter()
    return StreamingResponse(body, media_type=SSE_MEDIA_TYPE, headers=SSE_HEADERS)


def text_tracing(token: str, documents: [dict], trace_by_llm: bool, trigger_param: TriggerConfig, attr_param: AttributeParameter, web_documents_list=None, rerank_model_info=None):
    """溯源功能"""
    if not documents:
        attr_result = ""
        yield_token = token
        remain_token = ""
        return yield_token, attr_result, remain_token, trigger_param, attr_param

    if trace_by_llm:
        trigger_output = trigger_by_llm(token, trigger_param)
        if trigger_output.flag == 1:  # 需要将[1]替换成溯源标记
            attr_match = re.search("\[(\d+)]", token)
            yield_token = token[:attr_match.start()]
            remain_token = token[attr_match.end():]
            attr_result, attr_param = attribute_by_llm(int(attr_match.group(1)), attr_param)
            return yield_token, attr_result, remain_token, trigger_param, attr_param

        elif trigger_output.flag == -1:  # 这里包含了没完成的溯源标记 不能yield出去，只能yield 之前的
            return "", "", token, trigger_output.config, attr_param
        else:
            return token, "", "", trigger_output.config, attr_param
    else:
        i = 0
        while i < len(token):
            ch = token[i]
            if i + 1 < len(token) and token[i] == "\n" and token[i + 1] == "\n":  # 把"\n\n" 当成一个字符处理
                ch = token[i] + token[i + 1]

            trigger_output = trigger_by_rule(ch, trigger_param)
            if trigger_output.flag == 1:
                yield_token = token[:i + trigger_output.delta]
                remain_token = token[i + trigger_output.delta:]
                attr_result, attr_param = attribute(trigger_output.attribute_text, attr_param, rerank_model_info=rerank_model_info)
                return yield_token, attr_result, remain_token, trigger_param, attr_param
            #
            elif trigger_output.flag == 0:
                attr_result = ""
                yield_token = token[:i + trigger_output.delta]
                remain_token = token[i + trigger_output.delta:]
                return yield_token, attr_result, remain_token, trigger_param, attr_param

            i += len(ch)

        return token, "", "", trigger_param, attr_param


async def llm_open_chat(llm_open_model: LLMOpenChatConfig):
    """
    异步访问接口
    Args:
        llm_open_model:

    Returns:

    """

    # [R12-ADAPT-ALG-01] 原实现三处调用 text_tracing 的参数与函数签名不符：
    #   text_tracing(token, documents, trace_by_llm, trigger_param, attr_param, web_documents_list, rerank_model_info) -> 5 元组
    #   而原代码写成 text_tracing(full_answer, token, documents) 且尾部用不存在的 finally_flag=True，
    #   导致 /llm_open_chat 一进入流式循环即 TypeError（接口不可用）。
    # 这里按同文件 sync_llm_generate() 的既有正确用法重建溯源状态机（TriggerConfig + AttributeParameter），
    # 逐帧输出仍未改动：{"answer": ...} 若干帧 + 结束帧 {"end": ""}；documents 为空时 text_tracing 原样透传 token。
    async def event_stream():
        config_manager = return_nacos_model().get_config()
        trigger_param = TriggerConfig()          # 溯源触发状态（逐帧推进）
        merge_documents = list(llm_open_model.documents or [])
        if llm_open_model.web_documents_list:
            merge_documents.extend(llm_open_model.web_documents_list)
        attr_param = AttributeParameter(merge_documents)   # 溯源参考句切分结果
        model_name = llm_open_model.model_info["model_name"]
        generator = requests_qwen_llm(llm_open_model, config_manager) if "qwen_api" in model_name \
            else async_general_service(llm_open_model, config_manager)
        async for token in generator:
            if not isinstance(token, str):      # 上游异常时 async_general_service 会 yield {}（原行为）
                continue
            yield_token, attr_result, remain_token, trigger_param, attr_param = text_tracing(
                token, llm_open_model.documents, llm_open_model.trace_by_llm,
                trigger_param, attr_param,
                web_documents_list=llm_open_model.web_documents_list,
                rerank_model_info=llm_open_model.rerank_model_info)
            if yield_token:
                yield json.dumps({"answer": yield_token}, ensure_ascii=False) + "\r\n"
            if attr_result:
                yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"
            if remain_token:
                yield json.dumps({"answer": remain_token}, ensure_ascii=False) + "\r\n"

        # 流结束：冲刷未决句子并做末尾兜底溯源（等价 sync_llm_generate 的收尾分支）
        if llm_open_model.stream and llm_open_model.need_trace_source:
            if trigger_param.pending_lines or trigger_param.cur_text:
                _, attr_result, _, trigger_param, attr_param = text_tracing(
                    "\n\n", llm_open_model.documents, llm_open_model.trace_by_llm,
                    trigger_param, attr_param,
                    web_documents_list=llm_open_model.web_documents_list,
                    rerank_model_info=llm_open_model.rerank_model_info)
                if attr_result:
                    yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"
            if len(attr_param.matched_results) == 0:
                attr_text = "\n".join(trigger_param.pending_lines) if trigger_param.pending_lines else ""
                attr_result, attr_param = last_attribute(attr_text + trigger_param.cur_text, attr_param)
                if attr_result:
                    yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"
        if llm_open_model.stream:
            yield json.dumps({"end": ""}, ensure_ascii=False)

    return sse_response(event_stream())   # [R12-ADAPT-ALG-09] 标准 SSE 分帧


def llm_check_model(basic_config: LLMBasicConfig):
    """
    faq生成接口
    Args:
        basic_config:

    Returns:

    """
    config_manager = return_nacos_model().get_config()
    flag, msg = check_model(basic_config, config_manager)
    if flag:
        return BaseResponse(code=200, msg=f'{msg}')
    else:
        return BaseResponse(code=500, msg=f'{msg}')


def llm_faq_generate(faq_model: FAQChatConfig):
    """
    faq生成接口
    Args:
        faq_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        count, msg = requests_faq_llm(faq_model, config_manager)
        if msg:
            return BaseResponse(code=500, msg=f'生成FAQ问答对失败,{msg}')
        else:
            return BaseResponse(code=200, msg=f'{msg}，共生成{count}条数据', data={"count": count})
    except Exception as e:
        return BaseResponse(code=500, msg=f'生成FAQ问答对失败,{e}')


def llm_polish_answer(faq_model: FAQChatConfig):
    """
    润色接口
    Args:
        faq_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        count, msg, pred_dict_list = polish_answer_llm(faq_model, config_manager)
        return BaseResponse(code=200, msg=f'{msg}，共润色{count}条数据', data={"count": count, "pred_dict_list": pred_dict_list})
    except Exception as e:
        return BaseResponse(code=500, msg=f'润色问答对失败,{e}')


def llm_multi_model(multi_model: MultiModelConfig):
    """
    faq生成接口
    Args:
        multi_model:

    Returns:

    """

    def event_stream():
        config_manager = return_nacos_model().get_config()
        for token in sync_multi_model(multi_model, config_manager):
            yield json.dumps({"answer": token}, ensure_ascii=False) + "\r\n"
        if multi_model.stream:
            yield json.dumps({"end": ""}, ensure_ascii=False)

    return sse_response(event_stream())   # [R12-ADAPT-ALG-09] 标准 SSE 分帧


def sync_llm_generate(llm_open_model: LLMOpenChatConfig):
    """
    通过api访问接口
    Args:
        llm_open_model:

    Returns:

    """
    config_manager = return_nacos_model().get_config()
    model_name = llm_open_model.model_info["model_name"]

    def event_stream():
        # llm_open_model.documents = sort_document(llm_open_model.documents)

        # init 溯源触发参数
        trigger_param = TriggerConfig()
        full_answer_token = ""
        # init 溯源结果参数
        # 进行合并
        merge_documents = llm_open_model.documents
        if llm_open_model.web_documents_list and len(llm_open_model.web_documents_list) > 0:
            merge_documents.extend(llm_open_model.web_documents_list)
        attr_param = AttributeParameter(merge_documents)
        remain_token = ""
        think_flag = True
        open_bracket = False
        # 因为deepseek-r1 有思考但是没有think，所以需自定义拼接
        if model_name == "deepseek-r1" and llm_open_model.reasoning_flag:
            think_flag = False
            yield json.dumps({"answer": "<think>\n"}, ensure_ascii=False) + "\r\n"
        for token in sync_general_service(llm_open_model, config_manager):
            return_result = json.loads(token)
            if "prompt_content" in return_result:
                yield json.dumps({"prompt_content": return_result["prompt_content"]}, ensure_ascii=False) + "\r\n"
            else:
                if llm_open_model.database_documents and len(llm_open_model.database_documents) > 0:
                    if '[' in return_result["content"]:
                        open_bracket = True
                    if re.search(r'(\[\d+\])+', return_result["content"]):
                        return_result["content"] = re.sub(r'(\[\d+\])+', '', return_result["content"])
                        open_bracket = False
                    if re.search(r'\d*\]\[\d*$', return_result["content"]):
                        return_result["content"] = re.sub(r'\d*\]\[\d*', '', return_result["content"])
                        open_bracket = True
                    if re.search(r'\[\d*$',  return_result["content"]):
                        return_result["content"] = re.sub(r'\[\d*$', '', return_result["content"])
                        open_bracket = True
                    if re.search(r'\d+\]', return_result["content"]):
                        return_result["content"] = re.sub(r'\d+\]', '', return_result["content"])
                        open_bracket = False
                    elif re.match(r'\d+', return_result["content"]) and open_bracket:
                        return_result["content"] = ''
                    elif re.search(r'^\]([\s\S]*)$', return_result["content"]):
                        return_result["content"] = re.sub(r'^\]([\s\S]*)$', r'\1', return_result["content"])
                        open_bracket = False
                    elif re.search(r'\[([\s\S]*)$', return_result["content"]):
                        return_result["content"] = re.sub(r'\[([\s\S]*)$', r'\1', return_result["content"])
                remain_token = remain_token + return_result["content"]
                if "<think>" in remain_token:
                    think_flag = False
                elif "</think>" in remain_token:
                    remain_token = remain_token.split("</think>")[-1].strip()
                    yield json.dumps({"answer": "\n\n</think>\n\n"}, ensure_ascii=False) + "\r\n"
                    think_flag = True
                if not llm_open_model.stream:
                    if "</think>" in remain_token:
                        full_answer_token = remain_token.split("</think>")[-1].strip()
                    else:
                        full_answer_token = remain_token
                elif think_flag:
                    full_answer_token += remain_token
                if llm_open_model.stream and llm_open_model.need_trace_source and think_flag and (llm_open_model.documents or llm_open_model.web_documents_list):
                    yield_token, attr_result, remain_token, trigger_param, attr_param = text_tracing(remain_token,
                                                                                                     llm_open_model.documents,
                                                                                                     trace_by_llm=llm_open_model.trace_by_llm,
                                                                                                     trigger_param=trigger_param,
                                                                                                     attr_param=attr_param,
                                                                                                     web_documents_list=llm_open_model.web_documents_list,
                                                                                                     rerank_model_info=llm_open_model.rerank_model_info
                                                                                                     )
                    if yield_token:
                        yield json.dumps({"answer": yield_token}, ensure_ascii=False) + "\r\n"

                    if attr_result:
                        yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"
                else:
                    yield json.dumps({"answer": remain_token}, ensure_ascii=False) + "\r\n"
                    remain_token = ""
        if llm_open_model.stream and llm_open_model.need_trace_source:
            if llm_open_model.trace_by_llm:
                last_remain = ""
                while remain_token and remain_token != last_remain:
                    last_remain = remain_token
                    yield_token, attr_result, remain_token, trigger_param, attr_param = text_tracing(remain_token,
                                                                                                     llm_open_model.documents,
                                                                                                     trace_by_llm=llm_open_model.trace_by_llm,
                                                                                                     trigger_param=trigger_param,
                                                                                                     attr_param=attr_param,
                                                                                                     web_documents_list=llm_open_model.web_documents_list)

                    if yield_token:
                        yield json.dumps({"answer": yield_token}, ensure_ascii=False) + "\r\n"

                    if attr_result:
                        yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"

                if remain_token:
                    yield json.dumps({"answer": remain_token}, ensure_ascii=False) + "\r\n"
                yield json.dumps({"end": ""}, ensure_ascii=False)
            else:
                if trigger_param.pending_lines or trigger_param.cur_text:
                    _, attr_result, _, trigger_param, attr_param = text_tracing("\n\n", llm_open_model.documents, llm_open_model.trace_by_llm,
                                                                                trigger_param, attr_param, web_documents_list=llm_open_model.web_documents_list)
                    if attr_result:
                        yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"

                if len(attr_param.matched_results) == 0:
                    if trigger_param.pending_lines:
                        attr_text = "\n".join(trigger_param.pending_lines)
                    else:
                        attr_text = ""
                    attr_result, attr_param = last_attribute(attr_text + trigger_param.cur_text, attr_param)
                    if attr_result:
                        yield json.dumps({"answer": attr_result}, ensure_ascii=False) + "\r\n"
                yield json.dumps({"end": ""}, ensure_ascii=False)
        elif llm_open_model.stream and not llm_open_model.need_trace_source:
            yield json.dumps({"end": ""}, ensure_ascii=False)
        else:
            yield json.dumps({"end": ""}, ensure_ascii=False)

    def _sync_wrapper(ml, llm_open_model, config_manager, num):
        """同步函数的包装器，用于在线程池中运行"""
        _extract_llm_open_model = llm_open_model.__copy__()
        _extract_llm_open_model.stream = False
        _extract_llm_open_model.prompt_msg = ml
        _extract_llm_open_model.is_return_prompt = False
        _extract_llm_open_model.need_trace_source = False
        _extract_llm_open_model.query = ""

        s = time.time()
        logger.info(f"开始第{num}次多轮问答")

        try:
            for response in sync_general_service(_extract_llm_open_model, config_manager):
                response_dict = json.loads(response)
                if "content" in response_dict:
                    content = re.sub("<think>.*</think>", "", response_dict["content"], flags=re.S).strip()
                    if content:
                        task_time = time.time() - s
                        logger.info(f"第{num}次多轮问答所需时间：{task_time:.2f}s")
                        return {"page_content": content, "metadata": {}}, task_time
            return None, time.time() - s
        except Exception as e:
            logger.error(f"第{num}次多轮问答失败: {e}")
            return None, time.time() - s

    async def _process_with_threadpool(messages_list, llm_open_model, config_manager):
        """长召回内容回答慢，使用线程池处理同步函数进行加速"""
        loop = asyncio.get_event_loop()

        tasks = []
        for i, ml in enumerate(messages_list, 1):
            task = loop.run_in_executor(
                None,  # 使用默认的线程池执行器
                _sync_wrapper,
                ml, llm_open_model, config_manager, i
            )
            tasks.append(task)

        # 限制并发数
        semaphore = asyncio.Semaphore(5)

        async def bounded_task(task):
            async with semaphore:
                return await task

        bounded_tasks = [bounded_task(task) for task in tasks]

        results = await asyncio.gather(*bounded_tasks, return_exceptions=True)

        summary_texts_list = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"任务执行异常: {result}")
            elif result and result[0]:  # result[0] 是内容结果
                summary_texts_list.append(result[0])

        return summary_texts_list

    # 多轮问答， 需要先处理文本数据
    def _check_and_process_document():
        # 检查文本数据
        # 附件问答
        if llm_open_model.file_paths:
            llm_open_model.trace_by_llm = False  # 附件问答不需要溯源
            llm_open_model.need_trace_source = False  # 附件问答不需要溯源
            document_list = []
            config_manager = return_nacos_model()
            config_manager.load_initial_config()
            for key in llm_open_model.file_paths:
                if (document := config_manager.redis_manager.client.get(key)) is not None:
                    document_list.append({"page_content": document, "metadata": {}})
            document_list = check_document_length(document_list, llm_open_model.max_context_length)
            config_manager = config_manager.get_config()
        # 单文本问答
        elif llm_open_model.single_text:
            llm_open_model.trace_by_llm = False  # 单文本问答不需要溯源
            llm_open_model.need_trace_source = False  # 单文本问答不需要溯源
            config_manager = return_nacos_model()
            config_manager.load_initial_config()
            config_manager = config_manager.get_config()
            document_list = query_es_data(llm_open_model.single_text["knowledge_base_name"], llm_open_model.single_text["title"], config_manager)
        else:  # 正常问答
            config_manager = return_nacos_model()
            config_manager.load_initial_config()
            config_manager = config_manager.get_config()
            llm_open_model.documents = sort_document(llm_open_model.documents)
            document_list = check_document_length(llm_open_model.documents, llm_open_model.max_context_length, web_documents_list=llm_open_model.web_documents_list, database_documents=llm_open_model.database_documents, table_result_data=llm_open_model.table_result_data,
                                                  query=llm_open_model.query)

        if not document_list:
            return
        # 整理每次推理的prompt+文本+history
        # 拼接prompt
        prompt_list = build_chat_prompt(llm_open_model, document_list)
        # 拼接上下文， build message
        messages_list = build_message(llm_open_model, prompt_list)
        summary_texts_list = []
        if len(messages_list) > 1:
            # 开启多轮问答
            summary_texts_list = asyncio.run(_process_with_threadpool(messages_list, llm_open_model, config_manager))
            # _extract_llm_open_model = llm_open_model.__copy__()
            # num = 1
            # for ml in messages_list:
            #     _extract_llm_open_model.stream = False
            #     _extract_llm_open_model.prompt_msg = ml
            #     _extract_llm_open_model.is_return_prompt = False
            #     _extract_llm_open_model.need_trace_source = False
            #     _extract_llm_open_model.query = ""
            #     s = time.time()
            #     logger.info(f"开始第{num}次多轮问答")
            #     for response in sync_general_service(_extract_llm_open_model, config_manager):
            #         response_dict = json.loads(response)
            #         if "content" in response_dict:
            #             content = re.sub("<think>.*</think>", "", response_dict["content"], flags=re.S).strip()
            #             if content:
            #                 summary_texts_list.append({"page_content": content, "metadata": {}})
            #         elif "prompt_content" in response_dict:
            #             continue
            #         else:
            #             logger.error(f"模型输出异常 response: {response_dict}")
            #     logger.info(f"第{num}次多轮问答所需时间：{time.time() - s}")
        else:
            # 不需要拆分， 直接拼接messages，访问推理服务
            llm_open_model.prompt_msg = messages_list[0]
            llm_open_model.query = None
        if summary_texts_list:
            # 多轮问答，总结回答
            prompt_str = "\n---\n".join(build_chat_prompt(llm_open_model, summary_texts_list, is_round=True))
            message = build_message(llm_open_model, [prompt_str])
            llm_open_model.prompt_msg = message[0]
            llm_open_model.query = None

    _check_and_process_document()
    return sse_response(event_stream())   # [R12-ADAPT-ALG-09] 标准 SSE 分帧


def sync_llm_rounds_generate(llm_open_model: LLMOpenChatConfig):
    """
    劼翔针对表格多轮编写代码
    轮询问答：让大模型对大量的召回内容进行信息提炼，然后最后放入推理接口进行总结。
    Args:
        llm_open_model:

    Returns:
        """

    config_manager = return_nacos_model().get_config()
    model_name = llm_open_model.model_info["model_name"]

    def event_stream(summary_texts):

        if model_name == "deepseek-r1" and llm_open_model.reasoning_flag:
            yield json.dumps({"answer": "<think>\n"}, ensure_ascii=False) + "\r\n"

        llm_open_model.need_trace_source = False  # 从摘要中概括没办法进行溯源
        llm_open_model.trace_by_llm = False
        if summary_texts:
            llm_open_model.documents = summary_texts  # 后面改下参数名称
            llm_open_model.prompt_msg = build_chat_message(llm_open_model, prompt_type="summary_loop_prompt")
            llm_open_model.query = None

        remain_token = ""
        for token in sync_general_service(llm_open_model, config_manager):
            return_result = json.loads(token)
            remain_token = remain_token + return_result.get("content") if return_result.get("content") else return_result.get("prompt_content", "")

            if "</think>" in remain_token:
                remain_token = remain_token.split("</think>")[-1].strip()
                yield json.dumps({"answer": "\n\n</think>\n\n"}, ensure_ascii=False) + "\r\n"

            yield json.dumps({"answer": remain_token}, ensure_ascii=False) + "\r\n"
            remain_token = ""

        if llm_open_model.stream:
            yield json.dumps({"end": ""}, ensure_ascii=False)

    def knowledge_extract():
        """尽可能多拼接chunk 让大模型根据用户的问题进行信息提炼"""
        _extract_llm_open_model = llm_open_model.__copy__()
        _extract_llm_open_model.stream = False

        # 单次发给大模型的最大拼接长度
        if "rotate_answer" in config_manager:
            max_char_length = config_manager["rotate_answer"].get("max_char_length", 15000)
        else:
            logger.warning("nacos参数未更新，没有找到rotate_answer配置项，使用默认值")
            max_char_length = 15000

        summary_texts = []
        document_context = get_document_context(_extract_llm_open_model.documents, truncation=False)
        if len(document_context) <= 100:
            logger.info(_extract_llm_open_model.documents)

        logger.info(f"召回文本长度:{len(document_context)}")

        if len(document_context) < max_char_length:
            # 不需要进行信息提取
            return []

        cur_chat_length = 0
        documents = _extract_llm_open_model.documents[:]
        batch_documents = []
        for i, document in enumerate(documents):
            _doc_prompt = get_document_context([document], truncation=False)
            if cur_chat_length + len(_doc_prompt) < max_char_length:
                if len(batch_documents) == 0:
                    batch_documents.append([document])
                else:
                    batch_documents[-1].append(document)
            else:
                batch_documents.append([document])
                cur_chat_length = 0
            cur_chat_length += len(_doc_prompt)

        if len(batch_documents) >= 6:
            logger.warning(f"召回文本非常长，需要{len(batch_documents)}次LLM信息提炼")

        for batch in tqdm(batch_documents):
            _extract_llm_open_model.documents = batch[:]
            for response in sync_general_service(_extract_llm_open_model, config_manager):
                response_dict = json.loads(response)
                if "content" in response_dict:
                    content = re.sub("<think>.*</think>", "", response_dict["content"], flags=re.S).strip()
                    summary_texts.append(content)
                else:
                    logger.error(f"模型输出异常 response: {response_dict}")
        return summary_texts

    summary_texts = knowledge_extract()
    return sse_response(event_stream(summary_texts))   # [R12-ADAPT-ALG-09] 标准 SSE 分帧


def llm_question_recommend(recommend_model: QuestionRecommendConfig):
    """
    问题推荐生成
    Args:
        recommend_model:

    Returns:

    """
    # 问题推荐
    config_manager = return_nacos_model().get_config()
    history_list = []
    if recommend_model.chat_history:
        # 不能用dict，避免历史问答中存在相同问题，不同答案
        for history in recommend_model.chat_history:
            history_list.append(history["query"])
    prompt_value = get_prompt_value(question=recommend_model.query, page_contents=recommend_model.answer, prompt_type="question_recommend",
                                    top_k=recommend_model.top_k, annex_content=history_list)
    messages = [{'role': 'user', 'content': prompt_value.text}]
    llm_open_model = LLMOpenChatConfig(model_info=recommend_model.model_info, stream=False, prompt_msg=messages, query="", need_trace_source=False)
    for token in sync_general_service(llm_open_model, config_manager):
        return_result = json.loads(token)
        remain_token = return_result["content"]
        if "</think>" in remain_token:
            remain_token = remain_token.split("</think>")[-1].strip()
        try:
            result_list = ast.literal_eval(remain_token)
            result_list = result_list[:recommend_model.top_k]
        except Exception as e:
            logger.error(f"大模型返回数据格式错误，请重试，错误：{e}，数据：{remain_token}")
            return []
        return result_list
    return []


def llm_faq_select(faq_select_model: FAQSelectConfig):
    """
    faq 二次选择
    Args:
        faq_select_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        select_doc = requests_faq_select_llm(faq_select_model, config_manager)
        return BaseResponse(code=200, msg=f'大模型选择成功', data=select_doc)
    except Exception as e:
        return BaseResponse(code=500, msg=f'大模型失败,{e}')

def llm_sql_generate(sql_gen_model: SqlGenConfig):
    """
    大模型对sql进行生成
    Args:
        sql_gen_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        recall_sql_data = requests_select_database_llm(sql_gen_model, config_manager)
        gen_sql = requests_sql_gen_llm(sql_gen_model, recall_sql_data, config_manager)
        return BaseResponse(code=200, msg=f'大模型生成sql成功', data={
                "sql": gen_sql, 
                "database_id": recall_sql_data['metadata']['database_id'], 
                'table_name': recall_sql_data['metadata']['physical_name']
            }
        )
    except Exception as e:
        return BaseResponse(code=500, msg=f'大模型生成sql失败,{e}')

def llm_simi_question(faq_simi_model: FAQSimiConfig):
    """
    相似问生成接口
    Args:
        faq_simi_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        count, msg = requests_llm_simi_question(faq_simi_model, config_manager)
        if msg:
            return BaseResponse(code=500, msg=f'生成相似问失败，{msg}')
        else:
            return BaseResponse(code=200, msg=f'生成相似问成功，共生成{count}条数据，存入数据库')
    except Exception as e:
        return BaseResponse(code=500, msg=f'生成相似问失败,{e}')


def llm_question_prompt(recommend_model: QuestionRecommendConfig):
    """
    问题推荐生成
    Args:
        recommend_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        count, msg = requests_llm_prompt_question(recommend_model, config_manager)
        if msg:
            return BaseResponse(code=500, msg=f'生成提示问题失败，{msg}')
        else:
            return BaseResponse(code=200, msg=f'生成提示问题，共生成{count}条数据')
    except Exception as e:
        return BaseResponse(code=500, msg=f'生成提示问题失败,{e}')

def llm_question_rewrite(question_rewrite_model: QuestionRewriteConfig):
    """
    问题推荐生成
    Args:
        question_rewrite_model:

    Returns:

    """
    try:
        config_manager = return_nacos_model().get_config()
        rewrite_query, msg = requests_llm_question_rewrite(question_rewrite_model, config_manager)
        if msg:
            return BaseResponse(code=500, msg=f'问题改写失败，{msg}')
        else:
            return BaseResponse(code=200, msg=f'问题改写成功，改写后的问题是:{rewrite_query}', data={"query":rewrite_query})
    except Exception as e:
        traceback.print_exc()
        return BaseResponse(code=500, msg=f'问题改写失败,{e}')
