#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S14 收敛（第二轮，隔离库内单文件闭环）：
  A 同名新版本：旧版本 chunk 是否被淘汰（用"两版共有内容"作探针，避免只测新版独有标记而漏掉重复召回）
  B 重新解析：chunk pk / create_time 是否换代（用前端同款 payload，含 file_path）
  C 删除后：检索 + ES + 列表三处归零
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, api, es_docs, file_delete,
                     file_list, file_status, login, now, parse_tasks, retrieval, upload)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
KB_NAME = f"kb_{KB_ID}"
BASE = os.path.join(EVID, "fixtures", "converge")
MARK = "AG5-CONV-MARK-9001"
NAME = "AG5-CONV2-doc.docx"
SHARED_Q = "智造贷 适用对象 制造业中小微企业"     # V0/V1 共有内容
IDX = [KB_NAME, f"table_chunks_kb_{KB_ID}", f"table_summary_kb_{KB_ID}"]


def wait_terminal(s, token, fid, max_wait=240):
    t0 = time.time()
    last = None
    while time.time() - t0 < max_wait:
        c, b = file_status(s, token, fid)
        v = b.get("data") if isinstance(b, dict) else b
        last = v
        if v in (FILE_OK, FILE_FAIL):
            return v, round(time.time() - t0, 1)
        time.sleep(1.5)
    return last, round(time.time() - t0, 1)


def es_docs_of(fid):
    out = {}
    for idx in IDX:
        j = es_docs(idx, size=100, query={"term": {"metadata.file_id": int(fid)}})
        if "error" in j:
            out[idx] = {"error": str(j["error"])[:80]}
            continue
        hits = j.get("hits", {}).get("hits", [])
        out[idx] = [{"pk": h["_source"]["metadata"].get("pk"),
                     "version": h["_source"]["metadata"].get("version"),
                     "create_time": h["_source"]["metadata"].get("create_time"),
                     "update_time": h["_source"]["metadata"].get("update_time")} for h in hits]
    return out


def rtv(q, rerank=False):
    r = retrieval(KB_NAME, q, top_k=10, policy=1, rerank=rerank)
    b = r.get("body") or {}
    data = b.get("data") or {}
    raw = (data.get("documents_list") or []) if isinstance(data, dict) else []
    docs = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        md = d.get("metadata") or {}
        txt = d.get("page_content") or ""
        docs.append({"pk": md.get("pk"), "version": md.get("version"),
                     "file_path": md.get("file_path"),
                     "has_marker": MARK in txt, "score": d.get("score"),
                     "text": txt[:60]})
    return {"n": len(docs), "docs": docs, "msg": str(b.get("msg"))[:100],
            "rerank": rerank, "http": r.get("http"), "elapsed": r.get("elapsed")}


def upload_v(ftype, path):
    s, token = login()
    code, body, meta = upload(s, token, KB_ID, path, fname=NAME, ftype=ftype)
    fid = ((body.get("data") or [{}])[0] or {}).get("id") if isinstance(body, dict) else None
    st, w = wait_terminal(s, token, fid) if fid else (None, 0)
    return {"http": code, "file_id": fid, "status": FILE_STATUS.get(st), "waited": w,
            "resp": body}


def main():
    s, token = login()
    out = {"ts": now(), "kb": KB_NAME, "name": NAME, "marker": MARK, "shared_query": SHARED_Q}

    # ---------------- A 同名新版本 ----------------
    A = {}
    A["v0"] = upload_v("OVERWRITE", os.path.join(BASE, "v0", "R12FIX-product-loan.docx"))
    A["v0_es"] = es_docs_of(A["v0"]["file_id"])
    A["q_shared_v0_only"] = rtv(SHARED_Q)
    A["v1"] = upload_v("NEWVERSION", os.path.join(BASE, "v1", "R12FIX-product-loan.docx"))
    A["v1_es"] = es_docs_of(A["v1"]["file_id"])
    A["v0_es_after_v1"] = es_docs_of(A["v0"]["file_id"])
    A["q_marker_after_v1"] = rtv(MARK)
    A["q_shared_after_v1"] = rtv(SHARED_Q)
    A["q_shared_after_v1_rerank"] = rtv(SHARED_Q, rerank=True)
    c, b = file_list(s, token, KB_ID)
    recs = ((b.get("data") or {}).get("records") or [])
    A["list_group"] = [{"group": r.get("id"),
                        "kbFiles": [{"id": k.get("id"), "version": k.get("version"),
                                     "status": k.get("status")} for k in (r.get("kbFiles") or [])]}
                       for r in recs if NAME in json.dumps(r, ensure_ascii=False)]
    # 判定：新内容必须命中 V1；共有内容若同时给 V0+V1 → 旧版本仍在召回（重复/悬空引用风险）
    shared_versions = sorted({str(d["version"]) for d in A["q_shared_after_v1"]["docs"]
                              if NAME.split(".")[0] in str(d["file_path"] or "")})
    A["shared_versions_returned"] = shared_versions
    A["old_version_still_recalled"] = "V0" in shared_versions and "V1" in shared_versions
    A["marker_hits_v1"] = sum(1 for d in A["q_marker_after_v1"]["docs"] if d["has_marker"])
    out["A_version"] = A

    # ---------------- B 重新解析换代 ----------------
    B = {"file_id": A["v1"]["file_id"]}
    B["es_before"] = es_docs_of(B["file_id"])
    B["retrieval_before"] = rtv(MARK)
    r = [x for x in A["list_group"] if x["kbFiles"]][0]
    payload = {"files": [{"folder_id": None,
                          "file_path": f"r12-rag/{KB_NAME}/{NAME}/V1/{NAME}",
                          "file_id": str(B["file_id"]), "parent_file_name": NAME}],
               "folder_ids": [], "knowledge_base_name": KB_NAME,
               "knowledge_base_id": str(KB_ID), "override": True, "is_all": False}
    code, body = api(s, "POST", "/index/knowledgeBase/file/filesParse", token, json=payload)
    B["reparse"] = {"http": code, "body": body, "payload": payload, "req_time": now()}
    st, w = wait_terminal(s, token, B["file_id"])
    B["after_status"] = FILE_STATUS.get(st)
    B["waited"] = w
    B["tasks"] = [(t["task_id"], t["status_name"], t["start_time"], t["end_time"])
                  for t in (parse_tasks([B["file_id"]]).get("tasks") or [])]
    B["es_after"] = es_docs_of(B["file_id"])
    B["retrieval_after"] = rtv(MARK)

    def pks(d):
        return sorted([x["pk"] for v in d.values() if isinstance(v, list) for x in v if x.get("pk")])

    def cts(d):
        return sorted([x["create_time"] for v in d.values() if isinstance(v, list)
                       for x in v if x.get("create_time")])

    B["pk_before"], B["pk_after"] = pks(B["es_before"]), pks(B["es_after"])
    B["ct_before"], B["ct_after"] = cts(B["es_before"]), cts(B["es_after"])
    B["pk_changed"] = bool(B["pk_before"]) and bool(B["pk_after"]) and not (set(B["pk_before"]) & set(B["pk_after"]))
    B["ct_advanced"] = bool(B["ct_before"]) and bool(B["ct_after"]) and max(B["ct_after"]) > max(B["ct_before"])
    B["verdict"] = "PASS" if (B["pk_changed"] and B["retrieval_after"]["n"] > 0) else "FAIL"
    out["B_reparse"] = B

    # ---------------- C 删除后收敛 ----------------
    C = {"before_retrieval_marker": rtv(MARK), "before_es": {
        "v0": es_docs_of(A["v0"]["file_id"]), "v1": es_docs_of(A["v1"]["file_id"])}}
    dels = []
    for fid in (A["v0"]["file_id"], A["v1"]["file_id"]):
        code, body = file_delete(s, token, fid)
        dels.append({"file_id": fid, "http": code, "success": (body or {}).get("success")})
    C["delete_calls"] = dels
    time.sleep(6)
    C["after"] = {"retrieval_marker": rtv(MARK), "retrieval_shared": rtv(SHARED_Q),
                  "es_v0": es_docs_of(A["v0"]["file_id"]),
                  "es_v1": es_docs_of(A["v1"]["file_id"])}
    c, b = file_list(s, token, KB_ID)
    C["still_in_file_list"] = NAME in json.dumps(b, ensure_ascii=False)
    C["verdict"] = "PASS" if (C["after"]["retrieval_marker"]["n"] == 0
                              and not C["still_in_file_list"]) else "FAIL"
    out["C_delete"] = C

    p = os.path.join(EVID, "S14", f"S14b-converge-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("A v0", A["v0"]["file_id"], A["v0"]["status"], "| v1", A["v1"]["file_id"], A["v1"]["status"])
    print("A 共有内容召回版本:", shared_versions, "旧版本仍召回:", A["old_version_still_recalled"],
          "| marker命中:", A["marker_hits_v1"])
    print("A V0 chunk 在 V1 之后是否还在:", {k: len(v) for k, v in A["v0_es_after_v1"].items() if isinstance(v, list)})
    print("B pk", B["pk_before"], "->", B["pk_after"], "changed", B["pk_changed"],
          "| ct", B["ct_before"], "->", B["ct_after"], "advanced", B["ct_advanced"], "->", B["verdict"])
    print("C 删除后 marker命中", C["after"]["retrieval_marker"]["n"], "列表仍含", C["still_in_file_list"],
          "->", C["verdict"])
    print("[evidence]", p)


if __name__ == "__main__":
    main()
