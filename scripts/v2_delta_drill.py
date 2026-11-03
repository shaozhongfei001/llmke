#!/usr/bin/env python
"""增量重建真跑：全量建一次 → 删一个文件 + 加一段新文本 → 只走增量。

要回答的不是"指针切过去了"，而是**到底省掉了什么**：
- 已存在的块有没有被重新抽取（看 openie 结果条数与新增条数）；
- 新增的块有没有被抽取（条数必须 +1，不能"跳过"当成功）；
- 被删的块在快照里是否真的消失（chunk store 文本集合）；
- 增量耗时与全量耗时差多少（量级才说明问题，绝对值会被机器影响）。

不做的事：不测检索质量（那需要重排模型，波动大且与本能力无关）。
"""

import argparse
import glob
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services/rag-alg/index_data_service"))


def load_docs(payloads):
    docs = []
    for path in payloads:
        payload = json.load(open(path, encoding="utf-8"))
        for chunk in payload.get("chunks", []):
            meta = chunk.get("metadata", {})
            docs.append({"file_id": str(meta.get("file_id", "")),
                         "text": chunk["page_content"]})
    return docs


def openie_count(save_dir):
    files = sorted(glob.glob(os.path.join(save_dir, "openie_results_ner_*.json")))
    if not files:
        return 0
    data = json.load(open(files[-1], encoding="utf-8"))
    return len(data.get("docs") or [])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--drop-file", default=None, help="增量时删掉这个 file_id 的块")
    ap.add_argument("--add-text", default=None, help="增量时新增这段文本")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    from graph_engine_adapter.fence import FenceState
    from graph_engine_adapter.rebuild import read_pointer, rebuild, rebuild_delta

    if os.path.isdir(args.root):
        shutil.rmtree(args.root)
    os.makedirs(args.root, exist_ok=True)

    docs = load_docs(args.payloads)
    fence = FenceState()

    def full_build(live, target):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.build([d["text"] for d in live])

    started = time.time()
    base = rebuild(args.root, fence, docs, full_build, fencing=1)
    t_full = time.time() - started
    base_dir = base["current"]["dir"]
    base_texts = sorted(json.load(open(os.path.join(base_dir, "graph.json"), encoding="utf-8"))["chunks"]) \
        if os.path.isfile(os.path.join(base_dir, "graph.json")) else None
    base_openie = openie_count(base_dir)

    # 构造差异：删一个文件（默认第一个）+ 追加一段新文本
    drop = args.drop_file or (docs[0]["file_id"] if docs else None)
    delta_docs = [d for d in docs if d["file_id"] != drop]
    added_text = args.add_text or "新增制度条款：单笔授信超过五亿元须经董事会审议通过。"
    delta_docs = delta_docs + [{"file_id": "new-1", "text": added_text}]

    removed_texts = [d["text"] for d in docs if d["file_id"] == drop]

    def apply_fn(target, live_texts):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.apply_delta(live_texts)

    started = time.time()
    delta = rebuild_delta(args.root, fence, delta_docs, apply_fn, fencing=1)
    t_delta = time.time() - started
    delta_dir = delta["current"]["dir"]
    delta_openie = openie_count(delta_dir)

    engine_after = HippoRAGEngine(save_dir=delta_dir, llm_base_url=args.llm,
                                  embedding_base_url=args.embed)
    remaining_texts = set(engine_after.all_texts())
    leaked = [t[:30] for t in removed_texts if t in remaining_texts]

    pointer = read_pointer(args.root)
    report = {
        "root": args.root,
        "full": {"seconds": round(t_full, 1), "dir": base_dir,
                 "documents": base["current"]["documents"], "openie_docs": base_openie},
        "delta": {"seconds": round(t_delta, 1), "dir": delta_dir,
                  "documents": delta["current"]["documents"],
                  "openie_docs": delta_openie,
                  "apply": delta.get("apply_result")},
        "pointer": {"mode": pointer.get("mode"), "generation": pointer.get("generation"),
                    "fencing": pointer.get("fencing"), "documents": pointer.get("documents")},
        "deleted_file": drop,
        "deleted_still_present": leaked,
        "openie_reused": base_openie - len(removed_texts),
        "speedup_x": round(t_full / t_delta, 1) if t_delta else None,
        "base_graph_json_present": base_texts is not None,
    }
    problems = []
    if leakage := leaked:
        problems.append(f"被删文本仍在快照里: {leakage[:2]}")
    apply_result = delta.get("apply_result") or {}
    if not apply_result.get("consistent"):
        problems.append(f"块数不一致: {apply_result}")
    if pointer.get("mode") != "DELTA":
        problems.append(f"指针 mode 不是 DELTA: {pointer.get('mode')}")
    # 严格等式：增量后 openie 条数 == 旧条数 - 删除 + 新增。等号不成立就说明有人重跑了存量
    expected_openie = base_openie - int(apply_result.get("deleted", 0)) + int(apply_result.get("added", 0))
    report["openie_expected"] = expected_openie
    if delta_openie != expected_openie:
        problems.append(
            f"openie 条数 {delta_openie} != 期望 {expected_openie}"
            f"（旧 {base_openie}、删 {apply_result.get('deleted')}、增 {apply_result.get('added')}）")
    report["problems"] = problems
    report["status"] = "OK" if not problems else "FAIL"

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: report[k] for k in ("status", "speedup_x", "problems")},
                     ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
