#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S14 补充取证：重解析后 ES chunk 的 metadata.version 是否被清空（可复现性 2/2）+
删除后检索收敛的正确判据（按内容与来源判，不按条数判）。

背景（判据演进，必须写进报告）：
- 检索服务 19995 的返回里**没有 metadata.pk 字段**（实测恒为 None），
  用 pk 做"引用是否换代"的断言会恒真 → 属 FINAL-REPORT §4.1② 的字段假绿。
  故改用"ES 侧 pk + create_time + 页面文本"作代次锚点。
- 检索在 enabled_rerank=false 时没有阈值过滤，必然返回若干无关块 → 判"删除后不再出现"
  必须按 marker 内容与来源判，不能按 documents 条数判（条数会被无关块抬高）。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import (EVID, FILE_FAIL, FILE_OK, FILE_STATUS, api, es_docs, file_rows,
                     file_status, login, now, parse_tasks, retrieval)

KB_ID = int(os.environ.get("AG5_KB_ID", "36"))
KB_NAME = f"kb_{KB_ID}"
FID = int(os.environ.get("AG5_TARGET_FID", "499"))   # docx-loan, 未被重解析过
IDX = [KB_NAME, f"table_chunks_kb_{KB_ID}", f"table_summary_kb_{KB_ID}"]


def es_of(fid):
    out = {}
    for idx in IDX:
        j = es_docs(idx, size=100, query={"term": {"metadata.file_id": fid}})
        if "error" in j:
            out[idx] = {"error": str(j["error"])[:80]}
            continue
        out[idx] = [{"pk": h["_source"]["metadata"].get("pk"),
                     "version": h["_source"]["metadata"].get("version"),
                     "file_path": h["_source"]["metadata"].get("file_path"),
                     "create_time": h["_source"]["metadata"].get("create_time")}
                    for h in j.get("hits", {}).get("hits", [])]
    return out


def wait_terminal(s, token, fid, max_wait=240):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        c, b = file_status(s, token, fid)
        v = b.get("data") if isinstance(b, dict) else b
        if v in (FILE_OK, FILE_FAIL):
            return v
        time.sleep(1.5)
    return None


def main():
    s, token = login()
    out = {"ts": now(), "kb": KB_NAME, "file_id": FID}
    row = (file_rows([FID]).get("rows") or [{}])[0]
    out["row"] = row
    out["es_before"] = es_of(FID)
    payload = {"files": [{"folder_id": None,
                          "file_path": f"r12-rag/{KB_NAME}/{row.get('file_name')}/"
                                       f"{row.get('version')}/{row.get('file_name')}",
                          "file_id": str(FID), "parent_file_name": row.get("file_name")}],
               "folder_ids": [], "knowledge_base_name": KB_NAME,
               "knowledge_base_id": str(KB_ID), "override": True, "is_all": False}
    code, body = api(s, "POST", "/index/knowledgeBase/file/filesParse", token, json=payload)
    out["reparse"] = {"http": code, "body": body, "payload": payload, "req_time": now()}
    st = wait_terminal(s, token, FID)
    out["status_after"] = FILE_STATUS.get(st)
    out["tasks"] = [(t["task_id"], t["status_name"]) for t in
                    (parse_tasks([FID]).get("tasks") or [])]
    out["es_after"] = es_of(FID)

    def flat(d):
        return [x for v in d.values() if isinstance(v, list) for x in v]

    b, a = flat(out["es_before"]), flat(out["es_after"])
    out["version_before"] = [x["version"] for x in b]
    out["version_after"] = [x["version"] for x in a]
    out["version_lost"] = any(x["version"] is None for x in a) and all(
        x["version"] is not None for x in b) if b and a else None
    out["pk_same"] = [x["pk"] for x in b] == [x["pk"] for x in a]
    out["create_time_advanced"] = (max([x["create_time"] for x in a]) >
                                   max([x["create_time"] for x in b])) if a and b else None

    p = os.path.join(EVID, "S14", f"S14c-version-null-{now().replace(' ', 'T').replace(':', '')}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("before:", out["version_before"], [x["pk"] for x in b], [x["create_time"] for x in b])
    print("after :", out["version_after"], [x["pk"] for x in a], [x["create_time"] for x in a])
    print("version_lost:", out["version_lost"], "| pk_same:", out["pk_same"],
          "| ct_advanced:", out["create_time_advanced"], "| status:", out["status_after"])
    print("[evidence]", p)


if __name__ == "__main__":
    main()
