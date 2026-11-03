#!/usr/bin/env python3
"""为 `docker save` 出来的镜像 tar 生成可校验清单（仓库只存清单，不存 4 GB tar）。

镜像名与 tar 文件名的对应关系靠 `--map image=file` 显式给出，不做猜测：
tar 文件名可能被压平（`milvusdb_milvus_v2.5.6.tar`），而真正 `docker load` 后
得到的镜像标签只存在于 tar 内部——清单里两者都记，恢复时才能对得上。
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
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="r12-middleware-images")
    ap.add_argument("--map", action="append", default=[],
                    help="image=tar 文件，例如 milvusdb/milvus:v2.5.6=milvusdb_milvus_v2.5.6.tar")
    args = ap.parse_args(argv)

    entries, total, missing = [], 0, []
    for pair in args.map:
        image, _, filename = pair.partition("=")
        path = os.path.join(args.dir, filename)
        if not os.path.isfile(path):
            missing.append(filename)
            continue
        size = os.path.getsize(path)
        total += size
        entries.append({"image": image, "file": filename, "bytes": size,
                        "sha256": _sha256(path)})

    leftovers = sorted(f for f in os.listdir(args.dir) if f.endswith(".tar")
                       and f not in {e["file"] for e in entries})

    manifest = {"schema": "llmke.image-bundle.v1", "name": args.name,
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "load_command": "docker load -i <file>",
                "total_bytes": total, "images": entries,
                "untracked_tars": leftovers}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({"manifest": args.out, "images": len(entries),
                      "total_gb": round(total / 1024 ** 3, 2),
                      "missing": missing, "untracked": leftovers}, ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
