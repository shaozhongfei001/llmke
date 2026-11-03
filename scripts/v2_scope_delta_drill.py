#!/usr/bin/env python
"""按范围的增量重建真跑：两个范围各建一次全量 → 改一份文档 → 只重建"被影响的那个范围"。

要回答的不是"指针切过去了"，而是三件事：
1. **省了多少**：全量建一个范围 vs 增量重建同一个范围，耗时差多少倍（量级才说明问题）；
2. **改了没有**：apply 的 deleted/added/reused 与快照里实际剩下的块文本是否对得上，
   被删文件的内容是否真的从快照里消失；
3. **有没有波及别人**：**未变更范围**的快照目录、目录内容 sha、指针文件必须一个字节都没动；
   清单里两个范围的条目必须都还在（`write_manifest` 是整表覆盖，写漏一条那条范围就查不到了）。

不做的事：不测检索质量（需要重排模型，波动大且与本能力无关）。
"""

import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services", "rag-alg", "index_data_service"))


def load_docs(paths):
    """读文档，**保留 visibility**：丢了它，范围划分会把所有人当 public。"""
    docs = []
    for path in paths:
        payload = json.loads(open(path, encoding="utf-8").read())
        for chunk in payload.get("chunks") or []:
            meta = chunk.get("metadata") or {}
            docs.append({"file_id": str(meta.get("file_id", "")),
                         "text": chunk["page_content"],
                         "visibility": meta.get("visibility") or ["public"]})
    return docs


def openie_texts(save_dir):
    files = sorted(glob.glob(os.path.join(save_dir, "openie_results_ner_*.json")))
    if not files:
        return []
    data = json.loads(open(files[-1], encoding="utf-8").read())
    return [str(d.get("passage") or "") for d in (data.get("docs") or [])]


def dir_fingerprint(path):
    """目录指纹：文件相对路径 + 每个文件内容的 sha256。

    只比目录名不够——目录名会被时间戳换掉，但用户关心的是"内容有没有被碰过"。
    """
    if not path or not os.path.isdir(path):
        return {"exists": False, "files": 0, "sha256": None}
    digest = hashlib.sha256()
    count = 0
    for base, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, path)
            digest.update(rel.encode("utf-8"))
            with open(full, "rb") as fh:
                digest.update(hashlib.sha256(fh.read()).digest())
            count += 1
    return {"exists": True, "files": count, "sha256": digest.hexdigest()}


def file_sha(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def changed_scopes(before_plan, after_plan):
    """哪些范围的内容集合真的变了：不靠"我猜它属于哪个范围"，靠两份 plan 直接比。"""
    out = []
    for scope in sorted(set(before_plan) | set(after_plan)):
        a = sorted(d["text"] for d in before_plan.get(scope, []))
        b = sorted(d["text"] for d in after_plan.get(scope, []))
        if a != b:
            out.append(scope)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--root", default=".artifacts/scope-delta")
    ap.add_argument("--scopes", nargs="+", default=["dept-a", "dept-b"])
    ap.add_argument("--drop-file", default=None, help="改文档：删掉这个 file_id 的全部块")
    ap.add_argument("--add-text", default=None, help="改文档：新增这一段文本")
    ap.add_argument("--add-to-file", default=None,
                    help="新增文本挂到哪个 file_id（默认挂在被删的文件上，即'改同一份文档'）")
    ap.add_argument("--llm", default="http://127.0.0.1:18092/v1")
    ap.add_argument("--embed", default="http://127.0.0.1:18090/v1")
    ap.add_argument("--keep-last", type=int, default=2)
    ap.add_argument("--cjk-compat", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.cjk_compat:
        from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
        install_cjk_text_processing()

    from graph_engine_adapter.engine_hipporag import HippoRAGEngine
    from graph_engine_adapter.partition import (MANIFEST_NAME, build_plan, resolve,
                                                scope_delta_build, scope_dir)

    if os.path.isdir(args.root):
        shutil.rmtree(args.root)
    os.makedirs(args.root, exist_ok=True)

    docs = load_docs(args.payloads)
    problems = []

    def full_build(live, target):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.build([d["text"] for d in live])

    def apply_fn(target, live_texts):
        engine = HippoRAGEngine(save_dir=target, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        return engine.apply_delta(live_texts)

    # ---------- 阶段 1：每个范围各一次全量（显式 allow_full_build：首次构建就是全量） ----------
    full = {}
    t_all = time.time()
    for scope in args.scopes:
        t0 = time.time()
        out = scope_delta_build(args.root, scope, docs, full_build, apply_fn,
                                fencing=1, keep_last=args.keep_last, allow_full_build=True)
        seconds = time.time() - t0
        snap = out["current"]["dir"]
        full[scope] = {"seconds": round(seconds, 1), "dir": snap, "mode": out["mode"],
                       "documents": out["current"]["documents"],
                       "openie_docs": len(openie_texts(snap)),
                       "dir_sha": dir_fingerprint(snap)["sha256"]}
        print(f"[full] {scope}: {seconds:.1f}s, documents={out['current']['documents']}, "
              f"openie={full[scope]['openie_docs']}, dir={snap}", flush=True)
    full_total = time.time() - t_all
    t_full_single = max(v["seconds"] for v in full.values())

    # 改文档之前的基线：未变更范围必须与这些值逐字节相同
    before_state = {}
    for scope in args.scopes:
        entry = resolve(args.root, scope) or {}
        sroot = scope_dir(args.root, scope)
        before_state[scope] = {
            "snapshot": entry.get("snapshot"),
            "dir_sha": dir_fingerprint(entry.get("snapshot"))["sha256"],
            "dir_files": dir_fingerprint(entry.get("snapshot"))["files"],
            "pointer_sha": file_sha(os.path.join(sroot, "current.json")),
            "pointer_dir": json.loads(open(os.path.join(sroot, "current.json"),
                                           encoding="utf-8").read()).get("dir")
            if os.path.isfile(os.path.join(sroot, "current.json")) else None,
        }

    # ---------- 阶段 2：改一份文档 ----------
    drop = args.drop_file
    if not drop:
        problems.append("没有指定 --drop-file：本次没有产生文档变更，无法验证增量")
    dropped_docs = [d for d in docs if d["file_id"] == drop]
    if drop and not dropped_docs:
        problems.append(f"--drop-file {drop} 在语料里不存在")

    add_text = args.add_text or "补充条款：单笔授信超过五亿元须经董事会审议通过。"
    # 新增文本默认挂在被删的那个 file_id 上 —— "改同一份文档"，
    # 这样可见范围不变，才能干净地验证"另一个范围一点没动"。
    add_to = args.add_to_file or (f"{drop}" if drop else "new-1")
    # 新文本的可见范围 = 被改那份文档的可见范围（找不到才退回 public）。
    # 若这里随手给 public，改动就会扩散到另一个范围，"未变更范围没被动过"这条断言随之失效。
    inherited_visibility = None
    for doc in dropped_docs + [d for d in docs if d["file_id"] == add_to]:
        if doc.get("visibility"):
            inherited_visibility = doc["visibility"]
            break
    inherited_visibility = inherited_visibility or ["public"]

    after_docs = [d for d in docs if d["file_id"] != drop]
    after_docs.append({"file_id": add_to, "text": add_text,
                       "visibility": inherited_visibility})

    plan_before = build_plan(docs, args.scopes)
    plan_after = build_plan(after_docs, args.scopes)
    touched = changed_scopes(plan_before, plan_after)
    if not touched:
        problems.append("文档改动没有导致任何范围内容变化：演练无效")
    untouched = [s for s in args.scopes if s not in touched]

    # ---------- 阶段 3：只重建被影响的范围（走增量） ----------
    delta = {}
    for scope in touched:
        t0 = time.time()
        try:
            out = scope_delta_build(args.root, scope, after_docs, full_build, apply_fn,
                                    fencing=1, keep_last=args.keep_last)
        except Exception as exc:  # noqa: BLE001 - 演练脚本要如实报，不吞
            problems.append(f"{scope} 增量重建失败：{type(exc).__name__}: {exc}")
            continue
        seconds = time.time() - t0
        snap = out["current"]["dir"]
        engine = HippoRAGEngine(save_dir=snap, llm_base_url=args.llm,
                                embedding_base_url=args.embed)
        remaining = set(engine.all_texts())
        expected = {d["text"] for d in plan_after[scope]}
        stale = [t[:24] for t in (expected ^ remaining)]
        apply_result = out.get("apply_result") or {}

        if snap == before_state[scope]["snapshot"]:
            problems.append(f"{scope} 增量没有产生新快照目录")
        if not snap.startswith(scope_dir(args.root, scope) + os.sep):
            problems.append(f"{scope} 的快照不在 scope_dir 下：{snap}")
        if stale:
            problems.append(f"{scope} 快照文本与期望差 {len(stale)} 条：{stale[:2]}")
        if not apply_result.get("consistent"):
            problems.append(f"{scope} apply 后块数不一致：{apply_result}")
        # 被删的内容必须真的没了
        leaked = [d["text"][:24] for d in dropped_docs if d["text"] in remaining]
        if leaked:
            problems.append(f"{scope} 被删文件的内容仍在快照里：{leaked[:2]}")
        if out["mode"] != "DELTA":
            problems.append(f"{scope} 期望走增量，实际 mode={out['mode']}")

        delta[scope] = {"seconds": round(seconds, 1), "dir": snap, "mode": out["mode"],
                        "documents": out["current"]["documents"],
                        "openie_docs": len(openie_texts(snap)),
                        "apply": apply_result,
                        "dir_sha": dir_fingerprint(snap)["sha256"],
                        "texts_vs_expected": len(stale)}

    # ---------- 阶段 4：未变更范围必须一个字节都没动 ----------
    untouched_check = {}
    for scope in untouched:
        entry = resolve(args.root, scope) or {}
        snap = entry.get("snapshot")
        now = {"snapshot": snap,
               "dir_sha": dir_fingerprint(snap)["sha256"],
               "dir_files": dir_fingerprint(snap)["files"],
               "pointer_sha": file_sha(os.path.join(scope_dir(args.root, scope),
                                                   "current.json"))}
        same = (now["snapshot"] == before_state[scope]["snapshot"]
                and now["dir_sha"] == before_state[scope]["dir_sha"]
                and now["pointer_sha"] == before_state[scope]["pointer_sha"])
        untouched_check[scope] = {"snapshot_unchanged":
                                  now["snapshot"] == before_state[scope]["snapshot"],
                                  "dir_sha_unchanged":
                                  now["dir_sha"] == before_state[scope]["dir_sha"],
                                  "pointer_sha_unchanged":
                                  now["pointer_sha"] == before_state[scope]["pointer_sha"],
                                  "dir_sha": now["dir_sha"], "all_unchanged": same}
        if not same:
            problems.append(f"未变更范围 {scope} 被动到了：{untouched_check[scope]}")

    # ---------- 阶段 5：清单完整性（两个范围都必须还在，且都解析得到） ----------
    manifest_path = os.path.join(args.root, MANIFEST_NAME)
    raw = json.loads(open(manifest_path, encoding="utf-8").read()) if \
        os.path.isfile(manifest_path) else {"scopes": {}}
    listed = sorted(raw.get("scopes") or {})
    manifest_check = {}
    for scope in args.scopes:
        entry = resolve(args.root, scope)
        manifest_check[scope] = {
            "listed": scope in listed,
            "snapshot": (entry or {}).get("snapshot"),
            "resolvable": entry is not None,
            "snapshot_exists": bool(entry) and os.path.isdir(entry["snapshot"]),
            "mode": (entry or {}).get("mode"),
            "documents": (entry or {}).get("documents"),
            "chunks": (entry or {}).get("chunks"),
        }
        if not (manifest_check[scope]["listed"]
                and manifest_check[scope]["resolvable"]
                and manifest_check[scope]["snapshot_exists"]):
            problems.append(f"清单里 {scope} 不完整：{manifest_check[scope]}")
    if listed != sorted(args.scopes):
        problems.append(f"清单范围 {listed} != 期望 {sorted(args.scopes)}")

    t_delta = sum(v["seconds"] for v in delta.values())
    report = {
        "schema": "llmke.scope-delta-drill.v1",
        "root": args.root,
        "scopes": args.scopes,
        "documents": len(docs),
        "change": {"drop_file": drop, "dropped_chunks": len(dropped_docs),
                   "add_text": add_text[:40], "add_to_file": add_to,
                   "visibility": inherited_visibility, "touched_scopes": touched,
                   "untouched_scopes": untouched},
        "full": {"per_scope": full, "total_seconds": round(full_total, 1),
                 "max_single_scope_seconds": round(t_full_single, 1)},
        "delta": {"per_scope": delta, "total_seconds": round(t_delta, 1)},
        # 两种口径都给：对"这一个范围"的加速，和相对"范围数 × 全量"的加速
        "speedup_x_vs_single_scope": round(t_full_single / t_delta, 1) if t_delta else None,
        "speedup_x_vs_all_scopes": round(full_total / t_delta, 1) if t_delta else None,
        "untouched_check": untouched_check,
        "manifest": {"path": manifest_path, "listed": listed, "per_scope": manifest_check},
        "problems": problems,
        "status": "OK" if not problems else "FAIL",
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({
        "status": report["status"],
        "full_seconds": report["full"]["per_scope"],
        "full_total_seconds": report["full"]["total_seconds"],
        "delta_seconds": report["delta"]["per_scope"],
        "speedup_x_vs_single_scope": report["speedup_x_vs_single_scope"],
        "speedup_x_vs_all_scopes": report["speedup_x_vs_all_scopes"],
        "touched_scopes": touched,
        "untouched_check": untouched_check,
        "manifest_listed": listed,
    }, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
