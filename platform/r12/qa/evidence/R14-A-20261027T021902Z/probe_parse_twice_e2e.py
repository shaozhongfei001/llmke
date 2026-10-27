"""R14-A：同一文件连续两次真实解析（/parse_sync）→ 检查 ES / Milvus 是否翻倍、主键是否稳定。

走真实解析服务 12340 + 真实索引写入（19527/19526），索引名用 scratch：r12a_parse_idem。
不碰 kb_9 / community_summary_kb_9。

用法：platform/r12/venvs/alg/bin/python probe_parse_twice_e2e.py <tag> [fixture] [chunk_size]
      ⚠️ 必须用 `venvs/alg`（它装了 pymilvus）；`venvs/parse` 会在 `import pymilvus` 处 ModuleNotFoundError。
输出：parse_twice_e2e_<tag>.json（stdout）
"""
import json
import sys
import time
import urllib.error
import urllib.request

TAG = sys.argv[1] if len(sys.argv) > 1 else "before"
FIXTURE = sys.argv[2] if len(sys.argv) > 2 else "fixtures/cn-docx-direct.docx"
CHUNK_SIZE = int(sys.argv[3]) if len(sys.argv) > 3 else 512
BASE = "http://127.0.0.1:12340"
ES = "http://127.0.0.1:19200"
INDEX = "r12a_parse_idem"
MV_DB = "graph_base"


def call_parse_sync(timeout=1800):
    body = {
        "knowledge_base_name": "r12a-parse-idem",
        "files": [{"file_path": f"r12-rag/{FIXTURE}", "file_id": 990002, "file_size": "1"}],
        "file_type": "naive", "chunk_size": CHUNK_SIZE, "chunk_overlap": 100,
        "length_function": "char", "need_chunk": True, "index_name": INDEX,
        "model_info": {"model_id": "qwen2.5-7b-instruct", "url": "http://127.0.0.1:18092/v1/chat/completions"},
        "embedding_model_info": {"model_id": "bge-m3", "url": "http://127.0.0.1:18090/v1/embeddings"},
        "multi_model_info": {"model_id": "qwen2.5-vl-3b-instruct", "url": "http://127.0.0.1:18093/v1/chat/completions"},
    }
    req = urllib.request.Request(BASE + "/parse_sync", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = r.read().decode("utf-8", "replace")
            return {"status": r.status, "secs": round(time.perf_counter() - t0, 1),
                    "head": payload[:300]}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "secs": round(time.perf_counter() - t0, 1),
                "head": e.read().decode("utf-8", "replace")[:300]}


def es_state(name):
    out = {"index": name}
    try:
        with urllib.request.urlopen(f"{ES}/{name}/_count", timeout=10) as r:
            out["count"] = json.load(r).get("count")
    except Exception as e:  # noqa: BLE001
        return {**out, "count": None, "error": str(e)[:120]}
    req = urllib.request.Request(f"{ES}/{name}/_search",
                                 data=json.dumps({"size": 500, "_source": ["metadata.pk", "metadata.document_id",
                                                                          "metadata.chunk_index"]}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        hits = ((json.load(r).get("hits") or {}).get("hits")) or []
    out["ids"] = sorted(h["_id"] for h in hits)
    out["chunk_index"] = sorted(int(m["chunk_index"]) if m.get("chunk_index") is not None else -1
                                for m in (((h["_source"].get("metadata")) or {}) for h in hits))
    return out


def mv_state():
    """解析服务写 Milvus 的库由 alg 侧配置决定（实测为 rag_knowledge_base），这里两个库都看，避免漏判。"""
    from pymilvus import Collection, connections, utility
    out = {}
    for db in ("rag_knowledge_base", MV_DB):
        try:
            connections.connect(alias=db, host="127.0.0.1", port="19630", db_name=db)
        except Exception as e:  # noqa: BLE001
            out[db] = {"error": f"{type(e).__name__}: {e}"}
            continue
        name = "_" + INDEX
        if not utility.has_collection(name, using=db):
            connections.disconnect(db)
            continue
        try:
            coll = Collection(name, using=db)
            coll.load()
            rows = coll.query(expr="pk >= 0", output_fields=["pk", "chunk_index", "file_id"], limit=16384)
            out[db] = {"collection": name, "visible_rows": len(rows),
                       "pks": sorted(str(r["pk"]) for r in rows),
                       "chunk_index": sorted(int(r["chunk_index"]) if r.get("chunk_index") is not None else -1 for r in rows)}
        except Exception as e:  # noqa: BLE001
            out[db] = {"error": f"{type(e).__name__}: {e}"}
        connections.disconnect(db)
    return out


def main():
    res = {"tag": TAG, "index": INDEX, "fixture": FIXTURE, "chunk_size": CHUNK_SIZE, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    res["run1_parse"] = call_parse_sync()
    time.sleep(3)
    res["run1_es"] = {n: es_state(n) for n in (INDEX, f"table_chunks_{INDEX}", f"table_summary_{INDEX}")}
    res["run1_mv"] = mv_state()
    res["run2_parse"] = call_parse_sync()
    time.sleep(3)
    res["run2_es"] = {n: es_state(n) for n in (INDEX, f"table_chunks_{INDEX}", f"table_summary_{INDEX}")}
    res["run2_mv"] = mv_state()
    print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
