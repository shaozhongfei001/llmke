#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/11/20 18:10
# @Author  : yuxj
# @File    : graph_p_array.py
import igraph as ig
import numpy as np
from scipy.sparse import csr_array
from tqdm import tqdm

from graph_fun_tool import get_chunk_by_ppr_score, high_entity_triples
from operators.common.log import logger


def p_array_compute(doc_fact_dict, lose_fact_dict, kb_phrase_dict, unique_phrases):
    graph_json = {}
    inter_triple_weight = 1.0
    docs_to_facts = {}  # (Num Docs, Num Facts)
    facts_to_phrases = {}  # (Num Facts, Num Phrases)
    graph = {}  # (Num Phrases, Num Phrases)
    for triple, doc_id_list in doc_fact_dict.items():
        doc_phrases = []
        fact_edges = []
        # Iterate over triples
        # 遍历文档中的三元组，三元组转换为元组，获取三元组的 ID：从 lose_fact_dict 中获取三元组对应的 fact_id，这在后续用于建立映射。
        fact_id = lose_fact_dict[triple]
        if len(triple) == 3:
            triple = np.array(triple)[[0, 2]]
            # 文档到三元组映射：将 doc_id 和 fact_id 的组合存储到 docs_to_facts 中，表示某个文档包含某个三元组。这相当于创建了一个文档到三元组的连接矩阵。
            for doc_id in doc_id_list:
                docs_to_facts[(doc_id, fact_id)] = 1
            # 实体到短语 ID 映射，对于三元组中的每个实体（即主语和宾语），获取其在知识库中的 phrase_id。
            # 将 fact_id 与 phrase_id 的组合存储在 facts_to_phrases 中，这表示某个三元组与某个实体相关联。
            for i, phrase in enumerate(triple):
                phrase_id = kb_phrase_dict[phrase]  # 实体序号
                doc_phrases.append(phrase_id)

                facts_to_phrases[(fact_id, phrase_id)] = 1  # 三元组序号和实体序号的矩阵

                for phrase2 in triple[i + 1:]:  # 获取target
                    phrase2_id = kb_phrase_dict[phrase2]

                    fact_edge_r = (phrase_id, phrase2_id)  #
                    fact_edge_l = (phrase2_id, phrase_id)

                    fact_edges.append(fact_edge_r)
                    fact_edges.append(fact_edge_l)

                    graph[fact_edge_r] = graph.get(fact_edge_r, 0.0) + inter_triple_weight
                    graph[fact_edge_l] = graph.get(fact_edge_l, 0.0) + inter_triple_weight

                    phrase_edges = graph_json.get(phrase, {})
                    edge = phrase_edges.get(phrase2, ('triple', 0))
                    phrase_edges[phrase2] = ('triple', edge[1] + 1)
                    graph_json[phrase] = phrase_edges

                    phrase_edges = graph_json.get(phrase2, {})
                    edge = phrase_edges.get(phrase, ('triple', 0))
                    phrase_edges[phrase] = ('triple', edge[1] + 1)
                    graph_json[phrase2] = phrase_edges

    # 创建稀疏矩阵，创建文档到三元组的稀疏矩阵，表示每个文档中包含哪些三元组。
    triple_list_len = len(list(docs_to_facts.keys()))
    docs_to_facts_mat = csr_array(
        ([int(v) for v in docs_to_facts.values()], ([int(e[0]) for e in docs_to_facts.keys()], [int(e[1]) for e in docs_to_facts.keys()])),
        shape=(triple_list_len, triple_list_len))
    # 创建稀疏矩阵，创建三元组到实体的稀疏矩阵，表示每个三元组中包含哪些实体。使用稀疏矩阵（csr_array）可以有效地节省内存空间，特别是在大规模图谱中。
    facts_to_phrases_mat = csr_array(
        ([int(v) for v in facts_to_phrases.values()], ([e[0] for e in facts_to_phrases.keys()], [e[1] for e in facts_to_phrases.keys()])),
        shape=(triple_list_len, len(unique_phrases)))

    doc_to_phrases_mat = docs_to_facts_mat.dot(facts_to_phrases_mat)
    doc_to_phrases_mat[doc_to_phrases_mat.nonzero()] = 1
    phrase_to_num_doc = doc_to_phrases_mat.sum(0).T
    return phrase_to_num_doc, docs_to_facts_mat, facts_to_phrases_mat


def cal_ppr_score_hippo(triple_tuples, reset_prob_chunk, kb_node_phrase_to_id, alpha=0.1, weight='weight'):
    # 创建一个图
    g = ig.Graph()

    # 添加节点
    nodes = set()
    for rel in triple_tuples:
        nodes.add(rel[0])
        nodes.add(rel[2])
    g.add_vertices(list(nodes))

    # 添加边，边的权重可以根据需要进行设置，这里简单设置为 1
    edges = [(rel[0], rel[2]) for rel in triple_tuples]
    g.add_edges(edges)

    # 设置边的权重（可选，权重均为 1） # fixme 权重需要设置成词频
    g.es['weight'] = [1] * len(edges)
    # 计算个性化 PageRank
    pageranked_probabilities = []
    # 找到与关键词相关的节点
    for reset_prob in tqdm(reset_prob_chunk, desc='pagerank chunk'):
        pageranked_probs = g.personalized_pagerank(vertices=range(len(kb_node_phrase_to_id)),
                                                   damping=alpha, directed=False,
                                                   weights=weight, reset=reset_prob, implementation='prpack')
        node2score = {node: prob for node, prob in zip(kb_node_phrase_to_id, pageranked_probs)}
        logger.info("节点PPR得分:")
        logger.info(sorted(node2score.items(), key=lambda x: x[1], reverse=True)[:20])
        pageranked_probabilities.append(np.array(pageranked_probs))

        triple2score = {(h, r, t): node2score[h] + node2score[t] for h, r, t in triple_tuples}
        logger.info("三元组PPR得分")
        logger.info(sorted(triple2score.items(), key=lambda x: x[1], reverse=True)[:10])

    return np.array(pageranked_probabilities)


def cal_ppr_fun(triples_list, entity_info_list, entity_list, query_ner_list, entity_triples_dict, collection_name_entity, server_config):
    # 实体权重，计算ppr
    ppr_phrase_prob = cal_ppr_score(triples_list, entity_info_list, entity_list, query_ner_list)
    indexes_list = np.where(ppr_phrase_prob > 0.05)[1]
    # 高分实体
    high_entity_list = [entity_list[index_id] for index_id in indexes_list]
    print("高分实体")
    logger.info("三元组PPR得分")
    print(high_entity_list)
    # 高分实体对应的三元info
    entity_type_dict = high_entity_triples(high_entity_list, entity_triples_dict, collection_name_entity, server_config, entity_info_list)
    chunk_elements = get_chunk_by_ppr_score(entity_type_dict, entity_list, ppr_phrase_prob)  # [(chunk_pk, score)]
    pk_list = [int(datap[0]) for datap in chunk_elements]
    # R13-FIX-GRAPH-13：调用方（query_graph_data）需要把高分实体回给前端/检索侧，
    # 原实现只返回 chunk pk，导致接口 data.entity_list 恒为空数组。这里一并返回。
    return pk_list, high_entity_list


def cal_ppr_score(triples_list, milvus_dict, entity_list, start_entities):
    """

    Args:
        triples_list:
        milvus_dict:
        entity_list:
        start_entities: 顶点id，ppr让实体从顶点出发，避免造成权重参数不对

    Returns:

    """
    all_phrase_weights = np.zeros(len(entity_list))
    for entity in milvus_dict:
        entity_name = entity["page_content"]
        chunk_pk_list = entity["metadata"]["chunk_pk_list"]
        index = np.where(np.array(entity_list) == entity_name)[0]
        if entity_name in start_entities:
            if len(chunk_pk_list) == 0:
                all_phrase_weights[index[0]] = 1
            else:
                if index.size > 0:
                    all_phrase_weights[index[0]] = 1 / len(chunk_pk_list)
        else:
            all_phrase_weights[index[0]] = 0
    ppr_phrase_prob = cal_ppr_score_hippo(triples_list, [all_phrase_weights], entity_list, alpha=0.8, weight='weight')
    return ppr_phrase_prob


def min_max_normalize(x):
    return (x - np.min(x)) / (np.max(x) - np.min(x))


# def cal_query_doc_scores():
#     tensor_embedding_request(model_name, text, server_config)
#     query_embedding = embed_model.embed_query(query)
#     query_doc_scores = np.dot(doc_embedding_mat, np.array(query_embedding).T)
#     query_doc_scores = [query_doc_scores.T[0]]
#     return query_doc_scores


def rank_docs(ppr_phrase_probs, docs_to_facts_mat, facts_to_phrases_mat, top_k=30):
    """
    :param: ppr_phrase_probs
            docs_to_facts_mat
            facts_to_phrases_mat
    :return: doc_id
    """

    # 通过“短语-事实-文档”关系，将PageRank的短语概率扩展到整个文档集合
    fact_prob = facts_to_phrases_mat.dot(ppr_phrase_probs)
    ppr_doc_prob = docs_to_facts_mat.dot(fact_prob)
    ppr_doc_prob = min_max_normalize(ppr_doc_prob)
    doc_prob = ppr_doc_prob
    # query_doc_scores = cal_query_doc_scores()
    # doc_prob = ppr_doc_prob * 0.5 + min_max_normalize(query_doc_scores) * 0.5
    sorted_doc_ids = np.argsort(doc_prob, kind='mergesort')[::-1]
    sorted_scores = doc_prob[sorted_doc_ids]

    return sorted_doc_ids.tolist()[:top_k], sorted_scores.tolist()[:top_k]
