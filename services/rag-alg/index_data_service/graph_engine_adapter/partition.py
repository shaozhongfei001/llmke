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
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .fence import FenceState
from .rebuild import rebuild, rebuild_delta

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
    # 快照路径一律存**绝对路径**：清单是给另一个进程（worker/网关）读的，
    # 存相对路径时它的 cwd 未必和构建时一样，`resolve()` 会解析失败 → fail-closed
    # 变成"这个范围永远查不到"，而且看起来像隔离生效，极难排查。
    normalized = {}
    for scope, entry in (entries or {}).items():
        item = dict(entry or {})
        snapshot = item.get("snapshot")
        if snapshot:
            item["snapshot"] = os.path.abspath(snapshot)
        normalized[scope] = item
    payload = {"schema": SCHEMA, "scopes": normalized}
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
    if snapshot and not os.path.isabs(snapshot):
        # 兼容旧清单（相对路径）：按当前 cwd 试一次，仍不行就 fail-closed。
        snapshot = os.path.abspath(snapshot)
        entry = {**entry, "snapshot": snapshot}
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


# ---------------------------------------------------------------------------
# 按范围的增量编排
#
# 问题：构建期隔离让每个可见范围各有一份索引，于是"改一份文档"要整份重建**该范围**的索引，
# 总成本 = 范围数 × 全量。`rebuild.rebuild_delta` 已经能"复制上一份快照 + 只对新增块抽取"，
# 缺的只是把它落到某一个范围上：范围各有根目录、各有指针，而路由清单是**一张总表**。
#
# 两处最容易写错的地方，先说清楚：
# 1. `write_manifest` 是**整表覆盖**。重建 A 范围时如果只写 A 的条目，B 就从清单里消失了，
#    之后 `resolve(root, "B")` 返回 None —— 那条范围从此 fail-closed 查不到，等于事故。
#    所以必须先读旧清单、合并本次条目、再整表写回（其它范围的条目原样带过）。
# 2. 增量失败时**不动清单、不动指针**：路由还指着旧快照，旧快照继续服务；
#    把清单写上"新目录"而新目录是半成品，才是真正的坏结果。
# ---------------------------------------------------------------------------

SCOPE_DELTA_SCHEMA = "llmke.graph-engine.partition-delta.v1"


class ScopeDeltaError(RuntimeError):
    """按范围的增量编排失败。

    抛出时清单与范围指针都保持原样（旧快照继续可解析）——除了极少数在
    "指针已切换"之后才发现清单读不了的情形，那种情况消息里会明说。
    """


def _read_entries(root: str) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """读清单的 `scopes` 表，返回 `(entries, 不可用原因)`；原因非 None 表示清单当前不可信。

    不用 `resolve()` 来读：那个函数只回答"这个范围能不能查"，这里要的是**全表**——
    因为写回是整表覆盖，必须先把别人的条目原样拿到手。
    """
    path = os.path.join(root, MANIFEST_NAME)
    if not os.path.isfile(path):
        return {}, "NO_MANIFEST"
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.loads(fh.read())
    except (ValueError, OSError):
        return {}, "MANIFEST_UNREADABLE"
    entries = data.get("scopes")
    if not isinstance(entries, dict):
        return {}, "MANIFEST_UNREADABLE"
    return {str(k): v for k, v in entries.items()}, None


def delta_plan(root: str, scope: str, docs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """这个范围能不能走增量、基准快照在哪、这次该喂哪些文档。

    只回答"能不能"，**不做兜底**：拿不到基准就 `can_delta=False` 并给出具体原因，
    由调用方决定走全量还是报错。这里若自作聪明回退全量，"增量"就成了一个无法观测的猜想。

    原因码（给日志与断言用，不要靠中文消息匹配）：
    - `NO_MANIFEST`：清单文件不存在（首次构建）；
    - `MANIFEST_UNREADABLE`：清单存在但读不出/结构不对 —— 不猜它的内容；
    - `SCOPE_NOT_LISTED`：清单里没有这个范围（从未构建过，或被人手工改过）；
    - `SNAPSHOT_DIR_MISSING`：清单写了这个范围，但快照目录已经不在（被清理/被搬走）；
    - `NO_DOCUMENTS`：该范围本次没有可见文档，增量会产出空快照，必须拒绝；
    - `OK`：可以增量。
    """
    scoped = build_plan(list(docs), [scope])[scope]
    entries, reason = _read_entries(root)
    if reason:
        return {"base": None, "docs": scoped, "can_delta": False, "reason": reason}
    entry = entries.get(str(scope))
    if not entry:
        return {"base": None, "docs": scoped, "can_delta": False, "reason": "SCOPE_NOT_LISTED"}
    base = entry.get("snapshot")
    if not base or not os.path.isdir(str(base)):
        return {"base": None, "docs": scoped, "can_delta": False,
                "reason": "SNAPSHOT_DIR_MISSING"}
    if not scoped:
        return {"base": str(base), "docs": [], "can_delta": False, "reason": "NO_DOCUMENTS"}
    return {"base": str(base), "docs": scoped, "can_delta": True, "reason": "OK"}


def scope_delta_build(root: str, scope: str, docs: Iterable[Dict[str, Any]],
                      build_fn: Callable[[List[Dict[str, Any]], str], Any],
                      apply_fn: Callable[[str, List[str]], Any], *,
                      fencing: Optional[int] = None, keep_last: int = 2,
                      allow_full_build: bool = False) -> Dict[str, Any]:
    """只重建**一个范围**：复制该范围上一份快照 → 应用差异 → 切指针 → 合并清单。

    为什么要 `allow_full_build` 而不是"没基准就自动全量"：
    - 自动全量会让"配置说要增量、实际跑的是全量"变得不可见（`rebuild.py` 明确拒绝这种静默降级）；
    - 但"首次构建"确实是常态，让每个调用方自己写分支，编排逻辑就会在 N 个地方各写一遍。
    折中是：**显式开关 + 返回值里带 `mode` 与 `fallback_reason`**，谁走全量、为什么走，一眼可查。

    目标目录固定落在 `scope_dir(root, scope)` 下：同一范围同一根。换根会让旧指针与新快照
    分居两地，`resolve()` 读到的路由与实际快照就不是同一棵树了。

    `fencing` 原样透传给 `rebuild_delta`：被接管的旧主不能靠"按范围增量"这条路绕开写入保护。
    """
    plan = delta_plan(root, scope, docs)
    scope_root = scope_dir(root, scope)
    fence = FenceState()          # 撤权代次由调用方另行处理；本函数只负责"按范围"编排
    os.makedirs(scope_root, exist_ok=True)

    if plan["can_delta"]:
        try:
            out = rebuild_delta(scope_root, fence, plan["docs"], apply_fn,
                                keep_last=keep_last, fencing=fencing)
        except Exception as exc:  # noqa: BLE001 - 统一转成可读的编排错误
            raise ScopeDeltaError(
                f"范围 {scope!r} 增量重建失败（清单与指针未动，旧快照继续服务，"
                f"基准 {plan['base']}）：{type(exc).__name__}: {exc}") from exc
        mode, fallback_reason = "DELTA", None
    else:
        if not allow_full_build:
            raise ScopeDeltaError(
                f"范围 {scope!r} 没有可用的基准快照（{plan['reason']}），增量拒绝执行；"
                "请先做一次全量，或显式传 allow_full_build=True")
        try:
            out = rebuild(scope_root, fence, plan["docs"], build_fn,
                          keep_last=keep_last, fencing=fencing)
        except Exception as exc:  # noqa: BLE001
            raise ScopeDeltaError(
                f"范围 {scope!r} 全量重建失败（清单与指针未动）：{type(exc).__name__}: {exc}"
            ) from exc
        mode, fallback_reason = "FULL", plan["reason"]

    current = out["current"]

    # 快照目录必须真的在。`rebuild._promote` 按目录名排序做 keep_last 清理，而名字里的
    # 微秒尾巴在同一秒内并不单调——极端情况下刚建好的目录可能被当成"最旧的"删掉。
    # 那属于 rebuild 的命名约定（不在本文件范围内），但**清单绝不能跟着指向一个不存在的目录**：
    # 那会让这条范围从"可解析"变成"解析到空气"。宁可这里报错、清单留在旧快照上。
    if not os.path.isdir(str(current.get("dir") or "")):
        raise ScopeDeltaError(
            f"范围 {scope!r} 构建返回的快照目录不存在（{current.get('dir')}）："
            "清单保持上一次的值不动，旧快照继续服务")

    # ---- 合并清单：这一步才是本函数存在的理由 ----
    entries, reason = _read_entries(root)
    if reason == "MANIFEST_UNREADABLE":
        # 指针已切到新快照，但清单此刻读不出来：**不能**拿"只有本范围"的表去覆盖，
        # 那会把其它范围整片抹掉。宁可让 resolve() 继续 fail-closed，也不制造假路由。
        raise ScopeDeltaError(
            f"范围 {scope!r} 已切指针到 {current['dir']}，但清单{reason}："
            f"拒绝用单范围内容覆盖 {os.path.join(root, MANIFEST_NAME)}")
    # NO_MANIFEST 是"这张表本来就还没有"（首次构建）：此时没有别人的条目可保护，
    # 写 {本范围} 就是事实，不算猜。

    entry = dict(entries.get(str(scope)) or {})     # 保留本范围已有字段（如人工加的备注）
    entry.update({"snapshot": current["dir"], "documents": current["documents"],
                  "mode": current.get("mode"), "generation": current.get("generation"),
                  "built_at": current.get("built_at")})
    chunks = _chunk_count(out, mode)
    if chunks is not None:
        entry["chunks"] = chunks
    entries[str(scope)] = entry
    manifest = write_manifest(root, entries)        # 整表覆盖：entries 里含其它范围的原样条目

    return {"schema": SCOPE_DELTA_SCHEMA, "scope": str(scope), "status": "BUILT",
            "mode": mode, "fallback_reason": fallback_reason,
            "root": scope_root, "manifest": manifest, "current": current,
            "base": plan["base"], "apply_result": out.get("apply_result"),
            "build_result": out.get("build_result"),
            "other_scopes": sorted(k for k in entries if k != str(scope))}


def _chunk_count(out: Dict[str, Any], mode: str) -> Optional[int]:
    """块数优先取"实际剩下多少"，取不到就返回 None —— 不拿文档数冒充块数。"""
    if mode == "DELTA":
        remaining = (out.get("apply_result") or {}).get("remaining")
    else:
        remaining = (out.get("build_result") or {}).get("chunks")
    return remaining if isinstance(remaining, int) else None
