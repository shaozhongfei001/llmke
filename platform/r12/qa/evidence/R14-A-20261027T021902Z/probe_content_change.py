"""R14-A：内容覆盖（同 document_id/file_id/chunk_index，正文变化）时的身份行为。

期望：
- 只有正文变化的那一块换 id（其余块 id 不变）；
- 可见行数不翻倍（旧代按 source 删除）；
- 旧 id 在 ES / Milvus 都查不到（明确失效，不会错指到新文本）。

用法：platform/r12/venvs/alg/bin/python probe_content_change.py
输出：content_change.json
"""
import json
import time

import requests
from pymilvus import Collection, connections

KB = "r12a_content_chg"
ES_SVC = "http://127.0.0.1:19527"
MV_SVC = "http://127.0.0.1:19526"
ES = "http://127.0.0.1:19200"
MV_DB = "graph_base"
PATH = "r12-a-idem/r12a-content.docx"


def docs(text0):
    out = []
    for i in range(3):
        text = text0 if i == 0 else f"R14-A 内容覆盖测试第{i}段：保持不变的内容。"
        out.append({"page_content": text,
                    "metadata": {"knowledge_base_name": KB,
                                 "document_id": "cjEyLWEtaWRlbS9yMTJhLWNvbnRlbnQuZG9jeA==",
                                 "file_id": 990003, "source": PATH, "title": "r12a-content.docx",
                                 "chunk_index": i, "offset": [[0, 30]], "type": "text"}})
    return out


def es_state():
    r = requests.post(f"{ES}/{KB}/_search", json={"size": 100}, timeout=20)
    hits = ((r.json() or {}).get("hits") or {}).get("hits") or []
    return {"count": ((r.json() or {}).get("hits") or {}).get("total", {}).get("value"),
            "pairs": sorted((str(h["_id"]), ((h["_source"].get("metadata") or {}).get("chunk_index")))
                            for h in hits)}


def mv_state():
    connections.connect(alias="cc", host="127.0.0.1", port="19630", db_name=MV_DB)
    coll = Collection("_" + KB, using="cc")
    coll.load()
    rows = coll.query(expr="pk >= 0", output_fields=["pk", "chunk_index"], limit=16384)
    connections.disconnect("cc")
    return {"count": len(rows), "pairs": sorted((str(r["pk"]), r.get("chunk_index")) for r in rows)}


def es_insert(text0):
    return requests.post(f"{ES_SVC}/insert_fulltext_documents",
                         json={"index_name": KB, "document_list": docs(text0), "duplicate_flag": True},
                         timeout=120).json().get("msg")


def mv_insert(text0):
    return requests.post(f"{MV_SVC}/insert_vector_documents_custom",
                         json={"db_name": MV_DB, "collection_name": KB, "document_list": docs(text0),
                               "duplicate_flag": True, "model_name": "bge-m3"}, timeout=300).json().get("msg")


def es_get(doc_id):
    r = requests.post(f"{ES}/{KB}/_search", json={"size": 5, "query": {"ids": {"values": [doc_id]}}}, timeout=20)
    return ((r.json() or {}).get("hits") or {}).get("hits") or []


def main():
    res = {"kb": KB, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    requests.delete(f"{ES}/{KB}", timeout=30)
    res["create"] = requests.post(f"{ES_SVC}/create_es_index", json={"index_name": KB}, timeout=60).json().get("msg")
    res["v1_es_msg"] = es_insert("R14-A 内容覆盖测试第0段：原始版本 A（授信额度 3000 万元）。")
    res["v1_mv_msg"] = mv_insert("R14-A 内容覆盖测试第0段：原始版本 A（授信额度 3000 万元）。")
    time.sleep(3)
    res["v1_es"] = es_state()
    res["v1_mv"] = mv_state()
    old_id = res["v1_es"]["pairs"][0][0] if res["v1_es"]["pairs"] else None
    old_id = next((i for i, ci in res["v1_es"]["pairs"] if ci == 0), None)

    res["v2_es_msg"] = es_insert("R14-A 内容覆盖测试第0段：改版 B（授信额度 5000 万元）。")
    res["v2_mv_msg"] = mv_insert("R14-A 内容覆盖测试第0段：改版 B（授信额度 5000 万元）。")
    time.sleep(3)
    res["v2_es"] = es_state()
    res["v2_mv"] = mv_state()
    new_id = next((i for i, ci in res["v2_es"]["pairs"] if ci == 0), None)
    res["old_id"] = old_id
    res["new_id"] = new_id
    res["chunk0_id_changed"] = bool(old_id and new_id and old_id != new_id)
    res["other_chunks_stable"] = [p for p in res["v1_es"]["pairs"] if p[1] != 0] == \
                                 [p for p in res["v2_es"]["pairs"] if p[1] != 0]
    res["old_id_visible_in_es"] = bool(es_get(old_id)) if old_id else None
    print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
