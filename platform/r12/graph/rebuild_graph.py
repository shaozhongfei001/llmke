#!/usr/bin/env python3
"""R13 图数据回填：kb 级重建 Milvus 图向量 + 重新抽取（修 "图体检 200 但正文全空"）。

问题（源码事实 + 实测，见 platform/r12/graph/LOCAL-RETRIEVAL.md）：
  - 图实体/三元组里的 `chunk_pk_list` 存的是"抽取时刻 ES 文档 `_id`"
    （graph_fun_tool.get_document_chunk 用 `ed["_id"]` 当 pk）；
  - 知识库文本块入库 Milvus 时 pk 与 ES `_id` 同源，所以正常情况下可以直接用 Milvus pk 回取正文；
  - 但知识库"重新解析"会生成新的 `_id`，图数据里的旧 id 在 ES/Milvus 都已不存在 →
    POST 19529/query_graph_data 返回 200 但 result_data 为空（正文取不到）。
  - 增量抽取（Java POST /index/knowledgeBase/file/graphParse）只做 merge（append chunk id），
    没有清理旧 id 的路径，悬空引用会一直累积。

本脚本做的事：
  1) 默认 drop graph_base 库下 `graph_entity_<kb>` / `graph_triples_<kb>`，把悬空 chunk 引用一次性清掉；
  2) 调 19529/generate_triple_data 按当前 ES 文档全量重抽（space_name=<kb>，不带 col_name/col_values）；
  3) 打印 Nebula 顶点/边数、Milvus 两表行数，并跑一次 query_graph_data 自检。

Nebula 侧不 DROP：顶点 vid 就是实体名，重抽时同名顶点/边只会报"已存在"并被收集到错误列表，
不影响查询。若要连图一起重建，先 `POST 19529/del_space {"space_name":"<kb>"}` 再跑本脚本。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/rebuild_graph.py kb_9
  ... --no-drop        # 不 drop Milvus 集合（走增量 merge）
  ... --skip-extract   # 只做计数与自检
  ... --probe "智造贷"  # 自检用的问题（默认"智造贷"）
"""
import argparse
import json
import sys
import time
import urllib.request

GRAPH_API = "http://127.0.0.1:19529"
VECTOR_API = "http://127.0.0.1:19526"
GRAPH_DB = "graph_base"
MODEL_INFO = {
    "model_id": "qwen2.5-7b-instruct",
    "url": "http://127.0.0.1:18092/v1/chat/completions",
    "key": "sk-r12-local",
}


def post(url, payload, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def milvus_visible(collection):
    """集合可见行数（/get_doc_page 的 total_count）。

    注意不能用 /static_count 判"有没有写进去"：它走 Milvus `num_entities`，只统计已 flush 的段，
    刚 insert 完会稳定返回 0（本次实测 46 行数据、static_count=0），flush 后才对齐。
    """
    try:
        page = post(f"{VECTOR_API}/get_doc_page",
                    {"db_name": GRAPH_DB, "collection_name": collection,
                     "page_no": 1, "page_num": 1000})
        data = page.get("data") or {}
        visible = data.get("total_count")
        if visible is None:
            visible = len(data.get("result_data") or [])
        return int(visible or 0)
    except Exception:
        return None


def milvus_count(collection):
    visible = milvus_visible(collection)
    try:
        static = (post(f"{VECTOR_API}/static_count",
                       {"db_name": GRAPH_DB, "collection_name": collection}).get("data") or {}).get("count")
    except Exception as ex:
        static = f"ERR {ex}"
    return f"visible={visible}(num_entities={static})"


def drop_milvus_collection(collection):
    """del_doc_entity 在 update_condition_json 为空时直接 drop 集合（向量服务既有语义）。"""
    try:
        r = post(f"{VECTOR_API}/del_doc_entity",
                 {"db_name": GRAPH_DB, "index_name": collection, "update_condition_json": {}})
        print(f"  drop {collection}: {r.get('code')} {r.get('msg')}")
    except Exception as ex:
        print(f"  drop {collection} 失败: {ex}")


def nebula_counts(space):
    """返回 (顶点数, 边数)；空间不存在时返回 (None, None)。"""
    from nebula3.Config import Config
    from nebula3.gclient.net import ConnectionPool

    cfg = Config()
    pool = ConnectionPool()
    if not pool.init([("127.0.0.1", 19669)], cfg):
        return None, None
    s = pool.get_session("root", "nebula")
    try:
        if not s.execute(f"USE `{space}`").is_succeeded():
            return None, None
        v = s.execute("MATCH (v:entity) RETURN count(v) AS c")
        e = s.execute("MATCH ()-[e:relationship]->() RETURN count(e) AS c")
        return v.row_values(0)[0].as_int(), e.row_values(0)[0].as_int()
    finally:
        pool.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kb")
    ap.add_argument("--no-drop", action="store_true")
    ap.add_argument("--skip-extract", action="store_true")
    ap.add_argument("--probe", default="智造贷")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    kb = args.kb
    space = f"g_{kb}"
    ent_coll = f"graph_entity_{kb}"
    tri_coll = f"graph_triples_{kb}"

    v0, e0 = nebula_counts(space)
    print(f"[before] nebula {space}: vertices={v0} edges={e0} | "
          f"{ent_coll}={milvus_count(ent_coll)} {tri_coll}={milvus_count(tri_coll)}")

    if not args.no_drop and not args.skip_extract:
        print("[1/3] drop Milvus 图向量集合（清掉悬空 chunk 引用）")
        drop_milvus_collection(ent_coll)
        drop_milvus_collection(tri_coll)

    if not args.skip_extract:
        print(f"[2/3] 调 {GRAPH_API}/generate_triple_data 全量重抽 {kb}")
        resp = post(f"{GRAPH_API}/generate_triple_data",
                    {"space_name": kb, "model_info": MODEL_INFO}, timeout=args.timeout)
        print("  resp:", json.dumps(resp, ensure_ascii=False)[:800])
        if resp.get("code") != 200:
            print("  !! 抽取失败，终止")
            return 1

    v1, e1 = nebula_counts(space)
    if not args.skip_extract:
        for _ in range(6):
            if (milvus_visible(ent_coll) or 0) > 0:
                break
            time.sleep(5)
    c_ent, c_tri = milvus_count(ent_coll), milvus_count(tri_coll)
    print(f"[after] nebula {space}: vertices={v1} edges={e1} | "
          f"{ent_coll}={c_ent} {tri_coll}={c_tri}")

    print(f"[3/3] 自检 query_graph_data(query={args.probe})")
    q = post(f"{GRAPH_API}/query_graph_data",
             {"query": args.probe, "space_name": kb, "top_k": 10, "model_info": MODEL_INFO},
             timeout=args.timeout)
    data = q.get("data") or {}
    print(f"  code={q.get('code')} msg={q.get('msg')} "
          f"entity_list={len(data.get('entity_list') or [])} "
          f"result_data={len(data.get('result_data') or [])}")

    ok = (q.get("code") == 200 and (data.get("entity_list") or []) and (data.get("result_data") or []))
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
