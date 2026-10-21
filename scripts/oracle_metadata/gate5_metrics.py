#!/usr/bin/env python3
"""Gate 5 — metrics + derived fields; Owner-confirmed metrics protected."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

from catalog import connect_db
from conn import BUSINESS_FOCUS, REPORT_DIR, require_focus, scrub

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
PRIVATE = ROOT / "data" / "metadata" / "source_private"
OWNER_YAML = ROOT / "specs" / "domain" / "OWNER_METRIC_DECISIONS.yaml"
METRIC_DEF = ROOT / "specs" / "domain" / "metric-definitions.yaml"

RATIO_PAT = re.compile(
    r"(SUM\s*\(\s*([A-Z0-9_$#.]+)\s*\)\s*/\s*(?:NULLIF\s*\(\s*)?SUM\s*\(\s*([A-Z0-9_$#.]+)\s*\)(?:\s*,\s*0\s*\))?(?:\s*\*\s*100)?)",
    re.IGNORECASE,
)
NAME_HINTS = re.compile(
    r"(RATE|RATIO|PCT|YQ|DKYE|NPL|OVERDUE|RISK|SCORE|BAL|AMT|CNT|AVG|SUM)",
    re.I,
)
CN_HINTS = re.compile(r"(率|占比|金额|余额|户数|笔数|平均|逾期|不良|风险|评分|等级)")


def mid(*parts) -> str:
    return "m_" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:12]


def load_owner_metrics():
    """Return (protected_owner_metrics, catalog_seed_metrics).

    Only OWNER_METRIC_DECISIONS / explicitly owner-confirmed entries are protected.
    """
    protected = {}
    catalog = {}
    if OWNER_YAML.exists():
        doc = yaml.safe_load(OWNER_YAML.read_text(encoding="utf-8")) or {}
        od03 = (doc.get("od03_conflict_resolution") or {}).get("primary_metric_id")
        if od03:
            protected[od03] = {
                "metric_id": od03,
                "confidence_level": "OWNER_CONFIRMED",
                "confidence_source": "OWNER_DECISION",
                "owner_decision_ids": "OD-03",
                "formula_expression": "SUM(YQDKYE)/NULLIF(SUM(DKYE),0)*100",
                "metric_name_cn": "余额逾期率",
                "metric_name_en": od03,
                "business_definition": "Owner-confirmed primary overdue balance rate",
                "unit": "percent",
                "metric_status": "OWNER_CONFIRMED",
            }
        sec = (doc.get("od03_conflict_resolution") or {}).get("secondary_metric_id")
        if sec:
            protected[sec] = {
                "metric_id": sec,
                "confidence_level": "OWNER_CONFIRMED",
                "confidence_source": "OWNER_DECISION",
                "owner_decision_ids": "OD-03",
                "formula_expression": "overdue_customers/active_customers*100",
                "metric_name_cn": "客户逾期率",
                "metric_name_en": sec,
                "business_definition": "Owner-confirmed secondary customer overdue rate",
                "unit": "percent",
                "metric_status": "OWNER_CONFIRMED",
            }
    if METRIC_DEF.exists():
        md = yaml.safe_load(METRIC_DEF.read_text(encoding="utf-8")) or {}
        metrics = md.get("metrics") or md.get("definitions") or []
        if isinstance(metrics, dict):
            metrics = [{"metric_id": k, **v} for k, v in metrics.items()]
        for m in metrics:
            if not isinstance(m, dict):
                continue
            mid_ = m.get("id") or m.get("metric_id") or m.get("name")
            if not mid_:
                continue
            if mid_ in protected:
                # enrich formula if empty but never downgrade confidence
                if not protected[mid_].get("formula_expression"):
                    protected[mid_]["formula_expression"] = (
                        m.get("formula") or m.get("numerator") or ""
                    )
                if m.get("display_name"):
                    protected[mid_]["metric_name_cn"] = m["display_name"]
                continue
            signed = bool(m.get("business_signoff")) or m.get("status") == "APPROVED"
            conf = "OWNER_CONFIRMED" if signed else "CODE_CONFIRMED"
            entry = {
                "metric_id": mid_,
                "confidence_level": conf,
                "confidence_source": "SPEC_CATALOG_OWNER_SIGNED"
                if signed
                else "SPEC_CATALOG_UNSIGNED",
                "owner_decision_ids": ",".join(m.get("owner_decisions") or [])
                if isinstance(m.get("owner_decisions"), list)
                else (m.get("owner_decisions") or ""),
                "formula_expression": m.get("formula")
                or m.get("expression")
                or m.get("sql_expression")
                or m.get("numerator")
                or "",
                "metric_name_cn": m.get("display_name")
                or m.get("name_cn")
                or m.get("label_cn")
                or mid_,
                "metric_name_en": mid_,
                "business_definition": m.get("definition")
                or m.get("description")
                or m.get("notes")
                or "",
                "unit": m.get("unit") or "",
                "metric_status": m.get("status") or conf,
            }
            if conf == "OWNER_CONFIRMED":
                protected[mid_] = entry
            else:
                catalog[mid_] = entry
    return protected, catalog


def main() -> int:
    require_focus()
    sid = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    db = connect_db()
    owner_metrics, catalog_seed = load_owner_metrics()
    metrics = {}
    metrics.update(catalog_seed)
    metrics.update(owner_metrics)  # owner wins on key collision
    protected_ids = set(owner_metrics.keys())
    derived = []
    issues = []

    # Column comment / name candidates from EDWCRM
    cols = list(
        db.execute(
            """SELECT owner, table_name, column_name, column_comment, data_type
               FROM column_metadata WHERE snapshot_id=?""",
            (sid,),
        )
    )
    for owner, table, col, comment, dtype in cols:
        blob = f"{col} {comment or ''}"
        if NAME_HINTS.search(col) or (comment and CN_HINTS.search(comment)):
            did = mid("col", owner, table, col)
            category = "UNKNOWN"
            cl = col.upper()
            if any(x in cl for x in ("RATE", "RATIO", "PCT")) or (comment and "率" in comment):
                category = "RATE"
            elif any(x in cl for x in ("AMT", "BAL", "YE", "DKYE")) or (comment and ("金额" in comment or "余额" in comment)):
                category = "AMOUNT"
            elif any(x in cl for x in ("CNT", "NUM", "HS", "BS")) or (comment and ("户数" in comment or "笔数" in comment)):
                category = "COUNT"
            elif "SCORE" in cl or (comment and "评分" in comment):
                category = "SCORE"
            derived.append(
                {
                    "derived_field_id": did,
                    "target_owner": owner,
                    "target_object": table,
                    "target_column": col,
                    "target_comment": comment or "",
                    "business_name_cn": comment or f"根据字段名推测，需业务确认。({col})",
                    "business_description_cn": (
                        comment
                        if comment
                        else "根据字段名推测，需业务确认。"
                    ),
                    "field_category": category,
                    "source_fields": "UNKNOWN",
                    "transformation_expression": "UNKNOWN",
                    "transformation_type": "UNKNOWN",
                    "producer_program": "",
                    "code_line_range": "",
                    "source_hash": "",
                    "confidence_level": "COMMENT_SUPPORTED" if comment else "INFERRED",
                    "ambiguities": "REQUIRES_BUSINESS_CONFIRMATION",
                }
            )
            if category == "RATE":
                metric_id = f"db_{owner.lower()}_{table.lower()}_{col.lower()}"
                if metric_id not in metrics and col.lower() not in {
                    m.lower() for m in metrics
                }:
                    metrics[metric_id] = {
                        "metric_id": metric_id,
                        "metric_name_cn": comment or col,
                        "metric_name_en": col,
                        "metric_status": "CANDIDATE",
                        "confidence_level": "COMMENT_SUPPORTED" if comment else "INFERRED",
                        "confidence_source": "COLUMN_COMMENT" if comment else "NAME_INFERENCE",
                        "business_definition": comment
                        or "根据字段名推测，需业务确认。",
                        "formula_expression": "UNKNOWN",
                        "numerator_definition": "UNKNOWN",
                        "denominator_definition": "UNKNOWN",
                        "statistical_grain": "UNKNOWN",
                        "unit": "UNKNOWN",
                        "source_tables": f"{owner}.{table}",
                        "source_columns": col,
                        "target_schema": owner,
                        "target_table": table,
                        "target_column": col,
                        "producer_object_owner": "",
                        "producer_object_name": "",
                        "producer_object_type": "",
                        "code_start_line": None,
                        "code_end_line": None,
                        "source_hash": "",
                        "owner_decision_ids": "",
                        "existing_metric_mapping": "",
                        "business_confirmation_required": 1,
                    }

    # Code-discovered ratios from private sources
    programs = list(
        db.execute(
            "SELECT owner, object_name, object_type, source_hash FROM program_unit WHERE snapshot_id=?",
            (sid,),
        )
    )
    AGG_RISK_PAT = re.compile(
        r"SUM\s*\(\s*(?:T1\.)?(WJFLCJ|WJFLKY|WJFLSS|WJFLZC|WJFLGZ|YQDKYE|YQCS|DKJE|DKYE)\s*\)",
        re.IGNORECASE,
    )
    RISK_AGG_MAP = {
        "WJFLCJ": ("次级余额（五级分类·次级）", "npl_balance_amount"),
        "WJFLKY": ("可疑余额（五级分类·可疑）", "npl_balance_amount"),
        "WJFLSS": ("损失余额（五级分类·损失）", "npl_balance_amount"),
        "WJFLZC": ("正常余额（五级分类·正常）", ""),
        "WJFLGZ": ("关注余额（五级分类·关注）", ""),
        "YQDKYE": ("逾期余额汇总", "overdue_balance_amount"),
        "YQCS": ("逾期笔数汇总", ""),  # 笔数≠客户数，不挂载 overdue_customer_count（遗留口径）
        "DKJE": ("贷款金额汇总（DKJE≠DKYE 口径，近亲字段）", ""),  # 不挂载 loan_balance_amount
        "DKYE": ("贷款余额汇总", "loan_balance_amount"),
    }
    risk_agg_hits = []

    def attach_owner_evidence(mapped, owner_, name_, start_):
        if mapped in metrics:
            em = metrics[mapped].get("existing_metric_mapping") or ""
            tag = f";code:{owner_}.{name_}:L{start_}"
            if tag not in em:
                metrics[mapped]["existing_metric_mapping"] = em + tag

    for owner, name, otype, shash in programs:
        path = PRIVATE / f"{owner}.{name}.{otype.replace(' ', '_')}.sql"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        # risk aggregation components (DB_CODE candidates / owner evidence)
        for m in AGG_RISK_PAT.finditer(text):
            col = m.group(1).upper()
            start = text[: m.start()].count("\n") + 1
            risk_agg_hits.append(
                {"owner": owner, "object_name": name, "column": col, "line": start}
            )
            cn, mapped = RISK_AGG_MAP.get(col, ("", ""))
            if mapped and mapped in protected_ids or (mapped in metrics and metrics[mapped].get("confidence_level") == "OWNER_CONFIRMED"):
                attach_owner_evidence(mapped, owner, name, start)
                continue
            metric_id = mid("dbagg", owner, name, col)
            if metric_id in metrics or metric_id in protected_ids:
                continue
            metrics[metric_id] = {
                "metric_id": metric_id,
                "metric_name_cn": cn or f"{col} 汇总",
                "metric_name_en": f"sum_{col.lower()}",
                "metric_status": "CODE_DISCOVERED",
                "confidence_level": "CODE_CONFIRMED",
                "confidence_source": "DB_CODE",
                "business_definition": f"PL/SQL 中 SUM({col}) 聚合；{cn}；业务口径需确认",
                "formula_expression": f"SUM({col})",
                "numerator_definition": f"SUM({col})",
                "denominator_definition": "",
                "statistical_grain": "按程序分组键（需业务确认）",
                "unit": "yuan_or_count",
                "source_tables": "",
                "source_columns": col,
                "target_schema": "",
                "target_table": "",
                "target_column": "",
                "producer_object_owner": owner,
                "producer_object_name": name,
                "producer_object_type": otype,
                "code_start_line": start,
                "code_end_line": start,
                "source_hash": shash,
                "owner_decision_ids": "",
                "existing_metric_mapping": mapped,
                "business_confirmation_required": 1,
            }
        for m in RATIO_PAT.finditer(text):
            expr, num_c, den_c = m.group(1), m.group(2), m.group(3)
            start = text[: m.start()].count("\n") + 1
            end = text[: m.end()].count("\n") + 1
            metric_id = mid("code", owner, name, expr)
            # Map known Oracle formulas to Owner metrics without overwriting
            mapped = ""
            conf = "CODE_CONFIRMED"
            name_cn = "代码发现比率指标"
            if re.search(r"YQDKYE", num_c, re.I) and re.search(r"DKYE", den_c, re.I):
                mapped = "overdue_balance_rate"
                name_cn = "余额逾期率（代码证据）"
                # never overwrite OWNER_CONFIRMED — only attach evidence pointer
                if mapped in protected_ids or (
                    mapped in metrics
                    and metrics[mapped].get("confidence_level") == "OWNER_CONFIRMED"
                ):
                    metrics[mapped]["existing_metric_mapping"] = (
                        metrics[mapped].get("existing_metric_mapping") or ""
                    ) + f";code:{owner}.{name}:{start}"
                    continue
            # never replace any protected owner metric id
            if metric_id in protected_ids:
                continue
            metrics[metric_id] = {
                "metric_id": metric_id,
                "metric_name_cn": name_cn,
                "metric_name_en": metric_id,
                "metric_status": "CODE_DISCOVERED",
                "confidence_level": conf,
                "confidence_source": "DB_CODE",
                "business_definition": "从 PL/SQL 比率表达式还原；业务含义需确认"
                if not mapped
                else f"对齐 Owner 指标 {mapped}",
                "formula_expression": expr,
                "numerator_definition": f"SUM({num_c})",
                "denominator_definition": f"SUM({den_c})",
                "statistical_grain": "UNKNOWN",
                "unit": "ratio_or_percent",
                "source_tables": "UNKNOWN",
                "source_columns": f"{num_c},{den_c}",
                "target_schema": "",
                "target_table": "",
                "target_column": "",
                "producer_object_owner": owner,
                "producer_object_name": name,
                "producer_object_type": otype,
                "code_start_line": start,
                "code_end_line": end,
                "source_hash": shash,
                "owner_decision_ids": "",
                "existing_metric_mapping": mapped,
                "business_confirmation_required": 0 if mapped else 1,
            }

    # Persist metrics / derived
    _mcols = [
        "snapshot_id", "metric_id", "metric_name_cn", "metric_name_en",
        "metric_status", "confidence_level", "confidence_source",
        "business_definition", "formula_expression", "numerator_definition",
        "denominator_definition", "statistical_grain", "unit", "source_tables",
        "source_columns", "target_schema", "target_table", "target_column",
        "producer_object_owner", "producer_object_name", "producer_object_type",
        "code_start_line", "code_end_line", "source_hash",
        "owner_decision_ids", "existing_metric_mapping",
        "business_confirmation_required",
    ]
    _msql = (
        f"INSERT OR REPLACE INTO metric_definition ({','.join(_mcols)}) VALUES "
        f"({','.join('?' * len(_mcols))})"
    )
    for m in metrics.values():
        db.execute(
            _msql,
            (
                sid,
                m["metric_id"],
                m.get("metric_name_cn"),
                m.get("metric_name_en"),
                m.get("metric_status", "CANDIDATE"),
                m.get("confidence_level"),
                m.get("confidence_source", ""),
                m.get("business_definition"),
                m.get("formula_expression"),
                m.get("numerator_definition"),
                m.get("denominator_definition"),
                m.get("statistical_grain"),
                m.get("unit"),
                m.get("source_tables"),
                m.get("source_columns"),
                m.get("target_schema"),
                m.get("target_table"),
                m.get("target_column"),
                m.get("producer_object_owner"),
                m.get("producer_object_name"),
                m.get("producer_object_type"),
                m.get("code_start_line"),
                m.get("code_end_line"),
                m.get("source_hash"),
                m.get("owner_decision_ids"),
                m.get("existing_metric_mapping"),
                int(m.get("business_confirmation_required") or 0),
            ),
        )
    for d in derived:
        db.execute(
            """INSERT OR REPLACE INTO derived_field VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sid,
                d["derived_field_id"],
                d["target_owner"],
                d["target_object"],
                d["target_column"],
                d["target_comment"],
                d["business_name_cn"],
                d["business_description_cn"],
                d["field_category"],
                d["source_fields"],
                d["transformation_expression"],
                d["transformation_type"],
                d["producer_program"],
                d["code_line_range"],
                d["source_hash"],
                d["confidence_level"],
                d["ambiguities"],
            ),
        )
    db.commit()

    # Crosswalk
    crosswalk = []
    for mid_, m in metrics.items():
        crosswalk.append(
            {
                "oracle_metric_id": mid_,
                "confidence_level": m.get("confidence_level"),
                "owner_mapping": m.get("existing_metric_mapping")
                or (mid_ if m.get("confidence_level") == "OWNER_CONFIRMED" else ""),
                "formula": m.get("formula_expression"),
                "conflict": None,
            }
        )

    metric_list = list(metrics.values())
    (OUT / "metric-catalog.json").write_text(
        json.dumps({"snapshot_id": sid, "metrics": metric_list}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    # Markdown catalogs
    def conf_counts():
        c = {}
        for m in metric_list:
            k = m.get("confidence_level") or "UNKNOWN"
            c[k] = c.get(k, 0) + 1
        return c

    cc = conf_counts()
    db_code_n = sum(
        1 for m in metric_list if m.get("confidence_source") == "DB_CODE"
    )
    risk_agg_note = ""
    if risk_agg_hits:
        procs_hit = sorted({h["object_name"] for h in risk_agg_hits})
        risk_agg_note = (
            f"；风险字段聚合（WJFL*/YQDKYE/YQCS/DKJE）命中 {len(risk_agg_hits)} 处，"
            f"分布于 {len(procs_hit)} 个程序：{', '.join(procs_hit[:8])}"
        )
    lines = [
        "# Metric Catalog (Gate 5 v2.2)",
        "",
        f"- snapshot: `{sid}`",
        f"- metric_count: **{len(metric_list)}**",
        f"- confidence: `{cc}`",
        f"- **DB 代码证实(DB_CODE)的指标数: {db_code_n}**{risk_agg_note}",
        "- 风险台账血缘关键发现：`UP_F_CUST_LOAN_IFO` 读取 "
        "`S04_CRD_DBDKTZ`（台行，OD-01 粒度表）UNION ALL `S08_CRD_DBDKTZ`（村镇），"
        "聚合五级分类余额（WJFLZC/GZ/CJ/KY/SS）、YQCS、YQDKYE 写入 `F_CUST_LOAN_IFO`。",
        "",
        "| metric_id | cn | confidence | source | formula | producer |",
        "|-----------|----|------------|--------|---------|----------|",
    ]
    for m in metric_list[:500]:
        lines.append(
            f"| `{m['metric_id']}` | {m.get('metric_name_cn','')} | {m.get('confidence_level')} | {m.get('confidence_source','')} | `{m.get('formula_expression','')[:80]}` | {m.get('producer_object_owner','')}.{m.get('producer_object_name','')} |"
        )
    (OUT / "metric-catalog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    dlines = [
        "# Derived Field Catalog",
        "",
        f"- count: {len(derived)}",
        "",
        "| id | table.column | category | confidence | cn |",
        "|----|--------------|----------|------------|----|",
    ]
    for d in derived[:800]:
        dlines.append(
            f"| `{d['derived_field_id']}` | {d['target_owner']}.{d['target_object']}.{d['target_column']} | {d['field_category']} | {d['confidence_level']} | {d['business_name_cn'][:40]} |"
        )
    (OUT / "derived-field-catalog.md").write_text("\n".join(dlines) + "\n", encoding="utf-8")

    (OUT / "metric-owner-crosswalk.md").write_text(
        "# Owner Metric Crosswalk\n\n"
        + "\n".join(
            f"- `{c['oracle_metric_id']}` → `{c['owner_mapping'] or 'UNMAPPED'}` ({c['confidence_level']})"
            for c in crosswalk
            if c["confidence_level"] == "OWNER_CONFIRMED" or c["owner_mapping"]
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "oracle-to-ontology-crosswalk.json").write_text(
        json.dumps(crosswalk, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "oracle-to-ontology-crosswalk.md").write_text(
        "# Oracle → Ontology Crosswalk\n\n"
        "OWNER_CONFIRMED metrics are never overwritten by DB inference.\n\n"
        + "\n".join(
            f"| `{c['oracle_metric_id']}` | {c['confidence_level']} | `{c['owner_mapping']}` | `{c['formula']}` |"
            for c in crosswalk[:200]
        )
        + "\n",
        encoding="utf-8",
    )

    with (OUT / "metric-lineage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "metric_id",
                "confidence_level",
                "formula",
                "numerator",
                "denominator",
                "producer",
                "code_lines",
                "source_hash",
            ]
        )
        for m in metric_list:
            w.writerow(
                [
                    m["metric_id"],
                    m.get("confidence_level"),
                    m.get("formula_expression"),
                    m.get("numerator_definition"),
                    m.get("denominator_definition"),
                    f"{m.get('producer_object_owner')}.{m.get('producer_object_name')}",
                    f"{m.get('code_start_line')}-{m.get('code_end_line')}",
                    m.get("source_hash"),
                ]
            )

    # Ensure protected Owner metrics remain OWNER_CONFIRMED
    owner_ok = all(
        metrics.get(k, {}).get("confidence_level") == "OWNER_CONFIRMED"
        for k in protected_ids
    ) and len(protected_ids) > 0
    summary = {
        "metric_count": len(metric_list),
        "derived_field_count": len(derived),
        "confidence_counts": cc,
        "db_code_confirmed_count": db_code_n,
        "risk_aggregation_hits": len(risk_agg_hits),
        "risk_aggregation_programs": sorted({h["object_name"] for h in risk_agg_hits}),
        "owner_protected": owner_ok,
        "protected_owner_metric_count": len(protected_ids),
        "gate5": "PASS" if owner_ok else "FAIL",
    }
    (OUT / "gate5-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    db.close()
    return 0 if summary["gate5"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        raise
