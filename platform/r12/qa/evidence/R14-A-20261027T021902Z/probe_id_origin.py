"""R14-A：验证写入层记录的 metadata.id_origin（4 类取值），供图/审计侧判定 provenance。

用法：platform/r12/venvs/alg/bin/python probe_id_origin.py
"""
import json
import time

import requests

ES_SVC = "http://127.0.0.1:19527"
ES = "http://127.0.0.1:19200"
IDX = "r12a_id_origin"


def doc(page, meta):
    return {"page_content": page, "metadata": meta}


def main():
    requests.delete(f"{ES}/{IDX}", timeout=30)
    requests.post(f"{ES_SVC}/create_es_index", json={"index_name": IDX}, timeout=60)
    base = {"document_id": "cjEyLWEtaWRlbS9pZC1vcmlnaW4uZG9jeA==", "file_id": 990009,
            "source": "r12-a-idem/id-origin.docx", "title": "id-origin.docx", "type": "text",
            "knowledge_base_name": IDX}
    cases = [
        ("derived_chunk_index", doc("R14-A id_origin 用例：内容寻址", {**base, "chunk_index": 0})),
        ("pk_from_caller", doc("R14-A id_origin 用例：调用方给 pk", {**base, "chunk_index": 1, "pk": 123456789012345})),
        ("random", doc("R14-A id_origin 用例：缺 document/chunk_index", {"source": "r12-a-idem/x.txt",
                                                                        "title": "x.txt", "type": "text"})),
        ("derived_community", doc("R14-A id_origin 用例：社区摘要", {"community_id": "L0-deadbeef", "level": 0,
                                                                  "kb": "kb_probe", "create_time": "t"})),
    ]
    res = {"index": IDX, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "cases": []}
    for expect, d in cases:
        msg = requests.post(f"{ES_SVC}/insert_fulltext_documents",
                            json={"index_name": IDX if expect != "derived_community" else "community_summary_kb_probe",
                                  "document_list": [d], "duplicate_flag": False}, timeout=60).json().get("msg")
        res["cases"].append({"expect": expect, "msg": msg})
    time.sleep(2)
    for idx in (IDX, "community_summary_kb_probe"):
        r = requests.post(f"{ES}/{idx}/_search", json={"size": 20}, timeout=20)
        hits = ((r.json() or {}).get("hits") or {}).get("hits") or []
        for h in hits:
            md = (h.get("_source") or {}).get("metadata") or {}
            print(json.dumps({"index": idx, "_id": h["_id"], "id_origin": md.get("id_origin"),
                              "pk": str(md.get("pk")), "community_id": md.get("community_id"),
                              "chunk_index": md.get("chunk_index")}, ensure_ascii=False))
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
