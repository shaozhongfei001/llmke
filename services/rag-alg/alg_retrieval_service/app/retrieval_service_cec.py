#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/2/12 15:40
# @Author  : yuxj
# @File    : retrieval_service_cec.py
import asyncio
import re
import time

import requests

from base import BaseResponse, CECRetrieveConfig, CECTableRetrieveConfig
from operators.rephraser.llm_rephraser import LLMRephraser
from operators.reranker.bge_reranker import BGEReranker
from operators.retriever.hybrid_retriever import HybridRetriever
from operators.retriever.db_retriever import DBRetriever
from retrieval_fun_tool import process_return_results
from retrieval_service import retrieval_data, process_table_result, rerank_cal_fun
from utils import return_nacos_model, create_uuid
from operators.common.log import logger


def generate_prompt_for_section(data_list):
    # 获取段落标题和内容
    result = {}
    content = ""
    result_content = ""
    for item in data_list:
        item = item.replace("\n\n", "\n").replace("\n\n\n", "\n").replace("\n\n\n\n", "\n").replace("\\n", "\n")
        try:
            key, value = item.split('\n', 1)
        except Exception as e:
            logger.error(f"生成文本数据不符合标准：{item}，错误：{e}")
            continue
        if key == '参考资料':
            continue
        content += key + ":" + value + ","
        if key == "详细需求":
            continue
        result[key] = value.strip()
        # 生成 Prompt
    if "输出范例" in result.keys():
        result_content = result["输出范例"]
    if "借款人公司名称" in result.keys():
        company_name = result["借款人公司名称"]
    else:
        company_name = ""
    prompt = f"""
    以下是一段文本内容，请根据内容生成与其相关的检索问题，以便用于检索返回相关结果。
    步骤:
        1.请根据'##' 符号将文本拆分成多个文本块，如果没有'##'就无需拆分。
        2.你无需分析文本数据中的信息，你只需要根据文本信息进行问题生成就可以，保证我可以根据生成的问题的答案能查询到对应的答案可以说明该段文本中所有的内容。
        3.生成的问题，遵守以下格式： <q>问题1</q>\n<q>问题2</q>\n
    注意:
        1.如果有输出内容："{result_content}"，你需要按照输出范例的格式进行输出，确保内容中的所有项都能通过问题查询到对应的答案。
        2.如果输出内容是表格，确保列名和行名中都所有的对应的查询问题，保证根据问题可以查询出表格中所有的值，保证完整性。
        3.如果输出内容是指标，请根据每个指标生成出对应的问题，我想要是通过问题来获取指标中对应对答案。
        4.如果输出内容中有内容要求，请详细分析内容要求中的每句话、每个指标，都能生成对应的问题，保证生成的问题能覆盖所有内容的。
        5.如果有公司名称："{company_name}"公司相关信息，你所有的问题都需要加上该公司的名称。
        6.确保每个指标和需求都有对应都问题，希望你给出的问题是合理的、高质量的、逻辑性强的、意义明确的，还能表达文本中主要的意思。
    必须遵守：
        生成的问题，遵守以下格式： <q>问题1</q>\n<q>问题2</q>\n
    ######################
    -示例-
    ######################
    示例1:
    Text:
    ## 借款人公司名称
    成都蓉矽半导体有限公司
    ## 表格行名
    报表：主营业务收入
    增值税申报书：纳税收入
    增值税实际缴纳税额
    所得税申报书：纳税收入
    所得税实际缴纳税额
    
    ## 详细需求
    * 请根据上文提供的参考资料提取出表格的行名和列名对应的指标，生成表格以展示借款人不同年份下的纳税情况。
    * 使用markdown排版格式把生成内容总结为表格返回给用户。
    * 除表格本身外，不要返回任何无关内容。
    * 对于未能获得指标取值的指标不进行填写，不得编造指标。
    ######################
    Output:
    <q>成都蓉矽半导体有限公司主营业务收入是多少</q>\n<q>成都蓉矽半导体有限公司增值税申报书中纳税收入是多少</q>\n<q>成都蓉矽半导体有限公司增值税实际缴纳税额是多少</q>\n
    <q>成都蓉矽半导体有限公司主营所得税申报书中纳税收入是多少</q>\n<q>成都蓉矽半导体有限公司所得税实际缴纳税额是多少</q>\n
    <q>成都蓉矽半导体有限公司借款人不同年份下的纳税情况</q>\n
    ########
        """
    # prompt = f"""
    #     你是个信贷尽调报告小助手，下面都是关于信贷尽调报告方面。
    #     以下是一段文本内容，请根据内容生成与其相关的检索问题，问题应聚焦于文本的标题和内容，以便用于检索返回相关结果。
    #     请根据内容的每一个需求或者指标生成问题，确保内容中的所有项都能通过问题查询到对应的答案。
    #     如果标题中是主题信息，请根据内容生成对应的问题，，我想要是通过问题来获取主题内容中对应对答案。
    #     如果标题中是指标信息，请根据每个指标生成出对应的问题，我想要是通过问题来获取指标中对应对答案。
    #     如果标题是是详细需求，请结合上下文中的信息，在需求文本中，请提取其中业务关键信息来生成问题，不要跟上下文无关的问题，例如：上面的主题和指标都是信贷尽调报告相关问题，那么在提取需求文本中时，请不要提取其他类型都问题。
    #     如果标题是是其他方面，请按照对应内容生成问题，我想要是通过问题来获取内容中对应对答案。
    #     请你对生成的问题进行口语化，可以将同一个问题用不同的形式生成，但是不要窜改主要意思。
    #     生成的问题，遵守以下格式： <q>问题1</q>\n<q>问题2</q>\n
    #     标题：{title}
    #     内容：{content}
    #     生成的问题：
    #     """
    return prompt


def cec_create_factored_query(query, model_info, server_config):
    """
    :param query: 用户初始问题
    :param model_info: 大语言模型配置
    :param server_config: 配置
    :return: query重写

    """
    """联合"""
    sections = query.split("##")
    query_type_list = [section.strip() for section in sections if section.strip()]
    user_prompt = """
                ######################
                -文本数据-
                Text: {passage}
                ######################
                ######################
                Output:"""

    system_prompt = generate_prompt_for_section(query_type_list)
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt.format(passage=query)}]
    # prompts = [generate_prompt_for_section(section, query) for section in query_type_list]
    queries = []
    # for prompt in prompts:
    payload = {
        "prompt_msg": messages,
        "model_info": model_info,
        "is_return_prompt": False,
        "stream": False
    }
    headers = {'Content-Type': 'application/json'}
    llm_url = 'http://' + server_config["llm_server"]["host"] + ':' + str(server_config["llm_server"]["port"]) + '/' + \
              server_config["llm_server"]["api_name"]
    try:
        base_response = requests.post(llm_url, json=payload, headers=headers)
        data = base_response.json()
    except Exception as e:
        logger.error(f"请求模型推理服务错误，检查模型配置，可能是模型推理服务错误,{e}")
        return queries
    if base_response.status_code == 200 and "answer" in data.keys():
        verification_response = data["answer"]
        if "</think>" in verification_response:
            verification_response = verification_response.split('</think>')[-1]
    else:
        logger.info(f"参数：{payload}")
        logger.error(f"问题重改写失败，或是大模型返回格式不正确,{base_response.status_code},{base_response.text}")
        verification_response = ""
    for v_q in re.findall("<q>(.*)</q>", verification_response):
        queries.append(v_q)
        logger.info(f"问题：{v_q}")
    pattern = re.compile(r'^问题\d+$')
    queries = [q for q in queries if not pattern.match(q)]
    return queries

async def retrieval_documents_table(cec_model: CECTableRetrieveConfig):
    """通过query查询提取mysql查询所需信息，兼容retrieval_documents_cec
    """
    logger.info(f"参数：{str(cec_model.json())}")
    logger.info("开始召回")
    server_config = return_nacos_model().get_config()
    model_name = 'Qwen3-32B-AWQ'
    if model_name in server_config:
        cec_model.model_name = model_name
        cec_model.model_info = {"key": "", "model_id": model_name, "model_name": model_name,
                        "url": server_config[model_name]['url']}
    url = server_config["mysql-indicator-query"]["url"]
    url_table_indicator = server_config["url_table_indicator"]["url"]
    query = cec_model.query
    query_list = cec_model.query_list
    query_indicators = cec_model.query_indicators
    flag, indicators = await DBRetriever(cec_model).retrieve_query(url, query, query_list, query_indicators, url_table_indicator)
    if flag:
        return BaseResponse(code=200, msg=f'查询成功', data={"indicator": indicators, "documents_list": [], "log_list": []})
    else:
        response = await retrieval_documents_cec(cec_model)
        response.data['indicator'] = []
        for idx, cur in enumerate(response.data['documents_list']):
            response.data['documents_list'][idx]['metadata']["offset"] = str(cur['metadata']["offset"])
            response.data['documents_list'][idx]['metadata']["page_size"] = str(cur['metadata']["page_size"])
            response.data['documents_list'][idx]['metadata']["position"] = str(cur['metadata']["position"])
        return response


async def retrieval_table_cec(cec_model: CECTableRetrieveConfig):
    """
    多路召回检索服务_table
    :param cec_model:参数对象
    :return: 检索结果
    """
    logger.info(f"参数：{str(cec_model.json())}")
    logger.info("开始召回")
    server_config = return_nacos_model().get_config()
    model_name = 'Qwen3-32B-AWQ'
    if model_name in server_config:
        cec_model.model_name = model_name
        cec_model.model_info = {"key": "", "model_id": model_name, "model_name": model_name,
                        "url": server_config[model_name]['url']}
    url = server_config["mysql-indicator-query"]["url"]
    url_table_indicator = server_config["url_table_indicator"]["url"]
    query = cec_model.query
    query_list = cec_model.query_list
    query_indicators = cec_model.query_indicators
    flag, indicators = await DBRetriever(cec_model).retrieve_query(url, query, query_list, query_indicators, url_table_indicator)
    if flag:
        return BaseResponse(code=200, msg=f'查询成功', data={"indicator": indicators, "documents_list": [], "log_list": []})
    # 回答修正，模型给出其他问题，query扩展和分布
    t1 = time.time()
    query_rephrase = LLMRephraser(cec_model).rephrase(cec_model.query)
    
    logger.info(f"生成问题所需时间：{time.time() - t1},共生成1条问题")
    t2 = time.time()
    es_knowledge_base_list = ["table_summary_" + kn for kn in cec_model.knowledge_base_name]
    
    hybrid_retriever = HybridRetriever(cec_model)
    documents_hybrid = await hybrid_retriever.retrieve(cec_model.query, cec_model.knowledge_base_name, es_knowledge_base_list, 
                                                       cec_model.retrieval_top_k, server_config, None, cec_model.kb_file_list, None, None, 'and')
    documents_hybrid_rephrase = await hybrid_retriever.retrieve(query_rephrase, cec_model.knowledge_base_name, es_knowledge_base_list, 
                                                                cec_model.retrieval_top_k, server_config, None, cec_model.kb_file_list, None, None, 'and')
    documents_hybrid = hybrid_retriever.merge_result(documents_hybrid, documents_hybrid_rephrase)

    logger.info(f"共查出:{len(documents_hybrid)}条数据")
    logger.info(f"查询数据所需时间：{time.time() - t2}")
    t3 = time.time()
    logger.info(f"处理表格数据所需时间：{time.time() - t3}")
    idx_rerank = await BGEReranker().rerank(cec_model.query, documents_hybrid, server_config)
    documents_list_new = [documents_hybrid[idx] for idx in idx_rerank]
    documents_hybrid = list(map(lambda x: {
        "page_content": x.page_content, 
        "metadata": {
            "table_preceding_context": x.metadata.get('table_preceding_context'),
            "table_html_content": x.metadata['table_html_content']
        }}, documents_hybrid))
    documents_list_new = list(map(lambda x: {
        "page_content": x.page_content, 
        "metadata": {
            "table_preceding_context": x.metadata.get('table_preceding_context'),
            "table_html_content": x.metadata.get('table_html_content')
        }}, documents_list_new))
    logger.info(f"共所需时间：{time.time() - t1}")
    return BaseResponse(code=200, msg=f'查询成功', data={"indicator": [], "documents_list": documents_hybrid, "log_list": documents_list_new})


async def retrieval_documents_cec(cec_model: CECRetrieveConfig):
    """
    多路召回检索服务_cec
    :param cec_model:参数对象
    :return: 检索结果
    """
    logger.info(f"参数：{str(cec_model.json())}")
    log_pk_dict = {}
    queries = []
    log_list = []
    external_pk = create_uuid()
    logger.info("开始召回")
    server_config = return_nacos_model().get_config()
    # 回答修正，模型给出其他问题，query扩展和分布
    t1 = time.time()
    if cec_model.query_enrich:
        model_name = cec_model.model_name
        if model_name:
            model_info = {"key": server_config[model_name]["key"], "model_id": server_config[model_name]["model_id"], "model_name": model_name,
                          "url": server_config[model_name]["url"]}
        else:
            model_info = cec_model.model_info
        queries = cec_create_factored_query(cec_model.query, model_info, server_config)  # 回答修正，模型给出其他问题，query扩展和分布
    elif cec_model.query_list:
        queries = cec_model.query_list
    # 将原始问题添加问题列表中
    if cec_model.query:
        queries.append(cec_model.query)
    logger.info(f"生成问题所需时间：{time.time() - t1},共生成{len(queries)}条问题")
    t2 = time.time()
    cec_kb_file_list = cec_model.kb_file_list
    documents, table_summary_data, *others = await retrieval_data(cec_model.knowledge_base_name, cec_model.retrieval_top_k, server_config,
                                                         verify_queries=queries, enabled_faq=False, enabled_summary=cec_model.enabled_summary,
                                                         es_milvus_enabled={"es": cec_model.enabled_es, "milvus": cec_model.enabled_milvus},
                                                         cec_kb_file_list=cec_kb_file_list)
    logger.info(f"共查出:{len(documents)}条数据")
    logger.info(f"查询数据所需时间：{time.time() - t2}")
    t3 = time.time()
    if table_summary_data and cec_model.enabled_summary:
        documents, log_pk_dict = await process_table_result(documents, table_summary_data, external_pk, cec_model, server_config, queries, log_pk_dict,
                                                            cec_model.query)
    logger.info(f"处理表格数据所需时间：{time.time() - t3}")
    documents_list_new = []
    all_values = [value for value in documents.values()]
    if documents and any(all_values):
        # 合并数据开始计算排序
        t4 = time.time()
        documents, log_pk_dict = await rerank_cal_fun(cec_model, cec_model.query, documents, external_pk, server_config, log_pk_dict)
        logger.info(f"rerank所需时间：{time.time() - t4}")
        # 整合文档
        documents_list = []
        for que, doc_list in documents.items():
            doc_list = doc_list[:cec_model.top_k]
            for dl in doc_list:
                documents_list.append({"page_content": dl.page_content, "metadata": dl.metadata, "type": dl.type})
        if not documents_list:
            logger.info(f'查询成功,但是经过重拍模型后，查询结果皆小于重拍阈值，没有符合的答案，请重新设置阈值或修改问题')
            return BaseResponse(code=200, msg=f'查询成功,但是经过重拍模型后，查询结果皆小于重拍阈值，没有符合的答案，请重新设置阈值或修改问题',
                                data={"documents_list": documents_list_new, "log_list": log_list})
        logger.info(f"多路合并排序完成，还剩{len(documents_list)}条数据")
        documents_list_new = await asyncio.to_thread(lambda: process_return_results(documents_list))
        # documents_list_new = sorted(documents_list_new, key=lambda x: x["score"], reverse=True)
    if log_pk_dict:
        log_list = list(log_pk_dict.values())
    logger.info(f"共所需时间：{time.time() - t1}")
    return BaseResponse(code=200, msg=f'查询成功', data={"documents_list": documents_list_new, "log_list": log_list})
