"""相关性筛选：把"取到的块"变成"值得引用的块"。

为什么需要这一层
    检索返回的是候选（top-N），不是证据。把候选全部写进答案有两个后果：
      1. 无关块也被引用，读者无法判断哪句有依据；
      2. 支撑率被"凑数"抬高——引用越多越像有据，实际是稀释。
    真实事故形态：答案里三条引用，两条与问题无关。

为什么不用向量/模型打分
    本轮要可复现、可断言、可在无网络环境跑。字符 bigram + 词元覆盖度是确定性的，
    排序结果可以写进 golden 断言；将来换成向量分数时，只需替换 `score()`。

中文为什么用 bigram
    中文没有空格分词，按字算会把"第一段"和"第二段落"都算成命中（单字覆盖太粗）；
    bigram（连续两字）对"第一/一段"这种短语更敏感，且无需词典。
"""
from __future__ import annotations

import re

# 拉丁词元：字母数字下划线；中文按字切，后续再拼 bigram
_LATIN = re.compile(r"[a-z0-9_]+")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> set[str]:
    """返回特征集合：拉丁词（小写） + 中文 bigram（单字文本退化为单字）。"""
    if not isinstance(text, str) or not text:
        return set()
    low = text.lower()
    feats = set(_LATIN.findall(low))
    for run in re.findall(r"[\u4e00-\u9fff]+", low):
        if len(run) == 1:
            feats.add(run)
        else:
            feats.update(run[i:i + 2] for i in range(len(run) - 1))
    return feats


def score(query: str, text: str) -> float:
    """覆盖度：查询特征中被文本命中的比例（0..1），确定性、无平滑参数。"""
    q = tokenize(query)
    if not q:
        return 0.0
    t = tokenize(text)
    if not t:
        return 0.0
    return len(q & t) / len(q)


def rank_chunks(query: str, chunks: list[dict], *, min_score: float = 0.0,
                top_k: int | None = None) -> tuple[list[dict], list[dict]]:
    """返回 (保留, 丢弃)。排序键 = (-score, chunk_index)，保证同分时顺序稳定。

    丢弃不是静默的：调用方拿到第二返回值，必须把它写进审计（否则"筛掉了什么"无从复盘）。
    """
    if min_score < 0 or min_score > 1:
        raise ValueError("min_score 必须在 [0,1]")
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k 必须为正整数")

    scored = []
    for c in chunks:
        s = score(query, c.get("text", ""))
        scored.append((s, c))
    scored.sort(key=lambda x: (-x[0], x[1].get("chunk_index", 0)))

    kept = [c for s, c in scored if s >= min_score and s > 0]
    dropped = [{"chunk_id": c.get("chunk_id"), "score": round(s, 4),
                "reason": "below_min_score" if s < min_score else "no_overlap"}
               for s, c in scored if not (s >= min_score and s > 0)]
    if top_k is not None and len(kept) > top_k:
        dropped.extend({"chunk_id": c.get("chunk_id"), "score": None, "reason": "top_k_cut"}
                       for c in kept[top_k:])
        kept = kept[:top_k]
    return kept, dropped
