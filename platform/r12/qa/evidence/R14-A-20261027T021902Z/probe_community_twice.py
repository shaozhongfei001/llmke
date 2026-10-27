"""R14-A：社区摘要幂等验证——连续两次 /generate_community，要求 ES 与 Milvus 的 community_id 集合逐项相同。

- ES: community_summary_<kb>（metadata.community_id，_id 应为派生值）
- Milvus: graph_base._community_summary_<kb>（schema 无 community_id 列，逻辑身份落在 chunk_doc_id）

用法：platform/r12/venvs/alg/bin/python probe_community_twice.py [kb] [tag]
输出：community_twice_<tag>.json
"""
import json
import sys
import time

import requests
from pymilvus import Collection, connections

KB = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
TAG = sys.argv[2] if len(sys.argv) > 2 else "after"
GRAPH = "http://127.0.0.1:19529"
ES = "http://127.0.0.1:19200"
MV = ("127.0.0.1", "19630")
MV_DB = "graph_base"
INDEX = f"community_summary_{KB}"
COLL = f"_community_summary_{KB}"


def generate():
    body = {"space_name": KB, "max_level": 2, "min_community_size": 3, "resolution": 1.0,
            "with_summary": True,
            "model_info": {"model_id": "qwen2.5-7b-instruct",
                           "url": "http://127.0.0.1:18092/v1/chat/completions",
                           "key": "sk-r12-local"}}
    t0 = time.perf_counter()
    r = requests.post(f"{GRAPH}/generate_community", json=body, timeout=1800)
    try:
        payload = r.json()
    except Exception:  # noqa: BLE001
        payload = {"raw": r.text[:300]}
    return {"status": r.status_code, "secs": round(time.perf_counter() - t0, 1),
            "code": payload.get("code"), "msg": (payload.get("msg") or "")[:200],
            "data": {k: v for k, v in (payload.get("data") or {}).items() if k != "community_detail"}}


def es_state():
    body = {"size": 500, "_source": ["metadata.community_id", "metadata.level", "metadata.pk"]}
    r = requests.post(f"{ES}/{INDEX}/_search", json=body, timeout=30)
    hits = ((r.json() or {}).get("hits") or {}).get("hits") or []
    rows = []
    for h in hits:
        md = (h.get("_source") or {}).get("metadata") or {}
        rows.append({"community_id": md.get("community_id"), "level": md.get("level"),
                     "es_id": h.get("_id"), "meta_pk": str(md.get("pk"))})
    return {"count": len(rows), "rows": sorted(rows, key=lambda x: str(x["community_id"])),
            "community_ids": sorted({r["community_id"] for r in rows if r["community_id"]})}


def mv_state():
    connections.connect(alias="c", host=MV[0], port=MV[1], db_name=MV_DB)
    out = {}
    try:
        coll = Collection(COLL, using="c")
        coll.load()
        rows = coll.query(expr="pk >= 0", output_fields=["pk", "chunk_doc_id", "knowledge_base_name"], limit=16384)
        out = {"visible_rows": len(rows), "distinct_pk": len({r["pk"] for r in rows}),
               "pks": sorted(str(r["pk"]) for r in rows),
               "community_ids": sorted({str(r.get("chunk_doc_id")) for r in rows if str(r.get("chunk_doc_id") or "")}),
               "kb_names": sorted({str(r.get("knowledge_base_name")) for r in rows})}
    except Exception as e:  # noqa: BLE001
        out = {"error": f"{type(e).__name__}: {e}"}
    connections.disconnect("c")
    return out


def main():
    res = {"tag": TAG, "kb": KB, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    res["run1_generate"] = generate()
    time.sleep(2)
    res["run1"] = {"es": es_state(), "milvus": mv_state()}
    res["run2_generate"] = generate()
    time.sleep(2)
    res["run2"] = {"es": es_state(), "milvus": mv_state()}
    print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
