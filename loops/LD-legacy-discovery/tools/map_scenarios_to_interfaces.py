#!/usr/bin/env python3
"""B3：把 P0-03 负例场景与 506 条接口建立可追溯关联（仅关联，非漏洞判定）。

关联含义：该接口**可能受该场景约束**（因为它涉及的数据/权限边界与该场景重合）。
不表示该接口存在漏洞，也不表示已被验证。

置信级别统一为 KEYWORD_MATCH（低），全部标 UNCONFIRMED_ASSUMPTION。
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

import yaml

# 场景 -> (匹配规则, 关联理由, 对应草案类)
SCENARIOS = {
    "N1_cross_domain_and_deny_override": (
        r"(kb|file|doc|chunk|knowledge|retriev|search)",
        "涉及 KB/文件范围的数据读取，可能触发跨域或 deny 优先判定",
        "E2 + E3"),
    "N2_graph_unauthorized_interference": (
        r"(graph|community|entity|relation|neo4j)",
        "图/社区相关，未授权节点可能影响授权域社区结果",
        "E6"),
    "N3_side_channel_indistinguishability": (
        r"(list|page|count|stat|total|summary|tree)",
        "列表/统计类响应可能通过计数暴露越权对象存在性",
        "扩展（侧信道）"),
    "N4_cache_isolation_after_policy_change": (
        r"(get|query|search|detail|info)",
        "读接口若缓存不携带策略版本，撤权后可能命中旧结论",
        "扩展（缓存隔离）"),
    "N5_revocation_residue": (
        r"(auth|privilege|permission|role|user|group|login|token)",
        "权限/身份相关，撤权残留风险集中于此",
        "E4"),
    "N6_faq_inherit_source_permission": (
        r"(faq|question|answer|qa)",
        "FAQ/问答类，命中后需按来源文档复核权限",
        "E5"),
    "N7_error_metadata_leak": (
        r".*",
        "任何接口的错误响应都可能泄漏内部标识或计数",
        "扩展（错误元数据）"),
    "N8_neighbor_block_and_image_expansion": (
        r"(chunk|neighbor|adjacent|context|image|highlight)",
        "邻近块/图片回查会二次取数，需重新校验权限",
        "E7"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    a = ap.parse_args()

    inv = yaml.safe_load((a.repo_root / "docs/reuse/INTERFACE-ASSETS.yaml").read_text(encoding="utf-8"))
    items = inv["items"]

    rows = []
    per_scenario = {}
    for sid, (pattern, reason, draft) in SCENARIOS.items():
        rx = re.compile(pattern, re.I)
        hits = 0
        for it in items:
            hay = f"{it.get('service','')} {it.get('path','')}"
            if not rx.search(hay):
                continue
            hits += 1
            rows.append({
                "scenario_id": sid,
                "asset_id": it["asset_id"],
                "service": it.get("service", ""),
                "method": it.get("method", ""),
                "path": it.get("path", ""),
                "draft_class": draft,
                "reason": reason,
                "route_evidence": "CODE_ONLY",        # 未验证运行时路由
                "confidence": "KEYWORD_MATCH_LOW",
                "evidence_class": "UNCONFIRMED_ASSUMPTION",
                "note": "关联≠漏洞；需 security-owner 批准策略后在真实链上验证",
            })
        per_scenario[sid] = hits

    a.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with a.out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = ["# B3：P0-03 场景 ↔ 506 接口关联索引", "",
             "> 关联只表示「可能受该场景约束」，**不表示存在漏洞，也不表示已验证**。",
             "> 置信级别 `KEYWORD_MATCH_LOW`；策略状态 `UNCONFIRMED_ASSUMPTION`。", "",
             "## 场景覆盖", "",
             "| 场景 | 草案对应 | 命中接口数 |", "|---|---|---|"]
    for sid, (_p, _r, draft) in SCENARIOS.items():
        lines.append(f"| {sid} | {draft} | {per_scenario[sid]} |")
    # 六类覆盖：从 SCENARIOS 的 draft_class 反推，避免硬编码与实际脱节
    draft_map = {"E2": [], "E3": [], "E4": [], "E5": [], "E6": [], "E7": []}
    for sid, (_p, _r, draft) in SCENARIOS.items():
        for key in draft_map:
            if key in draft:
                draft_map[key].append(sid)
    lines += ["", "## 草案六类覆盖检查", "",
              "| 草案类 | 对应场景 | 状态 |", "|---|---|---|"]
    for key, label in [("E2", "E2 越权读（跨 KB/文件）"), ("E3", "E3 目录聚合 + deny 优先"),
                       ("E4", "E4 撤权即时性"), ("E5", "E5 FAQ 继承来源复核"),
                       ("E6", "E6 图路降级"), ("E7", "E7 邻近块/图片回查二次取数")]:
        sids = draft_map[key]
        lines.append(f"| {label} | {', '.join(sids) if sids else '—'} | "
                     f"{'有场景' if sids else '**缺场景（GAP）**'} |")
    lines += ["", "> N3/N4/N7 属**扩展场景**（侧信道/缓存/错误元数据），不强行计入六类。",
              "", "## 口径", "",
              "- `route_evidence=CODE_ONLY`：仅表示清单记有该路由且源码核验过，**未验证运行时可达**；",
              "- 未做任何漏洞推理；命中数只反映关键词覆盖面。"]
    a.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("rows=", len(rows))
    for k, v in per_scenario.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
