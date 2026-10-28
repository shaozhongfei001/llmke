#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S9-4（接口层）：/faq/changeStatus 真翻转 + ES 侧 status 是否同步（用于判"状态真翻转"）。
"""
import json
import time

import ag6_lib as L


def es_doc_status(primitive, pk):
    j = L.es_docs(f"faq_{primitive}", size=200)
    if "error" in j:
        return {"error": j["error"]}
    for h in j.get("hits", {}).get("hits", []):
        if str(h["_source"]["metadata"].get("pk")) == str(pk):
            return {"found": True, "status": h["_source"]["metadata"].get("status"),
                    "update_time": h["_source"]["metadata"].get("update_time")}
    return {"found": False}


def list_row(s, token, kb_id, folder, pk):
    c, b, _ = L.faq_list(s, token, kb_id, page_no=1, page_size=100,
                         file_id=folder, folder_id=folder)
    for r in (b.get("data") or {}).get("records") or []:
        if str(r.get("pk")) == str(pk):
            return r
    return None


def main():
    st = L.load_state()
    kb_id, primitive, folder = st["kb_id"], st["primitive"], st["faq_file_id"]
    s, token = L.login()
    tgt = st["faq_pairs"][1]           # item 002
    pk, related = tgt["pk"], tgt["relatedPk"]
    ev = {"time": L.now(), "kb_id": kb_id, "target": {"i": 2, "pk": pk, "relatedPk": related,
                                                      "q": tgt["q"]}, "steps": []}

    def step(name, **kw):
        row = list_row(s, token, kb_id, folder, pk)
        ev["steps"].append({"step": name, "list_status": None if row is None else row.get("status"),
                            "es": es_doc_status(primitive, pk), **kw})
        print(name, json.dumps(ev["steps"][-1], ensure_ascii=False)[:300])

    step("before")

    c, b, el = L.faq_change_status(s, token, kb_id, 0, related_pks=[related])
    time.sleep(2)
    step("disable(0)", http=c, body=b, elapsed=el)

    c2, b2, el2 = L.faq_change_status(s, token, kb_id, 1, related_pks=[related])
    time.sleep(2)
    step("enable(1)", http=c2, body=b2, elapsed=el2)

    ev["verdict"] = {"disable_ok": c == 200 and isinstance(b, dict) and b.get("success"),
                     "enable_ok": c2 == 200 and isinstance(b2, dict) and b2.get("success")}
    p = L.dump("S9-4-toggle-api.json", ev, "S9")
    print(json.dumps({"evidence": p, "verdict": ev["verdict"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
