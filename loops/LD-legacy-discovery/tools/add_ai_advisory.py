#!/usr/bin/env python3
"""按已授权口径 V1 给 555 行矩阵补「AI 技术建议」列（与 owner 决定严格分栏）。

口径 V1（本轮由业主授权，仅授权"如何给建议"，不授权任何处置结论）：
1. advisory_action 只能取 KEEP_CANDIDATE / ADAPT_CANDIDATE / REWRITE_CANDIDATE /
   RETIRE_CANDIDATE / INSUFFICIENT_EVIDENCE；
2. ai_confidence 最高只到 MEDIUM —— 没有 DDL、没有运行时数据，不允许 HIGH；
3. 每条必须给依据（引用已有证据文件/结论），禁止"业务上应该"这类推断；
4. 必须写 blocking_input（缺什么才能定）与 impact_scope（影响哪些批次）；
5. owner_decision / approved_by / approved_at 保持为空，AI 建议不得填入。
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

# 源码资产：依据第二轮 REUSE-STRATEGY 与 S1 实测（不是猜）
SRC_RULES = {
    "CODE-01": ("ADAPT_CANDIDATE", "MEDIUM",
                "S1 实测：25 处服务耦合可切断、5/5 样本一致；但 parser 全量导入与构造期 OCR 必须先改",
                "旧解析臂运行环境（magic_pdf/模型）", "L1 解析链"),
    "CODE-02": ("ADAPT_CANDIDATE", "LOW", "LLM 推理可复用，但需接新预算/超时/取消", "运行时超时与预算口径", "L1/L2"),
    "CODE-03": ("ADAPT_CANDIDATE", "LOW", "召回算子可复用，但授权范围未携带（P0-03 相关）", "E1 授权上下文规范", "L1/L3"),
    "CODE-04": ("ADAPT_CANDIDATE", "LOW", "索引写入需改造代次与幂等键（P0-04 相关）", "S1–S5 实测与代次口径", "L1/L2"),
    "CODE-05": ("REWRITE_CANDIDATE", "MEDIUM", "旧 token/会话体系与新 AuthContext 契约不兼容", "E1 规范定稿", "L1/L3/L4"),
    "CODE-06": ("ADAPT_CANDIDATE", "LOW", "KB 管理逻辑可复用，外边界需换成端口", "DDL 与表决议", "L2"),
    "CODE-07": ("ADAPT_CANDIDATE", "LOW", "问答编排需接证据绑定与 SSE 顺序约束", "E7/E5 策略确认", "L1/L3"),
    "CODE-08": ("INSUFFICIENT_EVIDENCE", "LOW", "图路收益未评估，且无法文件级隔离", "P0-03 图路裁决", "L3"),
    "CODE-09": ("KEEP_CANDIDATE", "MEDIUM", "敏感词匹配为纯函数逻辑、依赖少；仅需确认词库来源", "词库来源与授权", "L1"),
    "CODE-10": ("ADAPT_CANDIDATE", "LOW", "NL2SQL 需安全边界，不能直接暴露", "SQL 白名单与只读约束", "L2"),
    "CODE-11": ("ADAPT_CANDIDATE", "LOW", "公共库复用价值高，但含旧依赖与框架耦合", "依赖许可与 CVE 评估", "L1/L2"),
    "CODE-12": ("ADAPT_CANDIDATE", "LOW", "网关需映射到 /v1 命名空间", "路由口径", "L1"),
}


def advise(row: dict) -> tuple[str, str, str, str, str]:
    kind = row["kind"]
    if kind == "SOURCE_ASSET":
        r = SRC_RULES.get(row["row_id"])
        if r:
            return r
        return ("INSUFFICIENT_EVIDENCE", "LOW", "未做逐函数审阅", "代码审阅", "待定")
    if kind == "TABLE":
        if row["notes"].strip() == "count_mismatch":
            return ("INSUFFICIENT_EVIDENCE", "LOW",
                    "台账计数与实体不一致，方向未定（见 A2-FIELD-ATTRIBUTION）",
                    "真实 DDL + 字段名清单", "P0-02 / 该表决议")
        return ("INSUFFICIENT_EVIDENCE", "LOW",
                "无 DDL，无法判定保留/改造/新建", "真实 DDL", "P0-02 / 该表决议")
    # INTERFACE
    ev = row["evidence"]
    if "仅存在于注释" in ev:
        return ("RETIRE_CANDIDATE", "MEDIUM",
                "路径与方法仅存在于注释，源码层面无生效实现",
                "interface-owner 书面决议（是否曾上线）", "P0-01 / 该接口决议")
    if "行号漂移" in ev:
        return ("KEEP_CANDIDATE", "LOW",
                "路径与 handler 均命中，仅清单行号偏移，属清单质量问题",
                "确认 handler 归属", "P0-01 清单准确性")
    return ("INSUFFICIENT_EVIDENCE", "LOW",
            "代码存在但运行时可达性与调用方未知", "路由导出 / 访问日志 / 调用方确认",
            "P0-01 / 该接口决议")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    a = ap.parse_args()

    rows = list(csv.DictReader(a.matrix.open(encoding="utf-8")))
    new_fields = ["advisory_action", "ai_rationale", "ai_confidence",
                  "blocking_input", "impact_scope", "advisory_source"]
    for r in rows:
        act, conf, why, block, impact = advise(r)
        r.update(advisory_action=act, ai_rationale=why, ai_confidence=conf,
                 blocking_input=block, impact_scope=impact,
                 advisory_source="AI_ADVISORY_RULE_V1")
        # 硬约束：owner 字段不得被 AI 建议填充
        r["decision_status"] = "DECISION_PENDING"
        r["approved_by"] = ""
        r["approved_at"] = ""
        r["approval_evidence"] = ""

    fields = list(rows[0].keys())
    a.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with a.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    from collections import Counter
    import json
    summary = {"total": len(rows),
               "by_action": dict(Counter(r["advisory_action"] for r in rows)),
               "by_confidence": dict(Counter(r["ai_confidence"] for r in rows)),
               "owner_approved": sum(1 for r in rows if r["approved_by"]),
               "policy": "AI_ADVISORY_RULE_V1（置信上限 MEDIUM；不填 owner 字段）"}
    a.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
