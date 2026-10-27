"""R14-A 运行态探针：community_summary_<kb> 在 Milvus / ES 两侧的 schema 与可见行。

只读，不写任何存储。
用法：platform/r12/venvs/alg/bin/python probe_community_state.py [kb]
"""
import json
import sys

import requests
from pymilvus import Collection, connections

KB = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
MV_DB = "graph_base"
MV = ("127.0.0.1", "19630")
ES = "http://127.0.0.1:19200"


def milvus_probe(name):
    connections.connect(alias="p", host=MV[0], port=MV[1], db_name=MV_DB)
    out = {"collection": name}
    # 写入侧 generate_collection_name_uuid() 会给集合名加前导下划线
    cand = [name, "_" + name.replace("-", "_")]
    coll = None
    for c in cand:
        try:
            coll = Collection(c, using="p")
            out["resolved_name"] = c
            break
        except Exception as e:  # noqa: BLE001
            out.setdefault("tried", []).append(f"{c}: {type(e).__name__}")
    if coll is None:
        out["error"] = "collection not found"
        connections.disconnect("p")
        return out
    pk = None
    for f in coll.schema.fields:
        if f.is_primary:
            pk = f
    out["pk_field"] = {"name": pk.name, "dtype": str(pk.dtype), "auto_id": bool(pk.auto_id)} if pk else None
    out["fields"] = [f.name for f in coll.schema.fields]
    out["num_entities_raw"] = coll.num_entities
    coll.load()
    rows = coll.query(expr="pk >= 0", output_fields=["pk"], limit=16384)
    out["visible_rows"] = len(rows)
    out["distinct_pk"] = len({r["pk"] for r in rows})
    # community_id 是否可检索（当前 schema 没有该列时此处会报错，错误原样记录）
    for probe_field in ("community_id", "chunk_doc_id", "source", "knowledge_base_name", "create_time"):
        if probe_field in out["fields"]:
            try:
                r2 = coll.query(expr="pk >= 0", output_fields=[probe_field], limit=16384)
                vals = [str(x.get(probe_field)) for x in r2]
                out[f"values_{probe_field}"] = sorted(set(vals))
            except Exception as e:  # noqa: BLE001
                out[f"values_{probe_field}_error"] = f"{type(e).__name__}: {e}"
    connections.disconnect("p")
    return out


def es_probe(name):
    out = {"index": name}
    try:
        r = requests.get(f"{ES}/{name}/_count", timeout=10)
        out["count_status"] = r.status_code
        out["docs_count"] = (r.json() or {}).get("count") if r.status_code == 200 else None
    except Exception as e:  # noqa: BLE001
        out["count_error"] = f"{type(e).__name__}: {e}"
    try:
        body = {"size": 500, "_source": ["metadata.community_id", "metadata.level", "metadata.pk",
                                         "metadata.file_ids", "metadata.create_time"]}
        r = requests.post(f"{ES}/{name}/_search", json=body, timeout=30)
        out["search_status"] = r.status_code
        hits = ((r.json() or {}).get("hits") or {}).get("hits") or []
        out["hits"] = len(hits)
        ids, ids_pk = [], []
        for h in hits:
            md = (h.get("_source") or {}).get("metadata") or {}
            ids.append(md.get("community_id"))
            ids_pk.append({"id": md.get("community_id"), "_id": h.get("_id"), "meta_pk": md.get("pk")})
        out["community_ids"] = sorted([x for x in ids if x])
        out["id_pairs"] = sorted(ids_pk, key=lambda x: str(x["id"]))
    except Exception as e:  # noqa: BLE001
        out["search_error"] = f"{type(e).__name__}: {e}"
    return out


def main():
    name = f"community_summary_{KB}"
    print(json.dumps({"milvus": milvus_probe(name), "es": es_probe(name)},
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
