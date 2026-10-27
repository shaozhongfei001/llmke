"""R14-A：给某个 kb 出一份「引用对账基线」快照。

用途：B-graph 做开/关图对照时，需要"这批 chunk 的稳定身份集合"作为比对对象；
本脚本输出**稳定键（pk）集合**与 **id_origin 分布**，不输出 order_num（每请求随机，不可对账）。

只读；不写任何存储。

用法：
    platform/r12/venvs/alg/bin/python probe_kb_snapshot.py kb_9 > kb_9_snapshot.json
"""
import json
import sys

import requests

ES = "http://127.0.0.1:19200"
MILVUS = ("127.0.0.1", "19630")
KB = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
INDEXES = [KB, f"table_chunks_{KB}", f"table_summary_{KB}", f"community_summary_{KB}"]
MV_DBS = ["rag_knowledge_base", "graph_base"]


def es_snapshot(index):
    out = {"index": index}
    try:
        cnt = requests.get(f"{ES}/{index}/_count", timeout=10)
        out["es_count"] = (cnt.json() or {}).get("count") if cnt.status_code == 200 else None
    except Exception as e:  # noqa: BLE001
        return {**out, "error": str(e)[:120]}
    if out.get("es_count") is None:
        return out
    body = {"size": 0, "aggs": {"o": {"terms": {"field": "metadata.id_origin.keyword",
                                                "missing": "__MISSING__"}}}}
    agg = requests.post(f"{ES}/{index}/_search", json=body, timeout=20)
    out["id_origin"] = {b["key"]: b["doc_count"]
                        for b in (((agg.json() or {}).get("aggregations") or {}).get("o") or {}).get("buckets", [])}
    hits_body = {"size": 2000, "_source": ["metadata.document_id", "metadata.chunk_index"]}
    hits = requests.post(f"{ES}/{index}/_search", json=hits_body, timeout=30)
    rows = ((hits.json() or {}).get("hits") or {}).get("hits") or []
    out["pk_list"] = sorted(h["_id"] for h in rows)
    out["chunk_refs"] = sorted(
        f'{((h["_source"].get("metadata") or {}).get("document_id"))}#{(h["_source"].get("metadata") or {}).get("chunk_index")}'
        for h in rows)
    return out


def milvus_snapshot():
    from pymilvus import Collection, connections, utility
    out = {}
    for db in MV_DBS:
        try:
            connections.connect(alias=db, host=MILVUS[0], port=MILVUS[1], db_name=db)
        except Exception as e:  # noqa: BLE001
            out[db] = {"error": str(e)[:120]}
            continue
        coll_name = "_" + KB
        if not utility.has_collection(coll_name, using=db):
            connections.disconnect(db)
            continue
        try:
            coll = Collection(coll_name, using=db)
            coll.load()
            rows = coll.query(expr="pk >= 0", output_fields=["pk"], limit=16384)
            out[db] = {"collection": coll_name, "visible_rows": len(rows),
                       "pk_list": sorted(str(r["pk"]) for r in rows)}
        except Exception as e:  # noqa: BLE001
            out[db] = {"error": str(e)[:120]}
        connections.disconnect(db)
    return out


def main():
    res = {"kb": KB, "es": [es_snapshot(i) for i in INDEXES], "milvus": milvus_snapshot()}
    print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
