#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 / S9-1 夹具（修正）：按前端真实路径创建问答对（fileId + folderId 同时给）。

同时清掉上一轮"只给 folderId"的 12+1 条（它们在 FAQ 文件视角列表里不可见，
但确实落进 ES faq_kb_38 —— 这一现象作为观察项记录在报告 §缺陷/观察）。
"""
import json
import time

import ag6_lib as L


def es_total(primitive):
    return (L.es_count(f"faq_{primitive}") or {}).get("count")


def main():
    st = L.load_state()
    kb_id, primitive, folder = st["kb_id"], st["primitive"], st["faq_file_id"]
    s, token = L.login()
    ev = {"time": L.now(), "kb_id": kb_id, "faq_file_id": folder}

    # ---- 1) 清掉 folder-only 的 13 条（12 + 探针）
    orphan_pks = [p["relatedPk"] for p in st["faq_pairs"]]
    es0 = es_total(primitive)
    c, b, _ = L.faq_delete(s, token, kb_id, related_pks=orphan_pks)
    time.sleep(2)
    es1 = es_total(primitive)
    probe = L.faq_list(s, token, kb_id, page_no=1, page_size=100, file_id=folder,
                       folder_id=folder)
    ev["delete_orphans"] = {"requested_related_pks": len(orphan_pks), "http": c, "body": b,
                            "es_before": es0, "es_after": es1,
                            "file_scope_total_after": ((probe[1].get("data") or {})
                                                       .get("total"))}
    print("[del-orphans]", json.dumps(ev["delete_orphans"], ensure_ascii=False)[:400])

    # 探针单独删（它带 fileId，删除路径不同）
    c2, b2, _ = L.faq_delete(s, token, kb_id, related_pks=["2115289396757008387"])
    time.sleep(2)
    es2 = es_total(primitive)
    ev["delete_probe"] = {"http": c2, "body": b2, "es_after": es2}
    print("[del-probe]", c2, json.dumps(b2, ensure_ascii=False)[:200], "es=", es2)

    # ---- 2) 按前端真实 payload 建 12 条（fileId + folderId）
    stamp = time.strftime("%H%M%S")
    made = []
    for i in range(1, 13):
        q = f"AG6Q-{stamp}-{i:03d} 智造贷的最高授信额度是多少？"
        a = f"AG6A-{stamp}-{i:03d} 最高授信额度为 8000 万元。"
        c, b, _ = L.faq_create(s, token, kb_id, [{"question": q, "answer": a}],
                               folder_id=folder, file_id=folder)
        rec = (b.get("data") or [None])[0] if isinstance(b, dict) else None
        made.append({"i": i, "http": c, "rec": rec, "q": q, "a": a})
        time.sleep(0.15)
    time.sleep(2)
    lst = L.faq_list(s, token, kb_id, page_no=1, page_size=10, file_id=folder, folder_id=folder)
    d = (lst[1].get("data") or {}) if isinstance(lst[1], dict) else {}
    ev["created"] = [{"i": m["i"], "http": m["http"],
                      "pk": (m["rec"] or {}).get("pk"),
                      "relatedPk": (m["rec"] or {}).get("relatedPk"), "q": m["q"], "a": m["a"]}
                     for m in made]
    ev["list_file_scope"] = {"total": d.get("total"), "pages": d.get("pages"),
                             "size": d.get("size"), "len_page1": len(d.get("records") or [])}
    ev["es_total_final"] = es_total(primitive)
    p = L.dump("S9-1-fixture-v2.json", ev, "S9")
    st["faq_pairs"] = ev["created"]
    st["stamp3"] = stamp
    L.save_state(st)
    print(json.dumps({"evidence": p, "list": ev["list_file_scope"],
                      "es_total_final": ev["es_total_final"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
