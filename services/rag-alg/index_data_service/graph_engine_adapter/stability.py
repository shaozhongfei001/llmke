"""D3 更新稳定性门禁（纯函数）：两次检索结果（同问句）的一致性度量。

口径（与评审 D3 一致）：
- top1_agreement：同问句两次 top1 命中键相同才算一致（命中键=idx 或文本 hash）；
- ordered_agreement：按位置对命中的交并比（简单确定性口径，不用随机化 RBO）；
- 门禁阈值只做**可解释的默认值**（top1 一致率 ≥ 0.8 判 STABLE，否则 REVIEW），
  不假装是业务金标准；调用方（增量重建/发布）决定是否阻断。

只做度量，不做阻断——在哪阻断由发布流程决定并留证据。
"""

from typing import Any, Dict, List, Sequence, Tuple

SCHEMA = "llmke.stability.v1"


def _key(hit: Any) -> str:
    if isinstance(hit, dict):
        return str(hit.get("idx") or hit.get("text") or hit.get("id") or "")
    return str(hit)


def pair_metrics(a: Sequence[Any], b: Sequence[Any]) -> Dict[str, Any]:
    ka = [_key(x) for x in a if _key(x)]
    kb = [_key(x) for x in b if _key(x)]
    top1 = 1 if ka and kb and ka[0] == kb[0] else 0
    # 按位置交集：共同位置且同键的个数 / 两者最长列表长度（含"空对空"边界）
    n = max(len(ka), len(kb))
    same_pos = sum(1 for i in range(min(len(ka), len(kb))) if ka[i] == kb[i])
    ordered = (same_pos / n) if n else 1.0
    overlap = (len(set(ka) & set(kb)) / max(len(set(ka) | set(kb)), 1))
    return {"top1": top1, "ordered": round(ordered, 4), "overlap": round(overlap, 4),
            "len_a": len(ka), "len_b": len(kb)}


def evaluate(pairs: Sequence[Tuple[Sequence[Any], Sequence[Any]]],
             top1_min: float = 0.8) -> Dict[str, Any]:
    """pairs = [(旧结果命中列表, 新结果命中列表), ...]，每个下标对应同一问句。

    返回 per_query 明细 + aggregate + verdict。
    """
    per = [pair_metrics(a, b) for a, b in pairs]
    n = len(per)
    top1_ratio = (sum(p["top1"] for p in per) / n) if n else 0.0
    ordered_mean = (sum(p["ordered"] for p in per) / n) if n else 0.0
    overlap_mean = (sum(p["overlap"] for p in per) / n) if n else 0.0
    verdict = "STABLE" if top1_ratio >= top1_min else "REVIEW"
    return {"schema": SCHEMA, "queries": n,
            "top1_ratio": round(top1_ratio, 4),
            "ordered_mean": round(ordered_mean, 4),
            "overlap_mean": round(overlap_mean, 4),
            "top1_min": top1_min, "verdict": verdict,
            "per_query": per}
