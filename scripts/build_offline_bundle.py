#!/usr/bin/env python3
"""把 wheelhouse 变成**可校验的离线安装包清单**（不把 wheel 提交进仓库）。

为什么只提交清单
----------------
184 个 wheel 共 3.5 GB，进 git 会让仓库不可克隆；但"能装"必须可验证，
所以仓库里存的是：每个 wheel 的 sha256 + 大小 + 文件名 + 目标解释器/平台标签，
以及上游 requirements 清单的 sha256。任何一台机器拿到同目录的 wheel 都能自证一致。

用法：
  python scripts/build_offline_bundle.py --wheel-dir /tmp/wh-full \
      --requirements docs/design/unified-documents-v2/locks/hipporag-2.0.0a4-requirements.txt \
      --name hipporag-2.0.0a4-py311-linux-x86_64 \
      --out docs/design/unified-documents-v2/offline/<name>.manifest.json
"""

import argparse
import hashlib
import json
import os
import sys
import time


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel-dir", required=True)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--python", default=f"{sys.version_info.major}.{sys.version_info.minor}")
    ap.add_argument("--platform", default=None)
    args = ap.parse_args(argv)

    def kind_of(name):
        if name.endswith(".whl"):
            return "wheel"
        if name.endswith((".tar.gz", ".zip")):
            return "sdist"
        return None

    wheels = sorted(f for f in os.listdir(args.wheel_dir) if kind_of(f))
    if not wheels:
        print(f"no wheels in {args.wheel_dir}", file=sys.stderr)
        return 2

    entries, total = [], 0
    for name in wheels:
        path = os.path.join(args.wheel_dir, name)
        size = os.path.getsize(path)
        total += size
        entries.append({"file": name, "kind": kind_of(name), "bytes": size,
                        "sha256": _sha256(path)})

    # 冻结清单本身也要校验：清单换了而 wheel 没换，同样属于不可复现
    req_sha = _sha256(args.requirements)
    manifest = {
        "schema": "llmke.offline-bundle.v1",
        "name": args.name,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": args.python,
        "platform": args.platform or sys.platform,
        # 相对 manifest 的路径，安装器据此找冻结清单；不能只写 basename
        "requirements": {"path": os.path.relpath(os.path.abspath(args.requirements),
                                                 os.path.dirname(os.path.abspath(args.out))),
                         "sha256": req_sha},
        "install": {
            "command": ["pip", "install", "--no-index", "--find-links", ".",
                        "--no-deps", "-r", "requirements.txt"],
            "notes": "必须 --no-deps：冻结清单里有历史钉版冲突，带解析会 ResolutionImpossible",
        },
        "wheel_count": sum(1 for e in entries if e["kind"] == "wheel"),
        "sdist_count": sum(1 for e in entries if e["kind"] == "sdist"),
        "file_count": len(entries),
        "total_bytes": total,
        "wheels": entries,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"manifest": args.out, "wheels": len(entries),
                      "total_mb": round(total / 1024 / 1024, 1)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
