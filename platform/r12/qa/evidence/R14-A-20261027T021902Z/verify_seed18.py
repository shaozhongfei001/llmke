"""R14-A-FIX-18 回归：种子去掉 document_id 后的三组断言（可直接给 TL/B 看）。

运行（必须用 parse venv，因为要 import 解析服务的 server.utils）：
  platform/r12/venvs/parse/bin/python verify_seed18.py > verify_seed18_<tag>.json

三组断言（TL 定的）：
  1. 同一文件两种 document_id 形态 -> pk 完全相同
  2. 内容改一个字符 -> 只有对应块换 pk，其余块不变
  3. ES._id == Milvus.pk 逐条成立（三索引 13 块）

修复前（种子含 document_id）预期：断言 1 FAIL、断言 2 部分 PASS、断言 3 PASS。
修复后（种子去掉 document_id）预期：三组全 PASS。
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/services/rag-alg/alg_doc_parse_service")
from server.utils import create_chunk_pk  # noqa: E402

ES = "http://127.0.0.1:19200"
IDX = ("kb_9", "table_chunks_kb_9", "table_summary_kb_9")
MV = {"kb_9": "_kb_9", "table_chunks_kb_9": "_table_chunks_kb_9",
      "table_summary_kb_9": "_table_summary_kb_9"}

TEXT = "客户授信额度为人民币5000万元，其中票据贴现占用1000万元。"


def t1_same_document_id():
    a = create_chunk_pk("kb_9", "cjEyLXJhZy9rYl85L1IxMkZJWC1wcm9kdWN0LWxv", 328, 0, TEXT)
    b = create_chunk_pk("kb_9", "cHJvZHVjdC1sb2FuKDEpLmRvY3g=", 328, 0, TEXT)
    return {"doc_id_A": a, "doc_id_B": b, "pass": a == b}


def t2_content_change():
    base = [create_chunk_pk("kb_9", "DOC", 328, i, TEXT + str(i)) for i in range(3)]
    changed = list(base)
    changed[1] = create_chunk_pk("kb_9", "DOC", 328, 1, TEXT + "1改")
    changed_ids = [i for i in range(3) if base[i] != changed[i]]
    return {"base": base, "changed": changed, "changed_blocks": changed_ids,
            "pass": changed_ids == [1]}


def t3_es_mv():
    out = {}
    ok = True
    try:
        from pymilvus import Collection, connections
    except Exception as e:  # noqa: BLE001
        return {"error": f"pymilvus missing: {e}", "pass": None}
    connections.connect(alias="v", host="127.0.0.1", port="19630", db_name="rag_knowledge_base")
    for idx in IDX:
        body = {"size": 200, "_source": ["metadata.pk"]}
        req = urllib.request.Request(f"{ES}/{idx}/_search", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        es_ids = {h["_id"] for h in json.load(urllib.request.urlopen(req))["hits"]["hits"]}
        coll = Collection(MV[idx], using="v")
        coll.load()
        mv = {str(r["pk"]) for r in coll.query(expr="pk>=0", output_fields=["pk"], limit=500)}
        row = {"es": len(es_ids), "mv": len(mv), "inter": len(es_ids & mv),
               "es_only": sorted(es_ids - mv), "mv_only": sorted(mv - es_ids)}
        row["pass"] = es_ids == mv
        ok = ok and row["pass"]
        out[idx] = row
    connections.disconnect("v")
    out["pass"] = ok
    return out


def main():
    res = {"test1_same_doc_id": t1_same_document_id(),
           "test2_content_change": t2_content_change(),
           "test3_es_mv": t3_es_mv()}
    flags = [res["test1_same_doc_id"]["pass"], res["test2_content_change"]["pass"],
             res["test3_es_mv"].get("pass")]
    res["verdict"] = {"pass": all(f is True for f in flags),
                      "seed_still_has_document_id": res["test1_same_doc_id"]["pass"] is False}
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
