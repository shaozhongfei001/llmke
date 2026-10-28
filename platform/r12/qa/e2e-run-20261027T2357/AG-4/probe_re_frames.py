#!/usr/bin/env python3
"""UI 实际接口 /qa/ai/question_re 在 globalMode=true 下是否稳定以 status=3 收尾，
并累加增量帧，证明失败前已把旧代次数值（5000万）流给用户。"""
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


def run(token, gm, tag):
    body = {"configId": "1", "content": Q, "type": "text", "sysType": "KNO_INDEX",
            "sessionId": f"re-{int(time.time()*1000)}", "queryId": f"q-{int(time.time()*1000)}"}
    if gm:
        body["globalMode"] = True
    r = requests.post(GATEWAY + "/qa/ai/question_re", json=body,
                      headers={"Authorization": token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": UA},
                      stream=True, timeout=300)
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    txt = raw.decode("utf-8", "replace")
    with open(os.path.join(EVID, f"E-{tag}.sse.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    frames = []
    for p in txt.split("data:"):
        p = p.strip()
        if not p or p == "[DONE]":
            continue
        try:
            frames.append(json.loads(p))
        except Exception:
            pass
    # 增量累加（question_re 的 reply.content 是增量片段）
    acc, statuses, cumulative = "", [], []
    for f in frames:
        c = ((f.get("reply") or {}) if isinstance(f.get("reply"), dict) else {}).get("content") or ""
        acc += c
        cumulative.append(acc)
        if f.get("status") is not None:
            statuses.append(f["status"])
    return {"tag": tag, "http": r.status_code, "frames": len(frames), "statuses": statuses,
            "final_status": statuses[-1] if statuses else None,
            "accumulated_before_last": cumulative[-2] if len(cumulative) > 1 else "",
            "last_content": (((frames[-1].get("reply") or {}) if isinstance(frames[-1].get("reply"), dict) else {}).get("content") or ""),
            "has_5000": "5000" in acc, "has_1000": "1000" in acc, "has_8000": "8000" in acc,
            "refs_in_stream": sum(1 for f in frames if f.get("reference")),
            "cost_frame_n": len(frames)}


def main():
    s, token, _ = login()
    rows = [run(token, True, f"re-on-{i}") for i in (1, 2, 3)]
    rows += [run(token, False, "re-off-1")]
    with open(os.path.join(EVID, "E-re-frames-summary.json"), "w", encoding="utf-8") as f:
        json.dump({"question": Q, "endpoint": "/qa/ai/question_re", "runs": rows}, f,
                  ensure_ascii=False, indent=1)
    for r in rows:
        print(f"[{r['tag']}] frames={r['frames']} final_status={r['final_status']} "
              f"5000={r['has_5000']} 8000={r['has_8000']} 1000={r['has_1000']} refs_frames={r['refs_in_stream']}")
        print("   失败前累计内容:", (r["accumulated_before_last"] or "")[:120])
        print("   最后一帧内容  :", (r["last_content"] or "")[:120])


if __name__ == "__main__":
    main()
