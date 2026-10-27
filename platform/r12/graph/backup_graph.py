#!/usr/bin/env python3
"""kb 级图数据**只读备份**（重抽取前必跑，产出可恢复的 JSON 快照）。

背景（R14-B）：kb_9 图里的 `chunk_pk_list` 存的是"抽取时刻的 ES `_id`"，
重解析后全部悬空（图侧 10 个 pk ∩ 当前 ES _id = 0）。要修只能全量重抽取，
而重抽取会 drop 向量实体表/三元组表，并可能重建 Nebula 空间——一旦失败，
现存图（87 顶点 / 122 边、10 个 pk、社区摘要 7 条）就没有回头路。
所以先落快照，再动重建。

快照内容（全部只读拉取，不写任何库）：
  1. Nebula 顶点（id + 全部属性）
  2. Nebula 边（src/dst + 全部属性）
  3. Milvus `graph_entity_<kb>` / `graph_triples_<kb>` 全部行
  4. ES `community_summary_<kb>` 全部文档
  5. ES `<kb>` 的 chunk `_id` + file_id（用于事后判"引用是否还可回指"）
  6. manifest.json：行数、时间、服务端口、恢复步骤摘要

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/backup_graph.py kb_9
输出：platform/r12/graph/backup/<kb>-<UTC时间戳>/
"""
import json
import os
import sys
import time

import requests

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

from graph_fun_tool import user_connect_space  # noqa: E402

ES_PORT, MV_PORT, MV_DB = 19527, 19526, "graph_base"
OUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")


def _props(v):
    out = {}
    try:
        if v.is_map():
            for k, x in v.as_map().items():
                out[k] = x.as_string() if x.is_string() else str(x)
    except Exception:
        pass
    return out


def dump_nebula(kb, path):
    s = user_connect_space("g_" + kb)
    if s is None:
        raise RuntimeError(f"无法连接图空间 g_{kb}")
    verts = []
    r = s.execute("MATCH (v:entity) RETURN id(v) AS n, properties(v) AS p")
    for i in range(r.row_size()):
        vals = r.row_values(i)
        verts.append({"id": vals[0].as_string(), "props": _props(vals[1])})
    edges = []
    r = s.execute("MATCH (a:entity)-[e:relationship]->(b:entity) RETURN id(a) AS s, id(b) AS d, properties(e) AS p")
    for i in range(r.row_size()):
        vals = r.row_values(i)
        edges.append({"src": vals[0].as_string(), "dst": vals[1].as_string(), "props": _props(vals[2])})
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"vertices": verts, "edges": edges}, f, ensure_ascii=False, indent=1)
    return len(verts), len(edges)


def dump_milvus(kb, name, path):
    rows, page = [], 1
    while True:
        resp = requests.post(f"http://127.0.0.1:{MV_PORT}/get_doc_page",
                             json={"db_name": MV_DB, "collection_name": name,
                                   "page_no": page, "page_num": 500}, timeout=120)
        data = resp.json().get("data") or {}
        batch = data.get("result_data") or []
        rows.extend(batch)
        if len(batch) < 500 or page > 20:
            break
        page += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    return len(rows)


def dump_es(index, path, page_size=2000):
    resp = requests.post(f"http://127.0.0.1:{ES_PORT}/search_by_custom_param",
                         json={"index_name": [index], "page_no": 1, "page_size": page_size}, timeout=120)
    rows = ((resp.json().get("data") or {}).get("result_data")) or []
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    return len(rows)


def main():
    kb = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = os.path.join(OUT_ROOT, f"{kb}-{ts}")
    os.makedirs(out, exist_ok=True)

    nv, ne = dump_nebula(kb, os.path.join(out, "nebula.json"))
    me = dump_milvus(kb, f"graph_entity_{kb}", os.path.join(out, "milvus_entity.json"))
    mt = dump_milvus(kb, f"graph_triples_{kb}", os.path.join(out, "milvus_triples.json"))
    cs = dump_es(f"community_summary_{kb}", os.path.join(out, "es_community_summary.json"))
    ks = dump_es(kb, os.path.join(out, "es_chunks.json"))

    manifest = {
        "kb": kb, "utc": ts,
        "ports": {"es": ES_PORT, "milvus_svc": MV_PORT, "milvus_db": MV_DB, "graph": 19529},
        "counts": {"nebula_vertices": nv, "nebula_edges": ne,
                   "milvus_entity_rows": me, "milvus_triple_rows": mt,
                   "es_community_summary": cs, "es_chunks": ks},
        "restore": [
            "1) 若已 drop Nebula 空间：先 POST 19529/init_space 或 platform/r12/graph/init_space.py 重建 schema",
            "2) Nebula：按 nebula.json 的 vertices/edges 用 INSERT VERTEX/EDGE 逐条回灌（同名 vid 幂等）",
            "3) Milvus：用 /insert_vector_documents_custom 回灌 milvus_entity.json / milvus_triples.json",
            "4) ES：community_summary 用 /insert_vector_documents_custom（ES 侧入 kb 索引）回灌快照",
            "5) 回灌后跑 platform/r12/graph/m1_normalize_diff.py 与 A 的 probe_entity_citations.py 对账",
        ],
        "note": "本快照为**重抽取前**状态；重抽取后若 ref_validity 未改善，可直接据此回滚。",
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"# 备份完成 {out}")
    print(f"# Nebula 顶点 {nv} / 边 {ne}；Milvus 实体 {me} / 三元组 {mt}；"
          f"ES 社区摘要 {cs} / chunk {ks}")
    print("# 恢复步骤见 manifest.json")


if __name__ == "__main__":
    main()
