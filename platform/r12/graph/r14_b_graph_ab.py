#!/usr/bin/env python3
"""local 检索层"开图 / 关图"受控对照（同一问句、同一参数，只改 enabled_graph）。

为什么要单独做：
  经 /qa 时走的是**服务端配置**（`config_json.enabled_graph`），payload 里的开关不生效。
  实测证据：`--graph off` 那轮返回的块 `search_type` 里**仍然含 graph**，说明两次都是开图，
  拿它做"关图基线"会得出错误结论。所以对照必须在检索层按请求参数做，且固定 rerank 开关。

判据（TL 定）：
  1) 开图时 `search_type` 含 graph 的块数 > 0；
  2) **同一块在关图时缺席**（按 source + offset + 内容长度 作为块身份）；
  3) 逐块列出"只在开图出现 / 两边都有 / 只在关图出现"，不只看总数。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/r14_b_graph_ab.py "问题" [--rerank on|off]
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone

import requests

ALG = "http://127.0.0.1:19995/retrieval_documents"
EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
KB = "kb_9"


def _call(query, enabled_graph, enabled_rerank, kb=KB, top_k=10):
    payload = {
        "query": query,
        "knowledge_base_name": [kb],
        "top_k": top_k,
        "enabled_faq": False,
        "enabled_graph": enabled_graph,
        "enabled_rerank": enabled_rerank,
        "model_info": {"model_id": "qwen2.5-7b-instruct",
                       "url": "http://127.0.0.1:18092/v1/chat/completions",
                       "key": "sk-r12-local"},
    }
    t0 = time.time()
    r = requests.post(ALG, json=payload, timeout=300)
    docs = (((r.json() or {}).get("data") or {}).get("documents_list")) or []
    rows = []
    for d in docs:
        md = d.get("metadata") or {}
        st = md.get("search_type") or []
        rows.append({
            "source": md.get("source"),
            "offset": md.get("offset"),
            "len": len(d.get("page_content") or ""),
            "search_type": st,
            "is_graph": any("graph" in str(x).lower() for x in st),
            "recovered_by": md.get("recovered_by"),
            "chunk_pk": md.get("pk") or md.get("chunk_pk"),
        })
    return {"http": r.status_code, "cost": round(time.time() - t0, 1),
            "n": len(rows), "graph_blocks": sum(1 for x in rows if x["is_graph"]),
            "docs": rows}


def _key(x):
    return (x["source"], json.dumps(x["offset"], ensure_ascii=False), x["len"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--rerank", default="on")
    ap.add_argument("--kb", default=KB)
    ap.add_argument("--top-k", type=int, default=10)
    a = ap.parse_args()
    rerank = a.rerank.lower() in ("on", "true", "1")

    on = _call(a.query, True, rerank, a.kb, a.top_k)
    off = _call(a.query, False, rerank, a.kb, a.top_k)

    kon = {_key(x): x for x in on["docs"]}
    koff = {_key(x): x for x in off["docs"]}
    only_on = [k for k in kon if k not in koff]
    only_off = [k for k in koff if k not in kon]
    both = [k for k in kon if k in koff]

    print(f"[query] {a.query}")
    print(f"[same params] rerank={rerank} kb={a.kb} top_k={a.top_k}")
    print(f"[on ] http={on['http']} docs={on['n']} graph_blocks={on['graph_blocks']} cost={on['cost']}s")
    print(f"[off] http={off['http']} docs={off['n']} graph_blocks={off['graph_blocks']} cost={off['cost']}s")

    def _show(title, keys, table):
        print(f"  {title} ({len(keys)}):")
        for k in keys:
            x = table[k]
            print(f"    - {(x['source'] or '')[-46:]} off={x['offset']} len={x['len']} "
                  f"graph={x['is_graph']} st={x['search_type']} rec={x['recovered_by']}")

    print("[diff]")
    _show("只在开图出现", only_on, kon)
    _show("只在关图出现", only_off, koff)
    _show("两边都有", both, kon)

    verdict = {
        "graph_blocks_on": on["graph_blocks"],
        "graph_blocks_off": off["graph_blocks"],
        "only_on": len(only_on),
        "only_off": len(only_off),
        "graph_adds_blocks": bool(on["graph_blocks"] > 0 and len(only_on) > 0),
        "graph_absent_when_off": bool(off["graph_blocks"] == 0),
    }
    print("[verdict]", json.dumps(verdict, ensure_ascii=False))
    # 判据 2 的严格读法：图贡献的块必须"关图时不存在"
    strict = [k for k in only_on if kon[k]["is_graph"]]
    print(f"[strict] 只在开图出现且带 graph 标记的块：{len(strict)}"
          f"{' —— 满足' if strict and off['graph_blocks'] == 0 else ' —— 不满足'}")

    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-graph-ab-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"query": a.query, "rerank": rerank, "kb": a.kb, "top_k": a.top_k,
                   "on": on, "off": off,
                   "verdict": verdict}, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)


if __name__ == "__main__":
    main()
