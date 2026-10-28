#!/usr/bin/env python3
"""TL 追加三项：①global 对"智造贷单户最高授信额度是多少"的用户可见答案原文
②同题 local 对照 ③社区摘要 create_time 与 ES V1 chunk(fid=328) create_time 并列（代次证明）。"""
import json
import os
import re
import sys
import time

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import GATEWAY, UA, login  # noqa: E402

import requests  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(HERE, "evidence")
Q = "智造贷单户最高授信额度是多少？"


def ask(token, content, global_mode, timeout=300):
    body = {"sessionId": f"tl-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}",
            "content": content, "type": "text", "sysType": "KNO_INDEX", "configId": 1}
    if global_mode:
        body["globalMode"] = True
    t0 = time.time()
    r = requests.post(GATEWAY + "/qa/ai/question", json=body,
                      headers={"Authorization": token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=timeout)
    r.encoding = "utf-8"
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    txt = raw.decode("utf-8", "replace")
    answer, refs, status, frames = "", [], None, 0
    for part in txt.split("data:"):
        p = part.strip()
        if not p or p == "[DONE]":
            continue
        try:
            o = json.loads(p)
        except Exception:
            continue
        frames += 1
        c = ((o.get("reply") or {}) if isinstance(o.get("reply"), dict) else {}).get("content") or ""
        if len(c) > len(answer):
            answer = c
        if o.get("status") is not None:
            status = o["status"]
        if o.get("reference"):
            try:
                d = json.loads(o["reference"])
                v = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(v) if isinstance(v, str) else (v or [])
                if lst:
                    refs = lst
            except Exception:
                pass
    return {"http": r.status_code, "status": status, "frames": frames,
            "cost": round(time.time() - t0, 1), "answer": answer,
            "has_5000": "5000" in answer, "has_8000": "8000" in answer,
            "has_1000": "1000" in answer,
            "refs": [{"title": (x.get("metadata") or {}).get("title"),
                      "community_id": (x.get("metadata") or {}).get("community_id"),
                      "source": (x.get("metadata") or {}).get("source"),
                      "search_type": (x.get("metadata") or {}).get("search_type")} for x in refs]}


def main():
    s, token, _ = login()
    out = {"question": Q}
    out["global_on"] = [ask(token, Q, True) for _ in range(3)]
    out["local_off"] = [ask(token, Q, False) for _ in range(3)]

    # ③ 时间线：社区摘要 create_time 全部列出
    r = requests.post("http://127.0.0.1:19200/community_summary_kb_9/_search",
                      json={"size": 20, "_source": ["metadata.community_id", "metadata.create_time",
                                                    "metadata.file_ids", "metadata.sources",
                                                    "metadata.update_time", "page_content"]}, timeout=60)
    cs = []
    for h in (((r.json().get("hits") or {}).get("hits") or [])):
        sc = h.get("_source") or {}
        m = sc.get("metadata") or {}
        cs.append({"community_id": m.get("community_id"), "create_time": m.get("create_time"),
                   "update_time": m.get("update_time"), "file_ids": m.get("file_ids"),
                   "sources": m.get("sources"),
                   "has5000": "5000" in (sc.get("page_content") or ""),
                   "has8000": "8000" in (sc.get("page_content") or "")})
    # ES 侧 V1 chunk 的 create_time（fid=328 loan V1 / fid=343 intro V1），按存储事实取
    es = {}
    for tag, fid in (("loan_V1_fid328", "328"), ("intro_V1_fid343", "343"),
                     ("loan_V0_fid290", "290"), ("intro_V0_fid330", "330")):
        rr = requests.post("http://127.0.0.1:19200/kb_9/_search", json={
            "size": 3, "_source": ["metadata.file_id", "metadata.version", "metadata.create_time",
                                   "metadata.source"],
            "query": {"term": {"metadata.file_id.keyword": fid}}}, timeout=60)
        hits = (((rr.json() or {}).get("hits") or {}).get("hits") or [])
        es[tag] = [{"version": ((h["_source"].get("metadata") or {}).get("version")),
                    "create_time": ((h["_source"].get("metadata") or {}).get("create_time")),
                    "source": ((h["_source"].get("metadata") or {}).get("source"))} for h in hits]
    out["community_timeline"] = cs
    out["es_chunk_timeline"] = es
    with open(os.path.join(EVID, "D-tl-three.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for tag in ("global_on", "local_off"):
        print("====", tag)
        for i, x in enumerate(out[tag]):
            print(f"  run{i+1} http={x['http']} status={x['status']} frames={x['frames']} cost={x['cost']} "
                  f"5000={x['has_5000']} 8000={x['has_8000']} 1000={x['has_1000']}")
            print("   ANSWER:", x["answer"].replace("\n", " | "))
            print("   REFS:", [r0["source"] or r0["community_id"] for r0 in x["refs"]])
    print("=== 社区摘要 create_time")
    for c in cs:
        print(f"  {c['community_id']} create={c['create_time']} update={c['update_time']} has5000={c['has5000']} has8000={c['has8000']}")
    print("=== ES chunk create_time")
    for k, v in es.items():
        print(" ", k, v)


if __name__ == "__main__":
    main()
