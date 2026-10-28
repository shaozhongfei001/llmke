#!/usr/bin/env python3
"""抓 global 开/关同一问题的原始 SSE（逐帧 status/错误/引用），判"模型暂无法返回"是否可复现。"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/szf/data/dev/llmke-r12/platform/r12/qa")
from r12_client import GATEWAY, UA, login  # noqa: E402

import requests  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(HERE, "evidence")
Q = "智造贷最高额度是多少？"


def ask_raw(token, content, global_mode, tag, n=1):
    body = {"configId": "1", "content": content, "fileUids": [],
            "lastDate": int(time.time() * 1000),
            "name": content[:20],
            "queryId": f"query-{int(time.time()*1000)}",
            "sessionId": f"{int(time.time()*1000)}", "type": "text", "audioUrl": "",
            "enableThinking": False, "enableWebsearch": False}
    if global_mode:
        body["globalMode"] = True
    t0 = time.time()
    r = requests.post(GATEWAY + "/qa/ai/question", json=body,
                      headers={"Authorization": token, "X-Platform": "rag-qa",
                               "Accept": "text/event-stream", "Content-Type": "application/json",
                               "User-Agent": UA}, timeout=300)
    raw = r.text
    path = os.path.join(EVID, f"C-{tag}-{n}.sse.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    frames = []
    for part in raw.split("data:"):
        p = part.strip()
        if not p or p == "[DONE]":
            continue
        try:
            frames.append(json.loads(p))
        except Exception:
            pass
    answer, statuses, errs, refs = "", [], [], []
    for fr in frames:
        c = ((fr.get("reply") or {}) if isinstance(fr.get("reply"), dict) else {}).get("content") or ""
        if len(c) > len(answer):
            answer = c
        if fr.get("status") is not None:
            statuses.append(fr.get("status"))
        txt = json.dumps(fr, ensure_ascii=False)
        if "无法返回" in txt or "出错了" in txt or "异常" in txt or "error" in txt.lower():
            errs.append(txt[:300])
        if fr.get("reference"):
            try:
                d = json.loads(fr["reference"])
                v = d.get("documents") if isinstance(d, dict) else d
                lst = json.loads(v) if isinstance(v, str) else (v or [])
                if lst:
                    refs = lst
            except Exception:
                pass
    return {"tag": tag, "n": n, "http": r.status_code, "cost": round(time.time() - t0, 1),
            "frames": len(frames), "statuses": statuses[-3:], "answer": answer,
            "answer_len": len(answer), "errors": errs,
            "refs_n": len(refs),
            "refs": [{"source": ((x.get("metadata") or {}).get("source")),
                      "community_id": ((x.get("metadata") or {}).get("community_id")),
                      "search_type": ((x.get("metadata") or {}).get("search_type")),
                      "chunk_refs_stats": ((x.get("metadata") or {}).get("chunk_refs_stats")),
                      "content": (x.get("page_content") or "")[:150]} for x in refs],
            "sse_file": os.path.basename(path)}


def main():
    s, token, _ = login()
    rows = []
    for mode in (True, False):
        for i in range(1, 4):
            rows.append(ask_raw(token, Q, mode, "on" if mode else "off", i))
    with open(os.path.join(EVID, "C-sse-summary.json"), "w", encoding="utf-8") as f:
        json.dump({"question": Q, "runs": rows}, f, ensure_ascii=False, indent=1)
    for r in rows:
        print(f"[{r['tag']}{r['n']}] http={r['http']} statuses={r['statuses']} frames={r['frames']} "
              f"refs={r['refs_n']} cost={r['cost']} err={len(r['errors'])}")
        print("   answer:", (r["answer"] or "")[:150].replace("\n", " | "))
        if r["errors"]:
            print("   ERROR帧:", r["errors"][0][:200])


if __name__ == "__main__":
    main()
