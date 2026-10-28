#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9-6 前置：建一条"检索可唯一定位"的问答对（避免与其他问答对竞争），检索一次确认能命中。

随后由 s9_ui_delete.js 在页面删除，再由 s9_delete_verify.py 复核"列表与检索都不再返回"。
"""
import json
import time

import ag6_lib as L

MARK = "AG6-UNIQUE-" + time.strftime("%H%M%S")
Q = f"{MARK} 蓝色独角兽保证金比例是多少？"
A = f"{MARK} 蓝色独角兽保证金比例为 42.7%。"


def hits(question):
    r = L.retrieval(L.load_state()["primitive"], question, top_k=10, enabled_faq=True)
    d = (r.get("body") or {}).get("data") or {}
    return {"http": r.get("http"), "faq_result_list": d.get("faq_result_list"),
            "n_documents": len(d.get("documents_list") or [])}


def main():
    st = L.load_state()
    kb_id, primitive, folder = st["kb_id"], st["primitive"], st["faq_file_id"]
    s, token = L.login()
    c, b, _ = L.faq_create(s, token, kb_id, [{"question": Q, "answer": A}],
                           folder_id=folder, file_id=folder)
    rec = (b.get("data") or [None])[0]
    time.sleep(2)
    before = hits(Q)
    ev = {"time": L.now(), "mark": MARK, "question": Q, "answer": A,
          "create_http": c, "create_resp": rec, "retrieval_before": before,
          "hit_before": any(A == h.get("faq_answer") for h in (before.get("faq_result_list") or []))}
    p = L.dump("S9-6-delete-prep.json", ev, "S9")
    st["unique_faq"] = {"mark": MARK, "question": Q, "answer": A,
                        "pk": (rec or {}).get("pk"),
                        "relatedPk": (rec or {}).get("relatedPk")}
    L.save_state(st)
    print(json.dumps({"evidence": p, "pk": (rec or {}).get("pk"),
                      "hit_before": ev["hit_before"],
                      "faq_hits": len(before.get("faq_result_list") or [])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
