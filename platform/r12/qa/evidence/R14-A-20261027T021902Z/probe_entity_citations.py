"""R14-A：实体/三元组的「引用明细」快照（给 M1 归并前后对照用）。

回答的问题（不是只数实体）：
- 归并后哪个实体的 chunk_pk_list 变短了（= 引用被吸收/丢失）？
- 哪些实体 chunk_pk_list 为空（= 无法精确回填，只能走 entity_content 兜底）？
- 归并是"并集吸收"还是"覆盖"：多写法实体的引用条数是否 >= 归并前各写法之和？

只读；不写任何存储。

用法：
    platform/r12/venvs/alg/bin/python probe_entity_citations.py kb_9 > kb_9_entities.json
    # 副本对照：
    platform/r12/venvs/alg/bin/python probe_entity_citations.py kb_9_copy > kb_9_copy_entities.json
"""
import json
import sys

from pymilvus import Collection, connections, utility

KB = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
MV = ("127.0.0.1", "19630")
MV_DB = "graph_base"


def dump(collection, fields):
    coll = Collection(collection, using="e")   # 注意：using 要传连接别名，不是库名
    coll.load()
    rows = coll.query(expr="pk >= 0", output_fields=fields, limit=16384)
    out = []
    for r in rows:
        item = {"pk": str(r.get("pk"))}
        for f in fields:
            v = r.get(f)
            if f in ("chunk_pk_list", "file_id", "labels", "type"):
                v = [str(x) for x in (v or [])]
            item[f] = v
        out.append(item)
    return out


def main():
    connections.connect(alias="e", host=MV[0], port=MV[1], db_name=MV_DB)
    res = {"kb": KB, "entity_collection": f"_graph_entity_{KB}", "triple_collection": f"_graph_triples_{KB}"}
    ent_name, tri_name = res["entity_collection"], res["triple_collection"]

    if utility.has_collection(ent_name, using="e"):
        ents = dump(ent_name, ["text", "entity_type", "type", "chunk_pk_list", "file_id", "title", "folder_id"])
        no_ref = [e for e in ents if not e["chunk_pk_list"]]
        # 注意：Milvus 里 entity_type 恒为 "1"（实测 53/53），不能当类型维度；类型看 type(ARRAY) 或下游 infer_type()
        hist = {}
        for e in ents:
            key = ",".join(str(x) for x in (e.get("type") or [])) or "<empty>"
            hist[key] = hist.get(key, 0) + 1
        res["entities"] = {
            "rows": len(ents),
            "with_refs": len(ents) - len(no_ref),
            "without_refs": len(no_ref),
            "ref_len_distribution": _dist([len(e["chunk_pk_list"]) for e in ents]),
            "type_histogram_from_type_array": dict(sorted(hist.items(), key=lambda kv: -kv[1])),
            "entity_type_raw_values": sorted({str(e.get("entity_type")) for e in ents}),
            "entities_without_refs": sorted(e["text"] for e in no_ref)[:50],
            # 明细（供归并前后逐实体比对；文件不大，全量带出）
            "detail": sorted(({"text": e["text"], "types": e.get("type") or [],
                               "refs": len(e["chunk_pk_list"]), "chunk_pk_list": e["chunk_pk_list"],
                               "file_ids": e["file_id"], "folder_id": e.get("folder_id")}
                              for e in ents), key=lambda x: str(x["text"])),
        }
    else:
        res["entities"] = {"error": f"{ent_name} 不存在"}

    if utility.has_collection(tri_name, using="e"):
        tris = dump(tri_name, ["source_entity", "relationship", "target_entity", "chunk_pk_list", "file_id", "page_num"])
        res["triples"] = {
            "rows": len(tris),
            "without_refs": sum(1 for t in tris if not t["chunk_pk_list"]),
            "ref_len_distribution": _dist([len(t["chunk_pk_list"]) for t in tris]),
            "detail": sorted(({"s": t["source_entity"], "r": t["relationship"], "t": t["target_entity"],
                               "refs": len(t["chunk_pk_list"]), "chunk_pk_list": t["chunk_pk_list"]}
                              for t in tris), key=lambda x: f'{x["s"]}|{x["r"]}|{x["t"]}'),
        }
    else:
        res["triples"] = {"error": f"{tri_name} 不存在"}

    connections.disconnect("e")
    print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))


def _dist(nums):
    d = {}
    for n in nums:
        d[str(n)] = d.get(str(n), 0) + 1
    return dict(sorted(d.items(), key=lambda kv: int(kv[0])))


if __name__ == "__main__":
    main()
