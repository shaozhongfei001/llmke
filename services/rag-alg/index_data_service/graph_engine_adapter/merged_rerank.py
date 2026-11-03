"""合并结果重排：RRF 只看名次不看内容，这里补一次"看内容"的打分与截断。

背景：`merged.py` 用 RRF 融合多份范围索引，副作用是**相关但只在一个范围出现**的文档，
会排在**不相关却在多个范围重复出现**的文档之后——RRF 奖励多路共识，本身不判断相关性
（见 `docs/design/unified-documents-v2/EVIDENCE-MERGED-SCOPE-20261101.md` 的实测）。

这一层只做一件事：把合并后的前 `max_candidates` 条交给一个**可注入的** scorer 打相关性分，
按分数重排后截断到 `top_k`。

几条写进代码里的判断：

1. **只给前 `max_candidates` 条打分，其余直接丢弃**。对没打分的候选做"排序"等于编造分数，
   那比不重排更坏：结果看起来更"新鲜"，但排序依据无从追责。
2. **失败必须回退到 RRF 顺序，且结果非空**。把"重排失败"变成"没结果"是最坏的降级——
   用户看到的是"查不到"，而真相是"打分器坏了"，两者该有不同的处置。
   失败原因如实写进 `reason`（`SCORER_ERROR` / `TIMEOUT` / `EMPTY_SCORES`）+ `detail`。
3. **同分按原 RRF 顺序（稳定排序）**。重排结果必须可复现，否则"谁排第一"每次不同，
   灰度对比与排查都做不了。
4. **候选 id 用下标字符串**（`"0"`, `"1"`, …），与 `llm_scorer` 要求模型输出的
   `{"scores": {"0": 0.9}}` 对齐。用正文当 key 会因为正文超长/重复/被截断而对不上。

诚实边界：
- `timeout_s` 约束的是**等待**，不是底层调用本身：超时后后台线程可能仍在跑，
  它的结果被丢弃（真实 LLM 调用应自己带 connect/read 超时，这里只是兜底别让查询挂死）；
- scorer 返回里出现**不属于候选集合的下标**视为打分器不可信 → 回退（不猜、不忽略）；
- 缺失下标的候选**不丢**：排在已打分候选之后、保持原 RRF 相对顺序，并在 `unscored` 里计数；
- 只做相关性重排，不改 `rrf_score`，也不重新融合多路结果。
"""

import json
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence

SCHEMA = "llmke.graph-engine.merged-rerank.v1"

DEFAULT_TOP_K = 5
DEFAULT_MAX_CANDIDATES = 20

RERANKED = "RERANKED"
NO_SCORER = "NO_SCORER"
EMPTY_HITS = "EMPTY_HITS"
TOP_K_NON_POSITIVE = "TOP_K_NON_POSITIVE"
MAX_CANDIDATES_NON_POSITIVE = "MAX_CANDIDATES_NON_POSITIVE"
SCORER_ERROR = "SCORER_ERROR"
TIMEOUT = "TIMEOUT"
EMPTY_SCORES = "EMPTY_SCORES"

# 提示词里单条候选正文的截断长度：正文过长会让"只输出 JSON"这件事先崩掉，
# 而重排只需要判断"这段讲的是不是这个问题"，不需要全文。
PROMPT_TEXT_LIMIT = 600


class ScorerError(Exception):
    """scorer 的输出不可信（非 JSON / 下标越界 / 值不是数）。上层据此回退到 RRF。"""


def _text_of(hit: Any) -> str:
    if isinstance(hit, dict):
        return str(hit.get("text") or "")
    return str(hit or "")


def _candidates(rows: Sequence[Any], limit: int) -> List[Dict[str, str]]:
    """候选 id = 下标字符串；只取前 `limit` 条，之后的不进打分集合。"""
    return [{"id": str(i), "text": _text_of(row)} for i, row in enumerate(rows[:limit])]


def _clean_scores(raw: Any, allowed: set) -> Dict[str, float]:
    """校验 scorer 的返回。任何含糊的地方都当错误处理，而不是"尽量理解"。"""
    if not isinstance(raw, dict):
        raise ScorerError(f"scorer 返回的不是 dict：{type(raw).__name__}")
    scores: Dict[str, float] = {}
    for key, value in raw.items():
        sid = str(key)
        if sid not in allowed:
            raise ScorerError(f"scorer 返回了候选集合之外的下标：{sid}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ScorerError(f"下标 {sid} 的分数不是数：{value!r}")
        if value != value or value in (float("inf"), float("-inf")):
            raise ScorerError(f"下标 {sid} 的分数非法：{value!r}")
        scores[sid] = float(value)
    return scores


class _Timeout:
    """超时哨兵：与"scorer 返回了 None"区分开，别把两种情况混成一个 reason。"""


TIMED_OUT = _Timeout()


def _call_with_timeout(fn: Callable[[], Any], timeout_s: Optional[float]) -> Any:
    if timeout_s is None:
        return fn()
    holder: Dict[str, Any] = {}

    def _run():
        try:
            holder["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - 原样带回主线程再分类
            holder["error"] = exc

    worker = threading.Thread(target=_run, name="merged-rerank-scorer", daemon=True)
    worker.start()
    worker.join(timeout_s)
    if worker.is_alive():                      # 只放弃等待，不假装调用被取消了
        return TIMED_OUT
    if "error" in holder:
        raise holder["error"]
    return holder.get("value")


def _pack(rows: Sequence[Dict[str, Any]], *, reranked: bool, scores: Dict[str, float],
          dropped: int, reason: str, detail: Optional[str] = None,
          candidates: int = 0, unscored: int = 0) -> Dict[str, Any]:
    return {"schema": SCHEMA, "hits": list(rows), "reranked": reranked,
            "scores": dict(scores), "dropped": dropped, "reason": reason,
            "detail": detail, "candidates": candidates, "unscored": unscored}


def _fallback(rows: Sequence[Dict[str, Any]], top_k: int, reason: str,
              detail: Optional[str], candidates: int = 0) -> Dict[str, Any]:
    """回退：保持 RRF 原序，仍然按 top_k 截断，**绝不返回空列表**。"""
    hits = list(rows[:top_k]) if top_k and top_k > 0 else list(rows)
    return _pack(hits, reranked=False, scores={}, dropped=len(rows) - len(hits),
                 reason=reason, detail=detail, candidates=candidates)


def rerank(query: str, hits: Optional[Sequence[Any]], *, scorer: Optional[Callable] = None,
           top_k: int = DEFAULT_TOP_K, max_candidates: int = DEFAULT_MAX_CANDIDATES,
           timeout_s: Optional[float] = None) -> Dict[str, Any]:
    """对合并后的候选做一次相关性重排并截断。

    `scorer(query, [{"id","text"}, ...]) -> {id: score}` 可注入：真实用 LLM（见 `llm_scorer`），
    测试用桩。`dropped` = 输入 hits 中未出现在最终结果里的条数（含超出 `max_candidates`
    未打分、以及被 `top_k` 截断两部分）。
    """
    rows = list(hits or [])
    if not rows:
        return _pack([], reranked=False, scores={}, dropped=0, reason=EMPTY_HITS)
    if scorer is None:
        return _pack(rows, reranked=False, scores={}, dropped=0, reason=NO_SCORER,
                     detail="未注入 scorer，保持 RRF 原序")
    if top_k is None or top_k <= 0:
        return _pack(rows, reranked=False, scores={}, dropped=0, reason=TOP_K_NON_POSITIVE,
                     detail=f"top_k={top_k}，不截断")
    if max_candidates is None or max_candidates <= 0:
        return _pack(rows, reranked=False, scores={}, dropped=0,
                     reason=MAX_CANDIDATES_NON_POSITIVE, detail=f"max_candidates={max_candidates}")

    candidates = _candidates(rows, int(max_candidates))
    allowed = {c["id"] for c in candidates}

    try:
        raw = _call_with_timeout(lambda: scorer(query, candidates), timeout_s)
    except Exception as exc:  # noqa: BLE001 - scorer 千奇百怪，一律回退
        return _fallback(rows, top_k, SCORER_ERROR, f"{type(exc).__name__}: {exc}",
                         candidates=len(candidates))
    if raw is TIMED_OUT:
        return _fallback(rows, top_k, TIMEOUT, f"scorer 等待超过 {timeout_s}s 未返回",
                         candidates=len(candidates))

    try:
        scores = _clean_scores(raw, allowed)
    except ScorerError as exc:
        return _fallback(rows, top_k, SCORER_ERROR, str(exc), candidates=len(candidates))
    if not scores:
        return _fallback(rows, top_k, EMPTY_SCORES, "scorer 未给出任何分数",
                         candidates=len(candidates))

    # 稳定排序：分数降序，同分保持原 RRF 名次（下标升序），保证可复现。
    ranked = sorted((i for i in range(len(candidates)) if str(i) in scores),
                    key=lambda i: (-scores[str(i)], i))
    tail = [i for i in range(len(candidates)) if str(i) not in scores]  # 未打分的排在后面，不丢

    ordered: List[Dict[str, Any]] = []
    for i in ranked + tail:
        row = rows[i]
        record = dict(row) if isinstance(row, dict) else {"text": _text_of(row)}
        if str(i) in scores:
            record["rerank_score"] = round(scores[str(i)], 6)
        ordered.append(record)

    final = ordered[:top_k]
    return _pack(final, reranked=True, scores={k: round(v, 6) for k, v in scores.items()},
                 dropped=len(rows) - len(final), reason=RERANKED,
                 detail=f"参与打分 {len(candidates)} 条，未返回分数 {len(tail)} 条",
                 candidates=len(candidates), unscored=len(tail))


SYSTEM_PROMPT = (
    "你是检索结果重排器。给定一个查询和若干候选片段，为每个候选打 0~1 的相关性分数"
    "（1 表示直接回答问题，0 表示无关）。\n"
    "只输出 JSON，不要解释、不要 markdown 代码块。格式：{\"scores\": {\"0\": 0.9, \"1\": 0.2}}\n"
    "key 必须是候选的**下标字符串**（从 0 开始），不要用正文当 key；"
    "必须为每一个候选都给出分数。"
)


def _extract_json(content: Any) -> Any:
    """从模型输出里取出 JSON：容忍 ```json 围栏与前后废话，其余一律当解析失败。"""
    if not isinstance(content, str) or not content.strip():
        raise ScorerError("模型返回为空")
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ScorerError(f"不是合法 JSON：{exc}") from exc
    raise ScorerError("模型输出里没有 JSON 对象")


def _parse_scores(content: Any, allowed: set) -> Dict[str, float]:
    payload = _extract_json(content)
    if not isinstance(payload, dict):
        raise ScorerError(f"JSON 顶层不是对象：{type(payload).__name__}")
    raw = payload.get("scores", payload)      # 容忍直接给 {"0":0.9} 的简写
    if not isinstance(raw, dict):
        raise ScorerError(f"scores 不是对象：{type(raw).__name__}")
    return _clean_scores(raw, allowed)


def llm_scorer(llm_call: Callable[..., str], *, model: Optional[str] = None) -> Callable:
    """把 LLM 调用包成 scorer。

    `llm_call` 的签名与 `llm_config.make_llm_call` 返回的一致：`llm_call(messages=..., **kw)`。
    模型与温度**不设默认值**：不同端点/模型对 temperature 的语义不一致，由调用方决定；
    `model=None` 时连这个参数都不传，沿用调用方自己的配置。

    解析失败（非 JSON / 下标越界 / 值不是数）→ 抛 `ScorerError`，由 `rerank` 回退到 RRF 顺序。
    """
    if not callable(llm_call):
        raise TypeError("llm_scorer 需要一个可调用的 llm_call(messages=..., **kw)")

    def scorer(query: str, candidates: Sequence[Dict[str, Any]]) -> Dict[str, float]:
        listing = []
        for cand in candidates:
            text = str(cand.get("text") or "")[:PROMPT_TEXT_LIMIT].replace("\n", " ")
            listing.append(f"[{cand['id']}] {text}")
        user = f"查询：{query}\n\n候选（共 {len(candidates)} 条）：\n" + "\n".join(listing)
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user}]
        kwargs: Dict[str, Any] = {}
        if model:
            kwargs["model"] = model
        content = llm_call(messages=messages, **kwargs)
        return _parse_scores(content, {str(c.get("id")) for c in candidates})

    return scorer
