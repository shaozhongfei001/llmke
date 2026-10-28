#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-6 收工清理：
 1) 删除我建的对话（sessionId 前缀 ag6 / ag6-faq / ag6q；以及本轮 UI 提问产生的那一条）
 2) 删除自建库（id 取自 state，不硬编码）
 3) 复核：知识库列表条数回到开工前、ES 四索引 404、Milvus 集合不存在
 4) 如实登记 MySQL 残留行（不手动改库）
"""
import json
import time

import ag6_lib as L

KB_TABLES = ("knowledge_base", "knowledge_base_list", "file_parse_task", "syn_log")


def es_state(primitive, kb_id):
    out = []
    for idx in (f"kb_{primitive.split('_')[-1]}", f"faq_{primitive}",
                f"table_chunks_{primitive}", f"table_summary_{primitive}"):
        out.append({"idx": idx, "count": L.es_count(idx)})
    return out


def milvus_state(kb_id):
    return L.milvus_stats(kb_id)


def main():
    st = L.load_state()
    kb_id, kb_name, primitive = st["kb_id"], st["kb_name"], st["primitive"]
    s, token = L.login()
    ev = {"time": L.now(), "kb_id": kb_id, "kb_name": kb_name, "primitive": primitive}

    # ---- 1) 对话清理
    c, b, _ = L.api(s, "GET", "/qa/dialogue/list?pageNo=1&pageSize=100", token)
    recs = (b.get("data") or {}).get("records") if isinstance(b, dict) else None
    if recs is None and isinstance(b, dict) and isinstance(b.get("data"), list):
        recs = b["data"]
    recs = recs or []
    mine_questions = {"客户的日均存款是多少？", "客户访前准备属于哪一部分？",
                      "文档的第一段主要讨论了什么？", "文档中提到了日均存款的具体数值吗？",
                      "AG6-UNIQUE"}
    todo = []
    for r in recs:
        sid = str(r.get("sessionId") or "")
        name = str(r.get("name") or r.get("dialogueName") or "")
        ts = str(r.get("gmtCreate") or r.get("createTime") or r.get("gmtCreateTime") or "")
        if sid.startswith(("ag6", "ag6q")) or (name in mine_questions and "11:5" in ts):
            todo.append({"sessionId": sid, "name": name, "time": ts})
    deleted = []
    for t in todo:
        code, body, _ = L.api(s, "DELETE", f"/qa/dialogue/delete?sessionId={t['sessionId']}", token)
        deleted.append({**t, "http": code, "resp": body})
        time.sleep(0.2)
    ev["dialogues"] = {"candidates": len(todo), "deleted": deleted,
                       "list_total_before": len(recs)}

    # ---- 2) 删库
    code, body, _ = L.kb_delete(s, token, kb_id)
    ev["kb_delete"] = {"http": code, "body": body}
    time.sleep(3)

    # ---- 3) 复核
    c2, b2, _ = L.kb_list(s, token)
    recs2 = (b2.get("data") or {}).get("records") or []
    names2 = [r.get("kbName") for r in recs2]
    ev["after"] = {"kb_list_count": len(names2), "kb_list_names": names2,
                   "kb_baseline": st.get("kb_baseline"),
                   "back_to_baseline": names2 == st.get("kb_baseline"),
                   "es": es_state(primitive, kb_id),
                   "milvus": milvus_state(kb_id)}

    # ---- 4) MySQL 残留
    resid = {}
    for t in KB_TABLES:
        col = "id" if t == "knowledge_base" else "kb_id"
        r = L.mysql_rows(f"select count(*) from gienrag.{t} where {col}={int(kb_id)}")
        resid[t] = r.get("rows", r)
    kb_row = L.mysql_rows("select id,kb_name,status from gienrag.knowledge_base "
                          f"where id={int(kb_id)}")
    ev["mysql_residual"] = {"counts": resid, "knowledge_base_row": kb_row.get("rows")}
    p = L.dump("cleanup-" + L.ts() + ".json", ev, "")
    print(json.dumps({"evidence": p, "kb_delete": ev["kb_delete"],
                      "after": {"kb_list_count": ev["after"]["kb_list_count"],
                                "back_to_baseline": ev["after"]["back_to_baseline"],
                                "es": ev["after"]["es"], "milvus": ev["after"]["milvus"]},
                      "mysql_residual": ev["mysql_residual"],
                      "dialogues": {"candidates": len(todo),
                                    "deleted": [(d["sessionId"], d["http"]) for d in deleted]}},
                     ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
