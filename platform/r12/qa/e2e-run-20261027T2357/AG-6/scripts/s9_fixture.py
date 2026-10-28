#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 / S9-1 夹具：在 FAQ 文件（folder_id=525，由抽取生成）下建 12 条确定性问答对。

同时复核一条已观测事实：不带 folder/file 的 /faq/create 返回 200+pk，但任何列表都看不到（孤立）。
"""
import json
import time

import ag6_lib as L


def lst(s, token, kb_id, **kw):
    c, b, e = L.faq_list(s, token, kb_id, **kw)
    d = (b.get("data") or {}) if isinstance(b, dict) else {}
    return {"http": c, "total": d.get("total"),
            "types": sorted({r.get("dataType") for r in (d.get("records") or [])}),
            "records": d.get("records") or [], "raw_total": d.get("total"),
            "size": d.get("size"), "pages": d.get("pages"), "body": b}


def main():
    st = L.load_state()
    kb_id = st["kb_id"]
    s, token = L.login()

    # FAQ 文件（抽取产生的 parse_type=5 行）
    rows = L.mysql_rows("select id,file_name,parse_type,faq_extract_status from "
                        "knowledge_base_list where kb_id=%s order by id" % int(kb_id))["rows"]
    faq_row = next((r for r in rows if r[2] == "5"), None)
    folder_id = int(faq_row[0])
    print("[faq-file]", faq_row)

    stamp = time.strftime("%H%M%S")
    made = []
    for i in range(1, 13):
        q = f"AG6Q-{stamp}-{i:03d} 智造贷的最高授信额度是多少？"
        a = f"AG6A-{stamp}-{i:03d} 最高授信额度为 8000 万元。"
        c, b, _ = L.faq_create(s, token, kb_id, [{"question": q, "answer": a}], folder_id)
        rec = None
        if isinstance(b, dict):
            d = b.get("data")
            if isinstance(d, list) and d:
                rec = d[0]
            elif isinstance(d, dict):
                rec = d
        made.append({"i": i, "http": c, "resp": b, "rec": rec, "q": q, "a": a})
        time.sleep(0.15)
    L.dump("S9-1-faq-create-under-folder.json", made, "S9")
    print("[create]", [(m["i"], m["http"], (m["rec"] or {}).get("pk")) for m in made])

    time.sleep(2)
    root = lst(s, token, kb_id, page_no=1, page_size=10)
    fold = lst(s, token, kb_id, page_no=1, page_size=10, folder_id=folder_id)
    fold_all = lst(s, token, kb_id, page_no=1, page_size=100, folder_id=folder_id)
    es = L.es_count(f"faq_{st['primitive']}")

    ev = {"time": L.now(), "kb_id": kb_id, "faq_file_id": folder_id,
          "created": [{"i": m["i"], "pk": (m["rec"] or {}).get("pk"),
                       "relatedPk": (m["rec"] or {}).get("relatedPk"),
                       "q": m["q"], "a": m["a"]} for m in made],
          "list_root": {"http": root["http"], "total": root["total"],
                        "types": root["types"],
                        "rows": [{k: r.get(k) for k in
                                  ("dataType", "fileId", "folderId", "fileName", "question")}
                                 for r in root["records"]]},
          "list_folder_page1": {"total": fold["total"], "len": len(fold["records"]),
                                "types": fold["types"], "pages": fold["pages"],
                                "size": fold["size"]},
          "list_folder_all": {"total": fold_all["total"], "len": len(fold_all["records"])},
          "es": es}
    p = L.dump("S9-1-fixture-and-list.json", ev, "S9")
    st["faq_file_id"] = folder_id
    st["faq_pairs"] = ev["created"]
    st["stamp2"] = stamp
    L.save_state(st)
    print(json.dumps({"evidence": p, "root_total": root["total"],
                      "folder_total": fold["total"],
                      "folder_page1_len": len(fold["records"]),
                      "folder_pages": fold["pages"], "es": es}, ensure_ascii=False))


if __name__ == "__main__":
    main()
