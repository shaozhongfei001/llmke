#!/usr/bin/env python3
"""P6-L17 生产窗口：对 `kb_9` 逐文件 UPSERT 6 份标准四件套。

关键口径
--------
- 用**生产原有 file_id**（290/329/330/332/333/999019，映射见
  `STEP2-*` 证据的 sources.json title 对照），不用新 id；这样
  `wanted_docs` 仍覆盖原 11 个 file_id，「不削」判据才是「11 个全在」。
- 请求显式带 `graph_root`（`P4-L13C-PLAN.md:29` 的 fail-closed 要求）。
- 逐文件 request 模式，`kb_delta.diff()` 的 `removed` 恒空。
- **失败即停**：任一文件非 2xx / 异常，立即中止，不继续写后续文件。
- 完整请求与响应写入 `coordination/p6-window-20261112/ingest-responses.json`。

用法：
    python scripts/p6_window_ingest.py --dry-run     # 只打印请求体
    python scripts/p6_window_ingest.py               # 真实 POST
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

PARSED = Path("/home/szf/data/dev/doc2md/parsed/by_hash")
GRAPH_ROOT = "/home/szf/data/dev/llmke-runtime/app/platform/r12/data/graph-root"
ENDPOINT = "http://127.0.0.1:18096/kb/ingest"
BACKUP = Path("/home/szf/data/dev/coordination/p6-window-20261112")

# (生产 file_id, doc2md 源 sha256, 文件名)
ITEMS = [
    (290, "aa8f26b94de1302f7a776a772e2af465d4b5f6a9241389051728b8d1ce4f9cb2",
     "R12FIX-product-loan.docx"),
    (329, "53d265c710bc41f1a352030993ede86763cc14eed7df4069e96c4c7ae7e02231",
     "R12FIX-credit-ledger.xlsx"),
    (330, "50f2740f82444c677b23d5bfde02d1edbbedf3ec09da9185a3153432ae0dc62f",
     "R12FIX-product-intro.pptx"),
    (332, "f4982001defc71791fa7b5af39db08cb953df151d458da2799aca4abb824b3fc",
     "docx-plain.docx"),
    (333, "a846ab142d8d24afe3f552f95888c4b261dd7c8908921a16a2932c4a7838fa1d",
     "docx-table.docx"),
    (999019, "efd100b7227067c990d7bfd04f8d2a04ddded47a068af580ed1a4a59d446eceb",
     "docx-image.docx"),
]


def make_body(fid, sha: str, name: str) -> dict:
    d = PARSED / sha[:2] / sha[2:4] / sha
    return {"kb": "kb_9", "file_id": fid, "operation": "UPSERT",
            "doc2md_dir": str(d), "file_name": name, "graph_root": GRAPH_ROOT}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records = []
    for fid, sha, name in ITEMS:
        payload = make_body(fid, sha, name)
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False))
            continue
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        rec = {"file_id": fid, "request": payload}
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                rec["http"] = resp.status
                rec["response"] = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            rec["http"] = exc.code
            try:
                rec["response"] = json.loads(exc.read())
            except Exception:  # noqa: BLE001 - 错误体也要如实保留
                rec["response"] = {}
            rec["error"] = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - 失败必须可见
            rec["error"] = f"{type(exc).__name__}: {exc}"
        records.append(rec)

        data = rec.get("response", {}).get("data") or {}
        print(f"file_id={fid} http={rec.get('http')} "
              f"code={rec.get('response', {}).get('code')} "
              f"status={data.get('status')} err={rec.get('error', '')}", flush=True)
        if rec.get("error") or rec.get("http") not in (200, 207):
            print("ABORT: 写入失败即停，不继续后续文件", flush=True)
            break

    if not args.dry_run:
        out = BACKUP / "ingest-responses.json"
        out.write_text(json.dumps(records, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"written: {out} ({len(records)} records)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
