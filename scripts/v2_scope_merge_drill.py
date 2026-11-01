#!/usr/bin/env python
"""跨范围合并检索验收：单范围用户看不到越界内容，双范围用户能取到。

需要已建好的范围索引（`.artifacts/scoped/scopes.json`，由 `v2_partition_drill.py` 生成）。
引擎按需加载并缓存：两份索引同时驻留内存约 2×，语料大时要留意。
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services", "rag-alg", "index_data_service"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(HERE, ".artifacts", "scoped"))
    ap.add_argument("--scopes", nargs="+", default=["dept-a"])
    ap.add_argument("--other-scope", default="dept-b")
    ap.add_argument("--query", default="五级分类口径中的关注是什么意思")
    # 别用"五级分类"当特征：台账表头里就有这一列，单范围结果也会命中，
    # 会造出"隔离失效"的假阳性。要用只出现在目标文档正文里的句子。
    ap.add_argument("--needle", default="借款人能够履行合同",
                    help="只在 other-scope 可见的正文特征；单范围结果里不应出现")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    from graph_engine_adapter.merged import retrieve_merged

    cache = {}

    def loader(snapshot):
        if snapshot not in cache:
            cache[snapshot] = HippoRAGEngine(save_dir=snapshot, llm_base_url=args.llm,
                                             embedding_base_url=args.embed)
        return cache[snapshot]

    def run(scopes):
        got = retrieve_merged(scopes, root=args.root, loader=loader,
                              query=args.query, top_k=args.top_k)
        texts = [(h.get("text") or "") for h in got["hits"]]
        return {"scopes": scopes, "used": got["scopes_used"],
                "missing": got["scopes_missing"], "hit_count": got["hit_count"],
                "contains_needle": any(args.needle in t for t in texts),
                "top": [t[:24].replace("\n", " ") for t in texts]}

    started = time.time()
    single = run(args.scopes)
    both = run(list(args.scopes) + [args.other_scope])
    problems = []
    if single["contains_needle"]:
        problems.append("单范围用户检索到了只属于其它范围的文本（隔离失效）")
    if not both["contains_needle"]:
        problems.append("多范围用户检索不到其它范围的内容（合并失效）")

    report = {"schema": "llmke.scope-merge-drill.v1", "root": args.root,
              "query": args.query, "needle": args.needle,
              "single": single, "merged": both,
              "elapsed_s": round(time.time() - started, 1),
              "problems": problems, "status": "OK" if not problems else "FAIL"}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "single", "merged", "problems")},
                     ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
