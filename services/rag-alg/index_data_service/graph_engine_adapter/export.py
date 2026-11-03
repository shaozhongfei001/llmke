"""图导出：把引擎里的节点/边落成可 diff 的文本（JSONL），供巡检、审计与跨版本对比。

为什么要自己写而不是直接 pickle 引擎对象：
- pickle 依赖 igraph 版本，换环境读不出来；
- 导出物要能进 `git diff` / 邮件 / 审计台账，必须是**稳定排序的纯文本**；
- 需要过滤（最小边权）与截断（大图），这些是导出策略，不该散在调用方。

刻意不做的：不做图数据库格式（Neo4j/GraphML）转换——当前没有消费方，
写出来无人验证，等于给自己造一个"看起来能用"的假接口。
"""

import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = "llmke.graph-engine.export.v1"


def _node_record(vertex) -> Dict[str, Any]:
    attrs = vertex.attributes() if hasattr(vertex, "attributes") else {}
    return {"id": str(vertex["name"]),
            "name": attrs.get("name") or vertex["name"],
            "content": attrs.get("content"),
            "hash_id": attrs.get("hash_id")}


def _edge_record(edge, names: List[str]) -> Dict[str, Any]:
    attrs = edge.attributes() if hasattr(edge, "attributes") else {}
    return {"source": names[edge.source], "target": names[edge.target],
            "weight": float(attrs.get("weight", 0.0) or 0.0)}


def export_graph(graph: Any, out_dir: str, *, min_weight: float = 0.0,
                 limit_nodes: Optional[int] = None) -> Dict[str, Any]:
    """导出为 `nodes.jsonl` + `edges.jsonl` + `meta.json`（每次都整目录重写）。

    - 节点按 id 排序、边按 (source, target, weight) 排序：导出物能直接 `diff`，
      否则每次顺序不同，"有没有变化"永远看不清；
    - `limit_nodes` 用于大图抽样：只保留度数最高的 N 个节点（按 id 打平顺序截断会让
      结果依赖插入顺序，跨版本不可比）；
    - 指向被截断节点的边一并丢弃，并如实报告 `dropped_edges`，不留下悬空边。
    """
    names = [str(v["name"]) for v in graph.vs]
    nodes = [_node_record(v) for v in graph.vs]
    nodes.sort(key=lambda n: n["id"])

    edges = [_edge_record(e, names) for e in graph.es]
    edges = [e for e in edges if e["weight"] >= min_weight]
    edges.sort(key=lambda e: (e["source"], e["target"], e["weight"]))

    dropped = 0
    if limit_nodes is not None and limit_nodes < len(nodes):
        degree: Dict[str, int] = {}
        for e in edges:
            degree[e["source"]] = degree.get(e["source"], 0) + 1
            degree[e["target"]] = degree.get(e["target"], 0) + 1
        keep = sorted(nodes, key=lambda n: (-degree.get(n["id"], 0), n["id"]))[:limit_nodes]
        keep_ids = {n["id"] for n in keep}
        nodes = sorted(keep, key=lambda n: n["id"])
        before = len(edges)
        edges = [e for e in edges if e["source"] in keep_ids and e["target"] in keep_ids]
        dropped = before - len(edges)

    os.makedirs(out_dir, exist_ok=True)
    nodes_path = os.path.join(out_dir, "nodes.jsonl")
    edges_path = os.path.join(out_dir, "edges.jsonl")

    def _write(path: str, rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        digest = hashlib.sha256()
        count = 0
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for row in rows:
                line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                digest.update(line.encode("utf-8"))
                fh.write(line)
                count += 1
        os.replace(tmp, path)          # 原子替换：读者不会看到写了一半的导出物
        return {"count": count, "sha256": digest.hexdigest(),
                "bytes": os.path.getsize(path)}

    meta = {"schema": SCHEMA, "nodes": _write(nodes_path, nodes),
            "edges": _write(edges_path, edges),
            "min_weight": min_weight, "limit_nodes": limit_nodes,
            "dropped_edges": dropped,
            "source_nodes": graph.vcount(), "source_edges": graph.ecount()}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    return meta


def export_facts(docs: Iterable[Dict[str, Any]], path: str) -> Dict[str, Any]:
    """导出 openie 三元组（引擎原始形式，非归一化事实）。

    保留 `chunk` 便于回溯到来源块；按 (chunk, subject, predicate, object) 排序，
    保证同一份引擎结果导出可复现。
    """
    rows: List[Dict[str, Any]] = []
    for doc in docs:
        chunk = doc.get("idx") or doc.get("passage")
        # 真实落盘字段是 `extracted_triples`；`extracted_entities` 在同一份结果里**往往是空列表**。
        # 先读错的那版导出只得到 2 条事实（全库实际 29 条），输出"成功"但内容几乎为空——
        # 这类静默残缺比报错危险。`extracted_entities` 只作为老格式兜底。
        triples = doc.get("extracted_triples")
        if triples is None:
            triples = doc.get("extracted_entities") or []
        for fact in triples:
            parts = [str(x).strip() for x in fact]
            if len(parts) < 3:
                continue
            rows.append({"chunk": chunk, "subject": parts[0],
                         "predicate": parts[1], "object": parts[2]})
    rows.sort(key=lambda r: (str(r["chunk"]), r["subject"], r["predicate"], r["object"]))

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)
    return {"schema": SCHEMA + ".facts", "facts": len(rows), "path": path}
