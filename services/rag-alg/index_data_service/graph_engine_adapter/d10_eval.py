"""D10 验收评估器（结构层，纯函数）：固定语料 T-01…T-09 的**机器可核**判据。

只判结构可核项（引用非空、locator 存在、路线可识别、回退带原因、禁用对照成立）；
语义质量（答案对不对）由独立通道（M4 盲审 + 用户抽查）判，本模块不冒充。
"""

import json
from typing import Any, Dict, List, Optional

SCHEMA = "llmke.d10-eval.v1"

ROUTES = {"GRAPH", "COMMUNITY_REPORT", "DENSE_FALLBACK"}


def _check(result: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    reasons: List[str] = []
    answer = str(result.get("answer") or "").strip()
    checks["answer_nonempty"] = bool(answer)
    if not answer:
        reasons.append("答案为空")

    citations = result.get("citations") or []
    checks["citations_present"] = len(citations) > 0
    if case.get("requires_citation", True) and not citations:
        reasons.append("要求引用但 citations 为空")

    loc_ok = all(
        isinstance(c, dict) and str(c.get("locator") or "").strip()
        for c in citations
    )
    checks["locator_present"] = loc_ok
    if not loc_ok:
        reasons.append("存在无 locator 的引用")

    route = str(result.get("route") or "")
    checks["route_known"] = route in ROUTES
    if not checks["route_known"]:
        reasons.append(f"路线不可识别: {route!r}")
    if route == "DENSE_FALLBACK":
        checks["fallback_reason"] = bool(str(result.get("reason") or "").strip())
        if not checks["fallback_reason"]:
            reasons.append("回退但未给原因")
    else:
        checks["fallback_reason"] = True

    return {"checks": checks, "reasons": reasons}


def evaluate_case(case: Dict[str, Any], result_a: Dict[str, Any],
                  result_b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """判单个用例：A 组必须通过结构判据；B 组只用来验“禁用对照”。"""
    a = _check(result_a, case)
    pass_a = all(a["checks"].values())

    control_ok = True
    if case.get("disable_control", False):
        if result_b is None:
            control_ok = False
            a["reasons"].append("要求禁用对照但未提供 B 组结果")
        else:
            b = _check(result_b, case)
            control_ok = b["checks"].get("route_known") and \
                result_b.get("route") == "DENSE_FALLBACK"
            if not control_ok:
                a["reasons"].append("禁用对照未成立（B 组应显式 DENSE_FALLBACK）")

    return {"case_id": case.get("id"), "question": case.get("question"),
            "pass": pass_a and control_ok, "checks": a["checks"],
            "reasons": a["reasons"]}


def evaluate_all(spec: Dict[str, Any], results_a: Dict[str, Dict[str, Any]],
                 results_b: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    cases = spec.get("cases") or []
    per = [evaluate_case(c, results_a.get(str(c.get("id")), {}),
                         (results_b or {}).get(str(c.get("id")))) for c in cases]
    passed = sum(1 for p in per if p["pass"])
    return {"schema": SCHEMA, "total": len(per), "passed": passed,
            "failed": len(per) - passed, "per_case": per}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
