#!/usr/bin/env python
"""从快照目录导出图（节点/边/事实）为可 diff 的 JSONL。

用法：
    v2_graph_export.py --snapshot /tmp/dual-full --out /tmp/export-a
    v2_graph_export.py --snapshot a --compare b --out /tmp/export-diff.json

为什么要有 `--compare`：导出物的用途就是"两份快照差在哪"。只导出不比较，
还得人工 `diff` 三个文件；直接把结构化差异算出来，才能接进验收。
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services/rag-alg/index_data_service"))


def load_engine(snapshot, llm, embed):
    from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    return HippoRAGEngine(save_dir=snapshot, llm_base_url=llm, embedding_base_url=embed)


def export_one(snapshot, out_dir, llm, embed, min_weight, limit_nodes):
    from graph_engine_adapter.export import export_facts, export_graph

    engine = load_engine(snapshot, llm, embed)
    meta = export_graph(engine.hp.graph, out_dir,
                        min_weight=min_weight, limit_nodes=limit_nodes)
    facts = export_facts(engine.openie_docs(), os.path.join(out_dir, "facts.jsonl"))
    meta["facts"] = facts
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    return meta


def read_jsonl(path):
    if not os.path.isfile(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def compare_dirs(a_dir, b_dir):
    """比较两份导出物：节点/边的增删，事实三元组的增删。"""
    def keys(rows, fields):
        return {tuple(str(r[f]) for f in fields) for r in rows}

    a_nodes = keys(read_jsonl(os.path.join(a_dir, "nodes.jsonl")), ("id",))
    b_nodes = keys(read_jsonl(os.path.join(b_dir, "nodes.jsonl")), ("id",))
    a_edges = keys(read_jsonl(os.path.join(a_dir, "edges.jsonl")), ("source", "target"))
    b_edges = keys(read_jsonl(os.path.join(b_dir, "edges.jsonl")), ("source", "target"))
    a_facts = keys(read_jsonl(os.path.join(a_dir, "facts.jsonl")),
                   ("subject", "predicate", "object"))
    b_facts = keys(read_jsonl(os.path.join(b_dir, "facts.jsonl")),
                   ("subject", "predicate", "object"))

    def delta(a, b):
        return {"only_a": sorted(list(a - b))[:20], "only_b": sorted(list(b - a))[:20],
                "only_a_count": len(a - b), "only_b_count": len(b - a)}

    out = {"schema": "llmke.graph-export-diff.v1",
           "nodes": delta(a_nodes, b_nodes),
           "edges": delta(a_edges, b_edges),
           "facts": delta(a_facts, b_facts)}
    out["identical"] = all(out[k]["only_a_count"] == 0 and out[k]["only_b_count"] == 0
                           for k in ("nodes", "edges", "facts"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True, help="导出目录（nodes/edges/facts/meta）")
    ap.add_argument("--compare", default=None, help="与另一个快照导出物比较（会先导出临时副本）")
    ap.add_argument("--compare-out", default=None, help="差异 JSON 路径，默认打印")
    ap.add_argument("--min-weight", type=float, default=0.0)
    ap.add_argument("--limit-nodes", type=int, default=None)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    args = ap.parse_args(argv)

    meta = export_one(args.snapshot, args.out, args.llm, args.embed,
                      args.min_weight, args.limit_nodes)
    report = {"schema": meta["schema"], "snapshot": args.snapshot, "out": args.out,
              "nodes": meta["nodes"]["count"], "edges": meta["edges"]["count"],
              "facts": meta["facts"]["facts"],
              "nodes_sha256": meta["nodes"]["sha256"],
              "facts_sha256": meta["edges"]["sha256"]}

    if args.compare:
        other = args.out.rstrip("/") + "-compare"
        export_one(args.compare, other, args.llm, args.embed,
                   args.min_weight, args.limit_nodes)
        diff = compare_dirs(args.out, other)
        report["diff"] = diff
        report["identical"] = diff["identical"]
        if args.compare_out:
            with open(args.compare_out, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(diff, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("identical", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
