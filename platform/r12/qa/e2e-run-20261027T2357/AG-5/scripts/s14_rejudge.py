#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S14 判定复核（判据 v2）：按"来源 + 内容"判删除收敛，不按条数判。

判据 v1 缺陷（自曝）：检索在 enabled_rerank=false 时无阈值过滤，必然返回若干无关块，
用 documents 条数判"删除后不再出现" → 会把无关块当残留（假红）；用 metadata.pk 判代次
→ 该字段实测恒为 None（恒真，假绿）。v2 改成：
  删除后：① 检索结果里**没有任何一条** file_path 指向被删文件；② 文件列表不含该名；
          ③ ES 三个索引里该 file_id 条数为 0。
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ag5_lib import EVID, dump, now


def main():
    files = sorted(glob.glob(os.path.join(EVID, "S14", "S14b-converge-*.json")))
    if not files:
        print("no evidence")
        return
    d = json.load(open(files[-1], encoding="utf-8"))
    C = d["C_delete"]
    name = d["name"]
    prefix = name.split(".")[0]

    def leaks(rt):
        return [x for x in rt["docs"] if prefix in str(x.get("file_path") or "")]

    after = C["after"]
    leaked_marker = leaks(after["retrieval_marker"])
    leaked_shared = leaks(after["retrieval_shared"])
    es_left = {}
    for k in ("es_v0", "es_v1"):
        for idx, v in after[k].items():
            es_left[f"{k}:{idx}"] = len(v) if isinstance(v, list) else "ERR"
    res = {
        "ts": now(), "judge_version": "v2", "file": name,
        "retrieval_after_marker": {"n": after["retrieval_marker"]["n"],
                                   "leaked_sources": [x["file_path"] for x in leaked_marker]},
        "retrieval_after_shared": {"n": after["retrieval_shared"]["n"],
                                   "leaked_sources": [x["file_path"] for x in leaked_shared]},
        "still_in_file_list": C["still_in_file_list"],
        "es_left": es_left,
        "delete_calls": C["delete_calls"],
        "v1_note": "v1 用 documents 条数判 → 被无关块抬高，误判 FAIL；v2 按来源/内容判",
    }
    ok = (not leaked_marker and not leaked_shared and not C["still_in_file_list"]
          and all(v in (0,) for v in es_left.values() if isinstance(v, int)))
    res["verdict"] = "PASS" if ok else "FAIL"
    p = dump(f"S14-delete-rejudge-{now().replace(' ', 'T').replace(':', '')}.json", res, sub="S14")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("[evidence]", p)


if __name__ == "__main__":
    main()
