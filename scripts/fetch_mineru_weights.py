#!/usr/bin/env python3
"""从 ModelScope 拉取 MinerU（PDF-Extract-Kit）权重，只下**必需的子集**并出清单。

为什么不用整仓：`opendatalab/PDF-Extract-Kit-1.0` 全量 14 GB，其中 MFR/UniMERNet 单个就 3.5 GB、
TabRec 1.8 GB。扫描件/复杂版面这条路线只需要 layout + MFD + MFR(小) + 中文 OCR 四组，
按前缀挑出来约 1.6–2.5 GB，装到目标机才现实。

为什么不用 huggingface_hub：本机 huggingface.co 不可达（实测 000），modelscope.cn 可达（302/200）。

用法：
  python scripts/fetch_mineru_weights.py --dest $HOME/mineru-models \
      --preset scanned-cn --out docs/design/unified-documents-v2/offline/mineru-weights.manifest.json
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

REPO = "opendatalab/PDF-Extract-Kit-1.0"
API = f"https://www.modelscope.cn/api/v1/models/{REPO}/repo/files?Revision=master&Recursive=true"
DL = f"https://www.modelscope.cn/api/v1/models/{REPO}/repo?Revision=master&FilePath="

PRESETS = {
    # 扫描件/复杂版面最小集：版面 + 公式/表格检测 + 公式识别(小) + 中文 OCR
    "scanned-cn": [
        "models/Layout/YOLO/",
        "models/MFD/YOLO/",
        "models/ReadingOrder/layout_reader/",
        "models/MFR/unimernet_hf_small_2503/",
        "models/OCR/paddleocr_torch/Multilingual_PP-OCRv3_det_infer.pth",
        "models/OCR/paddleocr_torch/ch_PP-OCRv5_rec_infer.pth",
        "models/OCR/paddleocr_torch/ch_PP-OCRv5_det_infer.pth",
        "models/OCR/paddleocr_torch/ch_PP-OCRv4_rec_infer.pth",
        "models/OCR/paddleocr_torch/ch_ppocr_mobile_v2.0_cls_infer.pth",
    ],
    # 表格结构还原（可选，代价 +1.8 GB）
    "table": ["models/TabRec/StructEqTable/"],
}


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _list_files():
    with urllib.request.urlopen(API, timeout=60) as resp:
        data = json.loads(resp.read())
    files = (data.get("Data") or {}).get("Files") or []
    return [f for f in files if f.get("Type") == "blob"]


def _download(rel_path, dest, expect_size=None, retries=3):
    target = os.path.join(dest, rel_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    # 断点续传/幂等：已存在且大小一致就跳过，避免重复拉 1.6 GB
    if expect_size is not None and os.path.isfile(target) and os.path.getsize(target) == expect_size:
        return target
    url = DL + urllib.parse.quote(rel_path, safe="")
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp, open(target, "wb") as fh:
                while True:
                    block = resp.read(1 << 20)
                    if not block:
                        break
                    fh.write(block)
            return target
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                raise
            print(f"  retry {attempt} {rel_path}: {type(exc).__name__}", file=sys.stderr)
            time.sleep(2 * attempt)
    return target


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--preset", default="scanned-cn", choices=sorted(PRESETS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    prefixes = PRESETS[args.preset]
    blobs = _list_files()
    selected = [f for f in blobs if any(f["Path"].startswith(p) for p in prefixes)]
    if not selected:
        print(json.dumps({"status": "NO_MATCH", "preset": args.preset}, ensure_ascii=False))
        return 2

    total = sum(f["Size"] for f in selected)
    print(json.dumps({"preset": args.preset, "files": len(selected),
                      "total_mb": round(total / 1024 ** 2, 1)}, ensure_ascii=False))
    if args.dry_run:
        for f in selected:
            print("  ", f["Path"], round(f["Size"] / 1024 ** 2, 1), "MB")
        return 0

    entries = []
    for f in selected:
        rel = f["Path"]
        path = _download(rel, args.dest, expect_size=f["Size"])
        size = os.path.getsize(path)
        entries.append({"path": rel, "bytes": size, "sha256": _sha256(path)})
        print(f"  ok {rel} {size/1024**2:.1f} MB", flush=True)

    manifest = {
        "schema": "llmke.model-weights.v1",
        "source": f"modelscope:{REPO}",
        "preset": args.preset,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "file_count": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "files": entries,
    }
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"status": "OK", "files": len(entries),
                      "total_gb": round(manifest["total_bytes"] / 1024 ** 3, 2)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
