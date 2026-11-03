#!/usr/bin/env python3
"""诊断：HippoRAG 的图检索到底有没有被执行？为什么没执行？

背景（实测结论，先看这里再看代码）：在本机 qwen2.5-7b-instruct 上，`retrieve()` 的事实重排
（DSPy Filter）返回空 JSON `{}`，pydantic 校验失败 → `facts_after_rerank=0` → 引擎**永远**走
dense 回退。所以"检索有结果"绝不能当图执行证据。

本脚本做两件事，把两件事分开说清楚：
1. `retrieve` 路径：统计 `graph_search_with_fact_entities` 被调用次数（正常应为 0，
   证明回退真实存在），并给出 rerank 日志；
2. 直调路径：绕过重排，直接用候选事实调 `graph_search_with_fact_entities`，
   证明**引擎图检索本身能跑**（PPR 出得分），只是产品链路里到不了。

用法：
  /path/hipporag-venv/bin/python scripts/v2_hipporag_graph_probe.py \
      --save-dir /tmp/hippo-bridge --query "多指标对账口径是什么" --out /tmp/graph-probe.json
"""

import argparse
import json
import math
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))


def _count(value):
    """rerank 日志里可能是 numpy 数组，`or []` 会触发真值歧义，这里显式判 None。"""
    return 0 if value is None else len(value)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--save-dir", default="/tmp/hippo-bridge")
    ap.add_argument("--query", required=True)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    try:
        import numpy as np
        from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "ENV_MISSING", "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 2

    eng = HippoRAGEngine(save_dir=args.save_dir, llm_base_url=args.llm,
                         embedding_base_url=args.embed)
    hp = eng.hp
    if not hp.ready_to_retrieve:
        hp.prepare_retrieval_objects()

    # 1) 正常 retrieve：统计图调用次数
    out = eng.retrieve(args.query, top_k=3)

    # 2) 重排诊断：候选事实与重排后事实
    hp.get_query_embeddings([args.query])
    scores = hp.get_fact_scores(args.query)
    idx, facts_after, log = hp.rerank_facts(args.query, scores)

    # 3) 直调图检索：用候选事实（按分数取 top link_top_k），绕开重排
    link_top_k = hp.global_config.linking_top_k
    cand_idx = np.argsort(scores)[-link_top_k:][::-1].tolist() if len(scores) else []
    cand_facts = [eval(hp.fact_embedding_store.get_row(hp.fact_node_keys[i])["content"])
                  for i in cand_idx]
    direct = {"called": False}
    if cand_facts:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            doc_ids, doc_scores = hp.graph_search_with_fact_entities(
                query=args.query, link_top_k=link_top_k, query_fact_scores=scores,
                top_k_facts=cand_facts, top_k_fact_indices=cand_idx,
                passage_node_weight=hp.global_config.passage_node_weight)
        direct = {
            "called": True,
            "docs": len(doc_ids),
            "scores_finite": all(math.isfinite(float(s)) for s in np.ravel(doc_scores)),
            "warnings": sorted({f"{w.category.__name__}: {w.message}" for w in caught}),
            "top_doc_head": hp.chunk_embedding_store.get_row(
                hp.passage_node_keys[doc_ids[0]])["content"][:40] if len(doc_ids) else None,
        }

    report = {
        "schema": "llmke.graph-engine.probe.v1",
        "query": args.query,
        "retrieve_path": {"executed_route": out["executed_route"], "reason": out["reason"],
                          "graph_calls": out["trace"]["graph_calls"], "hits": out["hit_count"]},
        "rerank": {"facts_before_rerank": _count(log.get("facts_before_rerank")),
                   "facts_after_rerank": _count(log.get("facts_after_rerank"))},
        "direct_graph": direct,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
