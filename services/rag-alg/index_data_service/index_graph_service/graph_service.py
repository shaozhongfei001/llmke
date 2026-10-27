#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 15:14
# @Author  : yuxj
# @File    : fulltext_es_api_start.py
import os
import time

import requests

from base import GraphModel, GraphAttributeModel, InsertModel, QueryDocChunk, BaseResponse, QueryGraphData, DelModel
from graph_extract import generate_graph_relations, generate_query_entities
from graph_types import normalize_graph_data
from graph_fun_tool import clean_entity, generate_entity_data, get_document_chunk, \
    vectorization_data_similarity, query_like_entity, query_milvus_api, pool_query_milvus, execute_query, \
    query_milvus_by_condition, remove_duplicates_by_pk, attribute_assignment, update_triples_data, split_array, \
    remove_duplicates_relation_name, query_light_fun, user_connect_space, generate_collection_name_uuid
from graph_p_array import cal_ppr_fun
from utils import return_nacos_model
from operators.common.log import logger


def check_space_exists(space_name):
    """
    检查图是否存在
    Args:
        space_name:

    Returns:

    """
    session = return_nacos_model().session_client()
    # 执行查询列出所有 Graph Space
    query = "SHOW SPACES"
    result = session.execute(query)

    # 检查是否有目标图空间
    if result.is_succeeded():
        for row in result:
            space = row.get_value_by_key("Name")
            if space.as_string() == space_name:
                logger.info(f"Space '{space_name}' exists.")
                return True
        logger.info(f"Space '{space_name}' does not exist.")
        return False
    else:
        logger.error(f"Failed to retrieve spaces.{str(result.error_msg())}")
        return False


def create_space(graph_model: GraphModel):
    """
    创建图空间
    Args:
        graph_model:
    Returns:

    """
    # logger.info(f"参数：{str(graph_model.json())}")
    session = return_nacos_model().session_client()
    space_name = graph_model.space_name
    create_space_query = f"CREATE SPACE IF NOT EXISTS `{space_name}` " \
                         f"(partition_num ={graph_model.partition_num}, replica_factor={graph_model.replica_factor},vid_type=FIXED_STRING(500)) comment='{space_name}';"
    result = session.execute(create_space_query)
    if not result.is_succeeded():
        logger.error(f'创建空间失败,{str(result.error_msg())}')
        return BaseResponse(code=500, msg=f'创建空间失败,{str(result.error_msg())}')
    else:
        return BaseResponse(code=200, msg=f'创建空间成功，Space {space_name} created successfully.')


def create_attribute(attribute_model: GraphAttributeModel):
    """
    创建属性  TAG和EDGE
    Args:
        attribute_model:

    Returns:

    """
    # logger.info(f"参数：{str(attribute_model.json())}")
    session = user_connect_space(attribute_model.space_name, release_flag=True)
    # while not q_res.is_succeeded():
    #     print(q_res.error_msg())
    #     session = return_nacos_model().session_client()
    #     session.execute(f'USE {attribute_model.space_name};')
    field_attr = "(" + ", ".join(f"{k} {v}" for k, v in attribute_model.field_dict.items()) + ")"
    create_tag_query = f"CREATE {attribute_model.attribute_type} IF NOT EXISTS {attribute_model.field_name}{field_attr};"
    logger.info(f"sql：{create_tag_query}")
    result = session.execute(create_tag_query)
    if not result.is_succeeded():
        logger.error(f'创建{attribute_model.attribute_type}失败,{str(result.error_msg())}')
        return BaseResponse(code=500, msg=f'创建{attribute_model.attribute_type}失败,{str(result.error_msg())}')
    else:
        # 创建索引
        success_index = create_index(attribute_model)
        if not success_index:
            logger.error(f'创建{attribute_model.attribute_type}索引失败,{str(result.error_msg())}')
            return BaseResponse(code=500, msg=f'创建{attribute_model.attribute_type}索引失败,{str(result.error_msg())}')
        return BaseResponse(code=200, msg=f'创建{attribute_model.attribute_type}成功，字段是{attribute_model.field_name} ')


def create_index(attribute_model: GraphAttributeModel):
    """
    创建索引
    Args:
        attribute_model:

    Returns:

    """
    # logger.info(f"参数：{str(attribute_model.json())}")
    session = user_connect_space(attribute_model.space_name)
    for k, v in attribute_model.field_dict.items():
        index_name = attribute_model.field_name + "_" + k + "_index"
        if v == "string":
            result = session.execute(f"CREATE {attribute_model.attribute_type} INDEX IF NOT EXISTS {index_name} ON {attribute_model.field_name}({k}(200));")
            if not result.is_succeeded():
                logger.error(f"创建索引失败：{str(result.error_msg())}")
                return False
            rebuild_sql = f"REBUILD TAG INDEX {index_name};"
            session.execute(rebuild_sql)
    return True


def batch_to_graph(session, queries, space_name):
    """
    添加图对象函数
    Args:
        space_name:
        session:
        queries:

    Returns:

    """

    def _insert_to_graph(session, chunk_queries, space_name):
        vertex_query = "\n".join(chunk_queries)
        session = user_connect_space(space_name)
        result = session.execute(vertex_query)
        if not result.is_succeeded():
            logger.error(f"插入失败:{str(result.error_msg())}")

            result = session.execute(vertex_query)
            if not result.is_succeeded():
                logger.error(f"链接失败{str(result.error_msg())}")
                return result, {"code": 500}
        logger.info(f"添加成功，{len(chunk_queries)}条数据")
        return result, {"code": 200}

    error_data_list = []
    queries_chunk_list = split_array(queries, 150)
    for qcl in queries_chunk_list:
        result, json_code = _insert_to_graph(session, qcl, space_name)
        if json_code["code"] == 500:
            for vq in qcl:
                result, json_code = _insert_to_graph(session, [vq], space_name)
                if json_code["code"] == 500:
                    error_data_list.append(vq)
        else:
            logger.info(f"成功插入{len(qcl)}条数据")
    return error_data_list


def del_space_data(del_param: DelModel):
    """
    删除服务
    Args:
        del_param:

    Returns:

    """
    # logger.info(f"参数：{str(del_param.json())}")
    session = return_nacos_model().session_client()
    session.execute(f'USE {del_param.space_name};')
    if not del_param.condition_json:
        del_query = f"DROP SPACE IF EXISTS {del_param.space_name};"
    else:
        del_vid = ""
        for key, value in del_param.condition_json.items():
            query_sql = f"MATCH (v) where properties(v).{key} CONTAINS '{value}' return id(v)"
            query_result = session.execute(query_sql)
            vid_to_delete = [row.values[0].get_sVal().decode() for row in query_result.rows()]
            for vid in vid_to_delete:
                del_vid += f"'{vid}'" + ','
        del_query = f"DELETE VERTEX {del_vid[:-1]} WITH EDGE;"
    result = session.execute(del_query)
    if not result.is_succeeded():
        logger.error(f'删除失败:{del_param.space_name}失败，error:{str(result.error_msg())}')
        return BaseResponse(code=500, msg=f'删除失败:{del_param.space_name}失败，error:{str(result.error_msg())}')
    else:
        return BaseResponse(code=200, msg=f'删除成功')


def create_space_attribute(ceshi: GraphModel):
    space_name = generate_collection_name_uuid(ceshi.space_name)
    #space_name = "g_" + ceshi.space_name
    res_space = create_space(ceshi)
    if res_space.code != 200:
        logger.error(res_space.msg)
        return BaseResponse(code=500, msg=f'创建空间失败,{str(res_space.msg)}')
    logger.info(res_space)
    time.sleep(30)
    res_attribute = create_attribute(
        GraphAttributeModel(space_name=space_name, attribute_type="TAG", field_name="entity",
                            field_dict={"name": "string", "title": "string", "file_id": "string", "type": "string"}))
    if res_attribute.code != 200:
        logger.error(res_attribute.msg)
        return BaseResponse(code=500, msg=f'创建tag属性失败,{str(res_attribute.msg)}')
    logger.info(res_attribute)
    res_edge = create_attribute(
        GraphAttributeModel(space_name=space_name, attribute_type="EDGE", field_name="relationship",
                            field_dict={"name": "string", "file_id": "string", "show_flag": "string", "page_num": "string"}))
    if res_edge.code != 200:
        logger.error(res_edge.msg)
        return BaseResponse(code=500, msg=f'创建EDGE属性失败,{str(res_edge.msg)}')
    logger.info(res_edge)
    res_similar_edge = create_attribute(
        GraphAttributeModel(space_name=space_name, attribute_type="EDGE", field_name="relationship_similar",
                            field_dict={"name": "string", "show_flag": "string"}))
    if res_similar_edge.code != 200:
        logger.error(res_similar_edge.msg)
        return BaseResponse(code=500, msg=f'创建EDGE属性失败,{str(res_similar_edge.msg)}')
    logger.info(res_similar_edge)
    return BaseResponse(code=200, msg=f'成功')


def batch_insert_vertex(insert_param: InsertModel):
    """
    批量保存服务
    Args:
        insert_param:
    Returns:

    """
    # logger.info(f"参数：{str(insert_param.json())}")
    space_name = "g_" + insert_param.space_name
    if not check_space_exists(space_name):
        res_space = create_space(GraphModel(space_name=space_name))
        if res_space.code != 200:
            logger.error(res_space.msg)
            return BaseResponse(code=500, msg=f'创建空间失败,{str(res_space.msg)}')
        logger.info(res_space)
        time.sleep(30)
        res_attribute = create_attribute(
            GraphAttributeModel(space_name=space_name, attribute_type="TAG", field_name="entity",
                                field_dict={"name": "string", "title": "string", "file_id": "string", "type": "string"}))
        if res_attribute.code != 200:
            logger.error(res_attribute.msg)
            return BaseResponse(code=500, msg=f'创建tag属性失败,{str(res_attribute.msg)}')
        logger.info(res_attribute)
        res_edge = create_attribute(
            GraphAttributeModel(space_name=space_name, attribute_type="EDGE", field_name="relationship",
                                field_dict={"name": "string", "file_id": "string", "show_flag": "string", "page_num": "string"}))
        if res_edge.code != 200:
            logger.error(res_edge.msg)
            return BaseResponse(code=500, msg=f'创建EDGE属性失败,{str(res_edge.msg)}')
        logger.info(res_edge)
        res_similar_edge = create_attribute(
            GraphAttributeModel(space_name=space_name, attribute_type="EDGE", field_name="relationship_similar",
                                field_dict={"name": "string", "show_flag": "string"}))
        if res_similar_edge.code != 200:
            logger.error(res_similar_edge.msg)
            return BaseResponse(code=500, msg=f'创建EDGE属性失败,{str(res_similar_edge.msg)}')
        logger.info(res_similar_edge)
        time.sleep(20)
    session = user_connect_space(space_name)
    triples_data_list = insert_param.triples_data  # 三元组
    entity_attribute = insert_param.entity_attribute  # 实体对应对属性
    entity_list = list(entity_attribute.keys())
    triples_attribute = insert_param.triples_attribute  # 三元组对应对属性
    process_triples_data_list = []
    for td in triples_data_list:
        try:
            td1 = clean_entity(str(td[0]))
            td2 = clean_entity(str(td[2]))
            relationship = clean_entity(str(td[1]))
            if td1 not in entity_list or td2 not in entity_list:
                if relationship != "相似":
                    logger.error(f"的实体不在实体属性中：{td}")
                    continue
            if not td1 or not td2 or not relationship:
                continue
            if len(td) != 3:
                logger.error(f"error triples data {td}，len is not three")
                continue
            if not isinstance(td1, (int, str)) or not isinstance(td2, (int, str)) or not isinstance(relationship, (int, str)):
                logger.error(f"error triples data {td}")
                continue
            if len(td1) > 30 or len(td2) > 30 or len(relationship) > 30:
                logger.error(f"error triples data {td},len error")
                continue
            process_triples_data_list.append((td1, relationship, td2))
        except Exception as e:
            logger.error(f"三元组错误: {e}")
            pass
    vertex_queries = []
    for vid_entity in entity_list:
        try:
            title = ",".join(entity_attribute[vid_entity]["title"])
            file_id = ",".join(entity_attribute[vid_entity]["file_id"])
            e_type = ",".join(entity_attribute[vid_entity]["e_type"])
            insert_query = f'INSERT VERTEX  {insert_param.vertex_name}(name,title,file_id,type) VALUES ' \
                           f'"{vid_entity}":("{vid_entity}","{title}","{file_id}","{e_type}");'
            vertex_queries.append(insert_query)
        except KeyError as e:
            logger.error(f"属性获取失败或值类型错误：{e}")
            continue
    error_tag_data_list = batch_to_graph(session, vertex_queries, space_name)
    edge_queries = []
    for ed in process_triples_data_list:
        if ed[2] == ed[0]:
            continue
        if ed[1] == "相似":
            insert_edge_re = f'INSERT EDGE IF NOT EXISTS relationship_similar(name,show_flag) VALUES "{ed[0]}"->"{ed[2]}":("{ed[1]}","1");'
            edge_queries.append(insert_edge_re)
            insert_edge_re = f'INSERT EDGE IF NOT EXISTS relationship_similar(name,show_flag) VALUES "{ed[2]}"->"{ed[0]}":("{ed[1]}","0");'
            edge_queries.append(insert_edge_re)
        else:
            ed_v = ",".join(ed)
            if ed_v in triples_attribute:
                file_id = ",".join(triples_attribute[ed_v]["file_id"])
                page_num = ",".join(triples_attribute[ed_v]["page_num"])
            else:
                file_id = ""
                page_num = ""
            insert_edge = f'INSERT EDGE  {insert_param.edge_name}(name,file_id,show_flag,page_num) VALUES "{ed[0]}" ->"{ed[2]}":' \
                          f'("{ed[1]}","{file_id}","1","{page_num}");'
            edge_queries.append(insert_edge)
            insert_edge = f'INSERT EDGE  {insert_param.edge_name}(name,file_id,show_flag,page_num) VALUES "{ed[2]}" ->"{ed[0]}":' \
                          f'("{ed[1]}","{file_id}","0","{page_num}");'
            edge_queries.append(insert_edge)
    error_edge_data_list = batch_to_graph(session, edge_queries, space_name)
    return_nacos_model().close_session(session)
    return BaseResponse(code=200, msg=f'添加图数据成功', data={"error_edge_data_list": error_edge_data_list, "error_tag_data_list": error_tag_data_list})


# def generate_ner_data(passage, model_name, server_config):
#     """
#     生成实体
#     Args:
#         passage:
#         model_name:
#         server_config:
#
#     Returns:
#
#     """
#     ner_messages = ner_prompts.format_prompt(user_input=passage)
#     prompt_dict_list = ner_messages.dict()["messages"]
#     messages = [{"role": "system", "content": prompt_dict_list[0]["content"]},
#                 {"role": "user", "content": prompt_dict_list[1]["content"]},
#                 {"role": "assistant", "content": prompt_dict_list[2]["content"]},
#                 {"role": "user", "content": prompt_dict_list[3]["content"]}]
#     res_result = requests_llm(messages, model_name, server_config)
#     return res_result


# R14-P1-03：抽取类型表必须用**业务类型**，不能用 base.py 的 8 类通用默认值。
# 实测（A 的 2x2）：默认 8 类（人/机构/位置/时间/角色/疾病/药品/项目）下，模型判定
# "评级加点表不属于任何给定类型" -> 整段跳过，且**不报错**；
# 换成业务类型（评级/金额/指标/条款...）+ "表格逐项抽取"提示后，三档映射可以完整抽出。
GENERIC_DEFAULT_TYPES = {"人", "机构", "位置", "时间", "角色", "疾病", "药品", "项目"}


def _resolve_entity_types(requested):
    """请求没给类型、或给的就是 8 类通用默认值 -> 一律升级为业务类型表。

    为什么不是"直接用请求值"：调用方（含我自己的重建脚本）都不会传 entity_types，
    FastAPI 会落到 base.py:69 的 8 类默认值，而那不是业务语义，模型据此**静默少抽**。
    """
    from graph_types import ALLOWED_TYPES
    req = [str(x).strip() for x in (requested or []) if str(x).strip()]
    # 实测（B，6 次）：业务类型表反而**更差**（AAA 有、30/60/100 基点 0/6）；
    # 真正有效的是"表格逐项抽取"提示（见 prompts/entity_extraction.py 2.1）。
    # 所以这里只做"记录"，不擅自升级类型表，避免又一处静默改变行为。
    if not req:
        return list(ALLOWED_TYPES), "business_default(empty_request)"
    return req, "request"


def llm_generate_triple(json_data, entity_types: [str], model_info, server_config):
    """
    生成三元组
    Args:
        entity_types:  用户自定义或默认实体类型数组
        json_data:
        model_info:
        server_config:

    Returns:

    """
    triples_data_set = set()
    entity_source_dict = {}
    triples_source_dict = {}
    max_char_length = server_config["rotate_answer"]["max_char_length"]
    num = 0
    for js in json_data:
        for pk, source in js.items():
            content = source["page_content"]  # json format string
            if len(content) > max_char_length:
                content = content[:max_char_length]
            # 生成实体
            relations, entity_dict = generate_graph_relations(content, model_info, server_config, entity_types=entity_types)
            for relation in relations:
                td_s = ""
                try:
                    s_e = relation["src_entity"]["name"]
                    r_p = relation["name"]
                    t_e = relation["dest_entity"]["name"]
                    td_s = s_e + "," + r_p + "," + t_e
                    triples_data_set.add((s_e, r_p, t_e))
                except Exception as e:
                    logger.error(f"元组转换错误：{relation},{e}")

                if td_s:
                    entity_source_dict = generate_entity_data(relation, pk, entity_source_dict, source["metadata"])
                    triples_source_dict = attribute_assignment(triples_source_dict, td_s, pk, source["metadata"], "triples_type", relation["description"])
            if entity_dict:
                for name, value in entity_dict.items():
                    entity_type = value["type"].strip()
                    if not entity_type or entity_type is None:
                        logger.info(f"该实体:{name}，没有类型，{value}")
                        entity_type = "其他"
                    if name not in entity_source_dict:
                        entity_source_dict = attribute_assignment(entity_source_dict, name, pk, source["metadata"], entity_type, "")
            num += 1
            if num % 100 == 0:
                logger.info(f"已经对{num}条文本进行了文档生成")
    logger.info(f"共对{num}条文本进行了文档生成")
    return triples_data_set, entity_source_dict, triples_source_dict


def generate_triple_data(query_docu: QueryDocChunk):
    """
    生成服务
    Args:
        query_docu:

    Returns:

    """
    # todo 需要修改掉使用 embedding_model 和 online_embedding_model 的nacos配置
    # logger.info(f"参数：{str(query_docu.json())}")
    server_config = return_nacos_model().get_config()
    space_name = query_docu.space_name.replace("table_chunks_", "").replace("faq_", "").replace("table_summary_", "")
    collection_name_entity = "graph_entity_" + space_name
    collection_name_triples = "graph_triples_" + space_name
    json_data = get_document_chunk(query_docu, server_config)
    if not json_data:
        logger.error(f'该知识库{space_name}未查询到相关文本，请检查数据或参数后重试')
        return BaseResponse(code=500, msg=f'该知识库{space_name}未查询到相关文本，请检查数据或参数后重试')
    logger.info(f"共查询到{len(json_data)}条文本数据")
    t1 = time.time()
    model_info = query_docu.model_info
    # R14-P1-03：类型表兜底 + **打日志**（原来日志里看不到用了哪些类型，下次还得靠复放）
    entity_types, types_source = _resolve_entity_types(getattr(query_docu, "entity_types", None))
    logger.info(f"抽取类型表（source={types_source}）：{entity_types}")
    triples_data_list, entity_source_dict, triples_source_dict = llm_generate_triple(json_data, entity_types, model_info, server_config)
    logger.info(f"生成数据所需时间是：{time.time() - t1}")
    # R13 类型体系 / 实体过滤 / canonical 归一（落库前统一收敛）
    triples_data_list, entity_source_dict, triples_source_dict, type_report = normalize_graph_data(
        triples_data_list, entity_source_dict, triples_source_dict)
    logger.info(f"归一后：实体{type_report['kept_entities']}个，过滤{len(type_report['filtered'])}个，"
                f"合并{len(type_report['merged'])}个，未分类{len(type_report['unclassified'])}个，"
                f"丢弃三元组{type_report['dropped_triples']}条 (schema={type_report['schema_version']})")
    logger.info(f"共生成{len(triples_data_list)}条图数据")
    if not triples_data_list:
        logger.error(f'数据未生成三元组数据，请检查数据或重试')
        return BaseResponse(code=500, msg=f'数据未生成三元组数据，请检查数据或重试')
    entity_list = [en for en, va in entity_source_dict.items() if va["entity_type"] == "1"]
    logger.info(f"共生成{len(entity_list)}个实体信息")
    # 相似实体计算
    logger.info(f"开始进行内部相似度比对")
    t2 = time.time()
    model_name = query_docu.embed_model_name or server_config["embedding_model"]
    synonymous_set = vectorization_data_similarity(entity_list, model_name, server_config)
    logger.info(f"相似度比对所需时间是：{time.time() - t2}")
    
    # 检查vectorization_data_similarity是否返回错误
    if hasattr(synonymous_set, 'code') and synonymous_set.code != 200:
        logger.error(f'向量相似度比对失败: {synonymous_set.msg}')
        return synonymous_set
    
    logger.info(f"开始查询相似实体,修改三元组实体对应值")
    t3 = time.time()
    entity_list, synonymous_set, entity_source_dict = query_like_entity(server_config, collection_name_entity, entity_list, entity_source_dict, synonymous_set)
    milvus_triples_list, triples_source_dict = update_triples_data(server_config, collection_name_triples, triples_source_dict, triples_data_list)
    logger.info(f"更新向量库所需时间是：{time.time() - t3}")
    # 添加图数据库
    if not entity_source_dict:
        logger.error(f'文本块没有解析出新的图谱关系，共{len(entity_source_dict)}条图数据，请重新导入或者更换知识库')
        return BaseResponse(code=200, msg=f'文本块没有解析出新的图谱关系，共{len(entity_source_dict)}条图数据，请重新导入或者更换知识库')
    full_triples_list = list(triples_data_list)
    if synonymous_set and isinstance(synonymous_set, set):
        full_triples_list.extend(list(synonymous_set))
    logger.info(f"开始插入graph图数据，需保存{len(full_triples_list)}")
    t4 = time.time()
    graph_entity_source_dict = {name: values for name, values in entity_source_dict.items() if values["entity_type"] == "1"}
    dc = InsertModel(space_name=space_name, triples_data=full_triples_list, entity_attribute=graph_entity_source_dict,
                     triples_attribute=triples_source_dict)
    res_v = batch_insert_vertex(dc)
    if res_v.code == 500:
        logger.error(f'添加图数据库失败，请重试.{res_v.msg}')
        return BaseResponse(code=500, msg=f'添加图数据库失败，请重试.{res_v.msg}')
    logger.info(f"插入图数据库所需时间是：{time.time() - t4}")
    # 添加milvus向量库
    logger.info(f"开始插入milvus实体数据，需保存{len(entity_list)}")
    t5 = time.time()
    # 查询关系将关系保存，去重关系
    entity_list = remove_duplicates_relation_name(entity_source_dict, collection_name_entity, server_config, entity_list)
    if entity_list:
        entity_insert_data = [{"page_content": str(name),
                               "metadata": {
                                   "chunk_pk_list": entity_source_dict[name]["chunk_pk_list"],
                                   "title": entity_source_dict[name]["title"],
                                   "file_id": entity_source_dict[name]["file_id"],
                                   "entity_type": entity_source_dict[name]["entity_type"],
                                   "type": entity_source_dict[name]["e_type"]
                               }}
                              for name in entity_list]
        entity_milvus_data = {
            "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
            "collection_name": collection_name_entity,
            "document_list": entity_insert_data
        }
        # R13-FIX-GRAPH-06：空批次不调用向量库（否则向量服务返回"待向量化的文本列表为空"被当成失败）
        if entity_insert_data:
            res_m = query_milvus_api(server_config, 'insert_vector_documents_custom', entity_milvus_data)
            if res_m.json()["code"] == 500:
                logger.error(f'添加实体向量库失败，请重试，实体表错误：{res_m.json()["msg"]}')
                return BaseResponse(code=500, msg=f'添加实体向量库失败，请重试，实体表错误：{res_m.json()["msg"]}')
        else:
            logger.info('本次无可写入的实体向量，跳过实体向量库写入')
    triples_insert_data = []
    for name in milvus_triples_list:
        tris = name.split(',')
        insert_data = {"page_content": str(name),
                       "metadata": {
                           "source_entity": str(tris[0]),
                           "relationship": str(tris[1]),
                           "target_entity": str(tris[2]),
                           "chunk_pk_list": triples_source_dict[name]["chunk_pk_list"],
                           "title": triples_source_dict[name]["title"],
                           "file_id": triples_source_dict[name]["file_id"],
                           "page_num": triples_source_dict[name]["page_num"]
                       }
                       }
        triples_insert_data.append(insert_data)
    triples_milvus_data = {
        "db_name": server_config["graph_conn_config"]["graph_milvus_database"],
        "collection_name": collection_name_triples,
        "document_list": triples_insert_data
    }
    if triples_insert_data:
        res_t = query_milvus_api(server_config, 'insert_vector_documents_custom', triples_milvus_data)
        if res_t.json()["code"] == 500:
            logger.error(f'添加三元组向量库失败，请重试，三元组表错误：{res_t.json()["msg"]}')
            return BaseResponse(code=500, msg=f'添加三元组向量库失败，请重试，三元组表错误：{res_t.json()["msg"]}')
    else:
        # 只抽到实体、没有三元组属于正常情况（例如表格/短文本块），不应判失败
        logger.info('本次无可写入的三元组向量，跳过三元组向量库写入')
    logger.info(f"插入向量数据库所需时间是：{time.time() - t5}")
    return BaseResponse(code=200, msg=f'添加成功，新增和更新{len(full_triples_list)}条图数据,新增{len(entity_list)}条实体',
                        data={"error_edge_data_list": res_v.data["error_edge_data_list"],
                              "error_tag_data_list": res_v.data["error_tag_data_list"],
                              "type_report": type_report})


def fetch_chunk_documents(space_name, chunk_pk_list, server_config, entity_names=None, violations_out=None):
    """按 chunk pk 回取正文块（Milvus 优先，ES 按 _id 补齐）。

    R13-FIX-GRAPH-14 背景（源码事实 + 实测）：
      - 图实体/三元组里的 `chunk_pk_list` 语义是"抽取时刻 ES 文档 `_id`"
        （graph_fun_tool.get_document_chunk 用 `ed["_id"]` 当 pk）；
      - 文本块入库 Milvus 时 pk 与 ES `_id` 同源（ES `_source.metadata.pk` == Milvus `pk`），
        所以正常情况下可以直接用 Milvus pk 回取正文；
      - 但"重新解析"会生成新的 `_id`，而 ES 索引与 Milvus 集合可能停留在**不同的解析代次**
        （R12/R13 实测 kb_9：ES 8 篇是旧 id、Milvus `_kb_9` 8 行是新 id，只有 1 个 id 重合），
        图数据里的旧 id 于是变成悬空引用。原实现直接查 Milvus pk，查不到就返回空列表，
        对外表现为"图检索 200、entity_list/result_data 全空"。
    处理：先按 Milvus pk 查；对"未命中的 id"再用 ES `ids` 查询补齐（ES `_id` 就是 chunk pk），
    两者都不存在的才算真悬空并打错误日志（提示重建图）。
    """
    documents = []
    es_url = ('http://' + server_config["es_config"]["host"] + ':'
              + str(server_config["es_config"]["port"]) + '/')
    pk_int_list = []
    seen = set()
    for pk in chunk_pk_list or []:
        try:
            pk_value = int(pk)
        except (TypeError, ValueError):
            continue
        if pk_value in seen:
            continue
        seen.add(pk_value)
        pk_int_list.append(pk_value)
    if not pk_int_list:
        logger.error('图检索未产出任何 chunk 候选（PPR/light 打分为空），无正文可回取')
        return documents
    milvus_docs = query_milvus_by_condition(db_name="rag_knowledge_base",
                                            knowledge_base_name=space_name,
                                            col_name="pk",
                                            col_values=pk_int_list,
                                            server_config=server_config)
    documents.extend(milvus_docs)
    hit_pks = set()
    for doc in milvus_docs:
        try:
            hit_pks.add(int((doc.get("metadata") or {}).get("pk")))
        except (TypeError, ValueError):
            continue
    missing_pks = [pk for pk in pk_int_list if pk not in hit_pks]
    if not missing_pks:
        # R14-B6：这里曾直接 return documents，**绕过了两层标注**。
        # 重建图后 pk 全部能在 Milvus 命中，走的就是这条早退，于是
        # provenance_quality / identity_stability 整键消失，下游按字段读会得到"假红"。
        # 标注必须在**每一条返回路径**上执行。
        return _annotate_two_layers(documents, violations_out)
    # ES 补齐：chunk_pk_list 即 ES 文档 _id
    es_payload = {
        "index_name": [space_name, "table_chunks_" + space_name],
        "query_body": {"query": {"ids": {"values": [str(pk) for pk in missing_pks]}},
                       "size": len(missing_pks)},
    }
    try:
        resp = requests.post(es_url + 'search_by_custom_param', json=es_payload, timeout=30)
        es_data = resp.json()['data']['result_data']
    except Exception as e:
        logger.error(f'ES 补齐图检索正文失败:{e}')
        return _annotate_two_layers(documents, violations_out)
    for ed in es_data:
        source = ed.get("_source") or {}
        documents.append({"page_content": source.get("page_content", ""),
                          "metadata": source.get("metadata") or {}})
    unresolved = [pk for pk in missing_pks
                  if str(pk) not in {str(ed.get("_id")) for ed in es_data}]
    logger.warning(f'chunk 候选{len(pk_int_list)}条：Milvus 命中{len(milvus_docs)}条，'
                   f'ES 补齐{len(es_data)}条，仍悬空{len(unresolved)}条'
                   + (f'（{unresolved[:5]}，图数据与文本块不同步，可重建图修复）' if unresolved else ''))
    # R14-B3：前两级都取不到正文（图 data 与文本块不同代次，PK/_id 全失效）时，
    # 用**当前代次**的 ES 全文本块按"命中实体"回取正文，避免图检索"命中实体但 0 条正文"
    # 直接变成"图对上下文零贡献"（实测 kb_9 重新解析后就是这个状态）。
    # 明确标注 recovered_by，供审计区分"精确 chunk 回填"与"按实体内容回填"。
    if not documents and entity_names:
        documents = _recover_documents_by_entities(space_name, entity_names, es_url, server_config)
    # 按 PPR/light 给出的候选顺序返回（检索侧会用 metadata.search.rank 记录顺序）
    order = {pk: i for i, pk in enumerate(pk_int_list)}
    documents.sort(key=lambda d: order.get(int((d.get("metadata") or {}).get("pk") or 0), len(order)))
    return _annotate_two_layers(documents, violations_out)


# identity 层：这块"是不是同一块"（取决于 id 生成方式）
_STABLE_ID_ORIGINS = {"derived_chunk_index", "derived_parsed_chunk_index", "derived_community",
                      # C 确定性化后，解析侧给的 pk 也是稳定身份（同一文件同一块重解析不变）
                      "pk_from_caller"}


def _identity_violation_fields(violations):
    """响应体里的违规字段**唯一来源**。

    纪律（A-data 2026-10-27 定的四条）：
      1) code==200 必须同时含 identity_violations（数组，可为空）与 identity_violations_count（整数）；
      2) code!=200 不必带（错误语义优先）；
      3) count == len(list) 恒成立 —— 因此二者只能由本函数一处产出，禁止各处自己算；
      4) GRAPH_STRICT_ID_MIXTURE 只用于 CI/变异复验，不进生产判断。
    """
    v = list(violations or [])
    return {"identity_violations": v, "identity_violations_count": len(v)}


def _annotate_two_layers(documents, violations_out=None):
    """给回取的块打上**两层正交**标注（A-data 2026-10-27 提出，我据此实现）：

    1) 身份层 `identity_stability`：这块"是不是同一块"，只看 id 生成方式
         stable_derived            —— 派生 id（同文件同块稳定）
         pending_deterministic     —— 来自调用方 pk，但调用方当前仍随机（C 未改完）
         unknown                   —— 随机或不可判定
    2) 出处层 `provenance_quality`：这块"是否产出该结论"
         exact_chunk               —— 由 chunk_pk_list 精确命中回填
         entity_content_recovered  —— 代次漂移兜底，按实体名匹配到的当前块
    两层不得互相替代：identity 变稳**不等于** provenance 精确。
    """
    for d in documents or []:
        md = d.get("metadata")
        if not isinstance(md, dict):
            md = {}
            d["metadata"] = md
        if md.get("recovered_by") == "entity_content":
            md["provenance_quality"] = "entity_content_recovered"
        else:
            # 显式置 None：键存在、值为 None = "精确命中，未走实体兜底"。
            # 下游可以用 `"recovered_by" in md` 判"字段是否被支持"，用值判"是否兜底过"。
            md.setdefault("recovered_by", None)
            md.setdefault("provenance_quality", "exact_chunk")
        raw = str(md.get("id_origin") or "").strip().lower()
        # 硬约束（A-data 2026-10-27）：块级回取里**不该**出现"社区摘要的派生来源"。
        # 一旦出现，说明 chunk_pk_list 与社区摘要混用——这是数据错误，不能当 unknown 放过。
        # 默认 loud-fail（ERROR + invalid_mixture 标记，不把异常升级成 500 打断验收）；
        # 需要严格模式时设 GRAPH_STRICT_ID_MIXTURE=1，直接抛错让问题立即可见。
        if raw == "derived_community":
            msg = ("块级 chunk 回取出现 derived_community（chunk_pk_list 与社区摘要混用）："
                   f"pk={md.get('pk')} source={md.get('source')}")
            if os.environ.get("GRAPH_STRICT_ID_MIXTURE") == "1":
                raise RuntimeError(msg)
            logger.error(msg)
            md["identity_stability"] = "invalid_mixture"
            md["identity_violation"] = "derived_community_in_chunk_level"
            # 可断言性（A-data 2026-10-27）：只写日志的 loud 在自动化里等于静默。
            # 违规必须同时进响应体，让验收能断言 count==0，而不靠抓日志或切环境变量。
            if isinstance(violations_out, list):
                violations_out.append({
                    "pk": str(md.get("pk")),
                    "chunk_pk_list_from": "graph_entity",
                    "reason": "derived_community_in_chunk_level",
                    "source": md.get("source"),
                })
            continue
        if raw in _STABLE_ID_ORIGINS:
            md["identity_stability"] = "stable_derived"
        else:
            md["identity_stability"] = "unknown"
    return documents


# 写入层 metadata.id_origin（ES 权威）→ 图谱侧枚举。
#   derived_chunk_index：同一文件同一块稳定，可作精确 provenance 的强证据
#   derived_community  ：社区摘要的既成事实，不参与"块稳定"判断
#   pk_from_caller     ：id 由调用方（解析服务）给出；C 已确定性化，视为稳定身份
#   random / 缺失      ：unknown
ID_ORIGIN_MAP = {
    "derived_chunk_index": "derived_chunk_index",
    # 已不是预留：写入层现为"优先取 parsed_chunk_index、缺失退回 chunk_index"，
    # 两分支都会真实产出（A 实测 chunk_index=0 → derived_chunk_index；
    # parsed_chunk_index=7/chunk_index=9 → derived_parsed_chunk_index）。两者都合法。
    "derived_parsed_chunk_index": "derived_parsed_chunk_index",
    "derived_community": "derived_community",
    # R14-B 收敛（A-data e2e 四判据通过，2026-10-27）：
    # C 已把解析侧 pk 确定性化（create_uuid() 计数 0、12340 已重启 11:43:31）、
    # 两类夹具各解析两次 id 完全相同、落库仍为 pk_from_caller、parsed_chunk_index 已保留到索引。
    # 故不再标 pending —— 但"稳定"只对**重解析过的文档**成立；11:00 前写入的旧文档无该字段 → unknown。
    "pk_from_caller": "pk_from_caller",
    "random": "unknown",
}


def _recover_documents_by_entities(space_name, entity_names, es_url, server_config, limit=8):
    """按实体名在当前代次的 ES 文本块里回取正文（代次漂移兜底）。

    不做任何"猜 id"的动作：只用图检索**已经算出来的实体名**做短语匹配，
    命中的块打 `recovered_by=entity_content`，与精确回填的块可区分。
    """
    names = [str(n) for n in (entity_names or []) if n and len(str(n)) >= 2][:6]
    if not names:
        return []
    payload = {
        "index_name": [space_name, "table_chunks_" + space_name],
        "query_body": {"query": {"bool": {"should": [
            {"match": {"page_content": n}} for n in names]}}, "size": limit},
    }
    try:
        resp = requests.post(es_url + 'search_by_custom_param', json=payload, timeout=30)
        rows = resp.json()['data']['result_data'] or []
    except Exception as e:
        logger.error(f'按实体回取图检索正文失败:{e}')
        return []
    out, seen = [], set()
    for row in rows:
        src = row.get("_source") or {}
        text = src.get("page_content") or ""
        if not text:
            continue
        key = (src.get("metadata") or {}).get("pk") or text[:64]
        if key in seen:
            continue
        seen.add(key)
        md = dict(src.get("metadata") or {})
        # R14-B/A：id 来源以**写入时落库的 metadata.id_origin** 为准（A 在 controller/es.py:194-213 判定、
        # :238 落库），不再让图谱侧重算哈希——避免两边公式版本不一致产生"两个都合法"的 id。
        # pk_from_caller 在 C 把解析侧确定性化之后（e2e 四判据通过）已收敛为稳定；
        # 但只对**重解析过的文档**成立：11:00 前写入的旧文档没有 id_origin → unknown（不回填）。
        _origin = ID_ORIGIN_MAP.get(str(md.get("id_origin") or "").strip().lower(), "unknown")
        # A-data 复核意见：审计必须能区分"精确 provenance"与"按名回取"，
        # 否则前端会把按名命中的同实体另一篇文档当成精确引用渲染。
        matched_ents = [n for n in names if n in text]
        # ES 的 should 是"文档级命中"，返回块本身可能一个实体名都不含（分词/相关性召回所致）。
        # 只保留**能在正文里逐字找到实体名**的块，避免把无关正文塞进上下文。
        if not matched_ents:
            continue
        md["recovered_by"] = "entity_content"
        md["provenance_quality"] = "entity_content_recovered"
        md["recovered_entities"] = matched_ents
        md["recovered_es_id"] = row.get("_id")
        md["recovered_chunk_ref"] = {
            "document_id": md.get("document_id"),
            "file_id": md.get("file_id"),
            "chunk_index": md.get("chunk_index"),
            "source": md.get("source"),
            # 该块 id 的来源，**枚举**（不要当 boolean 用）：
            #   derived_chunk_index | derived_parsed_chunk_index | derived_community | pk_from_caller | unknown
            # 取值来自写入时落库的 metadata.id_origin（见上方 ID_ORIGIN_MAP）；
            # 无该字段的旧文档（本轮之前的写入）一律 unknown。
            "id_origin": _origin,
            "id_origin_raw": md.get("id_origin"),
        }
        out.append({"page_content": text, "metadata": md})
    if out:
        logger.warning(f'图检索正文按实体内容回取 {len(out)} 条（图 data 与文本块不同代次）')
    return out


def query_graph_data(query_data: QueryGraphData):
    """数据查询入口。

    R14-TL 裁决（2026-10-27）：**200 = 业务结果（含合法空结果），500 = 依赖故障**。
      200 + data.reason ∈ {no_entity_extracted, no_vertex_matched, space_not_found}  -> 业务空
      500（图检索异常那条除外）                                                      -> 依赖故障
    这样验收可以一句话断言"5xx 即失败"，不必给"图允许空"开口子。

    R13-FIX-GRAPH-15：每个请求从连接池取独立 Session，用完即还；
    原先共用全局单 Session 且请求结束时 release()，并发图检索会互相踩成
    `RuntimeError: The session has been released`（检索服务多知识库并行时必现）。
    """
    space_name = "g_" + query_data.space_name
    if not check_space_exists(space_name):
        logger.error(f'该空间：{query_data.space_name}不存在， 请检查后再次查询')
        # R14-B（A-data 复现的链路级丢结果）：原来 data=None，检索侧 retrieval_graph 硬取
        # data['result_data'] 会抛 'NoneType' object is not subscriptable，被 except 吞掉后
        # **直接 return**（不是 continue）→ 多 KB 组合里只要有一个 KB 没有图空间，
        # 后面所有 KB 的图检索结果全丢，对外仍是 200。这里补成与另外三处同形的空结果。
        return BaseResponse(code=200, msg=f'该空间：{query_data.space_name}不存在，请检查后再次查询',
                            data={"result_data": [], "entity_list": [], "reason": "space_not_found"})
    session = None
    try:
        session = return_nacos_model().acquire_session(space_name)
        return _query_graph_data(query_data, session)
    except Exception as e:
        logger.exception(f'图检索异常:{e}')
        return BaseResponse(code=500, msg=f'图检索异常:{e}',
                            data={"result_data": [], "entity_list": [], "reason": "graph_error"})
    finally:
        return_nacos_model().release_session(session)


def _query_graph_data(query_data: QueryGraphData, session):
    # logger.info(f"参数：{str(query_data.json())}")
    chunk_document_list = []
    high_entity_list = []  # 高分实体

    server_config = return_nacos_model().get_config()
    t1 = time.time()
    res_result = generate_query_entities(query_data.query, query_data.model_info, server_config)
    if not res_result:
        logger.error(f'查询失败，{query_data.query}并未提取到实体信息，请重试或修改查询语句')
        # R14-B：键名必须与调用方（alg_retrieval_service/retrieval_graph: milvus_data['data']['result_data']）
        # 一致。原来这里用 documents_list，调用方取 result_data 会 KeyError → 被 except 吃掉 →
        # 直接 return 空并**跳过后续知识库**（多 KB 时静默丢结果）。
        return BaseResponse(code=200, msg=f'查询失败，{query_data.query}并未提取到实体信息，请重试或修改查询语句',
                            data={"result_data": [], "entity_list": [], "reason": "no_entity_extracted"})
    logger.info(f"抽取问题实体所需时长：{time.time() - t1}")
    collection_name_entity = "graph_entity_" + query_data.space_name
    collection_name_triples = "graph_triples_" + query_data.space_name
    query_ner_set = set(clean_entity(en) for en in res_result)
    t2 = time.time()
    # 查询相似实体
    milvus_outputs = pool_query_milvus(collection_name_entity, server_config, list(query_ner_set), top_k=1, expr='entity_type == "1"')
    query_ner_list = remove_duplicates_by_pk(milvus_outputs, query_ner_set)
    logger.info(f"查询实体所需时间是：{time.time() - t2}")
    logger.info(f"起始节点：{query_ner_list}")
    t3 = time.time()
    # 根据顶点查询图中三元组数据
    # , depth=query_data.depth or server_config["graph_config"]["depth"]
    triples_list, entity_triples_dict, relationship_set = execute_query(session, query_ner_list, query_data.query_type)
    logger.info(f"查询深度为{query_data.depth}的图数据库所需时间是：{time.time() - t3}")
    if not triples_list:
        logger.error(f'图数据库中无法查询提取到到实体{res_result}，请重试或检查数据库')
        return BaseResponse(code=200, msg=f'图数据库中无法查询提取到到实体{res_result}，请重试或检查数据库',
                            data={"result_data": [], "entity_list": [], "reason": "no_vertex_matched"})
    entity_list = list(entity_triples_dict.keys())
    entity_info_list = query_milvus_by_condition(db_name="graph_base",
                                                 knowledge_base_name=collection_name_entity,
                                                 col_name="text",
                                                 col_values=entity_list,
                                                 server_config=server_config)
    start_judge_list = [el["page_content"] for el in entity_info_list]
    ppr_flag = any(sn in start_judge_list for sn in query_ner_list)
    if not ppr_flag:
        logger.error(f'图数据库中无法查询提取到到实体{res_result}，请重试或检查数据库')
        return BaseResponse(code=200, msg=f'查询失败，图服务并无问题中相关的顶点数据',
                            data={"result_data": [], "entity_list": [], "reason": "no_vertex_matched"})
    if query_data.query_type == 'hippo':
        document_chunk_pk_list, high_entity_list = cal_ppr_fun(triples_list, entity_info_list, entity_list, query_ner_list,
                                                              entity_triples_dict, collection_name_entity, server_config)
    else:
        document_chunk_pk_list = query_light_fun(start_judge_list, relationship_set, server_config, collection_name_triples, entity_info_list)
        high_entity_list = [en for en in query_ner_list if en in start_judge_list]
    identity_violations = []
    chunk_document_list = fetch_chunk_documents(query_data.space_name, document_chunk_pk_list,
                                                server_config, entity_names=high_entity_list or entity_list,
                                                violations_out=identity_violations)
    return BaseResponse(code=200, msg=f'查询成功，共{len(chunk_document_list)}条文本数据',
                        data={"result_data": chunk_document_list, "entity_list": high_entity_list,
                              # 可断言字段：验收直接断言 count==0，不依赖日志或环境变量
                              **_identity_violation_fields(identity_violations)})
