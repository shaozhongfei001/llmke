#!/usr/bin/env python
"""双写对比：同一语料分别用 full 与 delta 建两份快照，逐块比对抽取结果。

为什么需要它：增量重建目前只验到"结构性一致"（块数、openie 条数）。
如果两条路径抽出来的事实不同，灰度切过去就是**静默降质**——比崩溃更难发现。

对比口径（三层，从粗到细）：
1. 块集合：passage 文本必须完全一致（有序哈希集合比较）；
2. 事实集合：按 (chunk, subject, predicate, object) 归一化后比较；
3. 差异归因：只在一侧出现的事实，按块是否相同分成 `MISSING_CHUNK` / `EXTRACTION_DIFF`。

诚实边界：`EXTRACTION_DIFF` **不能**直接判为 bug——LLM 抽取本身有抖动。
要判定 delta 是否有问题，必须再跑一次 full 与 full 对比得到"基线噪声"，
本脚本只负责把差异**逐条列出来**，不做"差异=缺陷"的推断。
"""

import argparse
import collections
import glob
import hashlib
import json
import os


def load_openie(snapshot_dir):
    files = sorted(glob.glob(os.path.join(snapshot_dir, "openie_results_ner_*.json")))
    if not files:
        raise SystemExit(f"{snapshot_dir} 下没有 openie_results_ner_*.json")
    data = json.load(open(files[-1], encoding="utf-8"))
    return [(doc.get("idx"), doc.get("passage") or "",
             [tuple(str(x) for x in triple) for triple in (doc.get("extracted_triples") or [])])
            for doc in (data.get("docs") or [])]


def chunk_key(passage):
    return hashlib.sha256(passage.encode("utf-8")).hexdigest()[:16]


def diff(a_dir, b_dir):
    a_docs, b_docs = load_openie(a_dir), load_openie(b_dir)
    a_map = {chunk_key(p): (idx, p, triples) for idx, p, triples in a_docs}
    b_map = {chunk_key(p): (idx, p, triples) for idx, p, triples in b_docs}

    only_a = sorted(set(a_map) - set(b_map))
    only_b = sorted(set(b_map) - set(a_map))
    shared = sorted(set(a_map) & set(b_map))

    a_facts = collections.Counter((key, t) for key in a_map for t in a_map[key][2])
    b_facts = collections.Counter((key, t) for key in b_map for t in b_map[key][2])

    facts_only_a = [(key, t) for (key, t) in (a_facts - b_facts)]
    facts_only_b = [(key, t) for (key, t) in (b_facts - a_facts)]

    attribution = collections.Counter()
    samples = []
    for key, triple in facts_only_a + facts_only_b:
        if key not in a_map or key not in b_map:
            reason = "MISSING_CHUNK"
        else:
            reason = "EXTRACTION_DIFF"
        attribution[reason] += 1
        if len(samples) < 10:
            samples.append({"chunk": key, "triple": list(triple), "reason": reason,
                            "side": "a" if (key, triple) in facts_only_a else "b"})

    return {
        "schema": "llmke.dual-build-diff.v1",
        "a": {"dir": a_dir, "chunks": len(a_map), "facts": len(a_facts)},
        "b": {"dir": b_dir, "chunks": len(b_map), "facts": len(b_facts)},
        "chunks": {"only_a": only_a[:10], "only_b": only_b[:10],
                   "shared": len(shared), "identical": not only_a and not only_b},
        "facts": {"only_a": len(facts_only_a), "only_b": len(facts_only_b),
                  "shared": len(set(a_facts) & set(b_facts))},
        "attribution": dict(attribution),
        "samples": samples,
        "verdict": "IDENTICAL" if (not only_a and not only_b and not facts_only_a
                                   and not facts_only_b) else "DIFFERENT",
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="A 快照目录（如 full）")
    ap.add_argument("--b", required=True, help="B 快照目录（如 delta）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-extraction-diff", action="store_true",
                    help="块集合一致时，允许抽取差异（需另有基线噪声证据支撑）")
    args = ap.parse_args(argv)

    report = diff(args.a, args.b)
    problems = []
    if not report["chunks"]["identical"]:
        # 块集合不一致是硬问题：同一语料两条路径不该产出不同块
        problems.append(f"块集合不一致：only_a={len(report['chunks']['only_a'])} "
                        f"only_b={len(report['chunks']['only_b'])}")
    if report["facts"]["only_a"] or report["facts"]["only_b"]:
        if not args.allow_extraction_diff:
            problems.append(f"事实集合有差异（{report['facts']['only_a']} vs "
                            f"{report['facts']['only_b']}），未授权视为可接受")
        else:
            report["note"] = ("抽取差异已按 --allow-extraction-diff 接受；"
                              "仍需 full-vs-full 基线噪声佐证，否则可能是真降质")
    report["problems"] = problems
    report["status"] = "OK" if not problems else "FAIL"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"status": report["status"], "verdict": report["verdict"],
                      "chunks": report["chunks"],
                      "facts": report["facts"], "problems": problems}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
