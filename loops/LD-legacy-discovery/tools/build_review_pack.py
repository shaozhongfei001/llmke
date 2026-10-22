#!/usr/bin/env python3
"""把 555 行矩阵按组压成「默认建议 + 例外项」审阅包（供 owner 批量审）。

只做压缩，不做裁决：
- 默认建议恒为 UNDECIDED（静态证据不足以裁定）；
- 例外项 = 证据类型为 UNKNOWN/FACT，或置信为 HIGH 的行 —— 这些必须逐行看；
- 每行仍保留 row_id 与批准字段，可单独拒绝。
"""
from __future__ import annotations
import argparse, csv, json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()

    rows = list(csv.DictReader(a.matrix.open(encoding="utf-8")))
    groups = defaultdict(list)
    for r in rows:
        groups[r["batch_group"]].append(r)

    summary = []
    lines = ["# 批量审阅包（22 组）", "",
             "> 默认建议恒为 `UNDECIDED`：静态证据不足以裁定 KEEP/REWRITE。",
             "> **例外项** = 证据类型 UNKNOWN/FACT 或 置信 HIGH 的行，必须逐行裁决。",
             "> 每行仍可单独拒绝/修改；批准字段由 owner 填写。", ""]

    for g in sorted(groups):
        rs = groups[g]
        ev = Counter(r["evidence_type"] for r in rs)
        # 例外项 = 需要人看的行：证据未定/事实级/高置信，或带异常备注（行号漂移、仅注释、计数不符）
        exceptions = [r for r in rs
                      if r["evidence_type"] in ("UNKNOWN", "FACT")
                      or r["confidence"] == "HIGH"
                      or r["notes"].strip()]
        summary.append({"group": g, "rows": len(rs), "by_evidence": dict(ev),
                        "exceptions": len(exceptions),
                        "owners": sorted({r["owner_role"] for r in rs})})
        lines += [f"## {g}", "",
                  f"- 行数：**{len(rs)}**　例外项：**{len(exceptions)}**　责任角色：{', '.join(sorted({r['owner_role'] for r in rs}))}",
                  f"- 证据分布：{dict(ev)}",
                  "- 默认建议：`UNDECIDED`（需 owner 依据 DDL / 运行时证据裁定）", ""]
        if exceptions:
            lines += ["| row_id | 名称 | 证据 | 证据类型 | 备注 |", "|---|---|---|---|---|"]
            for r in exceptions[:25]:
                name = r["name"][:60].replace("|", "/")
                evd = r["evidence"][:70].replace("|", "/")
                lines.append(f"| {r['row_id']} | {name} | {evd} | {r['evidence_type']} | {r['notes'][:40]} |")
            if len(exceptions) > 25:
                lines.append(f"| … | 其余 {len(exceptions)-25} 行见矩阵 | | | |")
            lines.append("")
        else:
            lines += ["（无例外项：该组可整组按默认建议批量处理，但仍需逐行保留追溯）", ""]

    a.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    a.out_json.write_text(json.dumps({"groups": summary,
                                      "total_rows": len(rows),
                                      "total_exceptions": sum(s["exceptions"] for s in summary)},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"groups={len(groups)} rows={len(rows)} exceptions={sum(s['exceptions'] for s in summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
