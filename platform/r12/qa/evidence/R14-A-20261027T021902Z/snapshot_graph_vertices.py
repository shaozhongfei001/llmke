#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只读快照：Nebula 实体顶点（id / type / file_id）+ 代次归属 + 关键探针词。

用法：
    platform/r12/venvs/graph/bin/python snapshot_graph_vertices.py <space> <out.json>

判据用途（B 的重建验收）：
  · old_only_vertices 必须为 0        -> "旧代真的没了"
  · unclassified 占比必须下降          -> "归一化确实落库了"
  · probes 里被并掉的字面 count 必须为 0

注意：本环境 `RETURN v.<prop>`（不带 tag 前缀）恒返回 NULL，
必须用 `v.entity.<prop>` 或 FETCH PROP，否则会把"属性存在"读成"属性丢了"。
"""
import json
import sys
import urllib.request

from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

ES = "http://127.0.0.1:19200"
PROBES = [
    "加30个基点", "加60个基点", "加100个基点",
    "30个基点", "60个基点", "100个基点",
    "人民币5000万元", "5000万元", "人民币1000万元", "1000万元",
    "八千万元", "8000万元",
    "额度", "万元", "已用额度", "授信额度",
]


def es_current_file_ids(kb):
    """当前 ES 里**仍存在**的 file_id 集合，用来判顶点挂在哪一代。

    必须跨三个索引查：表格类文档的 chunk 落在 table_chunks_/table_summary_，
    只在主子索引查会把台账（file_id=329）误判成"旧代"，直接把 old_only 数虚高
    （实测 59/32 vs 正确 55/36 —— 差的 4 个顶点全挂 329）。
    """
    out = set()
    for idx in (kb, f"table_chunks_{kb}", f"table_summary_{kb}"):
        body = json.dumps({"size": 200, "_source": ["metadata.file_id"]}).encode()
        req = urllib.request.Request(f"{ES}/{idx}/_search", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            hits = json.load(urllib.request.urlopen(req))["hits"]["hits"]
        except Exception:
            continue
        for h in hits:
            fid = ((h["_source"].get("metadata") or {}).get("file_id"))
            if fid is not None:
                out.add(str(fid))
    return out


def main():
    space = sys.argv[1] if len(sys.argv) > 1 else "g_kb_9"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "graph_snapshot.json"
    kb = space[2:] if space.startswith("g_") else space
    current = es_current_file_ids(kb)

    cfg = Config()
    cfg.max_connection_pool_size = 2
    pool = ConnectionPool()
    if not pool.init([("127.0.0.1", 19669)], cfg):
        raise SystemExit("nebula pool init failed")
    s = pool.get_session("root", "nebula")
    if not s.execute(f"USE {space}").is_succeeded():
        raise SystemExit(f"USE {space} failed")

    # id / type / file_id 一次取全；必须带 tag 前缀
    r = s.execute("MATCH (v:entity) RETURN id(v) AS n, v.entity.type AS t, v.entity.file_id AS f")
    if not r.is_succeeded():
        raise SystemExit(f"query failed: {r.error_msg()}")

    rows = []
    for i in range(r.row_size()):
        vals = r.row_values(i)
        name = vals[0].as_string() if vals[0].is_string() else str(vals[0])
        etype = vals[1].as_string() if vals[1].is_string() else ""
        fid = vals[2].as_string() if vals[2].is_string() else ""
        rows.append({"name": name, "type": etype, "file_id": fid})

    def gen_of(fid_str):
        ids = [x.strip() for x in (fid_str or "").split(",") if x.strip()]
        if not ids:
            return "no_file_id"
        hit = [x for x in ids if x in current]
        if len(hit) == len(ids):
            return "current_only"
        if not hit:
            return "old_only"
        return "mixed"

    for row in rows:
        row["generation"] = gen_of(row["file_id"])

    by_gen = {}
    for row in rows:
        by_gen[row["generation"]] = by_gen.get(row["generation"], 0) + 1
    by_type = {}
    for row in rows:
        by_type[row["type"] or "(empty)"] = by_type.get(row["type"] or "(empty)", 0) + 1

    r2 = s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS c")
    edges = r2.row_values(0)[0].as_int() if r2.is_succeeded() and r2.row_size() else -1

    # 边级代次：社区摘要的 file_ids = 顶点 file_id ∪ **边** file_id（graph_summary.py:397），
    # 所以只验顶点不够——边仍挂旧代时，文件级引用会继续指旧代。
    # 注意读法：边用 `e.<prop>` / `properties(e)`；写成 `e.relationship.name` 会得到 NULL
    # （与顶点相反，顶点是 `v.<prop>` 为 NULL、`v.<prop>` 必须带 tag 前缀）。
    edge_rows = []
    re_ = s.execute("MATCH (a:entity)-[e:relationship]->(b:entity) "
                    "RETURN id(a) AS s, id(b) AS t, properties(e) AS p")
    if re_.is_succeeded():
        for i in range(re_.row_size()):
            vals = re_.row_values(i)
            src = vals[0].as_string() if vals[0].is_string() else str(vals[0])
            dst = vals[1].as_string() if vals[1].is_string() else str(vals[1])
            props = {}
            if vals[2].is_map():
                for k, v in vals[2].as_map().items():
                    props[k] = v.as_string() if v.is_string() else str(v)
            edge_rows.append({"src": src, "dst": dst,
                              "rel": props.get("name", ""),
                              "file_id": props.get("file_id", "")})
    for row in edge_rows:
        row["generation"] = gen_of(row["file_id"])
    edge_gen = {}
    for row in edge_rows:
        edge_gen[row["generation"]] = edge_gen.get(row["generation"], 0) + 1
    triples = [(e["src"], e["rel"], e["dst"]) for e in edge_rows]
    dup_triples = len(triples) - len(set(triples))

    probe_hits = {}
    for p in PROBES:
        rr = s.execute(f'MATCH (v:entity) WHERE id(v)=="{p}" RETURN count(v) AS c')
        probe_hits[p] = rr.row_values(0)[0].as_int() if rr.is_succeeded() and rr.row_size() else -1

    unclassified = by_type.get("unclassified", 0)
    snapshot = {
        "space": space,
        "es_current_file_ids": sorted(current),
        "vertices": len(rows),
        "edges": edges,
        "generation_split": by_gen,
        "edge_generation_split": edge_gen,
        "duplicate_triples": dup_triples,
        "type_distribution": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "unclassified_ratio": round(unclassified / max(len(rows), 1), 4),
        "probe_existence": probe_hits,
        "rows": rows,
        "edge_rows": edge_rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=1)

    print(f"space={space} vertices={len(rows)} edges={edges}")
    print(f"generation: {by_gen}  | edge_generation: {edge_gen}  | dup_triples: {dup_triples}")
    print(f"unclassified: {unclassified}/{len(rows)} = {snapshot['unclassified_ratio']:.1%}")
    print(f"probe: {probe_hits}")
    print(f"written -> {out_path}")
    pool.close()


if __name__ == "__main__":
    main()
