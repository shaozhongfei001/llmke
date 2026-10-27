"""R13 GraphRAG：社区检测（Louvain）。

只做一件确定性的事：从 Nebula `g_<kb>` 读出实体关系图，用 networkx 的 Louvain 划分社区。
不生成摘要（见 graph_summary.py），不写库（见 graph_community_store.py），便于单独验证。

R14-F05：community_id 必须是**逻辑身份**，即"同一图、同一划分 → 同一 id"。
原实现用 uuid4 生成，重建一次全变，导致既无法按 community_id 去重，也无法判断
"这一条摘要是不是同一社区的上一代"。现改为由 (kb, level, 成员集合) 派生：
    同一输入 → 同一 id（可用于覆盖写/去重）
    成员集合变化 → 新 id（旧摘要会被新代替换，而不是和新代混在一起）
"""
import hashlib
import time

import networkx as nx

from graph_fun_tool import user_connect_space
from operators.common.log import logger


def community_id_for(namespace: str, level: int, members) -> str:
    """确定性社区 id：L<level>-<sha1(kb|level|排序成员)8位>。

    排序保证与 Louvain 输出的成员顺序无关；namespace 隔离不同知识库的同名实体集。
    """
    seed = "|".join([str(namespace or ""), str(level)] + sorted(str(m) for m in members))
    return f"L{level}-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:8]}"


def load_graph(space_name: str):
    """读全图：返回 nx.Graph（无向，边权恒 1）。space_name 传不带 g_ 前缀的知识库名。"""
    space = "g_" + space_name
    session = user_connect_space(space)
    if session is None:
        raise RuntimeError(f"无法连接图空间 {space}")
    query = ('MATCH (a:entity)-[e:relationship]->(b:entity) '
             'RETURN id(a) AS src, id(b) AS dst')
    result = session.execute(query)
    if not result.is_succeeded():
        raise RuntimeError(f"读图失败: {result.error_msg()}")

    g = nx.Graph()
    for i in range(result.row_size()):
        vals = result.row_values(i)
        src, dst = vals[0].as_string(), vals[1].as_string()
        if not src or not dst or src == dst:
            continue
        g.add_edge(src, dst, weight=1.0)
    logger.info(f"读图完成：节点 {g.number_of_nodes()}，边 {g.number_of_edges()}")
    return g


def detect_communities(g, resolution=1.0, min_community_size=3, max_level=1, namespace=""):
    """
    返回 [{community_id, level, members, size, edge_count}]。
    level0：对实体图做 Louvain；level1：把每个社区折叠成超节点后再做一次（层级摘要的基础）。
    namespace 参与 community_id 派生（通常传知识库名），避免跨库同名实体集撞 id。
    """
    t0 = time.time()
    communities = []
    if g.number_of_nodes() == 0:
        return communities

    parts = nx.community.louvain_communities(g, weight="weight", resolution=resolution, seed=42)

    level0 = []
    for members in parts:
        members = sorted(members)
        if len(members) < min_community_size:
            continue
        sub = g.subgraph(members)
        level0.append({
            "community_id": community_id_for(namespace, 0, members),
            "level": 0,
            "members": members,
            "size": len(members),
            "edge_count": sub.number_of_edges(),
        })
    communities.extend(level0)

    if max_level >= 1 and len(level0) >= 2:
        # 超节点图：社区之间只要有边就相连
        node_to_comm = {}
        for c in level0:
            for m in c["members"]:
                node_to_comm[m] = c["community_id"]
        super_g = nx.Graph()
        for u, v in g.edges():
            cu, cv = node_to_comm.get(u), node_to_comm.get(v)
            if cu and cv and cu != cv:
                super_g.add_edge(cu, cv, weight=1.0)
        for cu in {c["community_id"] for c in level0}:
            super_g.add_node(cu)
        for part in nx.community.louvain_communities(super_g, weight="weight", resolution=resolution, seed=42):
            if len(part) < 2:
                continue
            members = []
            for cid in part:
                members.extend(next(c["members"] for c in level0 if c["community_id"] == cid))
            communities.append({
                "community_id": community_id_for(namespace, 1, members),
                "level": 1,
                "members": sorted(members),
                "size": len(members),
                "edge_count": sum(1 for _ in super_g.subgraph(part).edges()),
            })

    logger.info(f"社区检测完成：{len(communities)} 个社区（level0={len(level0)}），耗时 {time.time()-t0:.2f}s")
    return communities


def community_triples(space_name: str, members):
    """取某社区内部的边，用于摘要事实来源（只给模型看到社区内事实，避免编造）。"""
    space = "g_" + space_name
    session = user_connect_space(space)
    member_set = set(members)
    query = ('MATCH (a:entity)-[e:relationship]->(b:entity) '
             'RETURN id(a) AS src, id(b) AS dst, properties(e) AS p')
    result = session.execute(query)
    triples, chunk_pks = [], set()
    for i in range(result.row_size()):
        vals = result.row_values(i)
        src, dst = vals[0].as_string(), vals[1].as_string()
        if src not in member_set or dst not in member_set:
            continue
        props = {}
        try:
            if vals[2].is_map():
                props = {k: (v.as_string() if v.is_string() else str(v)) for k, v in vals[2].as_map().items()}
        except Exception:
            pass
        rel = props.get("name", "")
        triples.append((src, rel, dst))
        for fid in (props.get("file_id") or "").split(","):
            if fid:
                chunk_pks.add(fid)
    return triples, sorted(chunk_pks)


def community_file_ids(space_name: str, members):
    """从成员顶点的 file_id 属性收集来源文件 id（顶点属性是逗号串），用于引用回溯原文。"""
    space = "g_" + space_name
    session = user_connect_space(space)
    ids = set()
    # 分批查，避免单条语句过长
    for i in range(0, len(members), 50):
        batch = members[i:i + 50]
        vids = ", ".join(f'"{m}"' for m in batch)
        result = session.execute(f"FETCH PROP ON entity {vids} YIELD properties(vertex).file_id AS fids")
        if not result.is_succeeded():
            continue
        for j in range(result.row_size()):
            raw = result.row_values(j)[0]
            if raw.is_string():
                for fid in raw.as_string().split(","):
                    if fid.strip():
                        ids.add(fid.strip())
    return sorted(ids)
