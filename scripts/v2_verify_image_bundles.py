#!/usr/bin/env python3
"""镜像交付包校验：sha256 + 从 tar 内 `manifest.json` 读 RepoTags（**不 load**）。

为什么不直接 `docker load`：本机 docker 里跑着 r12 中间件容器，同名 tag 一旦被
新 tar 覆盖，下次重启容器就会换镜像——为了验包去改运行环境的 tag 不值得。
`docker save` 生成的 tar 里自带 `manifest.json`，读出 RepoTags + 层数就能证明
"这包是哪个镜像、结构完整"；真正 load 留到干净目标机做（那时没有在用容器）。

校验项：
1. 文件大小与清单一致；
2. sha256 与清单一致；
3. tar 内 manifest.json 的 RepoTags 含清单声明的 image；
4. 层文件在 tar 内都存在（缺层 = 包坏了）。
"""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs/design/unified-documents-v2/offline/r12-middleware-images.manifest.json"


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def check_image(entry, delivery):
    tar_path = Path(delivery) / "images-r12" / entry["file"]
    item = {"image": entry["image"], "file": entry["file"]}
    if not tar_path.is_file():
        return {**item, "status": "FAIL", "why": "tar 不存在"}
    size = tar_path.stat().st_size
    if size != entry["bytes"]:
        return {**item, "status": "FAIL", "why": f"size {size} != {entry['bytes']}"}
    digest = sha256(tar_path)
    if digest != entry["sha256"]:
        return {**item, "status": "FAIL", "why": f"sha256 {digest[:12]} != {entry['sha256'][:12]}"}

    try:
        with tarfile.open(tar_path, "r") as tf:
            names = set(tf.getnames())
            if "manifest.json" not in names:
                return {**item, "status": "FAIL", "why": "tar 内无 manifest.json"}
            inner = json.loads(tf.extractfile("manifest.json").read())
            tags = [t for entry_obj in inner for t in entry_obj.get("RepoTags") or []]
            layers = [layer for entry_obj in inner for layer in entry_obj.get("Layers") or []]
            missing = [layer for layer in layers if layer not in names]
    except Exception as exc:  # noqa: BLE001
        return {**item, "status": "FAIL", "why": f"{type(exc).__name__}: {exc}"}

    ok = entry["image"] in tags and not missing
    return {**item, "status": "PASS" if ok else "FAIL",
            "repo_tags": tags[:3], "layers": len(layers),
            "missing_layers": missing[:3], "sha256": digest[:16],
            "why": "" if ok else "RepoTags 不含声明镜像或缺层"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--delivery", default="/home/szf/data/dev/delivery")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = [check_image(e, args.delivery) for e in manifest["images"]]
    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL")}
    report = {"schema": "llmke.image-verify.v1", "summary": summary,
              "verdict": "PASS" if summary["FAIL"] == 0 else "FAIL",
              "note": "只校验包内容与标签，未执行 docker load（避免覆盖在用 tag）",
              "results": results}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    print(json.dumps({"summary": summary, "verdict": report["verdict"]}, ensure_ascii=False))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
