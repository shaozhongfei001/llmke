"""R14-A：同一份解析结果连续写入两次（duplicate_flag=True，等价于解析服务两次解析后对同一 source 的索引调用），
测量 ES / Milvus 是否翻倍、主键是否稳定。

基线采集（改代码之前跑一次即为 before；改完再跑为 after）。
使用独立 scratch 索引/集合，不碰 kb_9 / community_summary_kb_9。

用法：platform/r12/venvs/alg/bin/python probe_parse_twice.py <tag>
输出：parse_twice_<tag>.json
"""
import json
import sys
import time

import requests
from pymilvus import Collection, connections

TAG = sys.argv[1] if len(sys.argv) > 1 else "before"
KB = "r12a_idem_parse"
ES_SVC = "http://127.0.0.1:19527"
MV_SVC = "http://127.0.0.1:19526"
ES = "http://127.0.0.1:19200"
MV_DB = "graph_base"
PATH = "r12-a-idem/r12a-idem.docx"


def docs():
    out = []
    for i in range(3):
        out.append({
            "page_content": f"R14-A 幂等测试第{i}段：授信额度与票据贴现的关系说明（内容固定）。",
            "metadata": {
                "knowledge_base_name": KB,
                "document_id": "cjEyLWEtaWRlbS9yMTJhLWlkZW0uZG9jeA==",
                "file_id": 990001,
                "source": PATH,
                "title": "r12a-idem.docx",
                "parent_file_name": "r12a-idem.docx",
                "chunk_index": i,
                "offset": [[0, 30]],
                "type": "text",
            },
        })
    return out


def es_ids():
    r = requests.post(f"{ES}/{KB}/_search", json={"size": 100, "_source": ["metadata.pk", "metadata.chunk_index"]}, timeout=20)
    hits = ((r.json() or {}).get("hits") or {}).get("hits") or []
    return {"count": ((r.json() or {}).get("hits") or {}).get("total", {}).get("value"),
            "ids": sorted(h["_id"] for h in hits),
            "pks": sorted(str((h["_source"].get("metadata") or {}).get("pk")) for h in hits)}


def mv_rows():
    connections.connect(alias="q", host="127.0.0.1", port="19630", db_name=MV_DB)
    name = "_" + KB
    coll = Collection(name, using="q")
    coll.load()
    rows = coll.query(expr="pk >= 0", output_fields=["pk", "chunk_index", "source", "file_id"], limit=16384)
    raw = coll.num_entities
    connections.disconnect("q")
    return {"num_entities_raw": raw, "visible_rows": len(rows),
            "distinct_pk": len({r["pk"] for r in rows}),
            "pks": sorted(str(r["pk"]) for r in rows),
            "sources": sorted({str(r.get("source")) for r in rows})}


def es_insert():
    return requests.post(f"{ES_SVC}/insert_fulltext_documents",
                         json={"index_name": KB, "document_list": docs(), "duplicate_flag": True},
                         timeout=120).json()


def mv_insert():
    return requests.post(f"{MV_SVC}/insert_vector_documents_custom",
                         json={"db_name": MV_DB, "collection_name": KB, "document_list": docs(),
                               "duplicate_flag": True, "model_name": "bge-m3"},
                         timeout=300).json()


def main():
    res = {"tag": TAG, "kb": KB, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    # 干净起点
    requests.post(f"{ES_SVC}/del_index", json={"index_name": KB}, timeout=60)
    requests.delete(f"{ES}/{KB}", timeout=30)
    created = requests.post(f"{ES_SVC}/create_es_index", json={"index_name": KB}, timeout=60).json()
    res["create_index"] = created
    res["run1_es_insert"] = es_insert()
    time.sleep(2)
    res["run1_es_state"] = es_ids()
    res["run1_mv_insert"] = mv_insert()
    time.sleep(3)
    res["run1_mv_state"] = mv_rows()
    res["run2_es_insert"] = es_insert()
    time.sleep(2)
    res["run2_es_state"] = es_ids()
    res["run2_mv_insert"] = mv_insert()
    time.sleep(3)
    res["run2_mv_state"] = mv_rows()
    print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
