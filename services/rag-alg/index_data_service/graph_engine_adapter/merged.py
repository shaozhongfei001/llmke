"""跨可见范围合并检索：一个用户属于多个范围时，一次查全。

背景：做完构建期隔离后，每个范围一份索引，于是"用户同时属于 dept-a 与 project-x"
变成一个真实的检索问题——分别查再拼，还是查一次？

这里用 **RRF（Reciprocal Rank Fusion）** 而不是加权分数：

- 不同索引的相似度分数**不可比**（各自的 embedding/图结构不同，尺度不一样），
  直接比分数等于拿两把不同的尺子量同一段长度；
- RRF 只用名次：`score = Σ 1/(k + rank)`，单调、无需归一化、对各路分数尺度不敏感，
  这也是搜索引擎融合多路召回的标准做法；
- `k` 默认 60（原论文取值），调大更"温和"，调小更看重头部。

出现的次数比名次更重要：一条内容同时被两个范围召回，得到的分数天然高于只被一个召回，
这正是"多路共识"应有的效果。

诚实边界：
- 合并只做去重与名次融合，**不做跨索引的语义重排**（那需要一个能看到全部候选的模型）；
- 每个范围都要加载一次引擎，范围多时内存与延迟线性增长（调用方应缓存 retriever）；
- 清单里查不到的范围会**被跳过并记录**，不会回退到全量索引；全部查不到 → 拒绝。
"""

import hashlib
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .partition import resolve

SCHEMA = "llmke.graph-engine.merged-retrieval.v1"
DEFAULT_RRF_K = 60


def _text_of(hit: Any) -> str:
    if isinstance(hit, dict):
        return str(hit.get("text") or "")
    return str(hit or "")


def _source_keys(hit: Any) -> List[str]:
    if not isinstance(hit, dict):
        return []
    return sorted({str(s.get("file_id")) for s in (hit.get("sources") or [])
                   if isinstance(s, dict) and s.get("file_id")})


def rrf_merge(ranked_lists: Sequence[Sequence[Any]], *, k: int = DEFAULT_RRF_K,
              top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    """把多路召回按 RRF 融合。去重键是**归一化后的文本**（同一内容在多个范围都会出现）。

    平手时按文本 sha256 排序：融合结果必须可复现，否则"谁排第一"每次不同，
    灰度对比与排查都做不了。
    """
    scores: Dict[str, float] = {}
    picked: Dict[str, Any] = {}
    seen_in: Dict[str, List[int]] = {}
    for idx, rows in enumerate(ranked_lists):
        for rank, hit in enumerate(rows or [], start=1):
            text = _text_of(hit)
            if not text:
                continue
            key = hashlib.sha256(text.encode("utf-8")).hexdigest()
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            picked.setdefault(key, hit)
            seen_in.setdefault(key, []).append(idx)

    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    if top_k is not None:
        ordered = ordered[:top_k]
    out = []
    for key in ordered:
        hit = picked[key]
        record = dict(hit) if isinstance(hit, dict) else {"text": _text_of(hit)}
        record["rrf_score"] = round(scores[key], 6)
        record["scopes_hit"] = sorted(seen_in[key])
        out.append(record)
    return out


def retrieve_merged(scopes: Iterable[str], *, root: str,
                    loader: Callable[[str], Any], query: str,
                    top_k: int = 5, per_scope_k: Optional[int] = None,
                    rrf_k: int = DEFAULT_RRF_K) -> Dict[str, Any]:
    """按用户的范围集合查多份索引并融合。

    `loader(snapshot_dir)` 负责给出一个带 `.retrieve(query, top_k)` 的对象；
    这里不直接依赖引擎，避免把 hipporag 拖进单测与其它后端。
    """
    wanted = [str(s) for s in scopes]
    per_scope_k = per_scope_k or top_k
    ranked: List[List[Any]] = []
    used, missing, errors = [], [], []

    for scope in wanted:
        entry = resolve(root, scope)
        if not entry:
            missing.append(scope)          # 查不到就记录并跳过，绝不回退全量索引
            continue
        try:
            retriever = loader(entry["snapshot"])
            got = retriever.retrieve(query, top_k=per_scope_k)
        except Exception as exc:  # noqa: BLE001
            errors.append({"scope": scope, "error": f"{type(exc).__name__}: {exc}"})
            continue
        hits = got.get("hits") if isinstance(got, dict) else got
        if hits is None and isinstance(got, dict):
            hits = got.get("docs") or []
        ranked.append(list(hits or []))
        used.append(scope)

    merged = rrf_merge(ranked, k=rrf_k, top_k=top_k) if ranked else []
    if not ranked:
        reason = "NO_RESOLVABLE_SCOPE" if wanted else "NO_SCOPE_GIVEN"
    else:
        reason = "MERGED"
    return {"schema": SCHEMA, "query": query, "hits": merged,
            "hit_count": len(merged), "scopes_used": used,
            "scopes_missing": missing, "errors": errors,
            "per_scope": len(ranked), "reason": reason,
            "passed": bool(merged)}
