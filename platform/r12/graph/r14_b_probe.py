#!/usr/bin/env python3
"""R14 B（图谱/GraphRAG）取证探针。只发请求 + 落证据，不改任何服务代码。

用法：
  venvs/graph/bin/python platform/r12/graph/r14_b_probe.py global --query "..."
  venvs/graph/bin/python platform/r12/graph/r14_b_probe.py local  --query "..." --graph on|off
  venvs/graph/bin/python platform/r12/graph/r14_b_probe.py graphsvc --query "..."   # 直连 19529 看实体/回填
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qa"))
from r12_client import GATEWAY, UA, api, login  # noqa: E402

import requests  # noqa: E402

EVID_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")

NET = {"enabled": False, "out": []}

_orig = requests.Session.request


def _patched(self, method, url, **kw):
    r = _orig(self, method, url, **kw)
    if NET["enabled"]:
        try:
            rec = {
                "method": r.request.method,
                "url": r.request.url,
                "req_body": (r.request.body.decode("utf-8", "replace")
                             if isinstance(r.request.body, bytes) else r.request.body),
                "status": r.status_code,
            }
            # 流式响应不能读 .text（会吞掉 SSE），只记 URL/体
            if not kw.get("stream"):
                rec["resp_body"] = r.text[:4000]
            NET["out"].append(rec)
        except Exception:
            pass
    return r


requests.Session.request = _patched


def save(name, obj):
    os.makedirs(EVID_ROOT, exist_ok=True)
    p = os.path.join(EVID_ROOT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"[evidence] {p}")


def parse_sse(r):
    answer, ref, rt, status = "", [], None, None
    frames = []
    buf = b""
    for line in r.iter_lines():
        if not line:
            continue
        buf += line + b"\n"
    txt = buf.decode("utf-8", "replace")
    for part in txt.split("data:"):
        part = part.strip()
        if not part:
            continue
        try:
            o = json.loads(part)
        except Exception:
            continue
        frames.append(o)
        c = (o.get("reply") or {}).get("content") or ""
        if c:
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        if o.get("resultType") is not None:
            rt = o["resultType"]
        v = o.get("reference")
        if v:
            try:
                d = json.loads(v) if isinstance(v, str) else v
                raw = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(raw) if isinstance(raw, str) else (raw or [])
                if lst:
                    ref = lst
            except Exception:
                pass
    return answer, ref, rt, status, frames


def ask(s, content, config_id=1, global_mode=False, timeout=300):
    payload = {"sessionId": f"b-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}",
               "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": config_id}
    if global_mode:
        payload["globalMode"] = True
    t0 = time.time()
    NET["out"].clear()
    NET["enabled"] = True
    r = requests.post(GATEWAY + "/qa/ai/question", json=payload,
                      headers={"Authorization": s.token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=timeout)
    answer, ref, rt, status, frames = parse_sse(r)
    NET["enabled"] = False
    return {"http": r.status_code, "status": status, "resultType": rt, "answer": answer,
            "refs": ref, "cost": round(time.time() - t0, 1), "frames": frames,
            "http_trace": list(NET["out"]), "payload": payload}


def ref_summary(refs):
    out = []
    for i, d in enumerate(refs or []):
        md = d.get("metadata") or {}
        out.append({
            "i": i,
            "order_num": d.get("order_num"),
            "page_content_len": len(d.get("page_content") or ""),
            "page_content_head": (d.get("page_content") or "")[:160],
            "source": md.get("source"),
            "title": md.get("title"),
            "file_id": md.get("file_id"),
            "search_type": md.get("search_type"),
            "community_id": md.get("community_id"),
            "level": md.get("level"),
            "member_entities": (md.get("member_entities") or [])[:12],
        })
    return out


def cmd_global(s, query, tag):
    res = ask(s, query, global_mode=True)
    res["refs_summary"] = ref_summary(res["refs"])
    print(f"http={res['http']} status={res['status']} cost={res['cost']}s refs={len(res['refs'])}")
    print("answer:", (res["answer"] or "")[:800])
    for x in res["refs_summary"]:
        print(f"  [{x['i']}] order={x['order_num']} src={x['source']!r} title={x['title']!r} "
              f"comm={x['community_id']} len={x['page_content_len']}")
    save(f"R14-B-global-{tag}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json", res)
    return res


def cmd_local(s, query, graph, tag, config_id):
    # 经 /qa：config 的 config_json 里 enabled_graph 决定是否走图
    res = ask(s, query, config_id=config_id)
    res["refs_summary"] = ref_summary(res["refs"])
    res["graph_flag"] = graph
    print(f"[graph={graph}] http={res['http']} status={res['status']} cost={res['cost']}s refs={len(res['refs'])}")
    print("answer:", (res["answer"] or "")[:800])
    for x in res["refs_summary"]:
        print(f"  [{x['i']}] order={x['order_num']} src={x['source']!r} title={x['title']!r} "
              f"st={x['search_type']} len={x['page_content_len']}")
    save(f"R14-B-local-{graph}-{tag}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json", res)
    return res


def cmd_graphsvc(query, tag, kb="kb_9"):
    body = {"query": query, "space_name": kb, "top_k": 10,
            "model_info": {"model_id": "qwen2.5-7b-instruct",
                           "url": "http://127.0.0.1:18092/v1/chat/completions", "key": "sk-r12-local"}}
    r = requests.post("http://127.0.0.1:19529/query_graph_data", json=body, timeout=180)
    data = r.json()
    print(f"http={r.status_code} code={data.get('code')} msg={data.get('msg')}")
    d = data.get("data") or {}
    print("entity_list:", d.get("entity_list"))
    for x in (d.get("result_data") or [])[:8]:
        md = x.get("metadata") or {}
        print(f"  pk={x.get('pk') or x.get('id')} title={md.get('title')!r} len={len(x.get('page_content') or '')}")
    save(f"R14-B-graphsvc-{tag}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json",
         {"request": body, "status": r.status_code, "resp": data})
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["global", "local", "graphsvc"])
    ap.add_argument("--query", required=True)
    ap.add_argument("--graph", default="off")
    ap.add_argument("--tag", default="q")
    ap.add_argument("--config-id", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "graphsvc":
        cmd_graphsvc(a.query, a.tag)
        return
    s, token, _body = login()
    s.token = token
    if a.cmd == "global":
        cmd_global(s, a.query, a.tag)
    else:
        cmd_local(s, a.query, a.graph, a.tag, a.config_id)


if __name__ == "__main__":
    main()
