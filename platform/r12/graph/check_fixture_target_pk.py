#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夹具「图增量」第 ③ 条前置：图上两跳链的**终点是否落在目标块的 chunk_pk_list**。

TL 2026-10-27 裁决（方案 C）要求：拆 chunk 后必须能证明"第 2 段不可能被常规检索召回"，
其中第 ③ 条是 —— 图上 `恒星项目 -> 启明计划 -> 装备制造事业部` 的两跳终点，
其 `chunk_pk_list` 必须包含**第 2 段**的 chunk id。**连通 ≠ 取到块**，这条专门补那个缺口。

用法：
    platform/r12/venvs/graph/bin/python platform/r12/graph/check_fixture_target_pk.py [kb] [目标实体...]
默认 kb=kb_22，目标实体取 装备制造事业部。
"""
import json
import sys
import urllib.request

ES_PORT, MV_PORT, MV_DB = 19527, 19526, "graph_base"


def _post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=90))


def es_chunks(kb):
    """当前代次的 chunk id -> 可读标题（用来知道"第 2 段"是哪个 id）。"""
    r = _post(ES_PORT, "/search_by_custom_param",
              {"query_body": {"query": {"match_all": {}}, "size": 50}, "index_name": [kb]})
    rows = ((r.get("data") or {}).get("result_data")) or []
    out = {}
    for h in rows:
        md = h.get("metadata") or {}
        out[str(h.get("_id"))] = md.get("title") or md.get("source") or ""
    return out


def entity_pks(kb, names):
    """图侧实体 -> chunk_pk_list（存在向量实体表 graph_entity_<kb>，**不在 Nebula 顶点上**）。"""
    r = _post(MV_PORT, "/get_doc_by_col",
              {"collection_name": f"graph_entity_{kb}", "db_name": MV_DB,
               "expr": "text in [%s]" % ", ".join('"%s"' % n.replace('"', "") for n in names)})
    rows = ((r.get("data") or {}).get("result_data")) or []
    out = {}
    for row in rows:
        md = row.get("metadata") or {}
        text = row.get("page_content") or md.get("text")
        if text:
            out[str(text)] = [str(p) for p in (md.get("chunk_pk_list") or [])]
    return out


def main():
    kb = sys.argv[1] if len(sys.argv) > 1 else "kb_22"
    targets = sys.argv[2:] or ["装备制造事业部"]
    chunks = es_chunks(kb)
    print(f"[{kb}] 当前代次 chunk 数 = {len(chunks)}")
    for cid, title in chunks.items():
        print(f"    {cid}  {title[-40:]}")
    pks = entity_pks(kb, targets)
    ok = True
    for name in targets:
        got = pks.get(name)
        if got is None:
            print(f"  !! 图上没有实体 {name}（抽图未覆盖或名称不一致）")
            ok = False
            continue
        hit = [p for p in got if p in chunks]
        print(f"  实体 {name}: chunk_pk_list={got} -> 命中当前 ES {len(hit)}/{len(got)}")
        if not hit:
            ok = False
    print(f"[第③条] {'PASS（终点确实指向现存块）' if ok else 'FAIL'}")
    print("注：拆 chunk 后，这里必须**同时**出现第 2 段的 id；只出现第 1 段说明实体抽到了错的段，"
          "此时即使开图带回第 2 段，也解释不了图为什么能连过去。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
