#!/usr/bin/env python3
"""把**已安装**的纯 Python 包重打成 wheel（离线包缺版本时的兜底手段）。

为什么需要
----------
平台 venv 里有少数版本在公开源上不存在（例如 `soupsieve==3.0.4`，公开最高 2.10），
说明它们来自私有索引。拿不到私有索引时，唯一可行的合法做法是：从**本机已安装**的包
重建同版本 wheel，并在清单里标明来源，而不是悄悄换版本。

限制（必须显式检查，不能糊弄）
------------------------------
- 只支持纯 Python 包（存在 `.dist-info/WHEEL` 且 `Root-Is-Purelib: true`）；
  带扩展模块的包重打后 ABI 可能不匹配，直接拒绝。
- 不做任何依赖声明推断：METADATA 原样复制，`Requires-Dist` 保持上游写的值。

用法：
  python scripts/repack_installed_wheel.py --python <venv>/bin/python \
      --dist soupsieve --out /path/to/wheels [--tag py3-none-any]
"""

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile


def _hash(data):
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"sha256={digest}"


def _site_packages(python):
    code = "import sysconfig;print(sysconfig.get_paths()['purelib'])"
    out = subprocess.run([python, "-c", code], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"定位 site-packages 失败: {out.stderr.strip()[:200]}")
    return out.stdout.strip()


def _dist_info(site, name):
    prefix = name.replace("-", "_").lower()
    for entry in os.listdir(site):
        if entry.lower().startswith(prefix) and entry.endswith(".dist-info"):
            return os.path.join(site, entry)
    # .dist-info 目录名把连字符换成下划线是常见形式，再兜一层模糊匹配
    for entry in os.listdir(site):
        if entry.endswith(".dist-info") and prefix in entry.lower():
            return os.path.join(site, entry)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="py3-none-any")
    args = ap.parse_args(argv)

    site = _site_packages(args.python)
    dist_info = _dist_info(site, args.dist)
    if not dist_info:
        print(json.dumps({"status": "DIST_NOT_FOUND", "dist": args.dist}, ensure_ascii=False))
        return 2

    wheel_meta = open(os.path.join(dist_info, "WHEEL"), encoding="utf-8").read()
    if "Root-Is-Purelib: true" not in wheel_meta:
        print(json.dumps({"status": "REFUSED_NOT_PURE_PYTHON", "dist": args.dist},
                         ensure_ascii=False))
        return 2
    metadata = open(os.path.join(dist_info, "METADATA"), encoding="utf-8").read()
    name = next((ln.split(": ", 1)[1].strip() for ln in metadata.splitlines()
                 if ln.startswith("Name: ")), None)
    version = next((ln.split(": ", 1)[1].strip() for ln in metadata.splitlines()
                    if ln.startswith("Version: ")), None)
    if not name or not version:
        print(json.dumps({"status": "METADATA_INCOMPLETE"}, ensure_ascii=False))
        return 2

    dist_name = name.replace("-", "_")
    pkg_dirs = [d for d in os.listdir(site)
                if os.path.isdir(os.path.join(site, d))
                and (d.lower() == dist_name.lower()
                     or d.lower().startswith(dist_name.lower() + "."))]
    if not pkg_dirs:
        print(json.dumps({"status": "PACKAGE_DIR_NOT_FOUND", "dist": args.dist},
                         ensure_ascii=False))
        return 2

    wheel_name = f"{dist_name}-{version}-{args.tag}.whl"
    out_path = os.path.join(args.out, wheel_name)
    os.makedirs(args.out, exist_ok=True)

    records = []
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pkg in pkg_dirs:
            root = os.path.join(site, pkg)
            for dirpath, _dirnames, filenames in os.walk(root):
                for fname in filenames:
                    full = os.path.join(dirpath, fname)
                    arc = os.path.relpath(full, site).replace(os.sep, "/")
                    data = open(full, "rb").read()
                    zf.writestr(arc, data)
                    records.append((arc, _hash(data), str(len(data))))
        di_name = f"{dist_name}-{version}.dist-info"
        for fname in ("METADATA", "WHEEL"):
            full = os.path.join(dist_info, fname)
            data = open(full, "rb").read()
            arc = f"{di_name}/{fname}"
            zf.writestr(arc, data)
            records.append((arc, _hash(data), str(len(data))))
        # RECORD 自身不写哈希
        record_arc = f"{di_name}/RECORD"
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        for row in records:
            writer.writerow(row)
        writer.writerow((record_arc, "", ""))
        zf.writestr(record_arc, buf.getvalue())

    sha = hashlib.sha256(open(out_path, "rb").read()).hexdigest()
    print(json.dumps({"status": "OK", "wheel": wheel_name, "dist": f"{name}=={version}",
                      "source_python": args.python,
                      "note": "从已安装环境重打包，非上游发布物；清单需标注来源",
                      "sha256": sha, "bytes": os.path.getsize(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
