#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9-6 复核：删除后 ① 列表不再返回 ② 检索不再返回该条答案 ③ ES 文档消失。"""
import json
import time

import ag6_lib as L


def main():
    st = L.load_state()
    kb_id, primitive, folder = st["kb_id"], st["primitive"], st["faq_file_id"]
    tgt, uni = st["del_target"], st["unique_faq"]
    s, token = L.login()
    time.sleep(1)

    # ① 列表
    c, b, _ = L.faq_list(s, token, kb_id, page_no=1, page_size=200,
                         file_id=folder, folder_id=folder)
    recs = (b.get("data") or {}).get("records") or []
    in_list = any(str(r.get("pk")) == str(tgt["pk"]) for r in recs)

    # ② 检索（用删除前能召回该答案的那条唯一问题）
    r = L.retrieval(primitive, uni["question"], top_k=10, enabled_faq=True)
    d = (r.get("body") or {}).get("data") or {}
    fl = d.get("faq_result_list") or []
    still_returned = any(h.get("faq_answer") == tgt["answer"] for h in fl)

    # ③ ES
    j = L.es_docs(f"faq_{primitive}", size=500)
    es_has = False
    if "error" not in j:
        es_has = any(str(h["_source"]["metadata"].get("pk")) == str(tgt["pk"])
                     for h in j.get("hits", {}).get("hits", []))

    ev = {"time": L.now(), "kb_id": kb_id, "deleted": tgt,
          "list_total": len(recs), "pk_in_list": in_list,
          "retrieval_query": uni["question"], "retrieval_faq_result_list": fl,
          "deleted_answer_still_returned": still_returned,
          "es_has_pk": es_has,
          "verdict": {"list_clean": not in_list, "retrieval_clean": not still_returned,
                      "es_clean": not es_has}}
    p = L.dump("S9-6-delete-verify.json", ev, "S9")
    print(json.dumps({"evidence": p, "verdict": ev["verdict"],
                      "list_total": ev["list_total"],
                      "retrieval_faq_hits": len(fl)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
