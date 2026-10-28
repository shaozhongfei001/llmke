#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S14 收敛：上传新版本 / 解析完成后 / 删除之后，检索与引用是否跟着收敛。

三个子场景（每步都取存储层事实，不看接口 200）：
  C1 同名新版本：V0 内容与 V1 内容用唯一标记区分 → 检索必须只命中 V1（source 带 /V1/）
  C2 删除后：列表、ES、检索三处都不再出现（且不是"接口 200 但没删干净"）
  C3 重新解析后：同一查询的 chunk pk 必须换代（旧 pk 消失、新 pk 存在），
     否则"引用"仍是旧文本（页面看着是新的，引用是旧的）

说明（限制，如实记录）：
  答案级引用 /qa/ai/question 绑定助手配置 configId=1（指向 kb_9），本角色禁止改配置，
  因此对自建库的答案级引用不作断言；引用内容由检索结果驱动，收敛结论在检索层取证。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, FIXTURES, api, es_docs, file_delete,
                     file_rows, file_status, file_list, login, now, parse_tasks, retrieval, upload)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
KB_NAME = f"kb_{KB_ID}"
BASE = os.path.join(EVID, "fixtures", "converge")
MARK = "AG5-CONV-MARK-9001"
NAME = "AG5-CONV-doc.docx"
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


def docs_for(fid):
    out = {}
    for idx in IDX:
        j = es_docs(idx, size=200, query={"term": {"metadata.file_id": int(fid)}})
        if "error" in j:
            out[idx] = {"error": str(j["error"])[:100]}
            continue
        hits = j.get("hits", {}).get("hits", [])
        out[idx] = {"n": j.get("hits", {}).get("total", {}).get("value"),
                    "docs": [{"pk": h["_source"]["metadata"].get("pk"),
                              "version": h["_source"]["metadata"].get("version"),
                              "file_path": h["_source"]["metadata"].get("file_path"),
                              "create_time": h["_source"]["metadata"].get("create_time"),
                              "text": h["_source"]["page_content"][:70]}
                             for h in hits]}
    return out


def rtv(q, rerank=False):
    """检索并做内容级判定（判据不看条数——rerank 关闭时无阈值过滤，必然返回若干条）。"""
    r = retrieval(KB_NAME, q, top_k=10, policy=1, rerank=rerank)
    b = r.get("body") or {}
    data = b.get("data") or {}
    raw = (data.get("documents_list") or data.get("documents") or []) if isinstance(data, dict) else []
    docs = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        md = d.get("metadata") or {}
        txt = d.get("page_content") or ""
        docs.append({"pk": md.get("pk") or d.get("pk"),
                     "file_path": md.get("file_path") or md.get("source"),
                     "version": md.get("version"),
                     "parent_file_name": md.get("parent_file_name"),
                     "chunk_type": md.get("chunk_type"),
                     "score": d.get("score"),
                     "has_marker": MARK in txt,
                     "text": txt[:80]})
    return {"http": r.get("http"), "code": b.get("code"), "n": len(docs),
            "hit_marker": [d for d in docs if d["has_marker"]],
            "n_marker": sum(1 for d in docs if d["has_marker"]),
            "versions": sorted({str(d["version"]) for d in docs}),
            "sources": sorted({str(d["file_path"])[:60] for d in docs})[:6],
            "docs": docs, "elapsed": r.get("elapsed"), "msg": str(b.get("msg"))[:120]}


def main():
    s, token = login()
    out = {"ts": now(), "kb": KB_NAME, "marker": MARK}

    # ---------------- C1 同名新版本 ----------------
    v0 = os.path.join(BASE, "v0", "R12FIX-product-loan.docx")
    v1 = os.path.join(BASE, "v1", "R12FIX-product-loan.docx")
    c1 = {}
    code, body, meta = upload(s, token, KB_ID, v0, fname=NAME, ftype="OVERWRITE")
    fid0 = ((body.get("data") or [{}])[0] or {}).get("id") if isinstance(body, dict) else None
    st0, w0 = wait_terminal(s, token, fid0)
    c1["v0"] = {"file_id": fid0, "http": code, "status": FILE_STATUS.get(st0),
                "waited": w0, "resp": body}
    c1["v0_docs"] = docs_for(fid0)
    c1["retrieval_marker_before_v1"] = rtv(MARK)
    c1["retrieval_v0_content"] = rtv("最高额度 5000万元 制造业中小微企业 期限 最长3年")

    code, body, meta = upload(s, token, KB_ID, v1, fname=NAME, ftype="NEWVERSION")
    fid1 = ((body.get("data") or [{}])[0] or {}).get("id") if isinstance(body, dict) else None
    st1, w1 = wait_terminal(s, token, fid1) if fid1 else (None, 0)
    c1["v1"] = {"file_id": fid1, "http": code, "status": FILE_STATUS.get(st1),
                "waited": w1, "resp": body}
    c1["v1_docs"] = docs_for(fid1) if fid1 else {}
    c1["retrieval_marker_after_v1"] = rtv(MARK)
    c1["retrieval_v0_content_after_v1"] = rtv("最高额度 5000万元 制造业中小微企业")
    c, b = file_list(s, token, KB_ID)
    recs = ((b.get("data") or {}).get("records") or []) if isinstance(b, dict) else []
    c1["versions_in_list"] = [{"id": r.get("id"), "name": r.get("fileName") or r.get("file_name"),
                               "kbFiles": [{"id": k.get("id"), "version": k.get("version"),
                                            "status": k.get("status")}
                                           for k in (r.get("kbFiles") or [])]}
                              for r in recs if NAME.split(".")[0] in json.dumps(r, ensure_ascii=False)]
    out["C1_new_version"] = c1

    # ---------------- C3 重解析 pk 换代（用 C1 的 V1 文件，避免动别的文件） ----------------
    c3 = {}
    if fid1:
        before = rtv(MARK)
        c3["retrieval_before"] = before
        payload = {"files": [{"folder_id": None, "file_id": str(fid1),
                              "parent_file_name": NAME}],
                   "folder_ids": [], "knowledge_base_name": KB_NAME,
                   "knowledge_base_id": str(KB_ID), "override": True, "is_all": False}
        code, body = api(s, "POST", "/index/knowledgeBase/file/filesParse", token, json=payload)
        c3["reparse"] = {"http": code, "body": body, "req_time": now()}
        st, w = wait_terminal(s, token, fid1)
        c3["after_status"] = FILE_STATUS.get(st)
        c3["waited"] = w
        after = rtv(MARK)
        c3["retrieval_after"] = after
        pk_b = {d["pk"] for d in before["docs"]}
        pk_a = {d["pk"] for d in after["docs"]}
        c3["pk_before"] = sorted(x for x in pk_b if x)
        c3["pk_after"] = sorted(x for x in pk_a if x)
        c3["pk_changed"] = bool(pk_b) and bool(pk_a) and not (pk_b & pk_a)
        c3["tasks"] = [(t["task_id"], t["status_name"]) for t in
                       (parse_tasks([fid1]).get("tasks") or [])]
        c3["verdict"] = "PASS" if (c3["pk_changed"] and c3["retrieval_after"]["n_marker"] > 0) else "FAIL"
    out["C3_reparse_pk"] = c3

    # ---------------- C2 删除后收敛 ----------------
    c2 = {"before": {"retrieval": rtv(MARK),
                     "docs_v0": docs_for(fid0) if fid0 else {},
                     "docs_v1": docs_for(fid1) if fid1 else {}}}
    dels = []
    for fid in [x for x in (fid0, fid1) if x]:
        code, body = file_delete(s, token, fid)
        dels.append({"file_id": fid, "http": code, "body": body})
    c2["delete_calls"] = dels
    time.sleep(5)
    c2["after"] = {"retrieval": rtv(MARK),
                   "docs_v0": docs_for(fid0) if fid0 else {},
                   "docs_v1": docs_for(fid1) if fid1 else {},
                   "rows": (file_rows([x for x in (fid0, fid1) if x]).get("rows") or [])}
    c, b = file_list(s, token, KB_ID)
    txt = json.dumps(b, ensure_ascii=False)
    c2["still_in_list"] = NAME in txt
    c2["verdict"] = "PASS" if (c2["after"]["retrieval"]["n_marker"] == 0 and not c2["still_in_list"]
                               and all(v.get("n") in (0, None) for k, v in c2["after"].items()
                                       if k.startswith("docs_"))) else "FAIL"
    out["C2_after_delete"] = c2

    p = os.path.join(EVID, "S14", f"S14-converge-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("C1 v0:", c1["v0"]["file_id"], c1["v0"]["status"],
          "| v1:", c1["v1"]["file_id"], c1["v1"]["status"])
    print("  marker命中(建V1前):", c1["retrieval_marker_before_v1"]["n_marker"],
          "→ (建V1后):", c1["retrieval_marker_after_v1"]["n_marker"],
          [d["version"] for d in c1["retrieval_marker_after_v1"]["docs"]])
    print("  v0内容查询 建V1前:", [(d["version"], d["score"]) for d in c1["retrieval_v0_content"]["docs"]][:3])
    print("  v0内容查询 建V1后:", [(d["version"], d["score"]) for d in c1["retrieval_v0_content_after_v1"]["docs"]][:3])
    print("C3 pk before:", c3.get("pk_before"), "after:", c3.get("pk_after"),
          "changed:", c3.get("pk_changed"), "->", c3.get("verdict"))
    print("C2 删除后 marker命中:", c2["after"]["retrieval"]["n_marker"], "列表仍含:", c2["still_in_list"],
          "->", c2["verdict"])
    print("[evidence]", p)


if __name__ == "__main__":
    main()
