#!/usr/bin/env python3
"""R13 图谱一致性检查：Nebula 实体 ↔ Milvus 实体向量。

背景（源码事实）：
  - 图写入同时落 Nebula（`g_<kb>`）与 Milvus（`graph_base` 库下 `graph_entity_<kb>` / `graph_triples_<kb>`）；
  - `del_space_data`（graph_service.py:163-191）只 DROP/DELETE Nebula，**不删 Milvus 集合**；
  - 实体链接（graph_service.py:574）与 ppr_flag（:592）都依赖 Milvus，悬空实体向量会导致
    "图里没有、但检索命中了"的隐性问题。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/consistency_check.py kb_9 [--fix]
  --fix 只删除"Milvus 有、Nebula 没有"的悬空实体向量（安全方向），不会反向补图。
"""
import json
import sys
import urllib.request

from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

VECTOR_API = "http://127.0.0.1:19526"
GRAPH_DB = "graph_base"


def post(url, payload, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def nebula_entities(space):
    cfg = Config()
    pool = ConnectionPool()
    pool.init([("127.0.0.1", 19669)], cfg)
    s = pool.get_session("root", "nebula")
    if not s.execute(f"USE {space}").is_succeeded():
        return None
    r = s.execute("MATCH (v:entity) RETURN id(v) AS n")
    return {r.row_values(i)[0].as_string() for i in range(r.row_size())}


def milvus_entities(kb):
    coll = f"graph_entity_{kb}"
    try:
        data = post(f"{VECTOR_API}/get_doc_by_col",
                    {"db_name": GRAPH_DB, "collection_name": coll, "col_name": "", "col_values": []})
    except Exception as ex:
        print(f"  查询 {coll} 失败：{ex}")
        return None
    rows = (data.get("data") or {}).get("result_data") or []
    return {r.get("page_content") for r in rows if r.get("page_content")}


def main():
    if len(sys.argv) < 2:
        print("用法: consistency_check.py <kb> [--fix]")
        return 2
    kb = sys.argv[1]
    fix = "--fix" in sys.argv
    space = f"g_{kb}"

    nv = nebula_entities(space)
    if nv is None:
        print(f"Nebula 空间 {space} 不存在")
        return 1
    mv = milvus_entities(kb)
    if mv is None:
        print("Milvus 集合不可查，跳过")
        return 1

    only_nebula = sorted(nv - mv)
    only_milvus = sorted(mv - nv)
    print(f"空间 {space}: Nebula 实体 {len(nv)}；Milvus 实体 {len(mv)}")
    print(f"  仅 Nebula 有（图有向量缺，影响实体链接召回）：{len(only_nebula)}")
    for n in only_nebula[:10]:
        print("    -", n)
    print(f"  仅 Milvus 有（悬空向量，图已删但向量残留）：{len(only_milvus)}")
    for n in only_milvus[:10]:
        print("    +", n)

    if fix and only_milvus:
        # 删除悬空实体向量：按 text 精确匹配
        removed = 0
        for n in only_milvus:
            try:
                r = post(f"{VECTOR_API}/del_doc_by_col",
                         {"db_name": GRAPH_DB, "collection_name": f"graph_entity_{kb}",
                          "col_name": "text", "col_values": [n]})
                if (r.get("code") or 200) == 200:
                    removed += 1
            except Exception as ex:
                print("    删除失败", n, ex)
        print(f"  已删除悬空向量 {removed} 条")
        mv = milvus_entities(kb) or set()
        only_milvus = sorted(mv - nv)
        print(f"  复核：剩余悬空 {len(only_milvus)} 条")

    return 0 if not only_milvus and not only_nebula else 0


if __name__ == "__main__":
    sys.exit(main())
