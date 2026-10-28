#!/usr/bin/env python3
"""AG-4 第三轮只读探针：图开/关 only_on（按 source+内容指纹）、返回块 metadata 字段完整性。"""
import hashlib
import json
import os
import sys

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")

import requests  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(HERE, "evidence")
KB = "kb_9"


def dump(name, obj):
    with open(os.path.join(EVID, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print("  ->", name)


def retrieve(q, enabled_graph, top_k=10):
    payload = {"query": q, "knowledge_base_name": [KB], "top_k": top_k,
               "enabled_faq": False, "enabled_graph": enabled_graph, "enabled_rerank": False,
               "model_info": {"model_id": "qwen2.5-7b-instruct",
                              "url": "http://127.0.0.1:18092/v1/chat/completions",
                              "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19995/retrieval_documents", json=payload, timeout=180)
    try:
        b = r.json()
    except Exception:
        b = {}
    docs = ((b.get("data") or {}).get("documents_list") or [])
    rows = []
    for d in docs:
        m = d.get("metadata") or {}
        content = d.get("page_content") or ""
        rows.append({
            "fp": hashlib.md5((str(m.get("source")) + "|" + content[:120]).encode()).hexdigest()[:12],
            "source": m.get("source"), "version": m.get("version"),
            "search_type": m.get("search_type"), "score": d.get("score"),
            "meta_keys": sorted(list(m.keys())),
            "has_pk": bool(m.get("pk")), "content_len": len(content),
            "content_head": content[:60],
        })
    return {"http": r.status_code, "code": b.get("code"), "n": len(docs), "rows": rows}


def main():
    QS = [
        ("多跳1-评级到额度", "江南装备科技有限公司的信用评级是什么，按这个评级它适用的加点是多少，对应产品的最高授信额度又是多少？"),
        ("多跳2-关注类到额度", "海川电子材料股份有限公司被列为关注类，这家公司的授信额度使用率是多少，和台账里的准入条件有什么关系？"),
        ("多跳3-额度到加点", "信用评级AA的客户按智造贷规则要加多少基点，这类客户最高能借多少？"),
    ]
    res = {"queries": []}
    for tag, q in QS:
        on = retrieve(q, True)
        off = retrieve(q, False)
        fp_on = {r["fp"] for r in on["rows"]}
        fp_off = {r["fp"] for r in off["rows"]}
        src_on = {r["source"] for r in on["rows"] if r["source"]}
        src_off = {r["source"] for r in off["rows"] if r["source"]}
        res["queries"].append({
            "tag": tag, "question": q,
            "on": on, "off": off,
            "only_on_fp": sorted(fp_on - fp_off),
            "only_off_fp": sorted(fp_off - fp_on),
            "only_on_src": sorted(x for x in (src_on - src_off) if x),
            "only_off_src": sorted(x for x in (src_off - src_on) if x),
            "graph_tagged_on": sum(1 for r in on["rows"]
                                   if any("graph" in str(x).lower() for x in (r["search_type"] or []))),
            "graph_tagged_off": sum(1 for r in off["rows"]
                                    if any("graph" in str(x).lower() for x in (r["search_type"] or []))),
            "pk_present": any(r["has_pk"] for r in on["rows"] + off["rows"]),
        })
    dump("B8-graph-only-on.json", res)
    for q in res["queries"]:
        print(f"{q['tag']}: on={q['on']['n']} off={q['off']['n']} graph标记(on/off)={q['graph_tagged_on']}/{q['graph_tagged_off']} "
              f"only_on_fp={len(q['only_on_fp'])} only_on_src={len(q['only_on_src'])} pk字段={q['pk_present']}")
    print("meta_keys 示例:", json.dumps(res["queries"][0]["on"]["rows"][0]["meta_keys"], ensure_ascii=False))


if __name__ == "__main__":
    main()
