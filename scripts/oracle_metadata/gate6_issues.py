#!/usr/bin/env python3
"""Issue register — records findings into analysis_issues +
privilege-gaps.md + dispatch conclusion (scheduler)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from catalog import connect_db
from conn import BUSINESS_FOCUS, REPORT_DIR, connect_readonly, q, require_focus, scrub

ROOT = Path(__file__).resolve().parents[2]
OUT = REPORT_DIR


def iid(*parts) -> str:
    return "issue_" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def main() -> int:
    require_focus()
    sid = (OUT / "CURRENT_SNAPSHOT.txt").read_text().strip()
    db = connect_db()
    ora = connect_readonly()
    cur = ora.cursor()

    issues = []

    # m2: SP_* argument dictionary anomaly
    progs = {
        r[0]
        for r in db.execute(
            "SELECT object_name FROM program_unit WHERE snapshot_id=? AND owner=?",
            (sid, BUSINESS_FOCUS),
        )
    }
    with_args = {
        r[0]
        for r in db.execute(
            "SELECT DISTINCT object_name FROM program_argument WHERE snapshot_id=?",
            (sid,),
        )
    }
    missing = sorted(progs - with_args)
    if missing:
        issues.append(
            (
                "MAJOR",
                "DICT_ANOMALY",
                f"ALL_ARGUMENTS 无参数记录的过程: {', '.join(missing)}；源码显式声明参数，"
                "Gate6 已改用 SOURCE_PARSE 并标注。需 DBA 侧确认字典异常原因。",
                "program_argument",
            )
        )

    # m3: DBETL referenced but invisible
    cg = json.loads((OUT / "program-call-graph.json").read_text())
    ext_owners = sorted(
        {
            e["callee_owner"]
            for e in cg["edges"]
            if e.get("callee_owner") and e["callee_owner"] not in (BUSINESS_FOCUS, "SYS", "PUBLIC")
        }
    )
    for eo in ext_owners:
        visible = q(
            cur,
            "SELECT COUNT(*) AS c FROM all_objects WHERE owner=:o",
            {"o": eo},
        )[0]["c"]
        if int(visible) == 0:
            issues.append(
                (
                    "MAJOR",
                    "PRIVILEGE_GAP",
                    f"外部 Schema `{eo}` 被 {BUSINESS_FOCUS} 源码调用但 ALL_OBJECTS 不可见"
                    f"（ALL_DEPENDENCIES 亦无记录）→ 调度日志包血缘断点；需业务/DBA 确认是否另开权限",
                    f"{eo}",
                )
            )

    # m3b: visible MVs not analyzed
    mvs = q(
        cur,
        "SELECT owner, mview_name FROM all_mviews",
    )
    for mv in mvs:
        if mv["owner"] != BUSINESS_FOCUS:
            issues.append(
                (
                    "MINOR",
                    "COVERAGE_GAP",
                    f"可见物化视图 {mv['owner']}.{mv['mview_name']} 属系统 Schema，"
                    f"未做 SQL 提取（INVENTORY_ONLY 策略）；如被 {BUSINESS_FOCUS} 依赖需补采",
                    f"{mv['owner']}.{mv['mview_name']}",
                )
            )

    # scheduler conclusion
    jobs = json.loads((OUT / "scheduler-jobs.json").read_text())
    focus_jobs = [j for j in jobs if j.get("owner") == BUSINESS_FOCUS]
    dispatch_conclusion = (
        f"{BUSINESS_FOCUS} 在 ALL_SCHEDULER_JOBS 中无作业（可见 {len(jobs)} 个均为系统 Schema）。"
        f"{BUSINESS_FOCUS} 加工链由外部 ETL 调度驱动：SP_* 过程为调度衔接入口"
        "（源码头注释自述『调度衔接调度包入口』），执行日志写入外部日志包（不可见）。"
        if not focus_jobs
        else f"{BUSINESS_FOCUS} 存在 {len(focus_jobs)} 个 Scheduler 作业，需逐一登记调度链。"
    )
    issues.append(
        (
            "INFO",
            "ARCHITECTURE_FINDING",
            dispatch_conclusion,
            "all_scheduler_jobs",
        )
    )

    # persist
    for sev, cat, msg, ref in issues:
        db.execute(
            "INSERT OR REPLACE INTO analysis_issue VALUES (?,?,?,?,?,?,?)",
            (sid, iid(sev, cat, ref), sev, cat, ref, msg, "OPEN"),
        )
    db.commit()

    # rewrite privilege-gaps.md
    gaps = [i for i in issues if i[1] == "PRIVILEGE_GAP" or "不可见" in i[2]]
    (OUT / "privilege-gaps.md").write_text(
        "# Privilege Gaps (v2)\n\n"
        "- Gate0 字典探测: 全部 PASS（ALL_*/DBMS_METADATA/Scheduler）\n"
        "- CHECK 约束 SEARCH_CONDITION 为 LONG，未采文本（PARTIAL）\n"
        "- 账号含 DBA 角色：存在写能力，全程只读策略约束\n\n"
        "## 登记缺口\n\n"
        + ("\n".join(f"- **{g[0]}** {g[2]}" for g in gaps) if gaps else "- （无新增）")
        + "\n",
        encoding="utf-8",
    )

    # dispatch conclusion
    (OUT / "dispatch-conclusion.md").write_text(
        "# 调度架构结论\n\n" + dispatch_conclusion + "\n",
        encoding="utf-8",
    )

    # merge into analysis-issues.md (dev-self-check will append its own findings later)
    (OUT / "analysis-issues.md").write_text(
        "# Analysis Issues Register (v2)\n\n"
        + "\n".join(f"- **{i[0]}** `{i[1]}`: {i[2]} _(ref: {i[3]})_" for i in issues)
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"issues_registered": len(issues), "missing_arg_procs": missing}, ensure_ascii=False))
    cur.close()
    ora.close()
    db.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR", scrub(e))
        raise
