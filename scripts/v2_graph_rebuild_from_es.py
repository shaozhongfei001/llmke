#!/usr/bin/env python3
"""从 ES 重建 18094 图谱 —— /tmp 图根/快照丢失时的恢复入口。

为什么从 ES
------------
ES 里的 chunk 是平台统一 pk 的权威投影产物，metadata 自带
`pk / file_id / chunk_index / title / parse_artifact_id`，与 18094 的
BuildDoc 一一对应。用它重建：
- 不依赖 /tmp 下的 doc2md 四件套或 kb_state.json（这两者曾随 /tmp 被清空）；
- 不需要重新解析原件（48MB PDF 走 MinerU 很慢）；
- pk 与 ES/Milvus 天然对齐，不新造第二套主键。

前置
----
18094 必须以**持久化** LLMKE_V2_ROOT 启动，例如：
    LLMKE_V2_ROOT=/home/szf/data/dev/llmke-r12/platform/r12/data/graph-root
    /home/szf/data/dev/hipporag-toolenv/bin/python -m uvicorn \
        graph_engine_adapter.api:app --host 127.0.0.1 --port 18094

用法
----
    python3 scripts/v2_graph_rebuild_from_es.py                       # 只统计，不建图
    python3 scripts/v2_graph_rebuild_from_es.py --kbs kb_9 --apply    # 重建 kb_9（快）
    python3 scripts/v2_graph_rebuild_from_es.py --kbs kb_1004 --apply  # 重建 kb_1004（数小时）
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                      / "services/rag-alg/index_data_service"))
from ingest_pipeline import kb_pipeline as K  # noqa: E402

ES_URL = "http://127.0.0.1:19200"
GRAPH_API = "http://127.0.0.1:18094"


def _post(url, payload, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def es_scroll(index, size=500):
    resp = _post(f"{ES_URL}/{index}/_search?scroll=2m",
                 {"query": {"match_all": {}}, "size": size}, timeout=60)
    sid = resp.get("_scroll_id")
    while True:
        hits = (resp.get("hits") or {}).get("hits") or []
        if not hits:
            break
        for h in hits:
            yield h
        resp = _post(f"{ES_URL}/_search/scroll",
                     {"scroll": "2m", "scroll_id": sid}, timeout=60)
        sid = resp.get("_scroll_id")


def collect(kb):
    """收集主索引 + table_chunks_ 索引的全部 chunk，转成 BuildDoc。"""
    docs = []
    per_index = {}
    for index in (kb, f"table_chunks_{kb}"):
        try:
            hits = list(es_scroll(index))
        except Exception as exc:  # noqa: BLE001 - 派生索引不存在时降级，不阻断主索引
            print(f"  {index}: 读取失败({type(exc).__name__}: {exc})，跳过",
                  file=sys.stderr)
            per_index[index] = 0
            continue
        n = 0
        for h in hits:
            src = h.get("_source") or {}
            text = src.get("page_content") or ""
            if not text.strip():
                continue
            meta = src.get("metadata") or {}
            pk = meta.get("pk")
            if pk is None:
                try:
                    pk = int(h.get("_id"))
                except (TypeError, ValueError):
                    pk = None
            file_id = meta.get("file_id")
            if not file_id:
                continue
            doc = {
                "file_id": str(file_id),
                "text": text,
                "pk": pk,
            }
            chunk_index = meta.get("chunk_index")
            if chunk_index is not None:
                doc["locator"] = f"chunk={chunk_index}"
            if meta.get("title"):
                doc["title"] = str(meta["title"])
            if meta.get("parse_artifact_id"):
                doc["parse_artifact_id"] = str(meta["parse_artifact_id"])
            docs.append(doc)
            n += 1
        per_index[index] = n
    return docs, per_index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kbs", nargs="+", default=["kb_9", "kb_1004"])
    ap.add_argument("--apply", action="store_true", help="实际调用 18094 建图（默认只统计）")
    ap.add_argument("--timeout", type=int, default=14400)
    args = ap.parse_args()

    for kb in args.kbs:
        docs, per_index = collect(kb)
        print(f"[{kb}] BuildDoc 总数 = {len(docs)}  明细 = {per_index}", flush=True)
        if not args.apply:
            print(f"[{kb}] dry-run（未加 --apply，未写图）", flush=True)
            continue
        if not docs:
            print(f"[{kb}] 无可建图的 chunk，跳过", file=sys.stderr)
            continue
        t0 = time.time()
        result = K.post_graph_build(kb, docs, graph_api=GRAPH_API, timeout=args.timeout)
        print(f"[{kb}] status={result.get('status')} 用时={time.time() - t0:.0f}s",
              flush=True)


if __name__ == "__main__":
    main()
