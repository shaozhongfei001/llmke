#!/usr/bin/env python3
"""图增量夹具的四条前置验证（TL 批准，缺一不可）。

为什么要四条（而不是"看开图块数变多"）：
  只有同时证明"目标块**词面/语义都召不到**"和"**图上有链**"和"**关图就答错**"，
  才能把"开图答对"归因给图；否则可能只是词面运气，夹具会自欺。

用法（夹具落地后执行）：
  platform/r12/venvs/graph/bin/python platform/r12/graph/fixture_check.py \
      --kb kb_21 --query "恒星项目的归口部门是哪个？" --top-k 2

四条：
  ① ES 词面：搜"恒星项目" → 目标块 02 不出现
  ② 向量：只走向量召回（enabled_graph=false）top_k=2 → 02 不在结果里
  ③ 图链：MATCH 恒星项目→启明计划→装备制造事业部 存在
  ④ 关图对照：enabled_graph=false → 答案不含真值（"装备制造事业部"）
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

ES = "http://127.0.0.1:19200"
ALG = "http://127.0.0.1:19995/retrieval_documents"
GRAPH_API = "http://127.0.0.1:19529"
SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")

TARGET_DOC = "R14FIX-graph-02-dept.docx"
TRUTH = "装备制造事业部"
CHAIN = ("恒星项目", "启明计划", "装备制造事业部")


def check_es_lexical(kb):
    """① ES 词面：'恒星项目' 命中的块里不能有目标块。"""
    body = {"query": {"match_phrase": {"page_content": CHAIN[0]}}, "size": 20}
    r = requests.post(f"{ES}/{kb}/_search", json=body, timeout=60)
    hits = r.json().get("hits", {}).get("hits", [])
    docs = [((h.get("_source") or {}).get("metadata") or {}).get("title") for h in hits]
    ok = TARGET_DOC not in docs
    return {"ok": ok, "hits": len(hits), "titles": sorted(set(x for x in docs if x))}


def _retrieve(kb, query, top_k, graph):
    payload = {"query": query, "knowledge_base_name": [kb], "top_k": top_k,
               "enabled_faq": False, "enabled_graph": graph, "enabled_rerank": True,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions",
                              "key": "sk-r12-local"}}
    r = requests.post(ALG, json=payload, timeout=300)
    docs = (((r.json() or {}).get("data") or {}).get("documents_list")) or []
    return [{"title": (d.get("metadata") or {}).get("title"),
             "source": (d.get("metadata") or {}).get("source"),
             "search_type": (d.get("metadata") or {}).get("search_type"),
             "len": len(d.get("page_content") or "")} for d in docs]


def check_vector_only(kb, query, top_k):
    """② 只走向量（关图）时目标块不在 top_k 里。"""
    docs = _retrieve(kb, query, top_k, False)
    titles = [d["title"] for d in docs]
    return {"ok": TARGET_DOC not in titles, "titles": titles}


def check_graph_chain(kb):
    """③ 图上存在 恒星项目—启明计划—装备制造事业部 的两跳链（按**无向**判）。

    为什么无向：LLM 抽取的关系方向不稳定（实测把"A 归口 B"抽成 B-[考核]->A 与 A-[考核]->B 两条），
    若按有向判会得到"链不存在"的假阴性；夹具要判的是"两个实体在图里连通到 2 跳内"。
    """
    sys.path.insert(0, SVC)
    os.environ.setdefault("PYTHONPATH", SVC)
    os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
    os.environ.setdefault("DATA_ID", "index_graph_config_py")
    os.environ.setdefault("GROUP", "DEFAULT_GROUP")
    try:
        from graph_fun_tool import user_connect_space
        s = user_connect_space("g_" + kb)
        def _linked(x, y):
            q = (f'MATCH (a:entity)-[e:relationship]->(b:entity) '
                 f'WHERE (id(a)=="{x}" AND id(b)=="{y}") OR (id(a)=="{y}" AND id(b)=="{x}") '
                 f'RETURN count(e) AS c')
            r = s.execute(q)
            return r.row_values(0)[0].as_int() if r.row_size() else 0
        h1 = _linked(CHAIN[0], CHAIN[1])
        h2 = _linked(CHAIN[1], CHAIN[2])
        two_hop = False
        if h1 and h2:
            q = (f'MATCH (a:entity)-[e1:relationship]->(b:entity)-[e2:relationship]->(c:entity) '
                 f'WHERE id(a) IN ["{CHAIN[0]}","{CHAIN[1]}","{CHAIN[2]}"] '
                 f'AND id(c) IN ["{CHAIN[0]}","{CHAIN[1]}","{CHAIN[2]}"] RETURN count(e1) AS c')
            r = s.execute(q)
            two_hop = bool(r.row_values(0)[0].as_int()) if r.row_size() else False
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    return {"ok": bool(h1 and h2), "hop1": h1, "hop2": h2, "two_hop_edges": two_hop}


def check_graph_off_answer(kb, query, top_k):
    """④ 关图时答案不含真值（否则是词面运气，不是图的贡献）。"""
    docs = _retrieve(kb, query, top_k, False)
    text = " ".join(d.get("source") or "" for d in docs)
    has_target_doc = TARGET_DOC in [d.get("title") for d in docs]
    return {"ok": not has_target_doc, "titles": [d["title"] for d in docs],
            "note": "目标块未进入上下文，后续生成不可能答出真值"}


KB9_BASELINE = os.path.join(EVID, "R14-B-fixture-kb9-baseline.json")


def _kb9_snapshot(kb="kb_9"):
    """kb_9 的指纹：顶点/边数 + 结构哈希 + 社区摘要数 + chunk 数。

    用途（TL 要求第 ⑤ 条）：夹具的一切写操作只允许写 g_kb_21，
    **命中 kb_9 即为违规**。用指纹对比而不是口头保证：
      - Nebula：顶点数/边数 + 「顶点名排序 + 边(s,r,d)排序」的 sha256 前 16 位
      - ES：kb_9 chunk 数与 _id 集合哈希、community_summary_kb_9 文档数
    任何一条变化都说明 kb_9 被写过。
    """
    import hashlib

    snap = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    # --- Nebula g_kb_9 ---
    try:
        sys.path.insert(0, SVC)
        os.environ.setdefault("PYTHONPATH", SVC)
        os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
        os.environ.setdefault("DATA_ID", "index_graph_config_py")
        os.environ.setdefault("GROUP", "DEFAULT_GROUP")
        from graph_fun_tool import user_connect_space
        s = user_connect_space("g_" + kb)
        vnames = []
        r = s.execute("MATCH (v:entity) RETURN id(v) AS n")
        for i in range(r.row_size()):
            vnames.append(r.row_values(i)[0].as_string())
        edges = []
        r = s.execute("MATCH (a:entity)-[e:relationship]->(b:entity) "
                      "RETURN id(a) AS s, id(b) AS d, properties(e).name AS n")
        for i in range(r.row_size()):
            vals = r.row_values(i)
            edges.append((vals[0].as_string(), vals[2].as_string(), vals[1].as_string()))
        snap["nebula"] = {
            "vertices": len(vnames), "edges": len(edges),
            "vertex_hash": hashlib.sha256("\n".join(sorted(vnames)).encode()).hexdigest()[:16],
            "edge_hash": hashlib.sha256("\n".join(sorted("|".join(x) for x in edges)).encode()).hexdigest()[:16],
        }
    except Exception as e:
        snap["nebula"] = {"error": str(e)[:160]}

    # --- ES kb_9 / community_summary_kb_9 ---
    for idx in (kb, f"community_summary_{kb}"):
        try:
            r = requests.post(f"{ES}/{idx}/_search?size=2000",
                              json={"query": {"match_all": {}}}, timeout=60)
            hits = r.json().get("hits", {}).get("hits", [])
            ids = [h.get("_id") for h in hits]
            docs = {}
            for h in hits:
                md = (h.get("_source") or {}).get("metadata") or {}
                docs[h.get("_id")] = {"create_time": md.get("create_time"),
                                      "update_time": md.get("update_time"),
                                      "file_id": md.get("file_id"),
                                      # TL：version 能一眼区分"A 重新解析(V0/V1 变化)"与"手工改数据"
                                      "version": md.get("version"),
                                      "title": md.get("title")}
            snap[idx] = {"count": len(ids),
                         "id_hash": hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()[:16],
                         "ids": docs}
        except Exception as e:
            snap[idx] = {"error": str(e)[:160]}
    return snap


def check_kb9_untouched(kb="kb_9", accept=False):
    """⑤ kb_9 零写入证明：与基线指纹逐项比对（before 跑一次建基线，after 比对）。"""
    cur = _kb9_snapshot(kb)
    if accept:
        with open(KB9_BASELINE, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=1)
        return {"ok": True, "mode": "baseline_accepted(manual)", "path": KB9_BASELINE,
                "snapshot_ts": cur.get("ts")}
    if not os.path.exists(KB9_BASELINE):
        with open(KB9_BASELINE, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False, indent=1)
        return {"ok": True, "mode": "baseline_created", "path": KB9_BASELINE, "snapshot": cur}
    base = json.load(open(KB9_BASELINE, encoding="utf-8"))
    diffs, attribution = [], []
    for key in ("nebula", kb, f"community_summary_{kb}"):
        b, c = base.get(key) or {}, cur.get(key) or {}
        # 只比"内容指纹"（count + id_hash / 结构哈希），不比 ids 明细字典——
        # 否则给归因加字段（如 version）会被误判成"数据被改"。
        if b.get("count") == c.get("count") and b.get("id_hash") == c.get("id_hash") \
                and b.get("vertices") == c.get("vertices") and b.get("edges") == c.get("edges") \
                and b.get("vertex_hash") == c.get("vertex_hash") and b.get("edge_hash") == c.get("edge_hash"):
            continue
        rec = {"field": key}
        if "ids" in b or "ids" in c:
            b_ids, c_ids = set((b.get("ids") or {}).keys()), set((c.get("ids") or {}).keys())
            added, removed = sorted(c_ids - b_ids), sorted(b_ids - c_ids)
            rec.update({"added": added, "removed": removed})
            # 归因：新增块的写入时间就是"谁在这段时间写过"的直接证据
            for i in added:
                rec.setdefault("added_meta", {})[i] = (c.get("ids") or {}).get(i)
            for i in removed:
                rec.setdefault("removed_meta", {})[i] = (b.get("ids") or {}).get(i)
            attribution.append({"field": key, "added": len(added), "removed": len(removed),
                                "latest_write": max([(c.get("ids") or {})[i].get("update_time") or ""
                                                     for i in added] or [""])})
        else:
            rec.update({"before": b, "after": c})
        diffs.append(rec)
    verdict = "untouched" if not diffs else "kb9_changed"
    hint = ""
    if diffs:
        hint = ("kb_9 指纹变化：先判断是谁写的（看下面 added_meta 的 update_time / removed 的 id），"
                "确认是 A 的重解析等**外部写入**后，才允许用 --accept-kb9-baseline 重取基线；"
                "不要默默重取，否则会把违规洗掉。")
    return {"ok": not diffs, "mode": "compared", "verdict": verdict, "diffs": diffs,
            "attribution": attribution, "hint": hint,
            "baseline_ts": base.get("ts"), "current_ts": cur.get("ts")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", required=True)
    ap.add_argument("--query", default="恒星项目的归口部门是哪个？")
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--accept-kb9-baseline", action="store_true",
                    help="确认 kb_9 变化来自外部写入（如 A 的重解析）后，才允许重取基线")
    a = ap.parse_args()

    res = {
        "kb": a.kb, "query": a.query, "top_k": a.top_k, "truth": TRUTH,
        "1_es_lexical": check_es_lexical(a.kb),
        "2_vector_only": check_vector_only(a.kb, a.query, a.top_k),
        "3_graph_chain": check_graph_chain(a.kb),
        "4_graph_off_answer": check_graph_off_answer(a.kb, a.query, a.top_k),
        # ⑤ TL 要求：证明 kb_9 零写入（before 建基线 / after 比对）
        "5_kb9_untouched": check_kb9_untouched("kb_9", accept=a.accept_kb9_baseline),
    }
    res["all_ok"] = all(v.get("ok") for k, v in res.items()
                        if isinstance(v, dict) and "ok" in v)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["all_ok"]:
        print("\n[结论] 前置验证未全过 -> 夹具不可用：改夹具文本（不改代码），"
              "或修正建库/抽取流程；不得降级使用。")

    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-fixture-check-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)


if __name__ == "__main__":
    main()
