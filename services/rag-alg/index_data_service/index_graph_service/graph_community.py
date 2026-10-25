#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GraphRAG 社区检测（R13 / S3）。

职责：从 Nebula `g_<kb>` 读出全图（实体 + 关系），构成无向加权图，
用 networkx 的 Louvain 算法做分层社区划分（level0 = 实体级社区；level1 = 社区超节点级社区）。

设计要点（与 R13 事实对齐）：
1. 图里的关系边是**双向写入**的（graph_service.batch_insert_vertex 对每条三元组写
   show_flag=1 / show_flag=0 两条边），所以构图必须是无向图，否则每次三元组会被算两次。
2. 关系名不在 `e.relationship.name` 单列时稳定，统一走 `properties(e)` 取（与
   graph_fun_tool.execute_query 的 GRAPH-03 修复口径一致）。
3. 社区编号按 (规模降序, 成员名升序) 确定性排序后生成 `L{level}C{idx:03d}`，
   配合固定 seed，保证同一张图重复跑得到同样的编号（摘要索引才可幂等覆盖）。
4. 本模块只做「划分」，不调用大模型、不写任何存储。
"""
import uuid

import networkx as nx

from graph_fun_tool import user_connect_space
from operators.common.log import logger

# Louvain 随机种子：固定以保证社区编号可复现
LOUVAIN_SEED = 42
# 图节点上限保护：超过该规模拒绝执行（避免一次拉爆内存/超时）
MAX_VERTEX_GUARD = 20000
MAX_EDGE_GUARD = 100000


def _sv(data_obj):
    """Nebula Value 安全转字符串（null / 非 string 都不抛异常）。"""
    try:
        if data_obj.is_null():
            return ""
    except Exception:
        pass
    try:
        return data_obj.as_string()
    except Exception:
        try:
            return str(data_obj)
        except Exception:
            return ""


def _props(value_wrapper):
    """把 properties(e) 的 MAP 值转成 python dict（值为字符串）。"""
    props = {}
    try:
        if not value_wrapper.is_map():
            return props
        for k, v in value_wrapper.as_map().items():
            props[str(k)] = _sv(v)
    except Exception as e:
        logger.warning(f"关系属性解析失败，按空属性处理: {e}")
    return props


def normalize_space_name(space_name):
    """
    统一空间名口径。

    图服务内部一律使用 `g_<kb>`（graph_service.batch_insert_vertex 拼的前缀），
    而对外接口（/query_graph_data 等）历史上有两种传法，这里统一收敛：
    入参可以是 `kb_9` 也可以是 `g_kb_9`，返回 (图空间名, 知识库名)。
    """
    if not space_name:
        raise ValueError("space_name 不能为空")
    space_name = str(space_name).strip()
    if space_name.startswith("g_"):
        return space_name, space_name[2:]
    return "g_" + space_name, space_name


def load_graph(space_name):
    """
    从 Nebula 读出整张图。

    Returns:
        nodes: {实体名: {"type": str, "file_id": str, "title": str}}
        edges: [{"src","rel","dst","file_id","page_num","edge_type"}]
    """
    graph_space, kb = normalize_space_name(space_name)
    session = user_connect_space(graph_space)

    nodes = {}
    result = session.execute('MATCH (v:entity) RETURN properties(v) AS props')
    if not result.is_succeeded():
        raise RuntimeError(f"读取实体失败: {result.error_msg()}")
    for i in range(result.row_size()):
        props = _props(result.row_values(i)[0])
        name = props.get("name", "")
        if not name:
            continue
        nodes[name] = {
            "type": props.get("type", "") or "unclassified",
            "file_id": props.get("file_id", ""),
            "title": props.get("title", ""),
        }
    if len(nodes) > MAX_VERTEX_GUARD:
        raise RuntimeError(f"实体数 {len(nodes)} 超过保护上限 {MAX_VERTEX_GUARD}，请先缩小范围")

    edges = []
    for edge_schema, edge_type in (("relationship", "relation"), ("relationship_similar", "similar")):
        query = (f'MATCH (v:entity)-[e:{edge_schema}]->(v2:entity) '
                 f'RETURN v.entity.name AS src, properties(e) AS props, v2.entity.name AS dst')
        result = session.execute(query)
        if not result.is_succeeded():
            # relationship_similar 等 schema 可能不存在，视为该类边为空，不影响主流程
            logger.warning(f"读取边 {edge_schema} 失败（按无此类边处理）: {result.error_msg()}")
            continue
        for i in range(result.row_size()):
            row = result.row_values(i)
            src, dst, props = _sv(row[0]), _sv(row[2]), _props(row[1])
            if not src or not dst or src == dst:
                continue
            edges.append({
                "src": src,
                "rel": props.get("name", "") or "相似",
                "dst": dst,
                "file_id": props.get("file_id", ""),
                "page_num": props.get("page_num", ""),
                "show_flag": props.get("show_flag", "1"),
                "edge_type": edge_type,
            })
    if len(edges) > MAX_EDGE_GUARD:
        raise RuntimeError(f"边数 {len(edges)} 超过保护上限 {MAX_EDGE_GUARD}，请先缩小范围")
    logger.info(f"图 {graph_space} 读取完成：实体 {len(nodes)} 个，边记录 {len(edges)} 条")
    return nodes, edges


def build_graph(nodes, edges):
    """
    构无向图。双向边去重（同一条三元组的 show_flag=1/0 只保留一条），
    边权 = 该实体对之间出现过的不同关系条数（同关系重复出现只算一次，避免抽取次数影响划分）。
    """
    graph = nx.Graph()
    for name in nodes:
        graph.add_node(name)
    seen = set()
    for edge in edges:
        src, dst = edge["src"], edge["dst"]
        if src not in graph or dst not in graph:
            # 理论上不会发生（MATCH 限定 :entity），出现则说明图里有脏边，跳过并记录
            logger.debug(f"跳过孤立边 {src}->{dst}（端点不在实体集合内）")
            continue
        key = (min(src, dst), max(src, dst), edge["rel"])
        if key in seen:
            continue
        seen.add(key)
        if graph.has_edge(src, dst):
            graph[src][dst]["weight"] += 1
            graph[src][dst]["relations"].append(edge["rel"])
        else:
            graph.add_edge(src, dst, weight=1, relations=[edge["rel"]])
    logger.info(f"构图完成：节点 {graph.number_of_nodes()}，无向边 {graph.number_of_edges()}（去重前边记录 {len(edges)}）")
    return graph


def _community_edge_count(members, graph):
    """社区内部无向边数。"""
    member_set = set(members)
    return graph.subgraph(member_set).number_of_edges()


def _sort_communities(communities):
    """确定性排序：规模降序，规模相同按最小成员名升序。"""
    return sorted((sorted(c) for c in communities), key=lambda m: (-len(m), m[0] if m else ""))


def _level0_communities(graph, resolution):
    """实体级 Louvain 划分。孤立节点会各自成 1 个社区。"""
    raw = nx.community.louvain_communities(graph, resolution=resolution, seed=LOUVAIN_SEED, weight="weight")
    return _sort_communities(raw)


def _super_graph(level0_list, graph):
    """
    用 level0 社区当超节点，社区间边数当权重，构造超图（level1 划分的输入）。
    """
    super_graph = nx.Graph()
    for idx, members in enumerate(level0_list):
        super_graph.add_node(idx)
    node_to_comm = {}
    for idx, members in enumerate(level0_list):
        for name in members:
            node_to_comm[name] = idx
    for u, v, data in graph.edges(data=True):
        cu, cv = node_to_comm.get(u), node_to_comm.get(v)
        if cu is None or cv is None or cu == cv:
            continue
        if super_graph.has_edge(cu, cv):
            super_graph[cu][cv]["weight"] += data.get("weight", 1)
        else:
            super_graph.add_edge(cu, cv, weight=data.get("weight", 1))
    return super_graph


def detect_communities(space_name, max_level=1, min_community_size=3, resolution=1.0):
    """
    社区检测入口。

    Args:
        space_name: 知识库名（kb_9）或图空间名（g_kb_9）
        max_level: 0 = 只做实体级；1 = 额外做社区超节点级（默认）
        min_community_size: 最小社区规模，小于该值的社区被丢弃（默认 3）
        resolution: Louvain 分辨率，越大社区越碎（默认 1.0）
    Returns:
        {
          "graph_space": str, "kb": str,
          "stats": {...},
          "communities": [{community_id, level, members, size, edge_count,
                           parent_id, member_types, file_ids}],
          "edges": [...],          # 原始边记录，供摘要模块复用
          "nodes": {name: info},   # 节点属性，供摘要模块复用
        }
    """
    graph_space, kb = normalize_space_name(space_name)
    max_level = int(max_level)
    min_community_size = max(1, int(min_community_size))
    resolution = float(resolution) if resolution else 1.0

    nodes, edges = load_graph(graph_space)
    if not nodes:
        raise RuntimeError(f"图空间 {graph_space} 没有实体，无法做社区检测")
    graph = build_graph(nodes, edges)

    level0_list = _level0_communities(graph, resolution)
    communities = []

    def _pack(idx, members, level, parent_id=None):
        member_set = set(members)
        types = {}
        file_ids = []
        for name in members:
            info = nodes.get(name, {})
            t = info.get("type") or "unclassified"
            types[t] = types.get(t, 0) + 1
            fid = info.get("file_id")
            if fid and fid not in file_ids:
                file_ids.append(fid)
        return {
            "community_id": f"L{level}C{idx:03d}",
            "level": level,
            "members": members,
            "size": len(members),
            "edge_count": _community_edge_count(member_set, graph),
            "parent_id": parent_id,
            "member_types": types,
            "file_ids": file_ids,
        }

    # ---- level 0 ----
    level0_packed = []
    for idx, members in enumerate(level0_list):
        packed = _pack(idx, members, 0)
        level0_packed.append(packed)
        if packed["size"] >= min_community_size:
            communities.append(packed)

    # ---- level 1 ----
    parent_of = {}
    if max_level >= 1 and len(level0_list) > 1:
        super_graph = _super_graph(level0_list, graph)
        raw_l1 = nx.community.louvain_communities(super_graph, resolution=resolution,
                                                  seed=LOUVAIN_SEED, weight="weight")
        # 超节点编号 → 实体成员
        l1_groups = []
        for group in raw_l1:
            members = []
            for super_idx in sorted(group):
                members.extend(level0_list[super_idx])
            l1_groups.append(sorted(members))
        for idx, members in enumerate(_sort_communities(l1_groups)):
            packed = _pack(idx, members, 1)
            children = [c["community_id"] for c in level0_packed if set(c["members"]).issubset(set(members))]
            packed["children"] = children
            for child in children:
                parent_of[child] = packed["community_id"]
            if packed["size"] >= min_community_size:
                communities.append(packed)

    for c in communities:
        if c["level"] == 0:
            c["parent_id"] = parent_of.get(c["community_id"])

    dropped = [c["community_id"] for c in level0_packed if c["size"] < min_community_size]
    stats = {
        "vertex_count": len(nodes),
        "edge_record_count": len(edges),
        "undirected_edge_count": graph.number_of_edges(),
        "level0_count": len(level0_list),
        "level0_dropped_below_min_size": len(dropped),
        "community_count": len(communities),
        "min_community_size": min_community_size,
        "resolution": resolution,
        "max_level": max_level,
        "seed": LOUVAIN_SEED,
        "modularity_level0": round(nx.community.modularity(graph, [set(c) for c in level0_list]), 6)
        if graph.number_of_edges() > 0 else 0.0,
    }
    logger.info(f"社区检测完成：level0 {len(level0_list)} 个，"
                f"保留(>= {min_community_size}) {len(communities)} 个，丢弃 {len(dropped)} 个；"
                f"模度 {stats['modularity_level0']}")
    return {
        "graph_space": graph_space,
        "kb": kb,
        "stats": stats,
        "communities": communities,
        "edges": edges,
        "nodes": nodes,
    }


def community_triples(community, edges):
    """
    取社区内部的三元组（两端都在社区内），按 (src, rel, dst) 去重。
    只保留一条方向（show_flag=1 优先），避免双向边重复。
    """
    members = set(community["members"])
    seen = set()
    triples = []
    for edge in edges:
        if edge["src"] not in members or edge["dst"] not in members:
            continue
        key = (edge["src"], edge["rel"], edge["dst"])
        rev = (edge["dst"], edge["rel"], edge["src"])
        if key in seen or rev in seen:
            continue
        seen.add(key)
        triples.append({"src": edge["src"], "rel": edge["rel"], "dst": edge["dst"],
                        "file_id": edge["file_id"]})
    return triples


def community_bridge_triples(community, edges, limit=10):
    """社区对外连边（一端在社区内、一端在社区外），用于摘要里交代社区的上下游关系。"""
    members = set(community["members"])
    seen = set()
    bridges = []
    for edge in edges:
        inside_src = edge["src"] in members
        inside_dst = edge["dst"] in members
        if inside_src == inside_dst:
            continue
        key = (edge["src"], edge["rel"], edge["dst"])
        if key in seen:
            continue
        seen.add(key)
        bridges.append({"src": edge["src"], "rel": edge["rel"], "dst": edge["dst"]})
        if len(bridges) >= limit:
            break
    return bridges


def stable_pk(*parts):
    """由 (kb, level, community_id) 生成稳定的 63 位正整数主键（幂等覆盖写入依赖它）。"""
    key = "|".join(str(p) for p in parts)
    return uuid.uuid5(uuid.NAMESPACE_DNS, key).int & ((1 << 63) - 1)
