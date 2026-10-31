#!/usr/bin/env python3
"""镜像交付包校验：sha256 + 从 tar 内 `manifest.json` 读 RepoTags（**不 load**）。

默认**不 load**：本机 docker 里跑着 r12 中间件容器，同名 tag 一旦被新 tar 覆盖，
下次重启容器就会换镜像。

`--load` 是"有前置条件的真 load"：先比对 tar 内 `Config` 摘要与本地 `docker image inspect`
的 `.Id`，**完全相同才 load**（此时 load 是 no-op，不改变任何 tag）；只要有一个不同就拒绝并
报 DIFF，让人先判断，而不是把运行环境的镜像悄悄换掉。
`--smoke` 在 load 之后 `docker run --rm --network none` 跑一次最轻的启动命令，
证明"镜像能起来"，而不只是"包完整"。

校验项：
1. 文件大小与清单一致；
2. sha256 与清单一致；
3. tar 内 manifest.json 的 RepoTags 含清单声明的 image；
4. 层文件在 tar 内都存在（缺层 = 包坏了）。
"""

import argparse
import hashlib
import os
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


SMOKE = {
    "mysql:8.4": ["mysql", "--version"],
    "redis:7.4.10-alpine": ["redis-server", "--version"],
    "quay.io/coreos/etcd:v3.5.5": ["etcd", "--version"],
    "minio/minio:RELEASE.2023-03-20T20-16-18Z": ["minio", "--version"],
    "r12/elasticsearch-ik:8.13.4": ["elasticsearch", "--version"],
    "milvusdb/milvus:v2.5.6": ["milvus", "--help"],
}


# 期望输出片段：`--network none` 下 ES 会先打一条 hostname 解析 ERROR（隔离产物），
# 但随后仍打印 Version 且 rc=0；只看 rc 会把"输出对但有一行噪声"和"真的没起来"混为一谈。
SMOKE_EXPECT = {
    "r12/elasticsearch-ik:8.13.4": "Version:",
    "mysql:8.4": "Ver ",
    "quay.io/coreos/etcd:v3.5.5": "etcd Version",
}


def local_image_id(image):
    """本地 tag 的镜像 ID（去掉 sha256: 前缀）；没有该镜像返回 None。"""
    import subprocess

    proc = subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip().removeprefix("sha256:") or None


def tar_config_digest(tar_path):
    with tarfile.open(tar_path, "r") as tf:
        inner = json.loads(tf.extractfile("manifest.json").read())[0]
    return (inner.get("Config") or "").removesuffix(".json")


def load_and_smoke(entry, delivery, timeout=60):
    """条件 load：只有 tar 与本地镜像 ID 完全一致才 load（no-op），否则拒绝。"""
    import subprocess

    tar_path = Path(delivery) / "images-r12" / entry["file"]
    image = entry["image"]
    want = tar_config_digest(tar_path)
    have = local_image_id(image)
    if have is None:
        return {"load": "SKIP", "why": "本地无该 tag（干净目标机上才做首次 load）"}
    if want != have:
        return {"load": "REFUSED", "why": f"tar 与本地 ID 不同（{want[:12]} != {have[:12]}），"
                                           "load 会覆盖在用 tag，需人工确认"}
    proc = subprocess.run(["docker", "load", "-i", str(tar_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return {"load": "FAIL", "why": (proc.stderr or "").strip()[-200:]}

    cmd = SMOKE.get(image)
    if not cmd:
        return {"load": "PASS", "smoke": "SKIP", "why": "没有为该镜像定义启动命令"}
    smoke = subprocess.run(["docker", "run", "--rm", "--network", "none", image, *cmd],
                           capture_output=True, text=True, timeout=timeout)
    combined = (smoke.stdout or "") + (smoke.stderr or "")
    lines = [ln for ln in (smoke.stdout or "").splitlines() if ln.strip()]
    expect = SMOKE_EXPECT.get(image)
    ok = smoke.returncode == 0 and (expect is None or expect in combined)
    return {"load": "PASS", "smoke": "PASS" if ok else "FAIL",
            "smoke_rc": smoke.returncode,
            "smoke_out": lines[0][:80] if lines else combined.strip()[:80],
            "smoke_expect": expect}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--delivery",
                    default=os.path.expanduser(os.environ.get("V2_DELIVERY", "~/delivery")))
    ap.add_argument("--out", default=None)
    ap.add_argument("--load", action="store_true", help="条件 load（ID 与本地一致才 load）")
    ap.add_argument("--smoke", action="store_true", help="load 后跑一次最轻启动命令")
    args = ap.parse_args(argv)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = [check_image(e, args.delivery) for e in manifest["images"]]
    if args.load or args.smoke:
        for entry, result in zip(manifest["images"], results):
            if result["status"] != "PASS":
                continue
            try:
                extra = load_and_smoke(entry, args.delivery)
            except Exception as exc:  # noqa: BLE001
                extra = {"load": "FAIL", "why": f"{type(exc).__name__}: {exc}"}
            result.update(extra)
            if extra.get("load") == "FAIL" or extra.get("smoke") == "FAIL":
                result["status"] = "FAIL"
    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL")}
    report = {"schema": "llmke.image-verify.v1", "summary": summary,
              "verdict": "PASS" if summary["FAIL"] == 0 else "FAIL",
              "note": ("含条件 load：tar 与本地镜像 ID 完全一致才 load（no-op），不一致一律拒绝；"
                       + ("并跑了最轻启动命令" if args.smoke else "未跑启动命令")),
              "results": results}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    print(json.dumps({"summary": summary, "verdict": report["verdict"]}, ensure_ascii=False))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
