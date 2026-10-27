#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/1/23 15:39
# @Author  : yuxj
# @File    : graph_fun_tool.py
import json
import re
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

import numpy as np
import time
import requests

from base import BaseResponse, QueryDocChunk
from config.conf import DEFAULT_EMBEDDING_MAX_TOKENS, EMBED_MAX_TOKEN_DELTA_DEFAULT
from utils import return_nacos_model
from operators.utils.token_utils import truncate_text_by_tokens
from operators.common.log import logger


def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]


def split_embedding_data(data_list, model_name, server_config):
    """
    分批embed
    Args:
        data_list:
        model_name:
        server_config:

    Returns:

    """
    full_entity_list = []
    logger.info(f"待向量化的数据集为{len(data_list)}")
    if len(data_list) > 100:
        chunk_entity_list = split_array(data_list, 100)
        for cel in chunk_entity_list:
            chunk_embed_data = xinference_embedding_request(model_name, cel, server_config)
            for ced in chunk_embed_data:
                ced["entity_name"] = cel[ced["index"]]
                full_entity_list.append(ced)
            # logger.info("已经完成100条数据的向量化")
    else:
        embed_data = xinference_embedding_request(model_name, data_list, server_config)
        for ced in embed_data:
            ced["entity_name"] = data_list[ced["index"]]
            full_entity_list.append(ced)
    # logger.info(f"已经完成数据的向量化,{len(data_list)}")
    return full_entity_list


def requests_llm(mes, model_info, server_config, prompt_flag=True, max_tokens=None,
                 temperature=None, seed=None):
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

    # if max_tokens:
    #     payload["max_tokens"] = max_tokens

    headers = {'Content-Type': 'application/json'}
    llm_url = 'http://' + server_config["llm_server"]["host"] + ':' + str(server_config["llm_server"]["port"]) + '/' + server_config["llm_server"]["api_name"]

    # R13-FIX-GRAPH-01：本文件原实现是"自研 LLM 编排协议"（prompt_msg/query + answer），
    # 与当前部署的 OpenAI 兼容服务（18092 /v1/chat/completions）不兼容，会永远拿到空串。
    # 当 api_name 指向 chat/completions 时改走 OpenAI 协议；否则保持原协议，兼容旧环境。
    if "chat/completions" in server_config["llm_server"].get("api_name", ""):
        if isinstance(mes, list):
            messages = mes
        else:
            messages = [{"role": "user", "content": str(mes)}]
        model_name = (model_info or {}).get("model_id") or (model_info or {}).get("model_name") \
            or server_config["llm_server"].get("model") or "qwen2.5-7b-instruct"
        # R14-B2：图谱侧允许显式指定 temperature/seed，让"同一问题同一事实"可复现，
        # 不必再用随机采样去掩盖稳定性问题（默认值保持 0.1，不改变既有调用方行为）。
        oa_payload = {"model": model_name, "messages": messages, "stream": False,
                      "temperature": 0.1 if temperature is None else float(temperature)}
        if seed is not None:
            oa_payload["seed"] = int(seed)
        if max_tokens:
            oa_payload["max_tokens"] = int(max_tokens)
        try:
            resp = requests.post(llm_url, json=oa_payload, headers=headers, timeout=600)
            if resp.status_code != 200:
                logger.error(f"OpenAI 协议模型请求失败:{resp.status_code} {resp.text[:300]}")
                return ""
            content = resp.json()["choices"][0]["message"]["content"] or ""
            if "</think>" in content:
                content = content.split("</think>")[-1]
            return content
        except Exception as e:
            logger.error(f"OpenAI 协议模型请求报错:{e}")
            return ""

    try:
        base_response = requests.post(llm_url, json=payload, headers=headers)
    except Exception as e:
        logger.error(f"大模型请求报错，请检查模型检查是否可用，或检查网络，模型参数:{model_info},错误:{e}")
        return res_data
    if not base_response or base_response.status_code != 200:
        logger.error(f"大模型请求失败:{base_response.text}")
        return res_data
    result_data = re.sub(r'\{\s*"end"\s*:\s*""\s*\}', '', base_response.text)
    res_json = json.loads(result_data)
    if "answer" not in res_json.keys():
        logger.error(f"大模型请求成功，但是格式不符合要求，请重新请求:{base_response.text}")
        return res_data
    else:
        res_data = res_json["answer"]
        if "</think>" in res_data:
            res_data = res_data.split('</think>')[-1]
    return res_data


def xinference_embedding_request(model_name, page_content_list, server_config):
    """
    请求api embed
    Args:
        model_name:
        page_content_list:
        server_config:

    Returns:

    """
    # 获取模型的最大token限制，从配置映射表读取
    max_tokens = server_config["online_embedding_model"].get(model_name, {}).get("max_tokens", DEFAULT_EMBEDDING_MAX_TOKENS)
    max_token_delta = server_config.get("embed_max_token_delta", EMBED_MAX_TOKEN_DELTA_DEFAULT)

    # 处理文本长度，确保不超过模型的最大token限制
    processed_content_list = []
    for content in page_content_list:
        truncated_content = truncate_text_by_tokens(content, max_tokens, max_token_delta)
        processed_content_list.append(truncated_content)

    embed_request = {
        "model": model_name,
        "input": processed_content_list,
    }
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    # todo nacos配置需要修改
    embed_url = server_config["online_embedding_model"][model_name]["server_url"]
    embed_result = requests.post(embed_url, json=embed_request, headers=headers)
    if embed_result.status_code == 200:
        return embed_result.json()["data"]
    else:
        logger.info(f'embed参数{embed_request}')
        logger.error(embed_result.text)
        return []


def validation_entity(s):
    """
    判断字符串是否符合规则
    Args:
        s:

    Returns:

    """
    flag = True
    s = str(s)
    # 正则表达式：仅含数字和非数字（符号）字符
    patterns = [
        r'^[\d\W]+$',  # 5%
        r'^-?\d*\.?\d+$',  # 1.1
        r'^\d+\([a-zA-Z]\)$',  # 5(a)
        r"\b\d+(?:[年级岁家人户天]|[块千百亿万]?元)\b"
    ]
    for pattern in patterns:
        matches = re.findall(pattern, s)
        if matches:
            flag = False
    if len(s) < 3 and s.isalpha():  # 避免小于2个字母相似
        flag = False
    if len(s) < 2:  # 避免小于2个字符
        flag = False
    # elif len(s) > 0 and not s.isalnum():  # 避免全是符号相似
    #     flag = False
    return flag


def process_entity_file_id(entity_list):
    """
    处理entity格式
    Args:
        entity_list:

    Returns:

    """
    entity_file_id = {}
    for el in entity_list:
        name = el.split('_')[1]
        fileid = el.split('_')[0]
        if name in entity_file_id:
            if fileid not in entity_file_id[name]:
                entity_file_id[name].append(fileid)
        else:
            entity_file_id[name] = [fileid]
    query_entity_list = list(entity_file_id)
    return entity_file_id, query_entity_list


def vectorization_data_similarity(entity_list, model_name, server_config):
    """
    内部向量化比较
    Args:
        entity_list:
        model_name:
        server_config:

    Returns:

    """
    # 批量向量化
    full_entity_list = split_embedding_data(entity_list, model_name, server_config)
    if not full_entity_list:
        logger.error(f'保存数据失败，embed请求失败，请检查配置后重试')
        return BaseResponse(code=500, msg=f'保存数据失败，embed请求失败，请检查配置后重试')
    logger.info("开始向量相似度比对")
    similarity_set = set()
    entity_name_list = [fn["entity_name"] for fn in full_entity_list]
    embed_vector_list = np.array([fn["embedding"] for fn in full_entity_list])
    normalized_embeddings = embed_vector_list / np.linalg.norm(embed_vector_list, axis=1, keepdims=True)
    cos_sim_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
    # cos_sim_matrix = cosine_similarity(embed_vector_list)
    threshold = 0.8
    similar_pairs = np.argwhere(cos_sim_matrix > threshold)
    for i, j in similar_pairs:
        if i < j:  # 只取上三角部分
            if validation_entity(entity_name_list[i]) and validation_entity(entity_name_list[j]):
                logger.info(f"符合:{entity_name_list[i], '|', entity_name_list[j]}", )
                similarity_set.add((entity_name_list[i], "相似", entity_name_list[j]))
    return similarity_set


def llm_format_data(prompt_dict_list):
    """
    推理 格式 处理
    Args:
        prompt_dict_list:

    Returns:

    """
    mes_list = []
    for pdl in prompt_dict_list:
        mag_dict = {}
        type = pdl["type"]
        if type != "system":
            type = "user"
        mag_dict["role"] = type
        mag_dict["content"] = pdl["content"]
        mes_list.append(mag_dict)
    return mes_list


def clean_string(s):
    """
    格式化字符串
    Args:
        s:

    Returns:

    """
    for ch in ['【', '】']:
        s = s.replace(ch, '')
    return s


def clean_entity(entity: str):
    """
    格式化字符串
    Args:
        entity:

    Returns:

    """
    chinese_regex = re.compile(r'[\u4e00-\u9fff]+')
    # 搜索字符串中是否包含汉字
    match = chinese_regex.search(entity)
    if match:
        return entity.strip().replace(' ', '').replace('"', '\'').replace('‘', '').replace('“', '').replace('\\', '').replace('\'', '')
    return entity.strip().replace('\'', '').replace('"', '').replace('‘', '').replace('“', '').replace('\\', '')


def extract_json_dict(text):
    """
    格式化json
    Args:
        text:

    Returns:

    """
    pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\})*)*\}'
    match = re.search(pattern, text)

    if match:
        json_string = match.group()
        try:
            json_dict = json.loads(json_string)
            # for key, value in json_dict.items():
            #     json_dict[key] = [item for item in value if len(item) > 1 and item.isalpha()]
            return json_dict
        except json.JSONDecodeError:
            return ''
    else:
        return ''


def entity_process_dict(entity_pk_dict, entity_list):
    """
    实体处理格式
    Args:
        entity_list:
        entity_pk_dict:

    Returns:

    """
    entity_dict = {}

    def _add_to_list_if_not_exists(target_dict, key, value):
        if key not in target_dict:
            target_dict[key] = []
        if value not in target_dict[key]:
            if isinstance(value, list):
                target_dict[key].extend(value)
            else:
                target_dict[key].append(value)

    for vid_entity, value in entity_pk_dict.items():
        if vid_entity not in entity_list:
            continue
        name = value["entity_name"]
        if name not in entity_dict:
            entity_dict[name] = {}

        _add_to_list_if_not_exists(entity_dict[name], "chunk_pk_list", value["chunk_pk_list"])
        _add_to_list_if_not_exists(entity_dict[name], "title", value["title"])
        _add_to_list_if_not_exists(entity_dict[name], "file_id", value["file_id"])
        _add_to_list_if_not_exists(entity_dict[name], "type", value["e_type"])

    return entity_dict


def attribute_assignment(entity_source_dict, entity_name, pk, source_value, e_type, description, entity_type="1"):
    """
    属性分配
    Args:
        entity_type:
        description:
        e_type:
        entity_source_dict:
        entity_name:
        pk:
        source_value:

    Returns:

    """

    def _add_to_list_if_not_exists(target_dict, key, value):
        if key not in target_dict:
            target_dict[key] = []
        if value not in target_dict[key]:
            target_dict[key].append(value)

    if entity_name not in entity_source_dict:
        entity_source_dict[entity_name] = {"entity_name": entity_name, "entity_type": entity_type}

    _add_to_list_if_not_exists(entity_source_dict[entity_name], "chunk_pk_list", str(pk))
    _add_to_list_if_not_exists(entity_source_dict[entity_name], "title", str(source_value["title"]))
    _add_to_list_if_not_exists(entity_source_dict[entity_name], "file_id", str(source_value["file_id"]))
    _add_to_list_if_not_exists(entity_source_dict[entity_name], "e_type", str(e_type))
    if source_value["page_number"]:
        for pn in source_value["page_number"]:
            _add_to_list_if_not_exists(entity_source_dict[entity_name], "page_num", str(source_value["file_id"]) + "_" + str(pn))
    else:
        entity_source_dict[entity_name]["page_num"] = []
    _add_to_list_if_not_exists(entity_source_dict[entity_name], "description", str(description))
    return entity_source_dict


def generate_entity_data(relation, pk, entity_pk_dict, source):
    src_info = relation["src_entity"]
    src_entity = src_info["name"]
    src_type = src_info["type"]

    dest_info = relation["dest_entity"]
    dest_entity = dest_info["name"]
    dest_type = dest_info["type"]
    description = relation["description"]
    entity_pk_dict = attribute_assignment(entity_pk_dict, src_entity, pk, source, src_type, description)  # 给抽取出来的实体加上节点属性
    entity_pk_dict = attribute_assignment(entity_pk_dict, dest_entity, pk, source, dest_type, description)
    entity_pk_dict = attribute_assignment(entity_pk_dict, relation["name"], pk, source, "", description, entity_type="2")
    return entity_pk_dict


def generate_triples_data(td_s, pk, triples_pk_dict):
    if td_s in triples_pk_dict:
        if int(pk) not in triples_pk_dict[td_s]:
            triples_pk_dict[td_s].append(int(pk))
    else:
        triples_pk_dict[td_s] = [int(pk)]
    return triples_pk_dict


def pool_query_milvus(space_name, server_config, entity_list, top_k, expr=""):
    """
    多线程请求实体
    Args:
        expr:
        space_name:
        server_config:
        entity_list:
        top_k:

    Returns:

    """
    threads_num = min(len(entity_list), 5)
    partial_func = partial(retrieval_milvus, knowledge_base_name=space_name, server_config=server_config, top_k=top_k, expr=expr)  #
    try:
        with ThreadPoolExecutor(max_workers=threads_num) as executor:
            futures = [executor.submit(partial_func, entity) for entity in entity_list]
            outputs = [future.result() for future in as_completed(futures)]
        return outputs
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return []


def query_milvus_api(server_config, fun_name, milvus_data):
    """
    查询
    Args:
        server_config:
        fun_name:
        milvus_data:

    Returns:

    """
    milvus_url = 'http://' + server_config["milvus_config"]["host"] + ':' + str(server_config["milvus_config"]["port"]) + '/'
    res_m = requests.post(milvus_url + fun_name, json=milvus_data)
    return res_m


def update_milvus_api(server_config, collection_name, update_data):
    """
    修改
    Args:
        server_config:
        collection_name:
        update_data:

    Returns:

    """
    milvus_data = {
        "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
        "index_name": collection_name,
        "update_condition_json": update_data
    }
    milvus_url = 'http://' + server_config["milvus_config"]["host"] + ':' + str(server_config["milvus_config"]["port"]) + '/'
    res_m = requests.post(milvus_url + "update_by_id_batch", json=milvus_data)
    return res_m


def update_data_fun(source_data_list, target_data_list, key_name, pk, update_data_dict):
    u_flag = False
    for dl in target_data_list:
        if dl not in source_data_list:
            source_data_list.append(dl)
            u_flag = True
    if u_flag:
        if pk not in update_data_dict:
            update_data_dict[pk] = {}
        update_data_dict[pk][key_name] = source_data_list.copy()
    return update_data_dict


def update_triples_data(server_config, collection_name_triples, triples_source_dict, triples_data_list):
    """

    Args:
        triples_data_list:
        server_config:  配置
        collection_name_triples: 集合名称
        triples_source_dict:  全部数据

    Returns:

    """
    triples_list = [",".join(tl) for tl in triples_data_list]
    milvus_payload = {
        "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
        "collection_name": collection_name_triples,
    }
    # 判断集合是否存在
    response_m = query_milvus_api(server_config, 'static_count', milvus_payload)
    if response_m.json()["code"] == 200:
        triples_chunk_list = split_array(triples_list, 50)
        update_data = {}
        for tcl in triples_chunk_list:
            res_m = query_col_values(server_config, collection_name_triples, tcl)
            if res_m.json()["code"] == 200:
                milvus_data_list = res_m.json()['data']['result_data']
                for mdl in milvus_data_list:
                    milvus_text = mdl["page_content"]
                    milvus_chunk_pk_list = mdl["metadata"]["chunk_pk_list"]
                    milvus_pk = mdl["metadata"]["pk"]
                    milvus_file_id = mdl["metadata"]["file_id"]
                    milvus_page_num = mdl["metadata"]["page_num"]
                    update_data = update_data_fun(milvus_chunk_pk_list, triples_source_dict[milvus_text]["chunk_pk_list"], "chunk_pk_list", milvus_pk,
                                                  update_data)
                    update_data = update_data_fun(milvus_file_id, triples_source_dict[milvus_text]["file_id"], "file_id", milvus_pk, update_data)
                    update_data = update_data_fun(milvus_file_id, triples_source_dict[milvus_text]["title"], "title", milvus_pk, update_data)
                    update_data = update_data_fun(milvus_page_num, triples_source_dict[milvus_text]["page_num"], "page_num", milvus_pk, update_data)
                    if update_data and milvus_pk in update_data:
                        if "chunk_pk_list" in update_data[milvus_pk]:
                            triples_source_dict[milvus_text]["chunk_pk_list"] = update_data[milvus_pk]["chunk_pk_list"]
                        if "file_id" in update_data[milvus_pk]:
                            triples_source_dict[milvus_text]["file_id"] = update_data[milvus_pk]["file_id"]
                        if "title" in update_data[milvus_pk]:
                            triples_source_dict[milvus_text]["title"] = update_data[milvus_pk]["title"]
                        if "page_num" in update_data[milvus_pk]:
                            triples_source_dict[milvus_text]["page_num"] = update_data[milvus_pk]["page_num"]
                    if milvus_text in triples_list:
                        triples_list.remove(milvus_text)
        if update_data:
            # milvus 修改接口
            res_u = update_milvus_api(server_config, collection_name_triples, update_data)
            if res_u.json()["code"] != 200:
                logger.error(f'修改向量三元组表失败，修改向量数据库字段出错.{res_u.json()["msg"]}')
                return BaseResponse(code=500, msg=f'修改向量三元组表失败，修改向量数据库字段出错.{res_u.json()["msg"]}')
    return triples_list, triples_source_dict


def query_like_entity(server_config, collection_name_entity, entity_list, entity_pk_dict, synonymous_set):
    milvus_payload = {
        "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
        "collection_name": collection_name_entity,
    }
    # 判断集合是否存在
    response_m = query_milvus_api(server_config, 'static_count', milvus_payload)
    if response_m.json()["code"] == 200:
        # 实体点查询相似和去重
        entity_chunk_list = split_array(entity_list, 50)  # 设置batch
        update_data = {}
        for ecl in entity_chunk_list:
            milvus_outputs = pool_query_milvus(collection_name_entity, server_config, ecl, top_k=5, expr='entity_type == "1"')  # 添加相似边
            milvus_outputs_dict = {k: v for d in milvus_outputs if d for k, v in d.items()}
            if not milvus_outputs_dict:
                continue
            if milvus_outputs:
                for source_entity in ecl:
                    if source_entity in milvus_outputs_dict:
                        milvus_outputs_list = milvus_outputs_dict[source_entity]
                        for md in milvus_outputs_list:
                            metadata = md["metadata"]
                            pk = metadata["pk"]
                            if source_entity == md["page_content"]:  # mivlus 中存在的实体名称
                                update_data = update_data_fun(metadata["chunk_pk_list"], entity_pk_dict[source_entity]["chunk_pk_list"], "chunk_pk_list", pk,
                                                              update_data)
                                update_data = update_data_fun(metadata["file_id"], entity_pk_dict[source_entity]["file_id"], "file_id", pk, update_data)
                                update_data = update_data_fun(metadata["title"], entity_pk_dict[source_entity]["title"], "title", pk, update_data)
                                update_data = update_data_fun(md["metadata"]["type"], entity_pk_dict[source_entity]["e_type"], "type", pk, update_data)
                                # 更新图属性
                                if update_data and pk in update_data:
                                    if "file_id" in update_data[pk]:
                                        entity_pk_dict[source_entity]["file_id"] = update_data[pk]["file_id"]
                                    if "title" in update_data[pk]:
                                        entity_pk_dict[source_entity]["title"] = update_data[pk]["title"]
                                    if "type" in update_data[pk]:
                                        entity_pk_dict[source_entity]["type"] = update_data[pk]["type"]
                                if source_entity in entity_list:
                                    entity_list.remove(source_entity)
                            else:
                                if validation_entity(source_entity) and validation_entity(md["page_content"]):
                                    # 确保synonymous_set是一个set对象
                                    if isinstance(synonymous_set, set):
                                        synonymous_set.add((source_entity, "相似", md["page_content"]))
                                    else:
                                        logger.warning(f"synonymous_set不是set类型，跳过添加相似实体: {source_entity} -> {md['page_content']}")
        if update_data:
            # milvus 修改接口
            res_u = update_milvus_api(server_config, collection_name_entity, update_data)
            if res_u.json()["code"] != 200:
                logger.error(f'修改向量实体表失败，修改向量数据库字段出错.{res_u.json()["msg"]}')
                return BaseResponse(code=500, msg=f'修改向量实体表失败，修改向量数据库字段出错.{res_u.json()["msg"]}')
    return entity_list, synonymous_set, entity_pk_dict


def calculate_entity_weights(entity_list, score_dict):
    """
    计算权重
    Args:
        entity_list:
        score_dict:

    Returns:

    """
    entity_dict_count = Counter(entity_list)
    weights = {}
    for element, count in entity_dict_count.items():
        score = score_dict.get(element, 0)  # 默认分数为 0
        weight = count * score
        weights[element] = weight
    sorted_elements = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:10]
    return sorted_elements


def query_light_fun(start_judge_list, relationship_set, server_config, collection_name_triples, entity_info_list):
    triples_pk_dict = {}
    triples_rep_info_list = query_milvus_by_condition(db_name="graph_base",
                                                      knowledge_base_name=collection_name_triples,
                                                      col_name="relationship",
                                                      col_values=list(relationship_set),
                                                      server_config=server_config)
    for tri_info in triples_rep_info_list:
        source_entity = tri_info["metadata"]["source_entity"]
        target_entity = tri_info["metadata"]["target_entity"]
        triples_data = tri_info["page_content"]
        chunk_pk_list = tri_info["metadata"]["chunk_pk_list"]
        if source_entity in start_judge_list or target_entity in start_judge_list:
            if triples_data in triples_pk_dict:
                save_chunk_pk_list = triples_pk_dict[triples_data]
                for ck in chunk_pk_list:
                    if ck in save_chunk_pk_list:
                        continue
                    else:
                        triples_pk_dict[triples_data].append(chunk_pk_list)
            else:
                triples_pk_dict[triples_data] = chunk_pk_list
    document_chunk_pk_list = get_chunk_by_light_score(triples_pk_dict, entity_info_list)  # [(chunk_pk, score)]
    return document_chunk_pk_list


def execute_query(session, entity_set, query_type):
    """
        图查询
        Args:
            entity_set:
            session:
            query_type:  查询类型
        Returns:

        """
    triples_set = set()
    relationship_set = set()
    triples_entity_dict = {}
    # R13-FIX-GRAPH-03：原实现用 result.dict_for_vis()["edges"]，nebula3 客户端在
    # "边属性存在但不整齐"时会抛 KeyError（add_to_nodes_or_edges），导致整个图检索 500。
    # 这里改为直接取 id + properties(e)，绕开该客户端缺陷，语义等价且更可控。
    if query_type == 'hippo':
        query = f'''
                    MATCH (v)-[e:relationship]-(v2)
                    RETURN id(v) AS src, properties(e) AS props, id(v2) AS dst;
            '''
    else:
        query = f'''
                    MATCH (v)-[e:relationship]-(v2)
                    WHERE v.entity.name IN {entity_set}
                    RETURN id(v) AS src, properties(e) AS props, id(v2) AS dst;
                '''
        logger.info(f"查询语句:{query}")
    result = session.execute(query)
    if not result.is_succeeded():
        logger.error(f"图查询失败:{result.error_msg()}")
        return triples_set, relationship_set, triples_entity_dict
    res_dict_list = []
    for i in range(result.row_size()):
        vals = result.row_values(i)
        src = vals[0].as_string() if vals[0].is_string() else str(vals[0])
        dst = vals[2].as_string() if vals[2].is_string() else str(vals[2])
        props = {}
        try:
            if vals[1].is_map():
                props = {k: (v.as_string() if v.is_string() else str(v)) for k, v in vals[1].as_map().items()}
        except Exception:
            props = {}
        res_dict_list.append({"src": src, "dst": dst, "props": props})
    if res_dict_list:
        for rd in res_dict_list:
            src = rd["src"].split("_")[-1]
            rep = rd["props"].get("name", "") if isinstance(rd.get("props"), dict) else ""
            dst = rd["dst"].split("_")[-1]
            triples_set.add((src, rep, dst))
            if src not in triples_entity_dict:
                triples_entity_dict[src] = []
                triples_entity_dict[src].append((src, rep, dst))
            else:
                triples_entity_dict[src].append((src, rep, dst))
            if dst not in triples_entity_dict:
                triples_entity_dict[dst] = []
                triples_entity_dict[dst].append((src, rep, dst))
            else:
                triples_entity_dict[dst].append((src, rep, dst))
            relationship_set.add(rep)
    return triples_set, triples_entity_dict, relationship_set


def execute_query_old(session, entity_set, depth=3):
    """
    图查询
    Args:
        entity_set:
        session:
        depth:
    Returns:

    """
    triples_set = set()
    triples_entity_set = set()
    for start_vertex in entity_set:
        for d_n in range(1, depth + 1):
            flag = False
            query = f"GO {d_n} STEPS FROM '{start_vertex}' OVER * YIELD src(edge) AS source_node, relationship.name AS relationship_text,dst(edge) AS target_node"  # relationship_similar.text AS similar_text ,
            print(query)
            result = session.execute(query)
            if not result.is_succeeded():
                print(result.error_msg())
                return [], ()
            for row in result.rows():
                triples_set.add((row.values[0].get_sVal().decode(), row.values[1].get_sVal().decode(),
                                 row.values[2].get_sVal().decode()))
                triples_entity_set.add(row.values[0].get_sVal().decode())
                triples_entity_set.add(row.values[2].get_sVal().decode())
                flag = True
            if flag is False:
                break
    return list(triples_set), list(triples_entity_set)


def query_col_values(server_config, collection_name, value_list):
    """
    查询服务
    Args:
        server_config:
        collection_name:
        value_list:

    Returns:

    """
    milvus_data = {
        "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
        "collection_name": collection_name,
        "col_name": "text",
        "col_values": value_list
    }
    res_m = query_milvus_api(server_config, 'get_doc_by_col', milvus_data)
    return res_m


def retrieval_milvus(question, knowledge_base_name, server_config, top_k, expr=""):
    """
    实体查询
    Args:
        expr:
        question:
        knowledge_base_name:
        server_config:
        top_k:

    Returns:

    """
    data = {
        "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
        "query": question,
        "top_k": top_k,
        "collection_name": [knowledge_base_name],
        "search_param": expr
    }

    milvus_url = 'http://' + server_config["milvus_config"]["host"] + ':' + str(server_config["milvus_config"]["port"]) + '/'
    response = requests.post(milvus_url + 'milvus_vector_search', json=data)
    try:
        if response.status_code == 200:
            try:
                milvus_data = response.json()['data']['result_data']
            except Exception as e:
                logger.error(f"milvus查询报错{e},{response.text}")
                return []
        else:
            logger.error(f"milvus查询报错,{response.text}")
            return []
    except Exception as e:
        logger.error(f"milvus查询报错{e},{response.text}")
        return []
    milvus_data = [md for md in milvus_data if md["metadata"]["score"] > 0.6]
    result_milvus_data_dict = {question: milvus_data}
    return result_milvus_data_dict


def query_milvus_by_condition(knowledge_base_name, col_name, col_values, server_config, db_name="rag_knowledge_base"):
    """
    条件查询
    Args:
        knowledge_base_name:
        col_name:
        col_values:
        server_config:
        db_name:

    Returns:

    """
    data = {
        "db_name": db_name,
        "collection_name": knowledge_base_name,
        "col_name": col_name,
        "col_values": col_values
    }
    milvus_url = 'http://' + server_config["milvus_config"]["host"] + ':' + str(server_config["milvus_config"]["port"]) + '/'
    response = requests.post(milvus_url + 'get_doc_by_col', json=data)
    try:
        if response.status_code == 200:
            try:
                milvus_data = response.json()['data']['result_data']
            except Exception as e:
                logger.error(f"Milvus Error! Message:{e},{response.text}")
                return []
        else:
            logger.error(f"Milvus Error! Message:,{response.text}")
            return []
    except Exception as e:
        logger.error(f"Milvus Error! Message:{e},{response.text}")
        return []
    return milvus_data


def get_document_chunk(query_docu: QueryDocChunk, server_config):
    """
    查询chunk数据
    Args:
        query_docu:
        server_config:

    Returns:

    """
    es_documents = []
    index_name = [query_docu.space_name, "table_chunks_" + query_docu.space_name]
    if query_docu.col_name:
        data = {
            "index_name": index_name,
            "col_name": query_docu.col_name,
            "col_values": query_docu.col_values
        }
    else:
        data = {
            "index_name": index_name
        }
    es_url = 'http://' + server_config["es_config"]["host"] + ':' + str(server_config["es_config"]["port"]) + '/'
    # R13-FIX-GRAPH-07：图抽取紧跟解析执行，ES 写入有 refresh 延迟，
    # 首次查询常见"未查询到相关文本"（尤其 xlsx 表格块）。这里做有限重试，避免把时序问题判成抽取失败。
    response = None
    for attempt in range(4):
        response = requests.post(es_url + 'search_by_custom_param', json=data)
        try:
            if response.status_code == 200 and response.json().get('data', {}).get('total_count', 0) > 0:
                break
        except Exception:
            pass
        if attempt < 3:
            time.sleep(5)
    try:
        if response.status_code == 200:
            try:
                es_data = response.json()['data']['result_data']
            except Exception as e:
                logger.error(f"es查询失败:{e},{response.text}")
                return es_documents
        else:
            logger.error(f"es查询失败:{response.text}")
            return es_documents
    except Exception as e:
        logger.error(f"es查询失败:{e},{response.text}")
        return es_documents
    data_dict_list = [{ed["_id"]: ed["_source"]} for ed in es_data]
    return data_dict_list


def process_milvus_to_dict(milvus_outputs, entity_list):
    milvus_dict = {}
    merged_dict = {k: v for d in milvus_outputs for k, v in d.items()}
    for el in entity_list:
        if el in merged_dict:
            data_list = merged_dict[el]
            for dl in data_list:
                if dl["page_content"] == el:
                    milvus_dict[el] = dl
    return milvus_dict


def remove_duplicates_relation_name(entity_source_dict, collection_name_entity, server_config, entity_list):
    relation_entity_list = [en for en, va in entity_source_dict.items() if va["entity_type"] == "2"]
    relation_entity_info_list = query_milvus_by_condition(db_name="graph_base",
                                                          knowledge_base_name=collection_name_entity,
                                                          col_name="text",
                                                          col_values=relation_entity_list,
                                                          server_config=server_config)
    for relation_entity in relation_entity_info_list:
        relation_entity_name = relation_entity["page_content"]
        if relation_entity_name not in relation_entity_list:
            entity_list.append(relation_entity_name)
    return entity_list


def remove_duplicates_by_pk(data_list, query_ner_set):
    """
    根据page_content去重
    Args:
        query_ner_set:
        data_list:

    Returns:

    """
    for data in data_list:
        for key, item_list in data.items():
            for item in item_list:
                text = item['page_content']
                if text not in query_ner_set:
                    query_ner_set.add(text)
    return list(query_ner_set)


def high_entity_triples(high_entity_list, entity_triples_dict, collection_name_entity, server_config, entity_info_list):
    """
    整理高分实体对应的三元组中的实体信息
    Args:
        high_entity_list:
        entity_triples_dict:
        collection_name_entity:
        server_config:

    Returns:

    """
    entity_type_dict = {}
    for en in high_entity_list:
        full_high_entity_set = set()
        for tt in entity_triples_dict[en]:
            full_high_entity_set.add(tt[0])
            full_high_entity_set.add(tt[2])
        high_entity_info_list = query_milvus_by_condition(db_name="graph_base",
                                                          knowledge_base_name=collection_name_entity,
                                                          col_name="text",
                                                          col_values=list(full_high_entity_set),
                                                          server_config=server_config)
        entity_type_dict[en] = high_entity_info_list
    return entity_type_dict


def get_chunk_by_light_score(triples_pk_dict, entity_info_list):
    count_pk_dict = {}
    for tp, pk_list in triples_pk_dict.items():
        for pl in pk_list:
            if pl not in count_pk_dict:
                count_pk_dict[pl] = 1
            else:
                count_pk_dict[pl] = count_pk_dict[pl] + 1
    for el in entity_info_list:
        for pk in el["metadata"]["chunk_pk_list"]:
            if pk not in count_pk_dict:
                count_pk_dict[pk] = 1
            else:
                count_pk_dict[pk] = count_pk_dict[pk] + 1
    sorted_elements = sorted(count_pk_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    pk_list = [int(datap[0]) for datap in sorted_elements]
    return pk_list


def get_chunk_by_ppr_score(entity_type_dict, entity_list, ppr_phrase_prob):
    """
    根据高分实体获取对应的chunk
    Args:
        entity_type_dict:
        entity_list:
        ppr_phrase_prob:

    Returns:

    """
    entity_to_score = {}
    for he, entity_info in entity_type_dict.items():
        hi = {}
        for ei in entity_info:
            if he == ei.get("page_content"):
                hi = ei
                entity_info.remove(ei)
                break
        # R13-FIX-GRAPH-16：高分红实体在实体向量表里查不到自身行时（悬空实体/实体被类型过滤、
        # 或刚写入尚未可见），原实现会在 hi["metadata"] 抛 KeyError，把整个图检索打成 500。
        # 这里跳过该实体并告警，不影响其它高分实体的召回。
        if not hi or "metadata" not in hi:
            logger.warning(f"高分实体{he}在实体向量表中无对应行，跳过其chunk聚合")
            continue
        for ei in entity_info:
            index_src = np.where(np.array(entity_list) == he)[0]
            index_dest = np.where(np.array(entity_list) == ei.get("page_content"))[0]
            if index_src.size == 0 or index_dest.size == 0 or "metadata" not in ei:
                continue
            ppr_score = float((ppr_phrase_prob[0, index_src] + ppr_phrase_prob[0, index_dest])[0])
            if ppr_score > 0.1:
                for eck in ei["metadata"].get("chunk_pk_list") or []:
                    if eck not in entity_to_score:
                        entity_to_score[eck] = ppr_score
                    else:
                        entity_to_score[eck] = entity_to_score[eck] + ppr_score
                for hck in hi["metadata"].get("chunk_pk_list") or []:
                    if hck not in entity_to_score:
                        entity_to_score[hck] = ppr_score
                    else:
                        entity_to_score[hck] = entity_to_score[hck] + ppr_score
    sorted_elements = sorted(entity_to_score.items(), key=lambda x: x[1], reverse=True)[:10]
    return sorted_elements


def user_connect_space(space_name, release_flag=False):
    session = return_nacos_model().session_client(release_flag=release_flag)
    try:
        result = session.execute(f'USE `{space_name}`;')
        if not result.is_succeeded():
            logger.error(f"USE space失败: {result.error_msg()}")
            raise RuntimeError(result.error_msg())
    except Exception as e:
        logger.error(f"链接失效，{e}")
        session = return_nacos_model().session_client()
        session.execute(f'USE `{space_name}`;')
    return session


def generate_collection_name_uuid(collection_name: str) -> str:
    """
    如果collection_name为带有汉字字符，需将汉字转成非汉字字符

    Args:
        collection_name (str): 集合名称。
    Returns:
        转换后的collection_name。
    """
    chinese_regex = re.compile(r'[\u4e00-\u9fff]+')

    # 搜索字符串中是否包含汉字
    match = chinese_regex.search(collection_name)
    if match:
        collection_name = str(uuid.uuid5(uuid.NAMESPACE_DNS, collection_name))
    elif re.search(r'[^a-zA-Z0-9_]', collection_name):
        collection_name = str(uuid.uuid5(uuid.NAMESPACE_DNS, collection_name))
    collection_name = "_" + collection_name.replace("-", "")
    return collection_name
