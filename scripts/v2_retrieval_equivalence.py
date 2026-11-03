#!/usr/bin/env python
"""检索层等价性：同一批 query 在两份快照上检索，比对命中文档集合与排序。

为什么抽完对比（C2）还不够：用户感知的是**检索结果**，不是 openie 条数。
两份快照抽取不同、但检索一致 → 切换风险低；抽取一致、排序却不同 → 照样"答非所问"。

做法：
1. 先加载 A 快照跑完所有 query 并**释放引擎**，再加载 B——同时驻留两份引擎容易 OOM，
   而且测的是检索结果不是内存占用；
2. 每条 query 记 top_k 命中文本的哈希（不比全文，避免日志爆炸）；
3. 输出：top1 一致率、集合 Jaccard、有序完全一致率；**基线对照**（A vs A' 两次）用来
   区分"实现差异"和"检索本身不稳定"。

诚实边界：embedding 模型与 PPR 都可能有微小随机性；没有基线对照就断言"差异=降质"是耍流氓。
"""

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services/rag-alg/index_data_service"))

DEFAULT_QUERIES = [
    "授信额度是多少",
    "华东精密制造有限公司的信用评级",
    "单笔授信超过五亿元由谁审议通过",
    "江南装备科技有限公司属于哪个产业链",
    "多指标对账口径里日均存款的数据源",
    "海川电子材料股份有限公司的授信额度",
]


def hit_key(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]


def run_queries(save_dir, queries, top_k, llm, embed):
    from graph_engine_adapter.engine_hipporag import HippoRAGEngine

    # 检索要调 LLM 做 query 实体抽取（NER），不传 llm_base_url 会退回公网默认地址 →
    # APIConnectionError。这是"检索也需要模型"，不是"检索只用向量"。
    engine = HippoRAGEngine(save_dir=save_dir, llm_base_url=llm,
                            embedding_base_url=embed)
    out = []
    for query in queries:
        started = time.time()
        result = engine.retrieve(query, top_k=top_k)
        # 引擎层返回的是 `docs`（纯文本列表），不是带 sources 的 `hits`——
        # `hits` 是 GraphRetriever 包装层才有的形状。按错字段读会得到"0 命中"，
        # 而空列表互相比较又是"完全一致"，这种假绿最危险。
        hits = list(result.get("hits") or [])
        texts = [h.get("text") for h in hits] if hits else list(result.get("docs") or [])
        out.append({"query": query,
                    "route": result.get("route") or result.get("executed_route"),
                    "hits": [hit_key(t) for t in texts],
                    "seconds": round(time.time() - started, 2)})
    return out


def compare(a_rows, b_rows, top_k):
    details, problems = [], []
    top1_same = 0
    ordered_same = 0
    jaccard_sum = 0.0
    for a, b in zip(a_rows, b_rows):
        sa, sb = a["hits"], b["hits"]
        inter = len(set(sa) & set(sb))
        union = len(set(sa) | set(sb)) or 1
        jacc = inter / union
        same_order = sa == sb
        top1 = bool(sa) and bool(sb) and sa[0] == sb[0]
        top1_same += 1 if top1 else 0
        ordered_same += 1 if same_order else 0
        jaccard_sum += jacc
        details.append({"query": a["query"], "jaccard": round(jacc, 3),
                        "top1_same": top1, "ordered_same": same_order,
                        "only_a": [h for h in sa if h not in sb][:3],
                        "only_b": [h for h in sb if h not in sa][:3],
                        "route": [a["route"], b["route"]]})
        if a["route"] != b["route"]:
            problems.append(f"路线不同：{a['query']} {a['route']} vs {b['route']}")
    n = max(len(a_rows), 1)
    return {"queries": n, "top1_same": top1_same, "ordered_same": ordered_same,
            "avg_jaccard": round(jaccard_sum / n, 3),
            "top1_rate": round(top1_same / n, 3),
            "ordered_rate": round(ordered_same / n, 3),
            "details": details, "problems": problems}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--a2", default=None, help="同一快照的第二次运行，用于采集检索基线噪声")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--queries", nargs="+", default=DEFAULT_QUERIES)
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    t0 = time.time()
    a_rows = run_queries(args.a, args.queries, args.top_k, args.llm, args.embed)
    a2_rows = (run_queries(args.a2, args.queries, args.top_k, args.llm, args.embed)
               if args.a2 else None)
    b_rows = run_queries(args.b, args.queries, args.top_k, args.llm, args.embed)

    report = {"schema": "llmke.retrieval-equivalence.v1",
              "a": args.a, "b": args.b, "top_k": args.top_k,
              "elapsed_s": round(time.time() - t0, 1),
              "a_vs_b": compare(a_rows, b_rows, args.top_k)}
    if a2_rows is not None:
        report["baseline_a_vs_a2"] = compare(a_rows, a2_rows, args.top_k)

    problems = list(report["a_vs_b"]["problems"])
    if report["a_vs_b"]["top1_rate"] < 1.0:
        problems.append(f"top1 一致率仅 {report['a_vs_b']['top1_rate']}")
    report["problems"] = problems
    report["status"] = "OK" if not problems else "FAIL"

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    summary = {k: report["a_vs_b"][k] for k in
               ("queries", "top1_rate", "ordered_rate", "avg_jaccard")}
    if "baseline_a_vs_a2" in report:
        summary["baseline"] = {k: report["baseline_a_vs_a2"][k] for k in
                               ("top1_rate", "ordered_rate", "avg_jaccard")}
    print(json.dumps({"status": report["status"], **summary, "problems": problems},
                     ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
