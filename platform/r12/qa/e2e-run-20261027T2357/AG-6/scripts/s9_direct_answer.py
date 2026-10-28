#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9-5（答案层）：kb_9 既有 FAQ 原问题 → /qa/ai/question_re（UI 实际端点）→ 判答案来源。

判定口径（逐字符）：
  SAME_AS_ASKED   返回答案 == 被问问答对的 answer
  FROM_OTHER_FAQ  返回答案 == 另一个问答对的 answer（串到邻近问答对）
  GENERATED       两者都不是（模型生成/改写）
另记 resultType 是否为 2（前端据此显示"FAQ 命中"）。
"""
import json
import re
import time

import requests

import ag6_lib as L


def kb9_faqs():
    r = requests.post("http://127.0.0.1:19200/faq_kb_9/_search",
                      json={"query": {"term": {"metadata.status": 1}}, "size": 40},
                      timeout=60).json()
    out = []
    for h in (r.get("hits", {}).get("hits") or []):
        m = h["_source"].get("metadata") or {}
        if m.get("question") and m.get("answer"):
            out.append({"pk": m.get("pk"), "question": m["question"], "answer": m["answer"]})
    if not out:  # status 可能不是 keyword，退回全量再筛
        r = requests.post("http://127.0.0.1:19200/faq_kb_9/_search",
                          json={"query": {"match_all": {}}, "size": 40}, timeout=60).json()
        for h in (r.get("hits", {}).get("hits") or []):
            m = h["_source"].get("metadata") or {}
            if m.get("question") and m.get("answer") and m.get("status") == 1:
                out.append({"pk": m.get("pk"), "question": m["question"], "answer": m["answer"]})
    return out


def ask_re(token, content, timeout=600):
    sid = f"ag6-{int(time.time()*1000)}"
    qid = f"ag6q-{int(time.time()*1000)}"
    payload = {"sessionId": sid, "queryId": qid, "content": content,
               "type": "text", "sysType": "KNO_INDEX", "configId": 1}
    t0 = time.time()
    r = requests.post(L.GATEWAY + "/qa/ai/question_re", json=payload,
                      headers={"Authorization": token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": L.UA},
                      stream=True, timeout=timeout)
    raw = b""
    for line in r.iter_lines():
        if line:
            raw += line + b"\n"
    text = raw.decode("utf-8", "replace")
    content_out, rt = None, None
    for m in re.finditer(r"data:(\{.*\})", text):
        try:
            j = json.loads(m.group(1))
        except Exception:
            continue
        if j.get("reply") and j["reply"].get("content"):
            content_out = j["reply"]["content"]
        if j.get("resultType") is not None:
            rt = j["resultType"]
    return {"http": r.status_code, "elapsed": round(time.time() - t0, 2),
            "answer": content_out, "resultType": rt, "raw_len": len(raw),
            "raw": text[:3000]}


def main():
    s, token = L.login()
    faqs = kb9_faqs()
    ev = {"time": L.now(), "kb": "kb_9(只读)", "endpoint": "POST /qa/ai/question_re",
          "n_faqs": len(faqs), "cases": []}
    # 选 4 条问题文本互不相同的问答对（避免同一问句重复）
    picked = faqs[:4]
    for f in picked:
        resp = ask_re(token, f["question"])
        ans = resp["answer"] or ""
        cls, from_pk = "GENERATED", None
        if ans.strip() == f["answer"].strip():
            cls = "SAME_AS_ASKED"
        else:
            for g in faqs:
                if g["pk"] != f["pk"] and ans.strip() and ans.strip() == g["answer"].strip():
                    cls, from_pk = "FROM_OTHER_FAQ", g["pk"]
                    break
        ev["cases"].append({
            "question": f["question"], "expected_answer": f["answer"],
            "got_answer": ans, "class": cls, "from_pk": from_pk,
            "resultType": resp["resultType"], "http": resp["http"],
            "elapsed": resp["elapsed"],
            "char_equal": ans.strip() == f["answer"].strip(),
            "len_expected": len(f["answer"]), "len_got": len(ans)})
        print(f"[{cls}] rt={resp['resultType']} {f['question'][:26]} -> {ans[:50]}")
    ev["summary"] = {
        "n": len(ev["cases"]),
        "same": sum(1 for c in ev["cases"] if c["class"] == "SAME_AS_ASKED"),
        "other": sum(1 for c in ev["cases"] if c["class"] == "FROM_OTHER_FAQ"),
        "generated": sum(1 for c in ev["cases"] if c["class"] == "GENERATED"),
        "resultType2": sum(1 for c in ev["cases"] if c["resultType"] == 2),
    }
    p = L.dump("S9-5-answer-level.json", ev, "S9")
    print(json.dumps({"evidence": p, "summary": ev["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
