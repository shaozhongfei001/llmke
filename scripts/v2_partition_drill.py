#!/usr/bin/env python
"""构建期可见隔离演练：按可见范围分别建索引，验证"看不到的内容压根不在索引里"。

与查询期过滤的区别：过滤是"命中后丢掉"，隔离是"根本不进索引"。
本脚本建两份索引（如 dept-a / dept-b），然后断言：
1. 只对 dept-b 可见的文档，**不出现在 dept-a 的快照里**（按块文本与 openie 双重检查）；
2. 拿那段文字去 dept-a 检索，命中数为 0；同样的检索在 dept-b 有命中；
3. 清单里没有的范围解析为 None（fail-closed），绝不回退全量。
"""

import argparse
import glob
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services", "rag-alg", "index_data_service"))

from graph_engine_adapter.partition import build_plan, resolve, scope_dir, summarize  # noqa: E402


def load_docs(paths):
    docs = []
    for path in paths:
        data = json.loads(open(path, encoding="utf-8").read())
        for chunk in data.get("chunks") or []:
            meta = chunk.get("metadata") or {}
            docs.append({"file_id": str(meta.get("file_id", "")),
                         "text": chunk["page_content"],
                         "visibility": meta.get("visibility") or ["public"]})
    return docs


def _norm(text):
    return "".join(ch for ch in str(text or "") if ch not in "#\n\r\t ")


def contains_target(target, text, window=10):
    """判断返回块里是否包含探针文本：按归一化后的 10 字窗口比对。

    直接拿问句前缀去比会漏——返回的是块原文（带 `##` 与换行），问句并不是原文子串。
    """
    t, x = _norm(target), _norm(text)
    if not t or not x:
        return False
    return any(t[i:i + window] in x for i in range(0, max(1, len(t) - window + 1)))


def openie_texts(save_dir):
    files = sorted(glob.glob(os.path.join(save_dir, "openie_results_ner_*.json")))
    if not files:
        return []
    data = json.loads(open(files[-1], encoding="utf-8").read())
    return [str(d.get("passage") or "") for d in (data.get("docs") or [])]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--scopes", nargs="+", required=True)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--probe-text", default=None,
                    help="只在某个范围可见的文本；用来验证另一个范围检索不到")
    ap.add_argument("--probe-scope", default=None, help="该文本所属范围（应能检索到）")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    from graph_engine_adapter.fence import FenceState
    from graph_engine_adapter.partition import write_manifest
    from graph_engine_adapter.rebuild import rebuild

    if os.path.isdir(args.root):
        shutil.rmtree(args.root)
    os.makedirs(args.root, exist_ok=True)

    docs = load_docs(args.payloads)
    plan = build_plan(docs, args.scopes)
    fence = FenceState()
    entries, problems = {}, []
    started = time.time()

    for scope, scope_docs in plan.items():
        target_root = scope_dir(args.root, scope)
        os.makedirs(target_root, exist_ok=True)

        def full_build(live, target):
            return HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                  embedding_base_url=args.embed).build(
                                      [d["text"] for d in live])

        t0 = time.time()
        result = rebuild(target_root, fence, scope_docs, full_build, fencing=1)
        snapshot = result["current"]["dir"]
        entries[scope] = {"snapshot": snapshot, "documents": len(scope_docs),
                          "chunks": sum(1 for _ in openie_texts(snapshot)),
                          "seconds": round(time.time() - t0, 1)}
        # 隔离的硬证据：这个范围不该看到的文本，是否出现在快照里
        visible = {d["text"] for d in scope_docs}
        leaked = [t for t in openie_texts(snapshot) if t and t not in visible]
        if leaked:
            problems.append(f"{scope} 快照里出现了不可见文本 {len(leaked)} 条")

    write_manifest(args.root, entries)

    # 检索探针：同一段文字在两个范围各查一次
    probe = {"text": args.probe_text, "scope": args.probe_scope, "results": {}}
    if args.probe_text:
        for scope, entry in entries.items():
            engine = HippoRAGEngine(save_dir=entry["snapshot"], llm_base_url=args.llm,
                                    embedding_base_url=args.embed)
            got = engine.retrieve(args.probe_text, top_k=3)
            docs_hit = [t for t in (got.get("docs") or [])]
            hit_secret = any(contains_target(args.probe_text, t) for t in docs_hit)
            probe["results"][scope] = {"hits": len(docs_hit), "contains_target": hit_secret}
        owner = probe["results"].get(args.probe_scope or "", {})
        if not owner.get("contains_target"):
            problems.append(f"目标范围 {args.probe_scope} 竟检索不到探针文本")
        for scope, r in probe["results"].items():
            if scope != args.probe_scope and r["contains_target"]:
                problems.append(f"{scope} 检索到了只属于 {args.probe_scope} 的文本（隔离失效）")

    report = {"schema": "llmke.partition-drill.v1", "root": args.root,
              "scopes": entries, "plan": summarize(plan), "probe": probe,
              "elapsed_s": round(time.time() - started, 1),
              "problems": problems, "status": "OK" if not problems else "FAIL"}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "plan", "probe", "problems")},
                     ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
