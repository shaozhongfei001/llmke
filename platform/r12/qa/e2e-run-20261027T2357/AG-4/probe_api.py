#!/usr/bin/env python3
"""AG-4 只读 API 探针：global 双向 / 多版本 V0-V1 / 图谱。

纪律：
- 全程只读。不建库、不删档、不重启、不改库。只 POST 问答与只读检索接口。
- 每个结论都落 JSON 到 AG-4/evidence/，供报告引用。
"""
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import GATEWAY, UA, api, login  # noqa: E402

import requests  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(HERE, "evidence")
os.makedirs(EVID, exist_ok=True)
KB_NAME = "kb_9"
ES = "http://127.0.0.1:19200"
IDX = (KB_NAME, "table_chunks_" + KB_NAME, "table_summary_" + KB_NAME)


def dump(name, obj):
    p = os.path.join(EVID, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"  -> {os.path.relpath(p, HERE)}")
    return p


def es_search(idx, body):
    r = requests.post(f"{ES}/{idx}/_search", json=body, timeout=60)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def ask(s, token, content, global_mode=False, config_id=1, path="/qa/ai/question", timeout=300):
    body = {"sessionId": f"ag4-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}",
            "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        body["globalMode"] = True
    t0 = time.time()
    try:
        r = requests.post(GATEWAY + path, json=body,
                          headers={"Authorization": token, "Accept": "text/event-stream",
                                   "Content-Type": "application/json", "User-Agent": UA},
                          stream=True, timeout=timeout)
    except Exception as e:
        return {"transport_error": f"{type(e).__name__}: {e}", "cost": round(time.time() - t0, 1),
                "globalMode_sent": global_mode}
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    txt = raw.decode("utf-8", "replace")
    answer, refs, status, rtype, frames = "", [], None, None, 0
    for part in txt.split("data:"):
        part = part.strip()
        if not part or part == "[DONE]":
            continue
        try:
            o = json.loads(part)
        except Exception:
            continue
        frames += 1
        c = ((o.get("reply") or {}) if isinstance(o.get("reply"), dict) else {}).get("content") or ""
        if len(c) > len(answer):
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        if o.get("resultType") is not None:
            rtype = o["resultType"]
        v = o.get("reference")
        if v:
            try:
                d = json.loads(v) if isinstance(v, str) else v
                rawl = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(rawl) if isinstance(rawl, str) else (rawl or [])
                if lst:
                    refs = lst
            except Exception:
                pass
    return {"http": r.status_code, "status": status, "resultType": rtype, "answer": answer,
            "refs": refs, "refs_n": len(refs), "frames": frames,
            "cost": round(time.time() - t0, 1), "globalMode_sent": global_mode,
            "raw_head": txt[:400]}


def src_of(x):
    return str(((x.get("metadata") or {}).get("source")) or "")


def main():
    s, token, body = login()
    print(f"login ok user={(body.get('data') or {}).get('userName')}")

    # ---------- A0 库清单：确认 kb_9 的 id ----------
    code, kbs = api(s, "GET", "/index/knowledgeBase/list?pageNo=1&pageSize=50", token)
    recs = ((kbs.get("data") or {}).get("records") or []) if isinstance(kbs, dict) else []
    kb9 = [k for k in recs if str(k.get("kbName")) == KB_NAME]
    dump("A0-kb-list.json", {"http": code, "total": len(recs),
                             "kb9": kb9[0] if kb9 else None,
                             "names": [k.get("kbName") for k in recs]})
    kb_id = (kb9[0].get("id") if kb9 else 9)

    # ---------- A1 多版本：版本分组接口 ----------
    code, ver = api(s, "GET", f"/index/knowledgeBase/file/multiple/version?kbNames={KB_NAME}"
                                f"&pageNo=1&pageSize=20", token)
    groups = ((ver.get("data") or {}).get("records") or []) if isinstance(ver, dict) else []
    slim = []
    for g in groups:
        slim.append({"parentFileName": g.get("parentFileName"),
                     "groupId": g.get("groupId"),
                     "files": [{"id": k.get("id"), "fileName": k.get("fileName"),
                                "version": k.get("version"),
                                "status": k.get("status"),
                                "filePath": k.get("filePath"),
                                "convertedFilePath": k.get("convertedFilePath"),
                                "parentFileName": k.get("parentFileName")}
                               for k in (g.get("kbFiles") or [])]})
    multi = [g for g in slim if len({(f.get("version") or "") for f in g["files"]}) >= 2]
    dump("A1-version-groups.json", {"http": code, "groups_n": len(slim), "multi_n": len(multi),
                                    "groups": slim})

    # ---------- A2 ES 事实：V0/V1 块与关键数值 ----------
    ver_facts = {}
    for kw in ("5000", "8000"):
        st, j = es_search(KB_NAME, {"size": 3, "_source": ["metadata.source", "metadata.version",
                                                           "metadata.file_id", "page_content"],
                                    "query": {"match_phrase": {"page_content": kw}}})
        hits = ((j.get("hits") or {}).get("hits") or [])
        ver_facts[kw] = [{"id": h.get("_id"),
                          "source": ((h.get("_source") or {}).get("metadata") or {}).get("source"),
                          "version": ((h.get("_source") or {}).get("metadata") or {}).get("version"),
                          "snippet": ((h.get("_source") or {}).get("page_content") or "")[:80]}
                         for h in hits]
    # 每个版本各有多少块
    per_ver = {}
    for src_kw in ("R12FIX-product-loan.docx", "R12FIX-product-intro.pptx"):
        st, j = es_search(KB_NAME, {"size": 0,
                                    "aggs": {"src": {"terms": {"field": "metadata.source.keyword", "size": 20}}},
                                    "query": {"wildcard": {"metadata.source.keyword":
                                                           {"value": f"*{src_kw}*"}}}})
        buckets = (((j.get("aggregations") or {}).get("src") or {}).get("buckets") or [])
        per_ver[src_kw] = [{"source": b.get("key"), "docs": b.get("doc_count")} for b in buckets]
    dump("A2-es-version-facts.json", {"number_hits": ver_facts,
                                      "per_file_sources": per_ver,
                                      "total_count": {i: (es_search(i, {"size": 0})[1].get("count"))
                                                      for i in IDX}})

    # ---------- A3 S8 global 双向 ----------
    G1 = ("江南装备科技有限公司、华东精密制造有限公司、北方重工配件厂三家的信用评级分别是什么？"
          "按智造贷的评级加点规则，它们执行利率相对一年期LPR的加点分别是多少？")
    SAME_Q = "智造贷的授信额度是多少？"
    R_Q = "海川电子材料股份有限公司被列为关注类，需要计提多少比例的贷款损失准备？"

    g_on = ask(s, token, G1, global_mode=True)
    g_off = ask(s, token, G1, global_mode=False)
    dump("A3-global-onoff.json", {
        "question": G1,
        "on": {**g_on, "sources": [src_of(x) for x in g_on.get("refs") or []]},
        "off": {**g_off, "sources": [src_of(x) for x in g_off.get("refs") or []]},
    })

    # 同题连跑 3 次（global 开）：记录 refs 波动
    runs = []
    for i in range(3):
        r = ask(s, token, SAME_Q, global_mode=True)
        runs.append({"i": i + 1, "http": r.get("http"), "status": r.get("status"),
                     "refs_n": r.get("refs_n"), "answer": r.get("answer"),
                     "sources": [src_of(x) for x in r.get("refs") or []]})
    dump("A3-global-3runs.json", {"question": SAME_Q, "runs": runs,
                                  "refs_counts": [x["refs_n"] for x in runs]})

    # 拒答
    rq_on = ask(s, token, R_Q, global_mode=True)
    rq_off = ask(s, token, R_Q, global_mode=False)
    dump("A3-global-refusal.json", {
        "question": R_Q,
        "on": {**rq_on, "sources": [src_of(x) for x in rq_on.get("refs") or []]},
        "off": {**rq_off, "sources": [src_of(x) for x in rq_off.get("refs") or []]},
    })

    # ---------- A4 S10 多版本问答：默认应答取哪一版 ----------
    Q_LOAN = "R12FIX-product-loan 这份文件里，智造贷的授信额度是多少？"
    v_default = ask(s, token, Q_LOAN, global_mode=False)
    dump("A4-version-default-answer.json",
         {**v_default, "sources": [src_of(x) for x in v_default.get("refs") or []]})

    # ---------- A5 S11 图谱存储事实 ----------
    st, j = es_search("kb_9", {"size": 0})
    es_total = j.get("count")
    # 图服务：整图 + 局部
    graph = {}
    try:
        r = requests.get("http://127.0.0.1:19529/query_graph_data",
                         json={"space_name": KB_NAME, "query": "智造贷 授信额度 票据贴现",
                               "knowledge_base_name": [KB_NAME], "top_k": 5,
                               "model_info": {"model_id": "qwen2.5-7b-instruct",
                                              "url": "http://127.0.0.1:18092/v1/chat/completions",
                                              "key": "sk-r12-local"}},
                         timeout=120)
        body = r.json()
        data = body.get("data") or {}
        blocks = data.get("result_data") or []
        graph["query_graph_data"] = {
            "http": r.status_code, "code": body.get("code"), "reason": data.get("reason"),
            "blocks_n": len(blocks),
            "identity_violations_count": data.get("identity_violations_count"),
            "keys": sorted(list(data.keys()))[:20],
            "blocks": [{ "pk": (b.get("metadata") or {}).get("pk"),
                        "source": (b.get("metadata") or {}).get("source"),
                        "version": (b.get("metadata") or {}).get("version"),
                        "search_type": (b.get("metadata") or {}).get("search_type"),
                        "content_len": len(b.get("page_content") or "")} for b in blocks[:6]],
        }
    except Exception as e:
        graph["query_graph_data"] = {"error": f"{type(e).__name__}: {e}"}

    code, wg = api(s, "POST", "/graph/search/wholeGraphSearch", token,
                   json={"spaceName": KB_NAME})
    wgd = (wg.get("data") if isinstance(wg, dict) else None) or {}
    nodes = wgd.get("nodes") or wgd.get("vertexes") or []
    edges = wgd.get("edges") or wgd.get("relationships") or []
    graph["wholeGraphSearch"] = {"http": code, "success": (wg or {}).get("success") if isinstance(wg, dict) else None,
                                 "keys": sorted(list(wgd.keys()))[:20],
                                 "nodes_n": len(nodes), "edges_n": len(edges)}

    code, gl = api(s, "GET", f"/index/knowledgeBase/file/folder/list?kbId={kb_id}"
                                f"&fileListType=3&pageNo=1&pageSize=20", token)
    glist = []
    for r0 in (((gl.get("data") or {}).get("data") or []) if isinstance(gl, dict) else []):
        glist.append({"fileId": r0.get("fileId"), "name": r0.get("name"),
                      "nodeCount": r0.get("nodeCount"), "edgeCount": r0.get("edgeCount"),
                      "status": r0.get("status"), "graphParseStatus": r0.get("graphParseStatus")})
    graph["graph-file-list"] = {"http": code, "rows_n": len(glist), "rows": glist}
    graph["es_total_kb9"] = es_total
    dump("A5-graph-facts.json", graph)

    # 图块 pk 是否存在于当前 ES
    pks = [b.get("pk") for b in (graph.get("query_graph_data", {}).get("blocks") or []) if b.get("pk")]
    hit = set()
    if pks:
        for idx in IDX:
            stt, jj = es_search(idx, {"size": len(pks) + 5, "_source": False,
                                      "query": {"ids": {"values": [str(p) for p in pks]}}})
            for h in (((jj.get("hits") or {}).get("hits") or [])):
                hit.add(str(h.get("_id")))
    dump("A5-graph-pk-vs-es.json", {"pks": pks, "hit": sorted(hit), "hit_n": len(hit)})

    print("done")


if __name__ == "__main__":
    main()
