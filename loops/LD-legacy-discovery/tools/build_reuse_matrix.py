#!/usr/bin/env python3
"""第七轮主交付：555 项复用候选矩阵（12 源码 + 37 表 + 506 接口）。

设计原则（必须遵守，否则矩阵会变成"看起来齐了"的假象）：
1. 每一行都必须有**证据或明确的未知原因**，不允许留空；
2. 证据类型严格分四档：FACT / SOURCE_OBSERVATION / INFERENCE / UNKNOWN；
3. 建议处置用项目既有词汇（KEEP/ADAPT/REWRITE/RETIRE/UNDECIDED），
   并标注该词汇状态为 PROPOSED（未经 owner 批准为新标准）；
4. 批准字段一律留空，`decision_status` 恒为 DECISION_PENDING；
5. 按证据模式分组（batch_group），供 owner 批量审阅，但每行可单独拒绝。

矩阵完成 != 555 项已批准。
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

import yaml

EVIDENCE_DIR = Path("loops/LD-legacy-discovery/evidence")


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()
    root = a.repo_root

    src = yaml.safe_load((root / "docs/reuse/SOURCE-ASSETS.yaml").read_text(encoding="utf-8"))["items"]
    dbs = yaml.safe_load((root / "docs/reuse/DATABASE-ASSETS.yaml").read_text(encoding="utf-8"))["items"]
    itf = yaml.safe_load((root / "docs/reuse/INTERFACE-ASSETS.yaml").read_text(encoding="utf-8"))["items"]

    iface_check = {r["asset_id"]: r for r in load_json(root / EVIDENCE_DIR / "interface-inventory-check.json").get("results", [])}
    db_check = {r["id"]: r for r in load_json(root / EVIDENCE_DIR / "db-entity-check.json").get("items", [])}
    orm = {r["id"]: r for r in load_json(root / EVIDENCE_DIR / "db-orm-coverage.json").get("tables", [])}
    sqlrefs = load_json(root / EVIDENCE_DIR / "sql-column-refs.json").get("summary", {})

    rows = []

    # ---------- 12 源码资产 ----------
    for it in src:
        aid = it["id"]
        rows.append({
            "row_id": aid, "kind": "SOURCE_ASSET", "name": it["legacy_path"],
            "evidence": f"台账申报 {it['reported_file_count']} 文件；首轮交叉验证 12/12 与实测主语言文件数全等",
            "evidence_path": "docs/reuse/SOURCE-ASSETS.yaml; loops/LD-legacy-discovery/evidence/M01-OBTAINABLE-SNAPSHOT.yaml",
            "evidence_type": "SOURCE_OBSERVATION",
            "suggested_action": "UNDECIDED",
            "rationale": "内部结构未逐函数审阅；S1 仅对 CODE-01 做了解析内核回放",
            "confidence": "LOW",
            "risk": "直接 KEEP 可能带入旧耦合（服务层 25 处 import、构造期加载 OCR）",
            "owner_role": it.get("proposed_owner_role", ""),
            "batch_group": "GRP-SRC-" + ("PY" if it.get("language", "").lower().startswith("py") else "JAVA"),
            "decision_status": "DECISION_PENDING", "approved_by": "", "approved_at": "",
            "approval_evidence": "", "notes": "",
        })

    # ---------- 37 张表 ----------
    for it in dbs:
        tid = it["id"]; chk = db_check.get(tid, {})
        o = orm.get(tid, {})
        refs = sqlrefs.get(it["legacy_table"], {})
        ref_cols = [c for c, v in refs.items() if v.get("referenced")] if refs else []
        if chk and chk.get("count_match"):
            ev = f"实体字段数 {chk['entity_field_count']} 与台账 {it['model_field_count']} 一致"
            et = "SOURCE_OBSERVATION"
        elif chk:
            ev = f"实体 {chk['entity_field_count']} vs 台账 {it['model_field_count']}（不一致，方向待 DDL）"
            et = "SOURCE_OBSERVATION"
        else:
            ev = "未找到实体"; et = "UNKNOWN"
        cov = o.get("coverage", "UNKNOWN")
        rows.append({
            "row_id": tid, "kind": "TABLE", "name": it["legacy_table"],
            "evidence": f"{ev}；ORM 覆盖 {cov}"
                        + (f"；SQL 引用列 {len(ref_cols)} 个" if refs else "；未做 SQL 引用扫描"),
            "evidence_path": f"loops/LD-legacy-discovery/evidence/db-entity-check.json; db-orm-coverage.json"
                             + ("; sql-column-refs.json" if refs else ""),
            "evidence_type": et if et == "UNKNOWN" else ("SOURCE_OBSERVATION"),
            "suggested_action": "UNDECIDED",
            "rationale": "无真实 DDL，无法判定保留/改造/新建；字段数与映射完整度均不足以替代 schema",
            "confidence": "LOW",
            "risk": "以静态字段数决策会导致迁移漏列或误建索引",
            "owner_role": it.get("proposed_owner_role", ""),
            "batch_group": "GRP-DB-" + (it.get("proposed_group", "MISC") or "MISC"),
            "decision_status": "DECISION_PENDING", "approved_by": "", "approved_at": "",
            "approval_evidence": "",
            "notes": "" if (chk and chk.get("count_match")) else "count_mismatch",
        })

    # ---------- 506 接口 ----------
    for it in itf:
        aid = it["asset_id"]; c = iface_check.get(aid, {})
        st = c.get("status", "NOT_CHECKED")
        if st == "OK":
            ev, et, conf = "源码存在该路由声明（路径+handler 命中）", "SOURCE_OBSERVATION", "MEDIUM"
        elif st == "LINE_DRIFT":
            ev, et, conf = "源码存在，清单行号漂移", "SOURCE_OBSERVATION", "MEDIUM"
        elif st == "PATH_ONLY_COMMENTED":
            ev, et, conf = "路径仅存在于注释，方法已注释", "FACT", "HIGH"
        elif st == "PATH_NOT_IN_SOURCE":
            ev, et, conf = "源码未命中", "UNKNOWN", "LOW"
        else:
            ev, et, conf = "未核验", "UNKNOWN", "LOW"
        rows.append({
            "row_id": aid, "kind": "INTERFACE", "name": f"{it.get('method','')} {it.get('path','')}",
            "evidence": ev, "evidence_path": f"{it.get('source_file','')}:{it.get('source_line','')}",
            "evidence_type": et,
            "suggested_action": "UNDECIDED",
            "rationale": "运行时可达性与调用方未知；代码存在不等于在用",
            "confidence": conf,
            "risk": "把注释命中的接口当在用，或把未命中当废弃，都会误裁",
            "owner_role": "interface-owner",
            "batch_group": "GRP-ITF-" + str(it.get("service", "unknown")),
            "decision_status": "DECISION_PENDING", "approved_by": "", "approved_at": "",
            "approval_evidence": "",
            "notes": "" if st == "OK" else f"static_status={st}",
        })

    fields = list(rows[0].keys())
    a.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with a.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    from collections import Counter
    summary = {
        "total": len(rows),
        "by_kind": dict(Counter(r["kind"] for r in rows)),
        "by_evidence_type": dict(Counter(r["evidence_type"] for r in rows)),
        "by_suggestion": dict(Counter(r["suggested_action"] for r in rows)),
        "by_decision_status": dict(Counter(r["decision_status"] for r in rows)),
        "by_group": dict(Counter(r["batch_group"] for r in rows)),
        "vocabulary_status": "PROPOSED（KEEP/ADAPT/REWRITE/RETIRE/UNDECIDED 沿用项目既有词，未批准为新标准）",
        "warning": "矩阵完成 != 555 项已批准；批准字段全空",
    }
    a.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"rows={summary['total']} kinds={summary['by_kind']}")
    print(f"evidence={summary['by_evidence_type']}")
    print(f"groups={len(summary['by_group'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
