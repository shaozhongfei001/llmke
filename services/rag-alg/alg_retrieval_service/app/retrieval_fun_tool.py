#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/2/12 15:40
# @Author  : yuxj
# @File    : retrieval_fun_tool.py
import json
import math
import re
import traceback
from collections import defaultdict

import pandas as pd
import httpx
from langchain_core.documents import Document

from utils import create_uuid
from operators.common.log import logger
from operators.client.es_client import ESClient


async def query_es_data(question, query_img_pk_list, knowledge_base_name, server_config):
    """
    查询chunk数据
    Args:
        question:
        query_img_pk_list:
        knowledge_base_name:
        server_config
    Returns:

    """
    es_documents = []
    data = {
        "index_name": knowledge_base_name,
        "condition_logic_operations": "or",
        "condition_json": [
            {
                "pk": query_img_pk_list
            }
        ]
    }
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/search_by_page'
    es_response = None

    try:
        es_response = await ESClient.request(es_url=es_url, data=data)
        es_data = es_response["data"]["result_data"]
    except Exception as e:
        logger.exception(f"index ES服务 查询异常, 错误详情: {e}。 请求URL: {es_url}, 请求参数data: {data}, 返回结果: {es_response}")
        return es_documents
    for i, x in enumerate(es_data):
        x['_source']['metadata']["search"] = {
            "type": ["es"],
            "query": question,
            "rank": [i]
        }
        es_documents.append(Document(page_content=x['_source']['page_content'], metadata=x['_source']['metadata']))
    return es_documents


async def query_es_table_data(question, table_summary_ids: list, knowledge_base_name, server_config):
    """
    查询指定表格数据
    Args:
        question:
        table_summary_ids:
        knowledge_base_name:
        server_config
    Returns:
    """
    es_documents = []
    data = {
        "index_name": knowledge_base_name,
        "condition_logic_operations": "or",
        "query_body": [],
        # "query": [
        #     {
        #         "table_summary_id": table_summary_ids,
        #     }
        # ],
        "page_num": 5000  # 最多返回5000个chunk
    }

    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    es_response = None

    try:
        es_response = await ESClient.request(es_url=es_url + 'search_by_page', data=data)
        es_data = es_response["data"]["result_data"]
    except Exception as e:
        logger.exception(f"index ES服务 查询异常, 错误详情: {e}。 请求URL: {es_url}, 请求参数data: {data}, 返回结果: {es_response}")
        return es_documents

    for i, x in enumerate(es_data):
        x['_source']['metadata']["search"] = {
            "type": ["es"],
            "query": question,
            "rank": [i]
        }
        es_documents.append(Document(page_content=x['_source']['page_content'], metadata=x['_source']['metadata']))
    return es_documents


def document_version(documents_list):
    """
    版本控制
    Args:
        documents_list:

    Returns:

    """

    def process_group(group):
        if group['revise_date'].isnull().any():  # 检查是否有空值
            # 如果有空值，返回 scores 最大的数据
            return group
        else:
            # 如果没有空值，返回 revise_date 最新的数据
            return group.loc[[group['revise_date'].idxmax()]]

    meta_dict_list = [{**{'page_content': dict(x)['page_content']}, **dict(x)['metadata'], 't_type': dict(x)['type']}
                      for x in documents_list]
    df = pd.DataFrame(meta_dict_list)
    if 'parent_file_name' not in df.columns or 'revise_date' not in df.columns:
        documents_list = [dict(x) for x in documents_list]
        return documents_list
    elif df['parent_file_name'].isnull().all() or df['revise_date'].isnull().all():
        documents_list = [dict(x) for x in documents_list]
        return documents_list
    df['revise_date'] = pd.to_datetime(df['revise_date'], errors='coerce')
    if 'score' in df.columns:
        df['score'] = df['score'].astype(float)
    result = df.groupby('parent_file_name', as_index=False).apply(process_group).reset_index(drop=True)
    result_list = result.to_dict(orient='records')
    documents_list = [{"page_content": rl.pop("page_content"), "type": rl.pop("t_type"), "metadata": rl} for rl in
                      result_list]
    return documents_list


def og_process(external_pk, ori_query, documents, server_config, log_pk_dict=None):
    """
    log日志记录功能
    Args:
        external_pk:
        ori_query:
        documents:
        server_config:
        log_pk_dict:

    Returns:

    """
    if log_pk_dict is None:
        log_pk_dict = {}
    for ques, doc_list in documents.items():
        for ed in doc_list:
            log_result = {"external_pk": external_pk, "question": ed.metadata["query"], "original_question": ori_query,
                          "knowledge_base_name": ed.metadata["knowledge_base_name"], "page_content": ed.page_content,
                          "search_source": json.dumps(ed.metadata.get("type", None)),
                          "source_rank": json.dumps(ed.metadata["rank"]), "top_k": server_config["retrieval_top_k"],
                          "offset": str(ed.metadata.get("offset", None)), "rrf_scores": ed.metadata["rrf_score"],
                          "score": ed.metadata["score"],
                          "query_weight": ed.metadata["query_weight"], "faq_answer": ed.metadata.get("answer", None),
                          "faq_filter_threshold": server_config["faq_score_threshold"]}
            log_pk_dict[ed.metadata["pk"]] = log_result
    return log_pk_dict


async def split_query(query, model_name, server_config):
    """
    :param query: 用户初始问题
    :param model_name: 大语言模型名称
    :param server_config: 配置
    :return: query重写

    """
    prompt = """
         如果需要，请以列表形式返回多个问题。请判断两个问题的连续性，如果存在先后关系，请在拆分后将每个问题补充完整,每个独立问题内要保证问题中的主语不是代词。
        如果不需要，返回"不"。不需要说明理由
        例1：
            问题：通过银行进行国际收支统计申报如何进行？
            回答：不
        例2：
            问题：大额交易报告的交易信息包含哪些？对于恐怖活动可疑交易信息，最迟何时提交？
            回答：["大额交易报告的交易信息包含哪些？", "对于恐怖活动可疑交易信息，最迟何时提交？"]
        例3：
            问题：浙商银行的发展历程中经历了哪些重要的阶段和变革？这些阶段和变革对其发展有何重要意义？
            回答：["浙商银行的发展历程中经历了哪些重要的阶段和变革？", "浙商银行的发展历程和变革中的重要阶段和改变对其发展有何重要意义？"]
        ----------------------------------------------
        问题：{}
        回答：    给你一个问题，判断这个问题是否需要拆分成多个独立的问题来回答。

     """
    fail_count = 3
    payload = {
        "query": prompt.format(query),
        "model_name": model_name,
        "stream": False
    }
    headers = {'Content-Type': 'application/json'}
    llm_url = 'http://' + server_config["llm_server"]["host"] + ':' + str(server_config["llm_server"]["port"]) + '/' + \
              server_config["llm_server"]["api_name"]

    count = 0
    success_flag = False
    while count < fail_count and not success_flag:

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
                base_response = await client.post(llm_url, json=payload, headers=headers)
                queries = base_response.json()["answer"]
                queries = json.loads(queries)
                if queries == "不":
                    return []
                if len(queries) == 1:
                    return []
                logger.info(f"原始问题：{query}")
                logger.info(f"问题列表：{queries}")
                return queries
        except Exception as e:
            traceback.print_exc()
            logger.error(f"重写错误：{e}")
            count += 1
    return []


async def factored_chain_of_verification(query, model_name, server_config):
    """
    :param query: 用户初始问题
    :param model_name: 大语言模型名称
    :param server_config: 配置
    :return: query重写

    """
    """联合"""
    verification_prompt = "根据下文中的3个事实性语段，分别提出4-5个验证问题。" \
                          "如果文中不存在可提问的内容，请指出文中的关键词也可进行一些改写。" \
                          "遵守以下格式：" \
                          "<q>问题1</q>\n<q>问题2</q>\n" \
                          "正文: {}"
    baseline_prompt = f"请根据用户提出的问题简短地回答问题。" \
                      f"注意，用户之前上传了一些文档供你参考，而此时你还没有看到这些文档。" \
                      "如果你认为这个问题必须先阅读文档才能进行回答，那么请指出你想要查找的文件内容。" \
                      "问题： {}"
    payload = {
        "query": baseline_prompt.format(query),
        "model_name": model_name,
        "stream": False
    }
    headers = {'Content-Type': 'application/json'}
    llm_url = 'http://' + server_config["llm_server"]["host"] + ':' + str(server_config["llm_server"]["port"]) + '/' + \
              server_config["llm_server"]["api_name"]
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        base_response = await client.post(llm_url, json=payload, headers=headers)
        payload["query"] = verification_prompt.format(base_response.json()["answer"])
    async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
        ver_response = await client.post(llm_url, json=payload, headers=headers)
        verification_response = ver_response.json()["answer"]
    logger.info(f"原始问题：{query}")
    logger.info("\t* baseline", str(base_response.json()))
    logger.info("\t* verification_response", str(ver_response.json()))
    queries = []
    for v_q in re.findall("<q>(.*)</q>", verification_response):
        logger.info("\t*", v_q)
        queries.append(v_q)
    pattern = re.compile(r'^问题\d+$')
    queries = [q for q in queries if not pattern.match(q)]
    return queries


async def requests_llm(mes, model_info, server_config, prompt_flag=True, max_tokens=None):
    """
    大模型请求服务
    Args:
        max_tokens:
        mes:
        model_info:
        server_config:
        prompt_flag:

    Returns:

    """
    res_data = ""
    if prompt_flag:
        payload = {
            "prompt_msg": mes,
            "model_info": model_info,
            "is_return_prompt": False,
            "stream": False
        }
    else:
        payload = {
            "query": mes,
            "model_info": model_info,
            "is_return_prompt": False,
            "stream": False
        }

    if max_tokens:
        payload["max_tokens"] = max_tokens

    headers = {'Content-Type': 'application/json'}
    llm_url = 'http://' + server_config["llm_server"]["host"] + ':' + str(server_config["llm_server"]["port"]) + '/' + \
              server_config["llm_server"]["api_name"]
    try:
        async with httpx.AsyncClient() as client:
            base_response = await client.post(llm_url, json=payload, headers=headers)
    except:
        logger.error(f"表格筛选时大模型请求失败!请求参数: {model_info}\n{traceback.format_exc()}")
        return ""

    # print(base_response.json())
    if not base_response or base_response.status_code != 200:
        logger.error(f"大模型请求失败:{base_response.text}")
        return res_data
    if "answer" not in base_response.json().keys():
        logger.error(f"大模型请求成功，但是格式不符合要求，请重新请求:{base_response.text}")
        return res_data
    else:
        res_data = base_response.json()["answer"]
    return res_data


def multiple_retrieval_data_process(results):
    # 处理验证查询的结果
    # 文档版本管理筛选
    # 1. 筛选table_summary，如果数据存在查询table_chunks，分开写，原因是针对性查询
    table_summary_data = {}
    documents = {}
    web_search = {}
    database_sql = {}
    if results:
        for docs in results:
            for qus, ds_list in docs.items():
                table_summary_list = []
                documents_list = []
                web_search_list = []
                sql_list = []
                for ds in ds_list:
                    if "database_id" in ds.metadata.keys():
                        sql_list.append(ds)
                    elif ds.type == "web_search":
                        web_search_list.append(ds)
                    elif "type" in ds.metadata.keys() and ds.metadata["type"] == "table_summary":
                        table_summary_list.append(ds)
                    else:
                        documents_list.append(ds)
                if table_summary_list:
                    if qus in table_summary_data:
                        table_summary_data[qus].extend(table_summary_list)
                    else:
                        table_summary_data[qus] = table_summary_list
                if documents_list:
                    if qus in documents:
                        documents[qus].extend(documents_list)
                    else:
                        documents[qus] = documents_list
                if web_search_list:
                    if qus in web_search:
                        web_search[qus].extend(web_search_list)
                    else:
                        web_search[qus] = web_search_list
                if sql_list:
                    if qus in database_sql:
                        database_sql[qus].extend(sql_list)
                    else:
                        database_sql[qus] = sql_list
    return documents, table_summary_data, web_search, database_sql


def process_return_results(documents_list):
    """
    处理返回结果
    Args:
        documents_list:
        top_k:
    Returns:

    """
    documents_list_new = []
    remove_duplicates = []
    for x in documents_list:
        if x["page_content"] in remove_duplicates:
            continue
        remove_duplicates.append(x["page_content"])
        if "document_id" not in x["metadata"].keys():
            x["metadata"]["document_id"] = ""
        if "search_type" in x["metadata"].keys():
            x["metadata"]["search_type"] = list(set(x["metadata"]["search_type"]))
        chunk_index = x["metadata"].get("chunk_index", None)
        title_path = x["metadata"].get("title_path", None)
        dict_new = {"page_content": x["page_content"],
                    "metadata": {
                        "source": x["metadata"].get("source", None),
                        "file_path": x["metadata"].get("file_path", None),
                        "id": x["metadata"].get("document_id", None),
                        "search_type": x["metadata"].get("search_type", None),
                        "offset": x["metadata"].get("offset", None),
                        "pic_offset_list": x["metadata"].get("pic_offset_list", None),
                        "pic_children_id_list": x["metadata"].get("pic_children_id_list", None),
                        "text_parent_id_list": x["metadata"].get("text_parent_id_list", None),
                        "chunk_type": x["metadata"].get("type", None),
                        "position": x["metadata"].get("position", None),
                        "file_id": int(x["metadata"].get("file_id", None)),
                        "image_path": x["metadata"].get("image_path", None),
                        "page_size": x["metadata"].get("page_size", None),
                        "page_number": x["metadata"].get("page_number", None),
                        "table_name": x["metadata"].get("table_name", None),
                        "labels": x["metadata"].get("labels", None),
                        "chunk_index": x["metadata"].get("chunk_index", None),
                        "table_summary_id": x["metadata"].get("table_summary_id", None),
                        "revise_date": x["metadata"].get("revise_date", None),
                        "score": x["metadata"].get("score", 0),
                        "rerank_score_rank": x["metadata"].get("rerank_score_rank", 0),
                        "rrf_score": x["metadata"].get("rrf_score", 0),
                        "rrf_score_rank": x["metadata"].get("rrf_score_rank", 0),
                    },
                    "type": x["metadata"].get("type", None),
                    "pic_url_list": x["metadata"].get("pic_url_list", None),
                    "knowledge_base_name": x["metadata"].get("knowledge_base_name", None),
                    "order_num": str(create_uuid()),
                    "faq_question": x["metadata"].get("question", None),
                    "faq_answer": x["metadata"].get("answer", None),
                    "pk": x["metadata"].get("pk", None),
                    "score": x["metadata"].get("score", 0),
                    "rerank_score_rank": x["metadata"].get("rerank_score_rank", 0),
                    "rrf_score": x["metadata"].get("rrf_score", 0),
                    "rrf_score_rank": x["metadata"].get("rrf_score_rank", 0),
                    }
        if chunk_index is not None and isinstance(chunk_index, (int, float)) and not math.isnan(chunk_index):
            dict_new["metadata"]["chunk_index"] = int(chunk_index)
        if title_path is not None and isinstance(title_path, str) and len(title_path) > 0:
            dict_new["metadata"]["title_path"] = title_path
        documents_list_new.append(dict_new)
    # documents_result_list = sorted(documents_list_new, key=lambda x: x["score"], reverse=True)
    return documents_list_new


def sorted_result(data):
    # 1. 按file_id分组
    groups = defaultdict(list)
    for item in data:
        groups[item["metadata"]['file_id']].append(item)

    # 2. 组内按score降序排序
    sorted_groups = {}
    for file_id, items in groups.items():
        sorted_items = sorted(items, key=lambda x: x["metadata"]['score'], reverse=True)
        sorted_groups[file_id] = sorted_items

    # 3. 按组的最高分降序排序
    sorted_group_list = sorted(
        sorted_groups.values(),
        key=lambda group: group[0]["metadata"]['score'],
        reverse=True
    )
    sorted_groups_index_list = []
    try:
        for item_dict in sorted_group_list:
            sorted_items = sorted(item_dict, key=lambda x: int(x["metadata"]['chunk_index']), reverse=False)
            sorted_groups_index_list.extend(sorted_items)
    except Exception as e:
        logger.error(f"排序错误，可能该文件没有生成chunk_index字段或者chunk_index没有正确赋值，错误：{e}")
        sorted_groups_index_list = [item for item_dict in sorted_group_list for item in item_dict]
        return sorted_groups_index_list

    return sorted_groups_index_list


async def filter_tables_by_query(query, table_summary_dict, model_info, server_config):
    """利用LLM 确认问题是否依赖于指定表格，找出指定表格后续利用
    table_summary_dict: {<query>: [Document(
                                        page_content: <table_summary>,
                                        metadata: {"source":"", "file_path": "", 'title': '图谱-报销流程.xlsx', 'type': 'table_summary', })]
                        }

    """
    user_prompt = """
**任务说明**
你负责利用数据库信息给用户提供帮助，现在你需要根据手头有的一些表格摘要信息快速缩小表格的筛选范围，你只需要扫一眼表头、标题判断和用户的指向是不是大致符合就可以。不需要依据表格内容严格匹配
1. 从用户的问题结合知识库中的文件，找到并且提取问题中的文件名、表格名称等关键字段。需要优先保证文件名、表格名称能够和用户的问题匹配，如果文件名、表格名称和用户问题都匹配，那么即可命中。
2. 如果用户的问题中提到了某个表的具体名称或者sheet名，不需要考虑表格内容返回表格编号。
3. 如果用户的问题中指向并不明确，那么依据表格内容进行判断是否关联。

表格只是作为内容的参考，并不概括所有表格内容，不需要严格遵照。

**输入数据**
用户问题：{{query}}
摘要列表：{{table_summary}}

**输出要求**
JSON格式：
[1,2,3 ...]

**示例**
[示例1]
问题：《银行业金融机构监督数据标准化规范（2021版）填报口径（第一期）》中答疑口径中涉及存着信息表有哪些，列出序号，报送说明，问题描述
摘要列表：
---
#1
摘要：文件名：《银行业金融机构监管数据标准化规范（2021版）填报口径（第一期）》.xls
sheet名：表1-答疑口径
表格标题: 表1-答疑口径  
表头: 序号,主题（必填）,表名,数据项,校核规则序号,报送说明（必填）,问题描述（必填）,问题案例,建议填报方案（必填）,提交时间,答复（必填）,检核规则调整说明,规范调整说明,答疑人联系方式,重点审定,报表牵头部门,业务部门  
表格内容: 该表格记录了银行业金融机构监管数据标准化规范（2021版）填报口径答疑的相关信息，包含7条记录。主要内容涉及会计科目报送范围、借贷标志处理、期初余额报送、科目归属填报等问题。例如，问题1讨论了表外科目借贷标志的报送方式，问题2涉及机构归属调整对期初余额报送的影响，问题3和问题4探讨了科目范围的报送要求，问题5讨论了会计科目报送范围的定义，问题6和问题7涉及内部科目对照表的填报口径。这些问题的解答有助于明确填报规则，提升数据报送的准确性和规范性。
---
#2 
摘要：文件名：《银行业金融机构监管数据标准化规范（2021版）填报口径（第一期）》.xls
sheet名：表4-即期及衍生品交易信息表填报示例5.1
表格标题: 表4-即期及衍生品交易信息表填报示例5.1  
表头: 交易背景,金融许可证号,内部机构号,银行机构名称,交易编号,业务品种  
表格内容: 该表格展示了银行业金融机构在2021年期间涉及的多种金融交易信息，包括即期结售汇、即期外汇买卖、贵金属交易、远期合约、掉期交易、利率互换、期权交易等。表格内容涵盖了交易时间、交易价格、交易金额、交易对手以及交易类型等信息。例如，填报机构在2021年6月1日以6.36元人民币/美元的价格向某交易对手卖出6360元人民币，属于即期结售汇交易；而在2021年12月14日以1.128美元/欧元的价格向某匿名交易对手卖出500欧元，则属于即期外汇买卖交易。此外，表格还记录了远期利率协议、利率互换、信用违约互换等复杂金融工具的交易细节，反映了填报机构在风险管理、对冲交易以及衍生品市场中的活跃程度。交易编号从101到701，覆盖了多种业务品种，体现了填报机构在不同金融领域的业务布局和风险敞口管理策略。
---
指定表格编号： [1]
原因： 用户的问题中提到了填报口径表和答疑口径，这两个信息点和#1 非常吻合，虽然摘要中没有提到存折信息表，考虑到表格摘要中只包含了部分信息只能反应表格结构和大致内容，因此指向性已经非常明确了。 

[示例2]
问题：帮我做数据可视化
摘要列表：
---
（无相关摘要）
---
指定表格编号： []

**输入**
问题： {query}
摘要列表：
{summary}

指定表格编号：
"""

    id2table_summary = dict()
    for q, table_summary_list in table_summary_dict.items():
        for summary in table_summary_list:
            id2table_summary[summary.metadata['pk']] = summary

    table_summary_list = list(id2table_summary.values())

    table_summary_string = "---\n".join(f'#{i + 1}\n'
                                        f'摘要：{table.page_content}\n'
                                        for i, table in enumerate(table_summary_list))

    messages = [{"role": "system", "content": ""},
                {"role": "user", "content": user_prompt.format(query=query, summary=table_summary_string)}]
    # print(user_prompt.format(query=query, summary=table_summary_string))
    res_result = await requests_llm(messages, model_info, server_config)
    # logger.info(f"模型回复：{res_result}")

    try:
        res_result = re.sub("<think>.*</think>", "", res_result, flags=re.S)
        res = re.search("\[[0-9,\n ]*]", res_result, flags=re.S)

        if not res:
            logger.info(f"问题：{query}，大模型未找到对应的summary, llm_response: {res}")
            return None

        index_string = res.group()

        summary_indexes = json.loads(index_string)
        selected_summary_pk_list = []
        for idx in summary_indexes:
            idx = int(idx)
            if idx in range(1, len(table_summary_list) + 1):
                selected_summary_pk_list.append(table_summary_list[idx - 1].metadata["pk"])

        if len(selected_summary_pk_list) == 0:
            logger.info(f"问题：{query}，无法根据模型输出找到对应摘要, llm_response: {res_result.strip()}")
        else:
            logger.info(f"问题：{query}，大模型根据摘要筛选出的表格pk: {selected_summary_pk_list}")
        return_table_summary_dict = {}
        for q, table_summary_list in table_summary_dict.items():
            for table_summary in table_summary_list:
                if table_summary.metadata["pk"] in selected_summary_pk_list:
                    if q not in return_table_summary_dict:
                        return_table_summary_dict[q] = [table_summary]
                    else:
                        return_table_summary_dict[q].append(table_summary)
        return return_table_summary_dict

    except:
        logger.error(f"大模型筛选报错, error message: {traceback.format_exc()}")
        return None


async def get_multi_version_dict(kb_names, server_config):
    multi_version_url = server_config['multi_version']['url']
    params = {
        "pageSize": 10,
        "pageNo": 1,
        "kbNames": ','.join(kb_names),
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        'Content-Type': 'application/json'
    }

    multi_version_dict = {}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            base_response = await client.get(multi_version_url, params=params, headers=headers)
            print(f"HTTP Status Code: {base_response.status_code}")

            if base_response.status_code == 200:
                res = base_response.json()
                parent_files = res['data']['records']
                # print(json.dumps(res['data']['records'], indent=4, ensure_ascii=False))
                for parent_file in parent_files:
                    if 'kbFiles' in parent_file:
                        for son_file in parent_file['kbFiles']:
                            multi_version_dict[son_file['id']] = parent_file['id']
                return multi_version_dict
            elif base_response.status_code == 500:
                logger.error(f"服务器内部错误 (500): {base_response.text}")
                print(f"服务器内部错误，请检查请求参数或联系API提供方")
            else:
                logger.error(f"API请求失败，状态码: {base_response.status_code}, 响应: {base_response.text}")
                print(f"API请求失败，状态码: {base_response.status_code}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP状态错误: {e.response.status_code}, 响应内容: {e.response.text}")
        print(f"HTTP状态错误: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"网络请求异常: {e}")
        print(f"网络请求异常: {e}")
    except Exception as e:
        logger.error(f"请求多版本参数报错: {e}")
        print(f"请求多版本参数报错: {e}")

    return None


async def query_es_file_index(file_name, index_names, chunk_index, server_config):
    data = {
        "query_body": {
            "query": {
                "bool": {
                    "must": [
                        # 精确匹配文件名（你也可以换成 file_id）
                        {"term": {"metadata.source.keyword": file_name}},
                        # 精确匹配 chunk_index
                        {"term": {"metadata.chunk_index": chunk_index}}
                    ]
                }
            },
            "size": 1
        },
        "index_name": index_names  # ES索引名
    }
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    es_documents = []
    es_response = None

    try:
        es_response = await ESClient.request(es_url=es_url + 'search_by_custom_param', data=data)
        results = es_response["data"]["result_data"]
        for x in results:
            es_documents.append(Document(page_content=x['_source']['page_content'], metadata=x['_source']['metadata']))
        return es_documents
    except Exception as e:
        logger.exception(f"index ES服务 查询异常, 错误详情: {e}。 请求URL: {es_url}, 请求参数data: {data}, 返回结果: {es_response}")
        return ""


async def query_max_index(file_name, index_names, server_config):
    data = {
        "query_body": {
            "size": 1,
            "_source": ["metadata.chunk_index"],
            "query": {
                "term": {
                    "metadata.source.keyword": file_name
                }
            },
            "sort": [
                {
                    "metadata.chunk_index": {
                        "order": "desc"
                    }
                }
            ]
        },
        "index_name": index_names
    }
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    es_response = None

    try:
        es_response = await ESClient.request(es_url=es_url + 'search_by_custom_param', data=data)
        results = es_response["data"]["result_data"]
        return results[0]['_source']['metadata']['chunk_index']
    except Exception as e:
        logger.exception(f"index ES服务 查询异常, 错误详情: {e}。 请求URL: {es_url}, 请求参数data: {data}, 返回结果: {es_response}")
        return 0
