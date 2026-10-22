#!/usr/bin/env python3
"""导出 P0-01 的 506 条接口可填决策表（CSV）。

设计原则：
- 「代码里存在」与「运行时在用」是两列，绝不合并成一列结论；
- 没有运行时证据的行一律写 PENDING，不推断为在用或废弃；
- 由 interface-owner 只需填 4 列（运行时路由 / 调用方 / 业务状态 / 结论），
  其余列为已核验事实，禁止手改（改则证据失配）。
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

import yaml

COLUMNS = [
    ("asset_id", "已核验"),
    ("stack", "已核验"),
    ("service", "已核验"),
    ("method", "已核验"),
    ("path", "已核验"),
    ("handler_reported", "已核验"),
    ("source_file", "已核验"),
    ("source_line", "已核验"),
    ("code_evidence", "已核验"),          # 静态结论
    ("code_note", "已核验"),
    ("runtime_route_evidence", "待 interface-owner"),   # 运行时导出
    ("caller_confirmation", "待 interface-owner"),      # 调用方确认
    ("in_use_judgement", "待 interface-owner"),         # 在用/未用/未知
    ("business_status", "待业务"),                      # 保留/替代/下线
    ("owner_role", "待指派"),
    ("conclusion", "待 owner 签署"),                    # KEEP/ADAPT/REWRITE/RETIRE/UNDECIDED
    ("evidence_link", "待填"),
    ("notes", "可填"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--check", type=Path, required=True, help="interface-inventory-check.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    inv = yaml.safe_load((a.repo_root / "docs/reuse/INTERFACE-ASSETS.yaml").read_text(encoding="utf-8"))
    check = json.loads(a.check.read_text(encoding="utf-8"))
    by_id = {r["asset_id"]: r for r in check["results"]}

    rows = []
    for item in inv["items"]:
        rec = by_id.get(item["asset_id"], {})
        status = rec.get("status", "NOT_CHECKED")
        if status == "OK":
            code_ev, note = "PRESENT_IN_CODE", ""
        elif status == "LINE_DRIFT":
            code_ev, note = "PRESENT_IN_CODE", f"行号漂移 {rec.get('line_drift')}"
        elif status == "PATH_ONLY_COMMENTED":
            code_ev, note = "COMMENTED_ONLY", "路径仅存在于注释，需单独决议"
        elif status == "PATH_NOT_IN_SOURCE":
            code_ev, note = "NOT_FOUND_IN_CODE", "源码未命中，需人工复核"
        elif status == "HANDLER_MISMATCH":
            code_ev, note = "HANDLER_MISMATCH", "handler 名与清单不符"
        else:
            code_ev, note = status, ""
        rows.append({
            "asset_id": item["asset_id"],
            "stack": item.get("stack", ""),
            "service": item.get("service", ""),
            "method": item.get("method", ""),
            "path": item.get("path", ""),
            "handler_reported": item.get("handler_reported", ""),
            "source_file": item.get("source_file", ""),
            "source_line": item.get("source_line", ""),
            "code_evidence": code_ev,
            "code_note": note,
            "runtime_route_evidence": "PENDING",
            "caller_confirmation": "PENDING",
            "in_use_judgement": "PENDING",
            "business_status": "PENDING",
            "owner_role": "interface-owner",
            "conclusion": "UNDECIDED",
            "evidence_link": "",
            "notes": "",
        })

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[c for c, _ in COLUMNS])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    c = Counter(r["code_evidence"] for r in rows)
    print(f"rows={len(rows)} {dict(c)}")
    print("静态事实列 9 个（已核验，勿手改）；待填列 6 个（runtime/caller/in_use/business/conclusion/evidence_link）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
