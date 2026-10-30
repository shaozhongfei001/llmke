#!/usr/bin/env python3
"""C1 最小真跑：HippoRAG 实际索引 + 检索 + 来源回指（本地 LLM/embedding 端点）。

用途
----
证明三件事，且都不靠模拟：
1. `hipporag==2.0.0a4` 能在本机装上并真正 `index()` / `retrieve()`（用 18092/18090 真实端点）；
2. 引擎 chunk 键 = `chunk-<md5(正文)>`，与平台 `native_key` 一致（已逐条核对）；
3. 同一段正文来自两个来源时，引擎只有一个 chunk，但平台映射表保留**两个 SourceRef**，
   检索结果能按正文回到各自的文件与快照。

运行（独立环境，不进 llmke 依赖）：
  /home/szf/data/dev/hipporag-toolenv/bin/python scripts/v2_hipporag_smoke.py --out /tmp/hippo-smoke.json

退出码：0 全部断言通过；1 结果不符；2 环境缺失。
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services/rag-alg/index_data_service"))

from graph_engine_adapter import InputUnit, SourceMap, native_key  # noqa: E402

DOCS = [
    ("产品甲的最高额度为8000万元，利率基准为1年期LPR。", "333", "r12-rag/kb_9/甲-产品定价.docx", 0),
    ("客户A申请产品甲，额度分项合计等于总额度。", "333", "r12-rag/kb_9/甲-产品定价.docx", 1),
    # 同文异源：同一句话出现在另一份文件里，引擎会合并成一个 chunk，来源必须都留下
    ("产品甲的最高额度为8000万元，利率基准为1年期LPR。", "334", "r12-rag/kb_9/乙-客户申请.docx", 0),
    ("产品乙的最高额度为5000万元，担保方式为保证。", "334", "r12-rag/kb_9/乙-客户申请.docx", 1),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--save-dir", default="/tmp/hippo-run")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--query", default="客户A申请产品甲的额度是多少")
    args = ap.parse_args(argv)

    os.environ.setdefault("OPENAI_API_KEY", "sk-local")
    try:
        from hipporag import HippoRAG
        from hipporag.utils.config_utils import BaseConfig
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "ENV_MISSING", "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 2

    # 1) 平台侧映射：一块一来源，允许同文多源
    sm = SourceMap()
    for i, (text, file_id, source, seq) in enumerate(DOCS):
        sm.add(InputUnit(text, content_uid="c" * 64, parse_artifact_id="a" * 64, seq=i,
                         source_ref={"file_id": file_id, "source": source, "seq": seq}))
    texts = [d[0] for d in DOCS]
    expect_engine_chunks = len({native_key(t) for t in texts})

    config = BaseConfig(save_dir=args.save_dir, llm_name="qwen2.5-7b-instruct",
                        llm_base_url=args.llm,
                        embedding_model_name="text-embedding-bge-m3",
                        embedding_base_url=args.embed, openie_mode="online")
    hp = HippoRAG(global_config=config)

    # 2) 真实索引与检索
    hp.index(texts)
    solutions = hp.retrieve([args.query], num_to_retrieve=2)

    hits = []
    for sol in (solutions or []):
        for doc_text in (getattr(sol, "docs", None) or []):
            key = native_key(doc_text)
            hits.append({"native_key": key, "text": doc_text[:60],
                         "sources": sm.sources_for(key)})

    engine_rows = hp.chunk_embedding_store.get_all_id_to_rows()
    report = {
        "status": "OK",
        "engine": {"version": "hipporag==2.0.0a4",
                   "llm_base_url": args.llm, "embedding_base_url": args.embed,
                   "chunk_ids": sorted(engine_rows)[:5],
                   "chunk_id_rule": "chunk-<md5(text)>"},
        "mapping": sm.stats(),
        "expected_engine_chunks": expect_engine_chunks,
        "actual_engine_chunks": len(engine_rows),
        "hits": hits,
        "query": args.query,
    }

    # 3) 断言：引擎侧合并、平台侧不丢来源
    problems = []
    if len(engine_rows) != expect_engine_chunks:
        problems.append(f"引擎 chunk 数 {len(engine_rows)} != 期望 {expect_engine_chunks}")
    shared = native_key(DOCS[0][0])
    if len(sm.sources_for(shared)) != 2:
        problems.append("同文异源未保留两个来源")
    if not hits:
        problems.append("检索无结果")
    if all(not h["sources"] for h in hits):
        problems.append("检索结果无法回指来源")

    if problems:
        report["status"] = "FAILED"
        report["problems"] = problems
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
