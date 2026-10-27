#!/usr/bin/env python3
"""图引用回填质量分档：exact_chunk / stale_version / entity_content。

为什么需要第三档（A 提出）：重建图只抽"当前有效版本"（同 parent 下 version 最大者），
但如果某实体只命中 **V0** 的 pk，按旧的二分会算成 exact_chunk —— 数字好看、语义是错的
（V0 是被替换的旧稿）。所以单列 `stale_version`，`exact_chunk` 只统计落到有效版本的块。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/provenance_stats.py kb_9
  ... --queries "问题1" "问题2"     # 不传则用内置探针问句
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

GRAPH = "http://127.0.0.1:19529"
ES = "http://127.0.0.1:19200"
EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")

MODEL_INFO = {"model_id": "qwen2.5-7b-instruct",
              "url": "http://127.0.0.1:18092/v1/chat/completions",
              "key": "sk-r12-local"}
# 与 F-qa 的 GRAPH_PROVENANCE 探针**完全同一句**，保证两边统计可对比：
# 之前我用三个自定义问句、他用一句，导致"我 0 个 stale、他 2 个 stale"看起来像数据不一致，
# 实际只是命中的块不同（我的探针恰好没命中带 V1 后继的文件）。
DEFAULT_QUERIES = ["智造贷 授信额度 票据贴现"]


def _ver_num(v):
    """'V1' -> 1；空 -> -1（用于判定"有效版本"）。"""
    m = re.fullmatch(r"[Vv](\d+)", str(v or "").strip())
    return int(m.group(1)) if m else -1


def _effective_versions(kb):
    """parent（同 parent_file_name，无则 title）→ 有效 version 数值。"""
    r = requests.post(f"{ES}/{kb}/_search?size=2000",
                      json={"query": {"match_all": {}}}, timeout=120)
    eff = {}
    for h in r.json().get("hits", {}).get("hits", []):
        md = (h.get("_source") or {}).get("metadata") or {}
        key = md.get("parent_file_name") or md.get("title")
        if not key:
            continue
        v = _ver_num(md.get("version"))
        eff[key] = max(eff.get(key, -1), v)
    return eff


def _canonical_file_ids(kb):
    """title -> 主索引里该文件当前(有效版本)的 file_id；用于判断 table_* 是否还挂旧行。

    现算而不是硬编码 329：台账的 file_id 会随重解析变化，写死就变成第二天的错误常量。
    """
    r = requests.post(f"{ES}/{kb}/_search?size=2000",
                      json={"query": {"match_all": {}}}, timeout=120)
    # 选基准行的规则（A 提醒：同名文件可能有多行历史，不能用 max(id)）：
    #   ① version 数值最大；② 同 version 取 update_time 最新
    # （ES metadata 里没有 is_enable 字段，用"最新写入"近似"当前有效行"，并在证据里注明该局限）
    best = {}
    for h in r.json().get("hits", {}).get("hits", []):
        md = (h.get("_source") or {}).get("metadata") or {}
        title = md.get("title")
        if not title:
            continue
        key = (_ver_num(md.get("version")), str(md.get("update_time") or md.get("create_time") or ""))
        if title not in best or key > best[title][0]:
            best[title] = (key, md.get("file_id"))
    return {k: v[1] for k, v in best.items()}


def _es_docs(kb, pks):
    """pk → ES 元数据；**跨 3 个索引**查（台账只在 table_chunks_ 里）。

    A 提醒：图抽取读 `[kb, table_chunks_kb]`，所以台账的 pk 不在 kb 主索引。
    只查主索引会把台账块误判成"文件级悬空"（F 报的就是这个现象）。
    """
    if not pks:
        return {}
    out = {}
    for idx in (kb, f"table_chunks_{kb}", f"table_summary_{kb}"):
        try:
            r = requests.post(f"{ES}/{idx}/_search",
                              json={"query": {"ids": {"values": list(pks)}},
                                    "size": len(pks)}, timeout=120)
            for h in r.json().get("hits", {}).get("hits", []):
                md = (h.get("_source") or {}).get("metadata") or {}
                out[str(h.get("_id"))] = {
                    "version": _ver_num(md.get("version")),
                    "parent": md.get("parent_file_name") or md.get("title"),
                    "title": md.get("title"),
                    "index_name": idx,
                    "file_id": md.get("file_id"),
                    "source": md.get("source"),
                }
        except Exception:
            continue
    return out


def _graph_blocks(kb, query, top_k=5):
    body = {"space_name": kb, "query": query, "model_info": MODEL_INFO,
            "depth": 3, "top_k": top_k}
    r = requests.post(f"{GRAPH}/query_graph_data", json=body, timeout=180)
    data = (r.json() or {}).get("data") or {}
    return data.get("result_data") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kb", nargs="?", default="kb_9")
    ap.add_argument("--queries", nargs="*", default=None)
    a = ap.parse_args()
    kb = a.kb
    queries = a.queries or DEFAULT_QUERIES

    eff = _effective_versions(kb)
    canonical_fid = _canonical_file_ids(kb)
    blocks, seen = [], set()
    for q in queries:
        for b in _graph_blocks(kb, q):
            md = b.get("metadata") or {}
            pk = str(md.get("pk") or md.get("recovered_es_id") or "")
            key = (pk, md.get("chunk_index"))
            if key in seen:
                continue
            seen.add(key)
            blocks.append({"query": q, "pk": pk,
                           "recovered_by": md.get("recovered_by"),
                           "provenance_quality": md.get("provenance_quality"),
                           "title": md.get("title")})

    docs = _es_docs(kb, [b["pk"] for b in blocks if b["pk"]])
    counts = {"exact_chunk": 0, "stale_version": 0, "entity_content": 0, "unknown": 0}
    for b in blocks:
        d = docs.get(b["pk"])
        if b["recovered_by"] == "entity_content" or not d:
            b["class"] = "entity_content" if b["recovered_by"] else "unknown"
            # 与 F-qa 的口径对齐：entity_content 块也要看"兜底命中的是哪一代"。
            # 他统计的 stale=2 正是这一类（兜底反查到 V0，而同名有 V1）。
            # 这里只作子属性记录，不改变主分类（主分类仍是 entity_content）。
            if d:
                valid = eff.get(d["parent"], -1)
                b["recovered_version"], b["effective_version"] = d["version"], valid
                b["recovered_stale"] = d["version"] < valid
                b["index_name"], b["file_id"] = d.get("index_name"), d.get("file_id")
        else:
            valid = eff.get(d["parent"], -1)
            b["class"] = "exact_chunk" if d["version"] >= valid else "stale_version"
            b["es_version"], b["effective_version"] = d["version"], valid
            b["index_name"], b["file_id"] = d.get("index_name"), d.get("file_id")
            if b["class"] == "stale_version":
                # A 定的判定顺序：① table_* 先看 file_id 是否仍是旧行（.md 解析失败致未归一）
                #                   ② 再看 file_id 是否属 V0 输入
                #                   ③ 最后才怀疑"回填把 V0 的 pk 写进 V1 实体行"
                # 注意：不硬编码 329/314 —— 用"主索引同名文件当前的 file_id"当基准现算。
                cur = canonical_fid.get(str(b.get("title") or ""))
                if str(b.get("index_name") or "").startswith("table_") and cur is not None \
                        and str(b.get("file_id")) != str(cur):
                    b["cause"] = f"table_file_id_stale(table 挂 {b.get('file_id')}，主索引当前 {cur})"
                else:
                    b["cause"] = "v0_input_or_backfill(看 file_id 属 V0 文件还是 V1 文件)"
        counts[b["class"]] += 1

    total = len(blocks) or 1
    # 判定顺序（A 定，避免"数字好看但语义错"）：
    #   1) 通过 = exact_chunk > 0 且 stale_version == 0
    #   2) stale>0 先查"输入里是否混进 V0(fid 290/330 的 pk)"，别先怀疑回填逻辑
    #   3) entity_content 允许存在，但占比必须一起报
    if counts["exact_chunk"] > 0 and counts["stale_version"] == 0:
        verdict = "PASS"
    elif counts["stale_version"] > 0:
        verdict = "FAIL_STALE_VERSION"
    elif counts["exact_chunk"] == 0:
        verdict = "UNVERIFIED_NO_EXACT"
    else:
        verdict = "UNKNOWN"
    hint = {
        "FAIL_STALE_VERSION": "先查抽取输入是否混进 V0（fid 290/330 的 pk），再怀疑回填逻辑",
        "UNVERIFIED_NO_EXACT": "重建前属预期；重建后仍 0 才是真问题",
    }.get(verdict, "")
    # A 的要求：stale 时把"命中 V0 的具体 pk"列出来，便于区分
    #   ① 输入里混进了 V0（抽取阶段就该过滤） vs ② 回填把 V0 的 pk 写进 V1 实体行（真 bug）
    stale_pks = [{"pk": b["pk"], "title": b.get("title"), "index_name": b.get("index_name"),
                  "file_id": b.get("file_id"), "cause": b.get("cause"),
                  "es_version": b.get("es_version"), "effective_version": b.get("effective_version")}
                 for b in blocks if b.get("class") == "stale_version"]
    res = {"kb": kb, "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "blocks": len(blocks), "counts": counts, "verdict": verdict, "hint": hint,
           "stale_pks": stale_pks,
           "ratios": {k: round(v / total, 3) for k, v in counts.items()}, "detail": blocks}
    rec_stale = [{"pk": b["pk"], "title": b.get("title"),
                  "recovered_version": b.get("recovered_version"),
                  "effective_version": b.get("effective_version")}
                 for b in blocks if b.get("recovered_stale")]
    res["recovered_stale"] = rec_stale
    print(json.dumps({"kb": kb, "blocks": len(blocks), "counts": counts,
                      "recovered_stale_count": len(rec_stale),
                      "ratios": res["ratios"], "verdict": verdict}, ensure_ascii=False, indent=1))
    if rec_stale:
        print("[recovered_stale] 兜底块命中旧版本（与 F 的 stale 统计同源）:")
        for x in rec_stale:
            print("   ", json.dumps(x, ensure_ascii=False))
    if hint:
        print("\n[说明]", hint)
    os.makedirs(EVID, exist_ok=True)
    out = os.path.join(EVID, "R14-B-provenance-"
                       f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("[evidence]", out)


if __name__ == "__main__":
    main()
