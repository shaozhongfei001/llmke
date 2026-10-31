#!/usr/bin/env python3
"""撤权窗口演练：重建**进行中**和**失败后**，读者是否都被安全挡住。

两段场景，都要真跑：
A. 重建失败：旧指针代次 0 + 撤权后 fence 代次 1 → 读者必须被拒（不能因为重建失败就放行旧索引）；
B. 重建成功：重建期间读者持续被拒；完成后指针代次 1 → 读者放行，
   且检索结果里**不得**出现已撤权文件的来源。

用法：
  /path/hipporag-venv/bin/python scripts/v2_concurrency_drill.py \
      --payloads /tmp/ingest-333.json /tmp/ingest-329.json --cjk-compat --out /tmp/concurrency.json
"""

import argparse
import json
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter.fence import (FenceState, StaleIndexError, assert_index_fresh,
                                        filter_hits)
from graph_engine_adapter.rebuild import RebuildFailed, read_pointer, rebuild


REVOKED = ["329"]


def load_payloads(paths):
    docs = []
    for path in paths:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")), "text": chunk["page_content"]})
    return docs


def read_once(pointer, fence):
    """模拟一次"打开索引"：代次不够就拒。返回 True=放行。"""
    try:
        assert_index_fresh((pointer or {}).get("generation"), fence)
        return True
    except StaleIndexError:
        return False


def scenario_failure(root, docs):
    """A：撤权后重建失败，指针停在旧代次 → 读者必须一直被拒。"""
    fence = FenceState()
    rebuild(root, fence, docs, lambda items, target: os.makedirs(target, exist_ok=True) or {"ok": 1})
    pointer_before = read_pointer(root)                 # generation 0

    fence.revoke(["329"])                               # fence generation -> 1

    def broken(items, target):
        raise RuntimeError("故意失败：模拟重建报错")

    failed = False
    try:
        rebuild(root, fence, docs, broken)
    except RebuildFailed:
        failed = True

    pointer_after = read_pointer(root)
    return {"rebuild_failed": failed,
            "pointer_unchanged": pointer_before == pointer_after,
            "pointer_generation": (pointer_after or {}).get("generation"),
            "fence_generation": fence.generation,
            "reader_allowed": read_once(pointer_after, fence)}


def scenario_success(root, docs, build_fn):
    """B：重建期间读者被拒；完成后放行，且撤权内容不出现。"""
    fence = FenceState()
    rebuild(root, fence, docs, lambda items, target: os.makedirs(target, exist_ok=True) or {"ok": 1})
    fence.revoke(["329"])                               # fence generation -> 1

    samples = {"blocked": 0, "allowed": 0}
    stop = threading.Event()
    building = threading.Event()          # 只统计"重建进行中"的采样，否则会把完成后的放行算进去

    def reader_loop():
        while not stop.is_set():
            pointer = read_pointer(root)
            allowed = read_once(pointer, fence)
            if building.is_set():
                key = "allowed" if allowed else "blocked"
                samples[key] += 1
            time.sleep(0.02)

    thread = threading.Thread(target=reader_loop, daemon=True)
    thread.start()
    building.set()
    try:
        out = rebuild(root, fence, docs, build_fn)
    finally:
        building.clear()
        time.sleep(0.1)
        stop.set()
        thread.join(timeout=2)

    pointer = read_pointer(root)
    allowed_after = read_once(pointer, fence)
    dropped = out["current"].get("dropped_revoked") or []
    # 正确判据：被剔除的**只能是**本次撤权的文件，不能顺带丢别的
    unexpectedly_dropped = sorted({fid for fid in dropped if fid not in set(REVOKED)})
    return {"during_rebuild": dict(samples),
            "pointer_generation": pointer.get("generation"),
            "fence_generation": fence.generation,
            "reader_allowed_after": allowed_after,
            "snapshot_doc_count": pointer.get("documents"),
            "dropped_revoked": sorted(set(dropped)),
            "unexpectedly_dropped": unexpectedly_dropped}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", default="/tmp/hippo-concurrency")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    docs = load_payloads(args.payloads)
    os.makedirs(args.root, exist_ok=True)

    fa = scenario_failure(os.path.join(args.root, "failure"), docs)

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine

    def real_build(items, target):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.build([d["text"] for d in items])

    fb = scenario_success(os.path.join(args.root, "success"), docs, real_build)

    expected_live_chunks = len([d for d in docs if d["file_id"] not in set(REVOKED)])
    passed = (fa["rebuild_failed"] and fa["pointer_unchanged"] and not fa["reader_allowed"]
              and fb["during_rebuild"]["blocked"] > 0
              and fb["during_rebuild"]["allowed"] == 0          # 重建期间一次都不许放行
              and fb["reader_allowed_after"]
              and fb["snapshot_doc_count"] == expected_live_chunks
              and fb["dropped_revoked"] == sorted(set(REVOKED))
              and not fb["unexpectedly_dropped"])
    report = {"schema": "llmke.concurrency-drill.v1",
              "failure_case": fa, "success_case": fb, "passed": passed}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"passed": passed, "failure": fa, "success": fb}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
