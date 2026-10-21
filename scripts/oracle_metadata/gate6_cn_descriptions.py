#!/usr/bin/env python3
"""Gate 6 (v2) — Chinese business descriptions.

Fixes vs v1:
- Harvests PL/SQL header comment block (功能描述/输入表/输出表/存过名称).
- When ALL_ARGUMENTS has no rows, parses source-declared parameters and
  labels them args_source=SOURCE_PARSE (dictionary anomaly registered).
- Adds called subprograms (from v2 call graph) into 加工步骤.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from catalog import connect_db
from conn import REPORT_DIR, scrub

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR
DESC_DIR = OUT / "program-business-descriptions"
PRIVATE = ROOT / "data" / "metadata" / "source_private"

FROM_RE = re.compile(r"\bFROM\s+([A-Z0-9_$#.\"]+)", re.I)
INSERT_RE = re.compile(r"\bINSERT\s+INTO\s+([A-Z0-9_$#.\"]+)", re.I)
UPDATE_RE = re.compile(r"\bUPDATE\s+([A-Z0-9_$#.\"]+)", re.I)
MERGE_RE = re.compile(r"\bMERGE\s+INTO\s+([A-Z0-9_$#.\"]+)", re.I)
DELETE_RE = re.compile(r"\bDELETE\s+FROM\s+([A-Z0-9_$#.\"]+)", re.I)
EXEC_RE = re.compile(r"EXECUTE\s+IMMEDIATE", re.I)
RATIO_RE = re.compile(
    r"SUM\s*\(\s*([A-Z0-9_$#.]+)\s*\)\s*/\s*(?:NULLIF\s*\(\s*)?SUM\s*\(\s*([A-Z0-9_$#.]+)",
    re.I,
)
HEADER_FIELD_RE = re.compile(
    r"(功能描述|存过名称|存储过程|输\s*入\s*表|输\s*出\s*表|创\s*建\s*者|创建日期|存\s*储\s*策\s*略|备\s*注)\s*[:：]\s*(.*)"
)
PROC_SIG_RE = re.compile(
    r"(?:PROCEDURE|FUNCTION)\s+([A-Za-z][\w$#]*)\s*\((.*?)\)\s*(?:IS|AS|RETURN)",
    re.I | re.S,
)
PARAM_LINE_RE = re.compile(
    r"([A-Za-z][\w$#]*)\s+(IN\s+OUT|IN|OUT)\s+([A-Za-z][\w$#.%()]*(?:\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?)",
    re.I,
)


def safe_filename(owner, name, otype) -> str:
    raw = f"{owner}.{name}.{otype}".replace(" ", "_")
    return re.sub(r"[^\w.\-]+", "_", raw)[:180] + ".md"


def extract_header_fields(raw: str) -> dict[str, str]:
    """Pull 功能描述/输入表/输出表 etc. from the leading comment block (first 80 lines)."""
    fields: dict[str, str] = {}
    head = "\n".join(raw.splitlines()[:80])
    for m in HEADER_FIELD_RE.finditer(head):
        key = re.sub(r"\s+", "", m.group(1))
        val = m.group(2).strip().rstrip("*#-/ ").strip()
        if val and key not in fields:
            fields[key] = val
    return fields


def parse_source_params(raw: str) -> list[dict]:
    m = PROC_SIG_RE.search(raw)
    if not m:
        return []
    out = []
    for pm in PARAM_LINE_RE.finditer(m.group(2)):
        out.append(
            {
                "argument_name": pm.group(1).upper(),
                "in_out": pm.group(2).upper().replace("  ", " "),
                "data_type": re.sub(r"\s+", "", pm.group(3)).upper(),
            }
        )
    return out


def describe(owner, name, otype, raw, shash, args, args_source, stmts, calls, metrics):
    header = extract_header_fields(raw or "")
    src_params = [] if args else parse_source_params(raw or "")
    shown_args = args or src_params
    shown_args_source = "ALL_ARGUMENTS" if args else ("SOURCE_PARSE" if src_params else "NONE")

    # statement-register-driven reads/writes (static only) — avoids raw-regex misses
    static_writes = sorted(
        {
            f"{s['target_owner']}.{s['target_object']}"
            for s in stmts
            if s["statement_kind"] in ("INSERT", "UPDATE", "MERGE", "DELETE", "CREATE")
            and s["dynamic_class"] == "STATIC_LITERAL"
            and s["target_object"]
        }
    )
    dyn_count = sum(1 for s in stmts if s["dynamic_class"] != "STATIC_LITERAL")
    reads = sorted({m.group(1).upper().strip('"') for m in FROM_RE.finditer(raw or "")})
    has_dyn = dyn_count > 0 or bool(EXEC_RE.search(raw or ""))
    called = sorted(
        {
            (f"{c['callee_owner']}." if c.get("callee_owner") else "")
            + (f"{c['callee_package']}." if c.get("callee_package") else "")
            + c["callee_subprogram"]
            for c in calls
        }
    )

    # purpose: prefer header 功能描述, else structural inference
    purpose = header.get("功能描述")
    if purpose:
        purpose = f"{purpose}（源码头注释，未执行过程验证）"
    elif static_writes and reads:
        purpose = (
            f"该程序读取 {', '.join(reads[:5])} 等对象，将加工结果写入 "
            f"{', '.join(static_writes[:5])}（静态结构推断，需业务确认）。"
        )
    elif called:
        purpose = (
            f"该程序为调度/编排入口，调用子程序 {', '.join(called[:5])}"
            f"（静态结构推断，需业务确认）。"
        )
    elif not raw:
        purpose = "源码不可读；用途 UNKNOWN。"

    lines = [
        f"# {owner}.{name}",
        "",
        f"- object_type: `{otype}`",
        f"- source_hash: `{shash}`",
        f"- evidence: `data/metadata/source_private/{owner}.{name}.{otype.replace(' ', '_')}.sql`",
        "",
        "## 一句话用途",
        "",
        purpose or "UNKNOWN — 需业务确认。",
        "",
        "## 源码头注释摘录（未经加工）",
        "",
    ]
    if header:
        for k, v in header.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- （无头注释字段）")

    lines += ["", "## 输入", ""]
    if shown_args:
        lines.append(f"参数（来源: `{shown_args_source}`）：")
        for a in shown_args[:40]:
            lines.append(f"- `{a['argument_name']}` {a['data_type']} {a['in_out']}")
        if shown_args_source == "SOURCE_PARSE":
            lines.append(
                "- ⚠ ALL_ARGUMENTS 无本程序参数记录（数据字典异常，见 analysis-issues.md）；以上从源码声明解析"
            )
    else:
        lines.append("- ALL_ARGUMENTS 与源码均未发现参数声明。")
    lines += ["", f"- 读取对象: {', '.join(reads) if reads else 'UNKNOWN / 动态 / 无静态 FROM'}", ""]
    lines += [
        "## 输出",
        "",
        f"- 写入对象（静态已登记）: {', '.join(static_writes) if static_writes else '无静态 DML 写目标'}",
        f"- 动态 SQL 语句数: {dyn_count}" + ("（写目标见 dynamic-sql-register，PARTIALLY_DYNAMIC 不伪造血缘）" if dyn_count else ""),
        "",
    ]

    lines += ["## 加工步骤（按静态识别顺序，非运行时）", ""]
    step = 1
    if called:
        lines.append(f"{step}. 调用子程序: {', '.join(called[:10])}。")
        step += 1
    if reads:
        lines.append(f"{step}. 从 {', '.join(reads[:8])} 读取数据。")
        step += 1
    if RATIO_RE.search(raw or ""):
        lines.append(f"{step}. 计算比率/聚合表达式（见指标节）。")
        step += 1
    if static_writes:
        lines.append(f"{step}. 将结果写入 {', '.join(static_writes[:8])}。")
        step += 1
    if has_dyn:
        lines.append(f"{step}. 存在 EXECUTE IMMEDIATE：动态 SQL，血缘可能不全（DYNAMIC_SQL_UNRESOLVED）。")
        step += 1
    if step == 1:
        lines.append("1. 未能从源码稳定还原步骤 — PARTIAL / UNKNOWN。")

    lines += ["", "## 二次加工字段和指标", ""]
    related = [m for m in metrics if m.get("producer_object_name") == name]
    if related:
        for m in related:
            lines += [
                f"### {m.get('metric_name_cn') or m['metric_id']}",
                f"- 业务含义: {m.get('business_definition')}",
                f"- 计算逻辑: `{m.get('formula_expression')}`",
                f"- 分子/分母: {m.get('numerator_definition')} / {m.get('denominator_definition')}",
                f"- 证据代码: lines {m.get('code_start_line')}-{m.get('code_end_line')} hash=`{m.get('source_hash')}`",
                f"- 置信度: `{m.get('confidence_level')}`",
                "",
            ]
    else:
        lines.append("未识别出绑定到本程序的代码指标；字段级候选见 derived-field-catalog。")

    lines += [
        "",
        "## 风险与待确认项",
        "",
        f"- 动态 SQL: {'是（EXECUTE IMMEDIATE，见 dynamic-sql-register）' if has_dyn else '未检出'}",
        "- 不得将推断业务含义当作已确认口径。",
        "- 本说明仅来自静态源码；未执行存储过程验证。",
        "",
        "## 语句证据摘要",
        "",
    ]
    for s in stmts[:20]:
        lines.append(
            f"- `{s['statement_kind']}` → `{s['target_owner']}.{s['target_object']}` "
            f"lines {s['start_line']}-{s['end_line']} id=`{s['statement_id']}` "
            f"dynamic=`{s['dynamic_class']}`"
        )
    if not stmts:
        lines.append("- （无已登记 sql_statement；若为纯编排入口，见上方调用子程序）")
    return "\n".join(lines) + "\n"


def main() -> int:
    sid = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    DESC_DIR.mkdir(parents=True, exist_ok=True)
    db = connect_db()

    call_graph = json.loads((OUT / "program-call-graph.json").read_text())
    calls_by_caller: dict[str, list] = {}
    for e in call_graph["edges"]:
        calls_by_caller.setdefault(e["caller_name"], []).append(e)

    programs = list(
        db.execute(
            """SELECT owner, object_name, object_type, source_hash, source_status
               FROM program_unit WHERE snapshot_id=?""",
            (sid,),
        )
    )
    metrics = [
        dict(
            zip(
                [
                    "metric_id", "metric_name_cn", "business_definition",
                    "formula_expression", "numerator_definition",
                    "denominator_definition", "producer_object_name",
                    "code_start_line", "code_end_line", "source_hash",
                    "confidence_level",
                ],
                row,
            )
        )
        for row in db.execute(
            """SELECT metric_id, metric_name_cn, business_definition, formula_expression,
                      numerator_definition, denominator_definition, producer_object_name,
                      code_start_line, code_end_line, source_hash, confidence_level
               FROM metric_definition WHERE snapshot_id=?""",
            (sid,),
        )
    ]
    written = 0
    source_parse_args = 0
    for owner, name, otype, shash, sstatus in programs:
        args = [
            {"argument_name": r[0], "data_type": r[1], "in_out": r[2]}
            for r in db.execute(
                """SELECT argument_name, data_type, in_out FROM program_argument
                   WHERE snapshot_id=? AND owner=? AND object_name=?
                   ORDER BY position""",
                (sid, owner, name),
            )
        ]
        stmts = [
            {
                "statement_kind": r[0], "target_owner": r[1], "target_object": r[2],
                "start_line": r[3], "end_line": r[4], "statement_id": r[5],
                "dynamic_class": r[6],
            }
            for r in db.execute(
                """SELECT statement_kind, target_owner, target_object, start_line, end_line,
                          statement_id, dynamic_class
                   FROM sql_statement WHERE snapshot_id=? AND owner=? AND object_name=?""",
                (sid, owner, name),
            )
        ]
        path = PRIVATE / f"{owner}.{name}.{otype.replace(' ', '_')}.sql"
        raw = ""
        if path.exists() and sstatus != "WRAPPED_SOURCE_UNREADABLE":
            raw = path.read_text(encoding="utf-8", errors="replace")
        calls = calls_by_caller.get(name, [])
        md = describe(owner, name, otype, raw, shash, args, "", stmts, calls, metrics)
        if not args and "## 输入" in md and "SOURCE_PARSE" in md:
            source_parse_args += 1
        outp = DESC_DIR / safe_filename(owner, name, otype)
        outp.write_text(md, encoding="utf-8")
        db.execute(
            "INSERT OR REPLACE INTO business_description VALUES (?,?,?,?,?,?,?)",
            (sid, owner, name, otype, "", str(outp.relative_to(ROOT)), shash),
        )
        written += 1
    db.commit()
    summary = {
        "version": "v2",
        "program_count": len(programs),
        "chinese_description_count": written,
        "programs_with_source_parsed_args": source_parse_args,
        "gate6": "PASS" if written == len(programs) and written > 0 else "FAIL",
    }
    (OUT / "gate6-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    db.close()
    return 0 if summary["gate6"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        raise
