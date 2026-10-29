#!/usr/bin/env python3
"""A10 更新删除与撤权（任务书 §5.2 A10）。

判据：更新/删除/重解析、改变权限范围后 → 无幽灵事实、无重复摘要、无混代；撤权立即围栏。
写操作边界：删除文件、重解析、建/撤用户权限都是写操作，本轮不执行（不改库、不建账号）。
只读可证伪的部分：
  N1 图里有来自失效文件（status!=3）的边 → 删除没围栏（幽灵事实）
  N2 社区摘要引用了失效 file_id → 旧产物流到报告层
  N3 ES 检索索引里仍有失效文件的行 → 文档已失效但检索仍可达
"""
import collections

import common as C

ID = "A10"
TITLE = "更新删除与撤权：无幽灵事实、旧产物不流入社区/检索"
WRITES = True


def run():
    checks = []
    active = C.active_fids()
    es = C.edges()
    vis = [e for e in es if e["sf"] == "1"]

    ghost = collections.Counter(e["fid"] for e in vis if e["fid"] not in active)
    checks.append(C.chk("N1 反例：图中无失效文件的事实", not ghost,
                        f"幽灵边来源={dict(ghost)}"))

    comms = C.communities()
    bad_files = {}
    for c in comms:
        fids = [str(x) for x in ((c["meta"] or {}).get("file_ids") or [])]
        stale = [f for f in fids if f not in active]
        if stale:
            bad_files[c["es_id"]] = stale
    checks.append(C.chk("N2 反例：社区不引用失效文件", not bad_files,
                        f"引用失效文件的社区={bad_files}"))

    d = C.es_search("kb_9", {"query": {"match_all": {}}}, size=1000)
    fid_docs = collections.Counter()
    for h in d["hits"]["hits"]:
        md = (h.get("_source") or {}).get("metadata") or {}
        fid = md.get("file_id")
        if fid is None:
            continue
        fid_docs[str(fid)] += 1
    stale_docs = {f: n for f, n in fid_docs.items() if f not in active}
    checks.append(C.chk("N3 反例：检索索引不含失效文件的行", not stale_docs,
                        f"ES kb_9 共 {d['hits']['total']['value']} 行；失效文件行={stale_docs}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="删除文件/重解析/建撤用户权限属写操作，本轮不执行；"
                                 "撤权后复查全部通路需真实账号，另行执行")
