#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9-5：直接提问命中 FAQ 直答（不是模型自由生成）。

三层取证：
  L1 检索层（我的库）：POST /retrieval_documents enabled_faq=true
      → faq_result_list 里有该问答对，faq_answer 与库里原文**逐字符相等**
  L2 对照：同一问题 enabled_faq=false → faq_result_list 为空（证明确实走的是 FAQ 通道）
  L3 答案层（kb_9，只读）：POST /qa/ai/question_re，问 kb_9 既有 FAQ 的原问题
      → 返回 resultType=2（AIResultTypeEnum.FAQ）且答案 == faq_kb_9 里的 faq_answer 原文
     备注：我的库要走答案层必须改助手配置（越界），故答案层在 kb_9 只读取证并标注。
"""
import json
import re
import time

import requests

import ag6_lib as L

SSE_TYPES = {1: "文档", 2: "FAQ", 3: "敏感词?", 4: "..."}


def faq_list_all(s, token, kb_id, folder):
    c, b, _ = L.faq_list(s, token, kb_id, page_no=1, page_size=200,
                         file_id=folder, folder_id=folder)
    return (b.get("data") or {}).get("records") or []


def faq_result_list(primitive, question, enabled_faq=True, top_k=10):
    r = L.retrieval(primitive, question, top_k=top_k, enabled_faq=enabled_faq)
    data = ((r.get("body") or {}).get("data") or {}) if isinstance(r.get("body"), dict) else {}
    return {"http": r.get("http"), "elapsed": r.get("elapsed"),
            "faq_result_list": data.get("faq_result_list"),
            "n_documents": len(data.get("documents_list") or []),
            "msg": (r.get("body") or {}).get("msg") if isinstance(r.get("body"), dict) else None,
            "raw_data_keys": sorted(data.keys())}


def ask_re(token, content, session_id, query_id, timeout=600):
    payload = {"sessionId": session_id, "queryId": query_id, "content": content,
               "type": "text", "sysType": "KNO_INDEX", "configId": 1}
    r = requests.post(L.GATEWAY + "/qa/ai/question_re", json=payload,
                      headers={"Authorization": token, "Accept": "text/event-stream",
                               "Content-Type": "application/json", "User-Agent": L.UA},
                      stream=True, timeout=timeout)
    raw = b""
    frames = []
    for line in r.iter_lines():
        if not line:
            continue
        raw += line + b"\n"
        t = line.decode("utf-8", "replace")
        frames.append(t[:600])
    return {"http": r.status_code, "frames": frames[:40], "text": raw.decode("utf-8", "replace")[:12000],
            "n_frames": len(frames)}


def main():
    st = L.load_state()
    kb_id, primitive, folder = st["kb_id"], st["primitive"], st["faq_file_id"]
    s, token = L.login()
    ev = {"time": L.now(), "kb_id": kb_id, "primitive": primitive}

    recs = faq_list_all(s, token, kb_id, folder)
    enabled = [r for r in recs if r.get("status") == 1 and r.get("question")]
    ev["counts"] = {"list_total": len(recs), "enabled": len(enabled)}
    target = enabled[0]
    q, a = target["question"], target["answer"]
    ev["target"] = {"pk": target.get("pk"), "question": q, "answer": a,
                    "status": target.get("status")}

    # L1 命中
    l1 = faq_result_list(primitive, q, enabled_faq=True)
    hits = l1.get("faq_result_list") or []
    match = [h for h in hits if h.get("faq_question") == q]
    ev["L1"] = {"query": q, "http": l1["http"], "elapsed": l1["elapsed"],
                "n_faq_hits": len(hits), "faq_result_list": hits[:5],
                "exact_question_match": bool(match),
                "answer_char_equal": bool(match) and match[0].get("faq_answer") == a,
                "answer_got": match[0].get("faq_answer") if match else None,
                "score": match[0].get("score") if match else None,
                "n_documents": l1["n_documents"], "msg": l1["msg"]}

    # L2 对照（关闭 FAQ 通道）
    l2 = faq_result_list(primitive, q, enabled_faq=False)
    ev["L2"] = {"http": l2["http"], "n_faq_hits": len(l2.get("faq_result_list") or []),
                "faq_result_list": l2.get("faq_result_list"),
                "n_documents": l2["n_documents"]}

    # L3 答案层（kb_9，只读）
    k9 = L.es_docs("faq_kb_9", size=30)
    k9_faqs = []
    for h in (k9.get("hits", {}).get("hits") or []):
        m = h["_source"].get("metadata") or {}
        if m.get("question") and m.get("answer"):
            k9_faqs.append({"pk": m.get("pk"), "status": m.get("status"),
                            "question": m.get("question"), "answer": m.get("answer")})
    ev["kb9_faqs"] = k9_faqs[:10]
    cand = next((x for x in k9_faqs if x.get("status") == 1), None)
    if cand:
        sid = f"ag6-faq-{int(time.time()*1000)}"
        qid = f"ag6q-{int(time.time()*1000)}"
        resp = ask_re(token, cand["question"], sid, qid)
        text = resp["text"]
        ev["L3"] = {"query": cand["question"], "expected_answer": cand["answer"],
                    "http": resp["http"], "n_frames": resp["n_frames"],
                    "frames_sample": resp["frames"][:12],
                    "answer_char_equal": cand["answer"] in text,
                    "resultType_2_present": bool(re.search(r'"?resultType"?\s*:\s*"?2"?', text)),
                    "text": text[:4000]}
    else:
        ev["L3"] = {"skipped": "kb_9 无启用状态的 FAQ"}

    p = L.dump("S9-5-direct.json", ev, "S9")
    print(json.dumps({"evidence": p, "target": ev["target"],
                      "L1": {k: ev["L1"][k] for k in ("http", "n_faq_hits",
                                                      "exact_question_match",
                                                      "answer_char_equal", "score",
                                                      "n_documents", "msg")},
                      "L2": {"n_faq_hits": ev["L2"]["n_faq_hits"],
                             "n_documents": ev["L2"]["n_documents"]},
                      "L3": {k: ev["L3"].get(k) for k in ("query", "expected_answer",
                                                          "http", "n_frames",
                                                          "answer_char_equal",
                                                          "resultType_2_present")}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
