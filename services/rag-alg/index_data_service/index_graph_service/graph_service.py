#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/6/03 15:14
# @Author  : yuxj
# @File    : fulltext_es_api_start.py
import time

from base import GraphModel, GraphAttributeModel, InsertModel, QueryDocChunk, BaseResponse, QueryGraphData, DelModel
from graph_extract import generate_graph_relations, generate_query_entities
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
    triples_data_list, entity_source_dict, triples_source_dict = llm_generate_triple(json_data, query_docu.entity_types, model_info, server_config)
    logger.info(f"生成数据所需时间是：{time.time() - t1}")
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
                        data={"error_edge_data_list": res_v.data["error_edge_data_list"], "error_tag_data_list": res_v.data["error_tag_data_list"]})


def query_graph_data(query_data: QueryGraphData):
    """
    数据查询
    Args:
        query_data:

    Returns:

    """
    # logger.info(f"参数：{str(query_data.json())}")
    chunk_document_list = []
    high_entity_list = []  # 高分实体

    space_name = "g_" + query_data.space_name
    if not check_space_exists(space_name):
        logger.error(f'该空间：{query_data.space_name}不存在， 请检查后再次查询')
        return BaseResponse(code=500, msg=f'该空间：{query_data.space_name}不存在，请检查后再次查询')
    session = user_connect_space(space_name)
    server_config = return_nacos_model().get_config()
    t1 = time.time()
    res_result = generate_query_entities(query_data.query, query_data.model_info, server_config)
    if not res_result:
        logger.error(f'查询失败，{query_data.query}并未提取到实体信息，请重试或修改查询语句')
        return BaseResponse(code=500, msg=f'查询失败，{query_data.query}并未提取到实体信息，请重试或修改查询语句', data={"documents_list": chunk_document_list})
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
        return BaseResponse(code=500, msg=f'图数据库中无法查询提取到到实体{res_result}，请重试或检查数据库', data={"documents_list": chunk_document_list, "entity_list": []})
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
        return BaseResponse(code=500, msg=f'查询失败，图服务并无问题中相关的顶点数据', data={"result_data": chunk_document_list})
    if query_data.query_type == 'hippo':
        document_chunk_pk_list = cal_ppr_fun(triples_list, entity_info_list, entity_list, query_ner_list, entity_triples_dict, collection_name_entity,
                                             server_config)
    else:
        document_chunk_pk_list = query_light_fun(start_judge_list, relationship_set, server_config, collection_name_triples, entity_info_list)
    chunk_document_list = query_milvus_by_condition(db_name="rag_knowledge_base",
                                                    knowledge_base_name=query_data.space_name,
                                                    col_name="pk",
                                                    col_values=document_chunk_pk_list,
                                                    server_config=server_config)
    return_nacos_model().close_session(session)
    return BaseResponse(code=200, msg=f'查询成功，共{len(chunk_document_list)}条文本数据', data={"result_data": chunk_document_list, "entity_list": high_entity_list})
