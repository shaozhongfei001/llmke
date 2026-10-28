#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 / S9-2：从语料抽取 FAQ（extractFQA）→ 判"条数 > 0"，不允许"报成功但 0 条"。
后续 S9-1：建 12 条确定性问答对用于分页/编辑/启停/删除/直答。
"""
import json
import time

import ag6_lib as L

EXTRACT_OK, EXTRACT_FAIL = 3, 4
ENDPOINT = "http://127.0.0.1:19000/"


def flatten(fl):
    d = fl.get("data") if isinstance(fl, dict) else None
    rows = d.get("records") if isinstance(d, dict) else (d if isinstance(d, list) else [])
    out = []
    for r in rows or []:
        if r.get("kbFiles"):
            out.extend(r["kbFiles"])
        else:
            out.append(r)
    return out


def poll_extract(s, token, fid, timeout=900):
    t0 = time.time()
    seen = []
    while time.time() - t0 < timeout:
        code, body, _ = L.faq_extract_status(s, token, fid)
        v = body.get("data") if isinstance(body, dict) else None
        if isinstance(v, dict):
            v = v.get("faqExtractStatus")
        seen.append({"t": round(time.time() - t0, 1), "faqExtractStatus": v})
        if v in (EXTRACT_OK, EXTRACT_FAIL):
            return {"final": v, "waited": round(time.time() - t0, 1), "samples": seen}
        time.sleep(3)
    return {"final": None, "waited": round(time.time() - t0, 1), "samples": seen}


def main():
    st = L.load_state()
    kb_id, primitive = st["kb_id"], st["primitive"]
    s, token = L.login()

    code, fl, _ = L.file_list(s, token, kb_id)
    files = flatten(fl)
    L.dump("S9-2-filelist-flat.json", files, "S9")
    src = next(f for f in files if f["status"] == 3 and "loan" in f["fileName"])
    key = (src.get("filePath") or "").replace(ENDPOINT, "")
    print("[src]", src["id"], src["fileName"], key, "faqExtractStatus=",
          src.get("faqExtractStatus"))

    before = L.faq_list(s, token, kb_id, page_no=1, page_size=10)
    d = before[1].get("data") if isinstance(before[1], dict) else None
    before_total = d.get("total") if isinstance(d, dict) else None
    es_before = L.es_count(f"faq_{primitive}")

    t0 = time.time()
    ex_code, ex_body, ex_el = L.faq_extract(
        s, token, kb_id, primitive, src["id"], key,
        file_size=str(src.get("fileSize") or "0MB"),
        parent_name=src["fileName"])
    poll = poll_extract(s, token, src["id"])
    total_elapsed = round(time.time() - t0, 1)

    after = L.faq_list(s, token, kb_id, page_no=1, page_size=100)
    da = after[1].get("data") if isinstance(after[1], dict) else None
    after_total = da.get("total") if isinstance(da, dict) else None
    recs = (da.get("records") if isinstance(da, dict) else None) or []
    es_after = L.es_count(f"faq_{primitive}")
    st_after = [x for x in flatten(L.file_list(s, token, kb_id)[1]) if x["id"] == src["id"]]

    ev = {"time": L.now(), "kb_id": kb_id, "primitive": primitive,
          "source": {"file_id": src["id"], "file_name": src["fileName"],
                     "file_path_key": key, "faqExtractStatus_before": src.get("faqExtractStatus")},
          "extract_endpoint": "POST /index/knowledgeBase/file/extractFQA",
          "extract_http": ex_code, "extract_body": ex_body, "extract_elapsed": ex_el,
          "extract_status_poll": poll, "total_elapsed": total_elapsed,
          "faq_total_before": before_total, "faq_total_after": after_total,
          "es_index": f"faq_{primitive}", "es_before": es_before, "es_after": es_after,
          "file_row_after": st_after,
          "faq_extracted_sample": recs[:5]}
    p = L.dump("S9-2-faq-extract.json", ev, "S9")
    print("[extract]", json.dumps({"evidence": p, "http": ex_code,
                                   "body": ex_body, "status": poll["final"],
                                   "waited": poll["waited"], "elapsed": total_elapsed,
                                   "faq_total_before": before_total,
                                   "faq_total_after": after_total,
                                   "es_before": es_before, "es_after": es_after},
                                  ensure_ascii=False))

    # ---- 建 12 条确定性问答对（稳定夹具）
    stamp = time.strftime("%H%M%S")
    made = []
    for i in range(1, 13):
        q = f"AG6Q-{stamp}-{i:03d} 智造贷的最高授信额度是多少？"
        a = f"AG6A-{stamp}-{i:03d} 最高授信额度为 8000 万元。"
        code, body, _ = L.faq_create(s, token, kb_id, [{"question": q, "answer": a}])
        rec = None
        if isinstance(body, dict):
            dd = body.get("data")
            if isinstance(dd, list) and dd:
                rec = dd[0]
            elif isinstance(dd, dict):
                rec = dd
        made.append({"i": i, "http": code, "resp": body, "rec": rec})
        time.sleep(0.2)
    L.dump("S9-1-faq-create.json", made, "S9")
    st["faq_created"] = made
    st["stamp"] = stamp
    st["extract_ev"] = ev
    L.save_state(st)
    print("[create]", [(m["i"], m["http"], (m["rec"] or {}).get("pk")) for m in made])

    lst = L.faq_list(s, token, kb_id, page_no=1, page_size=10)
    dl = lst[1].get("data") if isinstance(lst[1], dict) else None
    print("[list] total =", dl.get("total") if isinstance(dl, dict) else None,
          "len =", len((dl or {}).get("records") or []))


if __name__ == "__main__":
    main()
