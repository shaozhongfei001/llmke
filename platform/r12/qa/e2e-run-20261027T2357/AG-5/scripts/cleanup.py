#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-5 收工清理：删除自建库（R14-E2E-AG5-*）+ 核对 ES/Milvus/MySQL 残留。

先记 before（库、文件、ES 三索引、Milvus 集合、MySQL 行数），删库，再记 after。
任何 after 不为 0/N/A 的项都打印出来，不隐藏。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, es_count, kb_delete, kb_list, login, milvus_stats, mysql_rows, now)

MY_KBS = [k for k in (os.environ.get("AG5_KB_NAMES") or "R14-E2E-AG5-1111,R14-E2E-AG5-1121-C").split(",") if k]


def snapshot():
    s, token = login()
    code, body = kb_list(s, token)
    recs = ((body.get("data") or {}).get("records") or [])
    kbs = [{"id": r.get("id"), "name": r.get("kbName"), "primitive": r.get("primitiveName"),
            "files": r.get("fileCount")} for r in recs]
    mine = [r for r in kbs if (r["name"] or "") in MY_KBS]
    snap = {"ts": now(), "kb_total": len(kbs), "kbs": kbs, "mine": mine,
            "es": {}, "milvus": {}, "mysql": {}}
    for r in mine:
        kid = r["id"]
        for idx in (f"kb_{kid}", f"table_chunks_kb_{kid}", f"table_summary_kb_{kid}"):
            snap["es"][idx] = es_count(idx)
        snap["milvus"][f"kb_{kid}"] = milvus_stats(kid)
        q = (f"select (select count(*) from gienrag.knowledge_base_list where kb_id={kid}) as files,"
             f"(select count(*) from gienrag.file_parse_task where kb_id={kid}) as tasks,"
             f"(select count(*) from gienrag.syn_log where kb_id={kid}) as synlogs,"
             f"(select count(*) from gienrag.knowledge_base where id={kid}) as kb_rows")
        snap["mysql"][f"kb_{kid}"] = mysql_rows(q).get("rows")
    return snap


def main():
    out = {"before": snapshot()}
    print("[before]", json.dumps({k: out["before"][k] for k in ("kb_total", "mine")},
                                 ensure_ascii=False))
    s, token = login()
    dels = []
    for r in out["before"]["mine"]:
        code, body = kb_delete(s, token, r["id"])
        dels.append({"id": r["id"], "name": r["name"], "http": code,
                     "success": (body or {}).get("success") if isinstance(body, dict) else body})
        print("[delete]", r["id"], r["name"], code, dels[-1]["success"])
    out["delete_calls"] = dels
    time.sleep(8)
    out["after"] = snapshot()
    print("[after] kb_total", out["after"]["kb_total"], "mine", out["after"]["mine"])
    for k, v in out["after"]["es"].items():
        print("  es", k, v)
    for k, v in out["after"]["milvus"].items():
        print("  milvus", k, json.dumps(v, ensure_ascii=False))
    for k, v in out["after"]["mysql"].items():
        print("  mysql", k, v)
    p = os.path.join(EVID, f"cleanup-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence]", p)


if __name__ == "__main__":
    main()
