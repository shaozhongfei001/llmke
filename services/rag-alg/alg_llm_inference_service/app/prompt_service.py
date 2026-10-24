#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/7/1 18:02
# @Author  : yuxj
# @File    : prompt_service.py
import os

from langchain.prompts.prompt import PromptTemplate

from llm_tool import process_history_data
from prompt_config import PROMPT_TEMPLATES
from operators.common.log import logger


def build_chat_prompt(llm_open_model, document_list, is_round=False):
    """拼接输入模型的信息"""
    full_prompt_list = []
    attribute_task_prompt = ""

    if document_list:
        # 先检查document的长度问题
        if llm_open_model.need_trace_source and llm_open_model.trace_by_llm:
            attribute_task_prompt = get_system_prompt(sys_prompt_type="attribute_task_prompt")
        if is_round:
            attribute_task_prompt = attribute_task_prompt + "\n" + get_system_prompt(sys_prompt_type="summary_loop_prompt")
        # 多版本管理-prompt
        if all([doc['metadata'].get('revise_date', None) for doc in llm_open_model.documents]):
            attribute_task_prompt = attribute_task_prompt + "\n" + get_system_prompt(sys_prompt_type='multi_version_prompt')

        if llm_open_model.use_user_intro and llm_open_model.user_intro and len(llm_open_model.user_intro) > 0:
            sys_prompt = get_system_prompt(sys_prompt_type="speciality_prompt_add_user_intro").format(
                system_content=(llm_open_model.system_prompt or "")  +  get_system_prompt(sys_prompt_type="no_context"),
                attribute_task_prompt=attribute_task_prompt,
                user_intro=llm_open_model.user_intro
            )
        else:
            sys_prompt = get_system_prompt(sys_prompt_type="speciality_prompt").format(
                system_content=(llm_open_model.system_prompt or "" )  +  get_system_prompt(sys_prompt_type="no_context"),
                attribute_task_prompt=attribute_task_prompt
            )
        context_content_list = get_document_context_new(document_list, llm_open_model.max_context_length - 1000)  # -1000 留着给history
        for context_content in context_content_list:
            user_prompt = get_system_prompt(sys_prompt_type="user_prompt").format(context_content=context_content, query=llm_open_model.query)
            full_prompt_list.append(sys_prompt + "\n" + user_prompt)

    else:
        sys_prompt = f"""
                        # 任务
                        * 任务描述: {(llm_open_model.system_prompt or "")  +  get_system_prompt(sys_prompt_type="no_context")}
                     """
        user_prompt = get_system_prompt(sys_prompt_type="user_prompt").format(context_content="无参考资料", query=llm_open_model.query)
        full_prompt_list.append(sys_prompt + "\n" + user_prompt)
    return full_prompt_list


def build_message(llm_open_model, prompt_list):
    """拼接输入模型的信息"""
    messages_list = []
    for pl in prompt_list:
        messages = []
        if llm_open_model.chat_history and len(pl) < llm_open_model.max_context_length:
            messages.extend(process_history_data(llm_open_model.chat_history, len(pl), llm_open_model.max_context_length))
        messages.append({'role': 'user', 'content': pl})
        messages_list.append(messages)
    logger.info(f"本次请求的history：{llm_open_model.chat_history}")
    logger.info(f"本次请求的完整prompt：{messages_list}")
    return messages_list


def build_chat_message(llm_open_model, prompt_type="attribute_task_prompt"):
    """拼接输入模型的信息"""
    messages = []
    if llm_open_model.documents:
        # 先检查document的长度问题
        if llm_open_model.need_trace_source and llm_open_model.trace_by_llm:
            attribute_task_prompt = get_system_prompt(sys_prompt_type=prompt_type)
        else:
            attribute_task_prompt = ""
        if all([doc['metadata'].get('revise_date', None) for doc in llm_open_model.documents]):
            attribute_task_prompt = attribute_task_prompt + "\n" + get_system_prompt(sys_prompt_type='multi_version_prompt')
        sys_prompt = get_system_prompt(sys_prompt_type="speciality_prompt").format(
            system_content=llm_open_model.system_prompt or get_system_prompt(sys_prompt_type="no_context"),
            attribute_task_prompt=attribute_task_prompt
        )
        context_content = get_document_context(llm_open_model.documents, llm_open_model.max_context_length)
        user_prompt = get_system_prompt(sys_prompt_type="user_prompt").format(context_content=context_content, query=llm_open_model.query)
    else:
        sys_prompt = f"""
                        # 任务
                        * 任务描述: {llm_open_model.system_prompt or get_system_prompt(sys_prompt_type="no_context")}
                     """
        user_prompt = get_system_prompt(sys_prompt_type="user_prompt").format(context_content="无", query=llm_open_model.query)

    content_length = len(sys_prompt + user_prompt)

    # messages.append({'role': 'system', 'content': "})

    if llm_open_model.chat_history and content_length < llm_open_model.max_context_length:
        logger.info(f"本次请求的history：{llm_open_model.chat_history}")
        messages.extend(process_history_data(llm_open_model.chat_history, content_length, llm_open_model.max_context_length))
    messages.append({'role': 'user', 'content': sys_prompt + "\n" + user_prompt})
    # with open("input_prompt.md", "w") as f:
    #     f.write(sys_prompt + "\n\n")
    #     f.write("<省略历史对话>" + "\n\n")
    #     f.write(user_prompt)
    logger.info(f"本次请求的完整prompt：{messages}")
    return messages


# def build_summary_chat_message(llm_open_model):
#     """拼接输入模型的信息"""
#     messages = []
#     if llm_open_model.documents:
#
#         sys_prompt = f"""
# # 任务
# * 任务描述: {llm_open_model.system_prompt or get_system_prompt("default")}
#     你需要根据「参考资料」来回答接下来的「用户问题」，这些信息在 <context></context> XML tags 之内，你需要根据参考资料给出准确，简洁的回答。
#     参考资料是阅读了不同的资料后得出的答案，请你根据这些资料中得出的有效信息拼出一个最完整全面的答案提供给客户。
# * 你的回答要满足以下要求:
#     1. 回答内容必须在参考资料范围内，尽可能模仿和遵照参考资料的表述来回答问题，不能做任何参考资料以外的扩展解释，不要携带与用户提问无关内容。
#     2. 回答中需要根据客户问题和参考资料保持与客户的友好沟通,如果参考资料不能帮助你回答用户问题，告知客户无法回答该问题，并引导客户提供更加详细的信息。
#     3. 参考资料中的表格，以markdown形式呈现。其中，单元格中用"[-]"表示省略了重复的合并单元格，代表着这个格子中的内容和上或左侧格子内容一致，请合理推测单元格的内容。
#     4. 为了保密需要，委婉地拒绝回答有关参考资料的文档名称或文档作者等问题。
#     5. 如果用户的问题关于查找图片，直接返回检索结果就可以，不需要进行说明。
#     6. 客户有格式洁癖，为了给用户更好的体验，请严格按照Markdown的格式,选择合适的格式让答案看起来专业、简洁，如果不按照合适格式会带来客户投诉，带来严重后果。
#     7. Markdown的格式要求，请注意使用合适的换行,请不要在序号前面添加"#"符号(会生成标题格式导致字体变大),请严格按照上述要求，如果不按照合适格式会带来客户投诉。
#     8. Markdown的格式要求，尽量不要使用表格格式，如果非要生成表格时候一定要注意表格格式的正确，不能缺少，不然前端会出现乱码，损失很大。
#     9. Markdown的格式要求，生成的内容中不要带有markdown字样的内容。
# # 任务执行
# 现在请你根据提供的参考资料，遵循限制来回答用户的问题，你的回答需要准确和完整。
# """
#         #
#         # all_missing_chunk_index = all('chunk_index' not in doc.get('metadata', {}) for doc in llm_open_model.documents)
#         # if all_missing_chunk_index:
#         #     context_content = get_document_context(llm_open_model.documents)
#         # else:
#         #     context_content = get_document_context_sorted(llm_open_model.documents)
#
#         context_content = "\n---\n".join(llm_open_model.documents)
#         user_prompt = f"""
# # 参考资料
# <context>
# {context_content}
# </context>
#
# # 用户问题
# {llm_open_model.query}
#
# # 回答
# """
#     else:
#         sys_prompt = ""
#         user_prompt = llm_open_model.query
#
#     content_length = len(sys_prompt + user_prompt)
#     messages.append({'role': 'system', 'content': ""})
#
#     with open(f"logs/summary_prompt.json", "a") as f:
#         f.write(sys_prompt + "\n" + user_prompt + "-----\n\n")
#
#     # logger.info(f"参数保存到：logs/summary_prompt.json")
#     if llm_open_model.chat_history:
#         messages.extend(process_history_data(llm_open_model.chat_history, content_length))
#     messages.append({'role': 'user', 'content': sys_prompt + "\n" + user_prompt})
#     return messages


def get_prompt_value(question: str = "", page_contents: str = None, prompt_type="llm_chat", prompt: PromptTemplate = None, top_k: int = 20, annex_content=None, user_info=""):
    """
    提示词工程
    :param question: 用户问题
    :param page_contents: 参考答案
    :param top_k: 每段文本生成的问答对数量
    :param prompt_type: 配置参数
    :param prompt: 自定义提示词
    :param annex_content: 自定义文本
    :param user_info: 用户信息
    :return: prompt结果
    """
    if page_contents or prompt_type == "question_recommend":
        prompt_template = PROMPT_TEMPLATES[prompt_type].get("default")
        prompt = prompt or PromptTemplate.from_template(template=prompt_template)
        if prompt_type == "faq_llm_chat":
            prompt_value = prompt.format_prompt(top_k=top_k,context=page_contents)
        elif prompt_type == "polish_llm_chat":
            prompt_value = prompt.format_prompt(question=question, context=page_contents)
        elif prompt_type == "question_prompt":
            prompt_value = prompt.format_prompt(question=question, top_k=top_k)
        elif prompt_type == "question_recommend":
            prompt_value = prompt.format_prompt(question=question, answer=page_contents, top_k=top_k, annex_content=annex_content)
        else:
            prompt_value = prompt.format_prompt(context=page_contents, question=question)
    elif prompt_type == "question_rewrite":
        prompt_template = PROMPT_TEMPLATES[prompt_type].get("user_prompt")
        prompt = prompt or PromptTemplate.from_template(template=prompt_template)
        prompt_value = prompt.format_prompt(question=question)
    elif prompt_type == "question_rewrite_add_userinfo":
        prompt_template = PROMPT_TEMPLATES[prompt_type].get("user_prompt")
        prompt = prompt or PromptTemplate.from_template(template=prompt_template)
        prompt_value = prompt.format_prompt(question=question, user_info=user_info)
    else:
        prompt_template = PROMPT_TEMPLATES[prompt_type].get("no_context")
        prompt = prompt or PromptTemplate.from_template(template=prompt_template)
        prompt_value = prompt.format_prompt(question=question)
    return prompt_value


def get_system_prompt(prompt_catalog='system_prompt', sys_prompt_type="default"):
    return PROMPT_TEMPLATES[prompt_catalog].get(sys_prompt_type, "")


def get_document_context(document_list: [dict], max_length=10000, truncation=True) -> str:
    """
    拼接召回结果
    """
    if truncation:
        # 如果doc的chunk字数大于max_length 按照平均值进行截断
        page_contents = [doc["page_content"] for doc in document_list]
        if len("\n".join(page_contents)) > max_length:
            max_document_length = max_length // len(page_contents)
            logger.warning(f"召回文本过长，截断。截断长度为{max_document_length}")
        else:
            max_document_length = None
    else:
        max_document_length = None

    document_contexts = []
    for i, doc in enumerate(document_list):
        doc_name = os.path.split(doc['metadata'].get('source', ''))[-1]

        doc_content = f"""
## 参考资料{i}
* doc_name: {doc_name}
* chunk_title: {doc['metadata'].get("title_path") if doc['metadata'].get("title_path", None) is not None else ""}
* doc_type: {doc['metadata'].get("chunk_type")}
* index: {doc['metadata'].get('chunk_index') if 'chunk_index' in doc['metadata'] else 'N/A'}
* content: {doc["page_content"] if max_document_length is None else doc["page_content"][:max_document_length]}
* version_date: {doc['metadata'].get('revise_date')}"""
        document_contexts.append(doc_content)
    return "\n---\n".join(document_contexts)


def get_document_context_new(document_list: [dict], max_length):
    """
    拼接召回结果_new 多轮问答
    参考资料需要加载一下
    """

    document_contexts = []
    temp_content = ""
    for i, doc in enumerate(document_list):
        if "type" in doc and doc["type"] == "web_search":
            doc_source = "网络搜索"
        elif "type" in doc and doc["type"] == "database":
            doc_source = "数据库"
        else:
            doc_source = "本地知识库"
        doc_name = os.path.split(doc['metadata'].get('source', ''))[-1]
        doc_content = f"""
## 参考资料{i}
* doc_name: {doc_name or None}
* doc_source: {doc_source or None}
* chunk_title: {doc['metadata'].get("title_path") if doc['metadata'].get("title_path", None) is not None else None}
* doc_type: {doc['metadata'].get("chunk_type", None)}
* index: {doc['metadata'].get('chunk_index') if 'chunk_index' in doc['metadata'] else None}
* content: {doc["page_content"]}
* version_date: {doc['metadata'].get('revise_date', None)}"""
        if len(temp_content + "\n---\n" + doc_content) < max_length:
            temp_content += "\n---\n" + doc_content
        else:
            document_contexts.append(temp_content)
            temp_content = doc_content
    if temp_content:
        document_contexts.append(temp_content)
    return document_contexts


def get_document_context_sorted(document_list: [dict], max_length=10000) -> str:
    """
    按照 `source` 和 `index` 排序文档并拼接结果

    todo: 该函数功能已经拆分到其他函数中，该函数已无实际调用.
    功能拆分到以下函数中
     1. 排序document: llm_api_function.py -> sort_document()
     2. 拼接prompt: prompt_service.py -> get_document_context()
    """
    # 如果doc的chunk字数大于max_length 按照平均值进行截断
    page_contents = [doc["page_content"] for doc in document_list]
    if len("\n".join(page_contents)) >= max_length:
        max_document_length = max_length // len(page_contents)
        print(f"召回文本过长，截断。截断长度为{max_document_length}")
    else:
        max_document_length = None

    document_contexts = []
    document_list_sorted = []
    seen_sources = set()
    pk_file_list = []
    son_father = {}
    for doc in document_list:
        source = doc['metadata'].get('source', '')
        pk_id = doc.get('pk', None)
        son_pk_id = doc.get('son_pk_id', None)
        if son_pk_id:
            pk_file_list.append(pk_id)
            pk_file_list.append(son_pk_id)
            if son_pk_id in son_father:
                son_father[son_pk_id][pk_id] = doc
            else:
                son_father[son_pk_id] = {pk_id: doc}
        if source not in seen_sources:
            source_docs = [d for d in document_list if d['metadata'].get('source') == source]
            no_chunk_index_docs = [d for d in source_docs if 'chunk_index' not in d['metadata']]
            chunk_index_docs = [d for d in source_docs if 'chunk_index' in d['metadata']]
            sorted_chunk_index_docs = sorted(chunk_index_docs, key=lambda x: x['metadata'].get('chunk_index', 0))

            document_list_sorted.extend(no_chunk_index_docs)
            document_list_sorted.extend(sorted_chunk_index_docs)

            seen_sources.add(source)

    for doc in document_list_sorted:
        pk_id = doc.get('pk', None)
        son_pk_id = doc.get('son_pk_id', None)
        if son_pk_id:
            continue
        father_doc_list = []
        if pk_id in pk_file_list:
            for key in son_father[pk_id]:
                father_doc = son_father[pk_id][key]
                father_doc_list.append(father_doc)
        doc_name = os.path.split(doc['metadata'].get('source', ''))[-1]
        doc_content = f"""
                        * doc_name: {doc_name}
                        * chunk_title: {doc['metadata'].get("title_path") if doc['metadata'].get("title_path", None) is not None else ""}
                        * doc_type: {doc['metadata'].get("chunk_type")}
                        * index: {doc['metadata'].get('chunk_index') if 'chunk_index' in doc['metadata'] else 'N/A'}
                        * content: {doc['page_content'][:max_document_length] if max_document_length else doc['page_content']}"""
        # * index: {doc['metadata'].get('chunk_index')}
        document_contexts.append(doc_content)
        for father_doc in father_doc_list:
            doc = father_doc
            doc_name = os.path.split(doc['metadata'].get('source', ''))[-1]
            doc_content = f"""
                                    * doc_name: {doc_name}
                                    * chunk_title: {doc['metadata'].get("title_path") if doc['metadata'].get("title_path", None) is not None else ""}
                                    * doc_type: {doc['metadata'].get("chunk_type")}
                                    * index: {doc['metadata'].get('chunk_index') if 'chunk_index' in doc['metadata'] else 'N/A'}
                                    * content: {doc['page_content'][:max_document_length] if max_document_length else doc['page_content']}"""
            # * index: {doc['metadata'].get('chunk_index')}
            document_contexts.append(doc_content)
    return "\n---\n".join(document_contexts)
