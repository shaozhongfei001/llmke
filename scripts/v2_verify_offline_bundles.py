#!/usr/bin/env python3
"""离线交付验收：把每个 wheelhouse 装进**全新 venv**（`--no-index`），再验关键导入。

这是"干净目标机"的近似：不联网、不用现成 site-packages，只靠 manifest 列出的 wheel。
每项记录 PASS/FAIL/SKIP 与失败尾部，报告落 JSON；有 FAIL 才非零退出。

用法：
  scripts/v2_verify_offline_bundles.py --delivery /path/to/delivery \
      --out docs/design/unified-documents-v2/offline/clean-install-verify.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST_DIR = REPO / "docs/design/unified-documents-v2/offline"

# (名称, manifest, wheel 目录名, python, 关键导入, 额外补包[(wheel 目录, [包...])])
# parse/alg/graph 的 wheelhouse **不含 torch**（构建时按各自 requirements 收集，torch 只在 models 包里）。
# 这不是 bug 而是现状：干净机上必须把 models 包的 torch 一并装上，parse 才 import 得动。
# 所以这里显式声明"跨包依赖"，并在报告里记 extra_used，避免把"少装东西"说成"装好了"。
BUNDLES = [
    ("parse", "r12-parse-venv-py311.manifest.json", "wheels-r12-parse", "python3.11",
     ["fastapi", "pandas", "torch", "langchain_core"],
     [("wheels-r12-models", ["torch==2.6.0+cpu"])]),
    ("alg", "r12-alg-venv-py311.manifest.json", "wheels-r12-alg", "python3.11",
     ["fastapi", "numpy", "pandas"], []),
    ("models", "r12-models-venv-py311.manifest.json", "wheels-r12-models", "python3.11",
     ["torch", "transformers"], []),
    ("graph", "r12-graph-venv-py310.manifest.json", "wheels-r12-graph", "python3.10",
     ["numpy", "networkx"], []),
]


def _run(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def verify_one(name, manifest, wheel_dir, py, imports, extras, delivery, work_root, timeout):
    manifest_path = MANIFEST_DIR / manifest
    wheels = Path(delivery) / wheel_dir
    if not manifest_path.is_file() or not wheels.is_dir():
        return {"name": name, "status": "SKIP",
                "why": f"manifest={manifest_path.is_file()} wheels={wheels.is_dir()}"}

    venv = Path(work_root) / f"venv-{name}"
    t0 = time.time()
    try:
        r = _run([py, "-m", "venv", str(venv)], 300)
        if r.returncode != 0:
            return {"name": name, "status": "FAIL", "stage": "venv",
                    "tail": (r.stderr or r.stdout).strip().splitlines()[-4:]}
        r = _run([sys.executable, str(REPO / "scripts/install_offline_bundle.py"),
                  "--manifest", str(manifest_path), "--wheel-dir", str(wheels),
                  "--pip", str(venv / "bin/pip")], timeout)
        if r.returncode != 0:
            return {"name": name, "status": "FAIL", "stage": "install",
                    "tail": (r.stdout + r.stderr).strip().splitlines()[-6:]}
        extra_used = []
        for extra_dir, pkgs in extras:
            path = Path(delivery) / extra_dir
            if not path.is_dir():
                return {"name": name, "status": "FAIL", "stage": "extra_missing",
                        "tail": [f"{extra_dir} 不存在（跨包依赖无法满足）"]}
            r = _run([str(venv / "bin/pip"), "install", "-q", "--no-index",
                      "--find-links", str(path)] + pkgs, timeout)
            if r.returncode != 0:
                return {"name": name, "status": "FAIL", "stage": "extra_install",
                        "tail": (r.stderr or r.stdout).strip().splitlines()[-4:]}
            extra_used.append({"wheel_dir": extra_dir, "packages": pkgs})

        code = ("import importlib,json,sys\n"
                f"mods={imports!r}\n"
                "bad=[]\n"
                "for m in mods:\n"
                "    try: importlib.import_module(m)\n"
                "    except Exception as e: bad.append([m,type(e).__name__])\n"
                "print(json.dumps({'bad':bad}))\n")
        r = _run([str(venv / "bin/python"), "-c", code], 600)
        if r.returncode != 0:
            return {"name": name, "status": "FAIL", "stage": "import",
                    "tail": (r.stderr or r.stdout).strip().splitlines()[-4:]}
        bad = json.loads(r.stdout.strip())["bad"]
        return {"name": name, "status": "PASS" if not bad else "FAIL",
                "stage": "done" if not bad else "import",
                "imports_bad": bad, "extra_used": extra_used,
                "seconds": round(time.time() - t0, 1), "venv": str(venv)}
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "FAIL", "stage": "timeout"}
    finally:
        if os.environ.get("V2_KEEP_VERIFY_VENV") != "1":
            shutil.rmtree(venv, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--delivery", default="/home/szf/data/dev/delivery")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    work_root = tempfile.mkdtemp(prefix="v2-clean-install-")
    results = []
    try:
        for name, manifest, wheel_dir, py, imports, extras in BUNDLES:
            if args.only and name not in args.only:
                continue
            results.append(verify_one(name, manifest, wheel_dir, py, imports, extras,
                                      args.delivery, work_root, args.timeout))
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "SKIP")}
    report = {"schema": "llmke.clean-install.v1", "summary": summary,
              "verdict": "PASS" if summary["FAIL"] == 0 else "FAIL", "results": results}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    print(json.dumps({"summary": summary, "verdict": report["verdict"]}, ensure_ascii=False))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
