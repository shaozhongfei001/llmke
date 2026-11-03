#!/usr/bin/env python3
"""按清单校验并离线安装：先验 sha256，再 `--no-index --no-deps` 安装。

为什么先校验再装
----------------
离线环境最容易出现的不是"装不上"，而是"装上了另一份旧 wheel"。清单 + sha256 能让
"同名不同内容"的 wheel 当场失败，而不是等运行时报奇怪的 ImportError。

用法（wheel 与 manifest 同目录，或 --wheel-dir 指定）：
  python scripts/install_offline_bundle.py \
      --manifest docs/.../offline/hipporag-2.0.0a4-py311-linux-x86_64.manifest.json \
      --wheel-dir /tmp/wh-full --pip /tmp/venv/bin/pip
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--wheel-dir", required=True)
    ap.add_argument("--pip", default=sys.executable.replace("python", "pip"))
    ap.add_argument("--requirements-out", default=None,
                    help="把冻结清单写到该路径供 pip -r 使用（默认写到 wheel-dir）")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--prepare-build-deps", action="store_true",
                    help="清单含 sdist 时，先装 setuptools/wheel/Cython 并以 --no-build-isolation 安装")
    args = ap.parse_args(argv)

    manifest = json.loads(open(args.manifest, encoding="utf-8").read())
    missing, mismatched = [], []
    for entry in manifest["wheels"]:
        path = os.path.join(args.wheel_dir, entry["file"])
        if not os.path.isfile(path):
            missing.append(entry["file"])
            continue
        if args.skip_verify:
            continue
        if os.path.getsize(path) != entry["bytes"] or _sha256(path) != entry["sha256"]:
            mismatched.append(entry["file"])

    if missing or mismatched:
        print(json.dumps({"status": "FAILED", "missing": missing[:10],
                          "mismatched": mismatched[:10]}, ensure_ascii=False))
        return 1

    req_path = args.requirements_out or os.path.join(args.wheel_dir, "requirements.txt")
    # 冻结清单必须与打包时一致，否则"照清单装"和"照 wheel 装"会是两件事
    src_req = os.path.join(os.path.dirname(os.path.abspath(args.manifest)),
                           manifest["requirements"]["path"])
    if os.path.isfile(src_req):
        if _sha256(src_req) != manifest["requirements"]["sha256"]:
            print(json.dumps({"status": "REQUIREMENTS_DRIFT"}, ensure_ascii=False))
            return 1
        with open(src_req, encoding="utf-8") as fh:
            content = fh.read()
    else:
        content = None

    if content is not None:
        with open(req_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        cmd = [args.pip, "install", "--no-index", "--find-links", args.wheel_dir,
               "--no-deps", "--no-cache-dir", "-r", req_path]
    else:
        cmd = [args.pip, "install", "--no-index", "--find-links", args.wheel_dir,
               "--no-deps", "--no-cache-dir"] + [e["file"] for e in manifest["wheels"]]

    if args.prepare_build_deps or manifest.get("sdist_count"):
        # sdist 需要构建工具；离线环境下 pip 的构建隔离会去索引里找 wheel 而失败。
        # 先把构建工具从同一 wheelhouse 装进目标环境，再关掉隔离安装。
        subprocess.run([args.pip, "install", "--no-index", "--find-links", args.wheel_dir,
                        "--no-deps", "--no-cache-dir", "setuptools", "wheel", "Cython"],
                       capture_output=True, text=True)
        cmd.append("--no-build-isolation")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0
    print(json.dumps({"status": "OK" if ok else "INSTALL_FAILED",
                      "wheels": len(manifest["wheels"]),
                      "cmd": " ".join(cmd[:6]) + " …",
                      "tail": (proc.stdout or proc.stderr).strip().splitlines()[-1:] or []},
                     ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
