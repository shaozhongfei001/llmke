#!/usr/bin/env python
"""把验收用的图快照重建到**持久目录**，并写一份 `artifacts.json` 供 Q 使用。

为什么要有它：2026-11-01 关机后 `/tmp` 被清空，`dual-full` / `delta-drill` /
压力语料快照全部消失——Q 里 6 项图检查会整片 SKIP，而报告仍然是 PASS。
"跳过"比"失败"更危险：验收范围缩水了，没人看得出来。

所以这里把产物放到仓库下被 gitignore 的目录（默认 `.artifacts/`），
并写一份**稳定的清单**（不靠时间戳猜路径）。Q 侧只读清单，不猜路径。

用法：
    python scripts/v2_build_artifacts.py                 # 标准语料 + 压力语料
    python scripts/v2_build_artifacts.py --only stress   # 只重建压力语料
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROOT = os.path.join(HERE, ".artifacts")
def _pick_hipporag_python() -> str:
    """按顺序找一个存在的 hipporag 解释器；找不到就如实报错，不要落到不存在的路径上。"""
    candidates = [os.environ.get("V2_HIPPORAG_PYTHON"),
                  os.path.expanduser("~/hipporag-venv/bin/python"),
                  "/home/szf/data/dev/hipporag-toolenv/bin/python"]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return candidates[-1]


HIPPORAG_PY = _pick_hipporag_python()
SERVICE = os.path.join(HERE, "services", "rag-alg", "index_data_service")


def run(cmd, env=None, timeout=2400):
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, **(env or {})})
    return proc, round(time.time() - started, 1)


def build_pair(kind, payloads, root, drop_file=None, add_text=None):
    """跑一次 v2_delta_drill：它同时产出 full 与 delta 两份快照。"""
    out = os.path.join(root, f"{kind}.json")
    cmd = [HIPPORAG_PY, os.path.join(HERE, "scripts", "v2_delta_drill.py"),
           "--payloads", *payloads, "--root", os.path.join(root, kind),
           "--cjk-compat", "--out", out]
    if drop_file:
        cmd += ["--drop-file", drop_file]
    if add_text:
        cmd += ["--add-text", add_text]
    proc, seconds = run(cmd, env={"PYTHONPATH": SERVICE,
                                  "MINERU_TOOLS_CONFIG_JSON": os.environ.get(
                                      "MINERU_TOOLS_CONFIG_JSON", "")})
    if proc.returncode != 0 or not os.path.isfile(out):
        return {"kind": kind, "ok": False, "seconds": seconds,
                "error": (proc.stderr or proc.stdout or "")[-300:]}
    report = json.loads(open(out, encoding="utf-8").read())
    return {"kind": kind, "ok": report.get("status") == "OK", "seconds": seconds,
            "full": report["full"]["dir"], "delta": report["delta"]["dir"],
            "meta": {"full_s": report["full"]["seconds"], "delta_s": report["delta"]["seconds"],
                     "openie_docs": report["full"].get("openie_docs"),
                     "speedup_x": report.get("speedup_x"),
                     "apply": report["delta"].get("apply")}}


def safe_copy(src, dst):
    """基线对照需要第二份**独立构建**的全量快照；复制目录不算独立构建，只能重建。"""
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--only", choices=["all", "standard", "stress"], default="all")
    ap.add_argument("--skip-existing", action="store_true",
                    help="清单里已有的产物不再重建（省时间，但不会发现语料漂移）")
    ap.add_argument("--adopt", action="store_true",
                    help="不重建，只把磁盘上已有的演练输出（<root>/<name>.json）补进清单")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    os.makedirs(root, exist_ok=True)
    manifest_path = os.path.join(root, "artifacts.json")
    # 合并而不是覆盖：分两次跑（先 standard 后 stress）时，后一次不能把前一次从清单里抹掉——
    # 实测抹掉后 Q 的图检查会因为"清单里没有快照"整片 SKIP，而报告仍 PASS。
    manifest = {"schema": "llmke.artifacts.v1", "root": root, "built_at": None,
                "sets": {}}
    if os.path.isfile(manifest_path):
        try:
            old = json.loads(open(manifest_path, encoding="utf-8").read())
            manifest["sets"] = dict(old.get("sets") or {})
            manifest["payloads"] = old.get("payloads") or []
        except ValueError:
            pass

    if args.adopt:
        for name in ("standard", "standard_b", "stress", "stress_b"):
            report_path = os.path.join(root, f"{name}.json")
            if not os.path.isfile(report_path):
                continue
            try:
                rep = json.loads(open(report_path, encoding="utf-8").read())
            except ValueError:
                continue
            if rep.get("status") == "OK":
                manifest["sets"][name] = {
                    "kind": name, "ok": True, "seconds": rep["full"].get("seconds"),
                    "full": rep["full"]["dir"], "delta": rep["delta"]["dir"],
                    "meta": {"full_s": rep["full"].get("seconds"),
                             "delta_s": rep["delta"].get("seconds"),
                             "speedup_x": rep.get("speedup_x"),
                             "apply": rep["delta"].get("apply")}}
        manifest["built_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(manifest_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps({"ok": True, "adopted": sorted(manifest["sets"])}, ensure_ascii=False))
        return 0

    payload_dir = os.path.join(root, "payloads")
    os.makedirs(payload_dir, exist_ok=True)

    if args.only in ("all", "standard"):
        proc, _ = run([sys.executable, os.path.join(HERE, "scripts", "v2_make_payloads.py"),
                       "--out-dir", payload_dir], timeout=300)
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "stage": "payloads",
                              "error": (proc.stderr or "")[-200:]}, ensure_ascii=False))
            return 1
        std = [os.path.join(payload_dir, "ingest-333.json"),
               os.path.join(payload_dir, "ingest-329.json")]
        # 第二份独立全量：同一语料再建一次，用来量检索本身的噪声（不能靠复制目录冒充）
        manifest["sets"]["standard"] = build_pair("standard", std, root)
        manifest["sets"]["standard_b"] = build_pair("standard_b", std, root)
        manifest["payloads"] = std

    if args.only in ("all", "stress"):
        proc, _ = run([sys.executable, os.path.join(HERE, "scripts", "v2_stress_corpus.py"),
                       "--out-dir", os.path.join(root, "stress-payloads")], timeout=120)
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "stage": "stress_payloads"}, ensure_ascii=False))
            return 1
        stress = [os.path.join(root, "stress-payloads", "stress-1.json")]
        manifest["sets"]["stress"] = build_pair(
            "stress", stress, root, drop_file="s-401",
            add_text="补充条款：单笔授信超过五亿元须经董事会审议通过，并报监事会备案。")
        # 基线噪声需要**第二份独立构建**：复制目录会把"检索本身稳不稳"这个问题抹掉。
        manifest["sets"]["stress_b"] = build_pair("stress_b", stress, root)

    manifest["built_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    ok = all(s.get("ok") for s in manifest["sets"].values())
    print(json.dumps({"ok": ok, "root": root, "manifest": manifest_path,
                      "sets": {k: {"ok": v.get("ok"), "seconds": v.get("seconds")}
                               for k, v in manifest["sets"].items()}}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
