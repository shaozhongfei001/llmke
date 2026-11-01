"""构建期可见集合隔离：不该被某个范围看到的内容，**根本不进那个范围的索引**。

与查询期过滤的区别（这是本节唯一重要的一句话）：
- 查询期过滤（`retrieval_filter`）：内容在索引里，命中后被丢掉——"检索到但不给看"；
- 构建期隔离（本模块）：内容压根不在这个索引里——"检索都检索不到"。

后者才是隔离。前者一旦过滤逻辑写错、或者有人绕过去直接查引擎，就会漏。

代价（必须说清）：
- 每个可见范围一份索引 → 磁盘与构建时间随范围数线性增长；
- 同一份内容出现在多个范围时会被重复抽取（LLM 成本翻倍）；
- 跨范围查询需要合并多份索引，本模块不做（交给调用方按范围分别查）。

所以默认不开启：`scope=None` 时行为与单索引完全一致。
"""

import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence

SCHEMA = "llmke.graph-engine.partition.v1"
MANIFEST_NAME = "scopes.json"


def doc_visibility(doc: Dict[str, Any]) -> List[str]:
    """一份文档的可见范围：取 `visibility`，缺省 `["public"]`。

    缺省给 public 而不是"空集合"：空集合会把所有未标注内容变成"谁都看不见"，
    上线第一天就会全库检索不到——这类默认值必须是"最不惊讶"的那个。
    """
    raw = doc.get("visibility")
    if raw is None:
        raw = (doc.get("metadata") or {}).get("visibility")
    if isinstance(raw, str):
        raw = [raw]
    scopes = [str(s).strip() for s in (raw or []) if str(s).strip()]
    return scopes or ["public"]


def build_plan(docs: Sequence[Dict[str, Any]], scopes: Iterable[str]) -> Dict[str, List[Dict[str, Any]]]:
    """每个范围该建哪些文档：`scope` 只收"可见范围包含它"的文档。

    `public` 对所有范围可见（含未列出的范围）；这是"公共知识"的语义。
    """
    wanted = [str(s) for s in scopes]
    plan: Dict[str, List[Dict[str, Any]]] = {s: [] for s in wanted}
    for doc in docs:
        visible = set(doc_visibility(doc))
        for scope in wanted:
            if scope in visible or "public" in visible:
                plan[scope].append(doc)
    return plan


def scope_dir(root: str, scope: str) -> str:
    """范围 → 目录名。用哈希而不是原文：范围名来自外部，直接拼路径会被 `../` 穿越。"""
    digest = hashlib.sha256(str(scope).encode("utf-8")).hexdigest()[:12]
    safe = "".join(ch for ch in str(scope) if ch.isalnum() or ch in "-_")[:24] or "scope"
    return os.path.join(root, "scopes", f"{safe}-{digest}")


def write_manifest(root: str, entries: Dict[str, Dict[str, Any]]) -> str:
    """范围 → 快照目录/文档数。路由只读清单，不靠命名规则猜。"""
    path = os.path.join(root, MANIFEST_NAME)
    os.makedirs(root, exist_ok=True)
    payload = {"schema": SCHEMA, "scopes": entries}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, path)
    return path


def resolve(root: str, scope: str) -> Optional[Dict[str, Any]]:
    """按范围选快照。**查不到就返回 None（fail-closed）**，绝不回退到"默认全量索引"——

    回退等于把隔离作废：一次拼错范围名，就会读到所有人可见的那份索引。
    """
    path = os.path.join(root, MANIFEST_NAME)
    if not os.path.isfile(path):
        return None
    try:
        data = json.loads(open(path, encoding="utf-8").read())
    except ValueError:
        return None
    entry = (data.get("scopes") or {}).get(str(scope))
    if not entry:
        return None
    snapshot = entry.get("snapshot")
    if not snapshot or not os.path.isdir(snapshot):
        return None
    return entry


def summarize(plan: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """给日志/证据用：每个范围多少文档、多少块；以及"只出现在一个范围"的文档数。"""
    seen: Dict[str, int] = {}
    for docs in plan.values():
        for doc in docs:
            fid = str(doc.get("file_id", ""))
            seen[fid] = seen.get(fid, 0) + 1
    return {"scopes": {s: {"documents": len({x.get("file_id") for x in d}), "chunks": len(d)}
                       for s, d in plan.items()},
            "exclusive_documents": sum(1 for n in seen.values() if n == 1),
            "shared_documents": sum(1 for n in seen.values() if n > 1)}
