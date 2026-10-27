#!/usr/bin/env python3
"""kb_9 图全量重建：**只抽当前有效版本**（A 定的规则），并顺带重建社区摘要。

为什么按 `file_id` 过滤而不是 `version` 过滤：
  · 抽取接口（`get_document_chunk`）只支持单列 `col_name/col_values`；
  · "同 parent 取 version 最大"是**跨文档**的判定，用 `version in ["V0","V1"]` 无法表达；
  · 而 file_id 与 (文件, 版本) 一一对应 → 先算出"有效版本的 file_id 集合"，再用它过滤，语义等价且精确。
    实测：`file_id in [328,331,332,333,334,343,329]` → 9 个块（7 kb_9 + 2 table_chunks），
    恰好排除 290(V0 loan)/330(V0 intro)，符合"只抽有效版本"。

安全：默认 --dry-run，只打印将要做什么；--execute 才动手。
前置：备份已存在 + A 已确认最终清单（脚本会打印当前 ES 现状供人工核对）。
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

ES = "http://127.0.0.1:19200"
GRAPH = "http://127.0.0.1:19529"
VECTOR = "http://127.0.0.1:19526"
EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
MODEL_INFO = {"model_id": "qwen2.5-7b-instruct",
              "url": "http://127.0.0.1:18092/v1/chat/completions",
              "key": "sk-r12-local"}


def _ver(v):
    import re
    m = re.fullmatch(r"[Vv](\d+)", str(v or "").strip())
    return int(m.group(1)) if m else -1


def _scan(kb):
    """读三索引，返回 (docs, effective_file_ids, info)。"""
    docs = []
    for idx in (kb, f"table_chunks_{kb}", f"table_summary_{kb}"):
        r = requests.post(f"{ES}/{idx}/_search?size=2000",
                          json={"query": {"match_all": {}}}, timeout=180)
        for h in r.json().get("hits", {}).get("hits", []):
            md = (h.get("_source") or {}).get("metadata") or {}
            docs.append({"id": str(h.get("_id")), "index": idx,
                         "file_id": md.get("file_id"), "version": _ver(md.get("version")),
                         "version_raw": md.get("version"),
                         "parent": md.get("parent_file_name") or md.get("title"),
                         "title": md.get("title"), "chunk_index": md.get("chunk_index")})
    # 有效版本：同 parent 取 version 最大；table_summary 汇总行不参与抽取
    eff_by_parent = {}
    for d in docs:
        if d["index"].startswith("table_summary_"):
            continue
        if d["parent"]:
            eff_by_parent[d["parent"]] = max(eff_by_parent.get(d["parent"], -1), d["version"])
    eff = [d for d in docs
           if not d["index"].startswith("table_summary_") and d["parent"]
           and d["version"] == eff_by_parent.get(d["parent"])]
    eff_file_ids = sorted({int(d["file_id"]) for d in eff if d["file_id"] is not None})
    dropped = [{"id": d["id"], "title": d["title"], "version": d["version_raw"]}
               for d in docs if d not in eff and d["parent"]
               and not d["index"].startswith("table_summary_")]
    return docs, eff, eff_file_ids, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kb", nargs="?", default="kb_9")
    ap.add_argument("--execute", action="store_true", help="真正执行（默认只演练）")
    ap.add_argument("--drop-milvus", action="store_true", help="先删 Milvus 图两张表（全量重建）")
    a = ap.parse_args()
    kb = a.kb

    docs, eff, eff_fids, dropped = _scan(kb)
    print(f"# ES 现状：{len(docs)} 条（三索引）")
    print(f"# 有效版本块 {len(eff)} 个，file_id 集合 {eff_fids}")
    print(f"# 将被排除（V0 旧稿/汇总行）：{json.dumps(dropped, ensure_ascii=False)}")
    if not eff_fids:
        print("!! 有效 file_id 为空，终止")
        sys.exit(1)

    plan = {
        "kb": kb, "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "effective_blocks": len(eff), "effective_file_ids": eff_fids,
        "excluded": dropped,
        "steps": [
            ("drop_milvus" if a.drop_milvus else "(keep milvus)"),
            f"POST {GRAPH}/del_space {{space_name:g_{kb}}}   # 必须带 g_ 前缀，否则静默不删",
            f"POST {GRAPH}/generate_triple_data col_name=file_id col_values={eff_fids}",
            f"POST {GRAPH}/generate_community {{space_name:{kb},with_summary:true}}",
        ],
    }
    print(json.dumps(plan, ensure_ascii=False, indent=1))

    if not a.execute:
        print("\n[dry-run] 未执行。确认 A 的清单与备份后加 --execute。")
        return

    # 1) 可选：删 Milvus 图两表（全量重建时避免旧行残留）
    if a.drop_milvus:
        for coll in (f"graph_entity_{kb}", f"graph_triples_{kb}"):
            r = requests.post(f"{VECTOR}/del_collection",
                              json={"db_name": "graph_base", "collection_name": coll}, timeout=180)
            print(f"# del_collection {coll} -> {r.status_code} {r.text[:80]}")

    # 2) 删 Nebula 空间
    # **必须传完整 space 名（带 g_ 前缀）**：del_space 内部直接 `DROP SPACE IF EXISTS {name}`，
    # 不补前缀。传 "kb_9" 时目标空间不存在 -> 返回 200「删除成功」但**什么都没删**，
    # 于是后续重抽变成"追加"（实测后果：87 -> 91，55 个旧代顶点全部留存）。
    full_space = kb if kb.startswith("g_") else "g_" + kb
    r = requests.post(f"{GRAPH}/del_space", json={"space_name": full_space}, timeout=300)
    print(f"# del_space({full_space}) -> {r.status_code} {r.text[:120]}")
    # 删后必须复查：空间真的不存在了才算成功（不能只信 code=200）
    try:
        chk = requests.post(f"{GRAPH}/check_space", json={"space_name": full_space}, timeout=60)
        print(f"# check_space -> {chk.status_code} {chk.text[:120]}")
    except Exception as e:
        print(f"# check_space 失败（不阻断，但请人工确认已删）: {str(e)[:80]}")

    # 3) 只抽有效版本
    payload = {"space_name": kb, "col_name": "file_id",
               "col_values": [str(x) for x in eff_fids],
               "model_info": MODEL_INFO}
    t0 = time.time()
    r = requests.post(f"{GRAPH}/generate_triple_data", json=payload, timeout=3600)
    print(f"# generate_triple_data -> {r.status_code} 用时 {time.time() - t0:.0f}s")
    print(f"  {r.text[:300]}")

    # 4) 重建社区（含 chunk_refs）
    t0 = time.time()
    r = requests.post(f"{GRAPH}/generate_community",
                      json={"space_name": kb, "with_summary": True, "model_info": MODEL_INFO},
                      timeout=3600)
    print(f"# generate_community -> {r.status_code} 用时 {time.time() - t0:.0f}s")
    print(f"  {r.text[:300]}")

    plan["executed"] = True
    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-rebuild-plan-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)


if __name__ == "__main__":
    main()
