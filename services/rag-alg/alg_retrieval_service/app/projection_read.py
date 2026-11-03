"""检索读路径的投影切换（legacy / snapshot），默认 legacy、可逆、按知识库粒度。

为什么放在"基础知识库名"这一层
------------------------------
检索下游所有索引名都是 `table_chunks_<kb>` / `table_summary_<kb>` / `<kb>` 这样拼出来的
（`retrieval_service.py:53-60`）。只要把**基础名**换掉，三条通道会一起切走，
不需要在每个调用点各改一遍，也不会出现"正文切了、表格没切"的半切换状态。

开关
----
- `INGEST_READ_MODE=legacy|snapshot`（默认 legacy）；
- `INGEST_READ_PREFIX`（默认 `v2cand`）；
- `INGEST_READ_KBS`（可选，逗号分隔）：只有列出的知识库走 snapshot，其余保持 legacy。
  这保证"先在一个库上验证，再扩量"，而不是一刀切全库。

fail-closed
-----------
未知 mode 直接抛错，不静默退回 legacy：静默退回会让"以为切了其实没切"，
而这一层的错误表现是"检索结果看起来正常但来源是旧数据"，最难发现。
"""

import os

MODES = ("legacy", "snapshot")
DEFAULT_MODE = "legacy"
DEFAULT_PREFIX = "v2cand"


def _split(value):
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def resolve(names, mode=None, prefix=None, only=None):
    """返回 (新的基础名列表, 说明)。`说明` 用于打点/对照，不含敏感信息。"""
    names = [n for n in (names or []) if n and n.strip()]
    mode = (mode or os.environ.get("INGEST_READ_MODE") or DEFAULT_MODE).strip().lower()
    if mode not in MODES:
        raise ValueError(f"INGEST_READ_MODE 非法: {mode!r}，允许 {MODES}")
    if mode == "legacy":
        return list(names), {"mode": "legacy", "switched": []}

    prefix = (prefix or os.environ.get("INGEST_READ_PREFIX") or DEFAULT_PREFIX).strip()
    if not prefix:
        raise ValueError("INGEST_READ_PREFIX 为空，snapshot 模式必须有前缀")
    only = set(only if only is not None else _split(os.environ.get("INGEST_READ_KBS")))

    out, switched, kept = [], [], []
    for name in names:
        if only and name not in only:
            out.append(name)
            kept.append(name)
        else:
            out.append(f"{prefix}_{name}")
            switched.append(name)
    return out, {"mode": "snapshot", "prefix": prefix,
                 "switched": switched, "kept_legacy": kept}
