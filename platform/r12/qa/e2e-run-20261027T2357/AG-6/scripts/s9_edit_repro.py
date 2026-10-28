#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9-3 复现：编辑问答对（/faq/update）——对"抽取生成的 FAQ"再复现一次，确认不是只有 API 新建的才失败。

同时记录：失败前后的 ES 条数 / 列表条数（判"编辑失败且数据被删掉"）。
"""
import json
import time

import ag6_lib as L


def snap(s, token, kb_id, folder, primitive, pk):
    es = L.es_count(f"faq_{primitive}")
    c, b, _ = L.faq_list(s, token, kb_id, page_no=1, page_size=100,
                         file_id=folder, folder_id=folder)
    d = (b.get("data") or {}) if isinstance(b, dict) else {}
    pks = {str(r.get("pk")) for r in (d.get("records") or [])}
    return {"es_count": es.get("count"), "list_total": d.get("total"),
            "pk_in_list": str(pk) in pks}


def main():
    st = L.load_state()
    kb_id, primitive, folder = st["kb_id"], st["primitive"], st["faq_file_id"]
    s, token = L.login()

    # 挑一条"抽取生成"的 FAQ（不是我 /faq/create 建的）
    c, b, _ = L.faq_list(s, token, kb_id, page_no=1, page_size=100,
                         file_id=folder, folder_id=folder)
    recs = (b.get("data") or {}).get("records") or []
    mine = {str(p["pk"]) for p in st["faq_pairs"]}
    extracted = [r for r in recs if str(r.get("pk")) not in mine]
    target = extracted[0]
    pk = target["pk"]
    old_q, old_a = target["question"], target["answer"]
    print("[target-extracted]", pk, old_q)

    before = snap(s, token, kb_id, folder, primitive, pk)
    new_q = old_q + "（编辑校验-抽取项）"
    new_a = old_a + " 【AG6-EDIT-EXTRACTED】"
    code, body, el = L.faq_update(s, token, kb_id,
                                 [{"pk": int(pk), "question": new_q, "answer": new_a,
                                   "status": target.get("status")}],
                                 file_id=folder)
    time.sleep(3)
    after = snap(s, token, kb_id, folder, primitive, pk)
    ev = {"time": L.now(), "case": "edit extracted FAQ", "kb_id": kb_id,
          "target": {"pk": pk, "question": old_q, "answer": old_a},
          "update_http": code, "update_body": body, "elapsed": el,
          "before": before, "after": after,
          "verdict": {"http_ok": code == 200 and isinstance(body, dict) and body.get("success"),
                      "persisted": after["pk_in_list"],
                      "data_lost": before["pk_in_list"] and not after["pk_in_list"]}}
    p = L.dump("S9-3-edit-extracted-repro.json", ev, "S9")
    print(json.dumps({"evidence": p, "http": code, "body": body,
                      "before": before, "after": after,
                      "verdict": ev["verdict"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
