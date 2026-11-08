"""P3-L9 · 18094 增量端点编排（`POST /v2/graph/delta` 的业务实现）。

为什么不写在 `api.py`
-------------------
`api.py` 顶层 import fastapi / pydantic；而 `llmke-v2-toolenv`（本仓主口径解释器）
**既没有 fastapi 也没有 pydantic**。若把编排写进 `api.py`，本模块的 J2/J3/J4/J8
在 v2 环境连 import 都过不去。所以这里**刻意不 import fastapi / pydantic / starlette**，
`req` 走**鸭子类型**（只读属性），HTTP 层（`api.py`）负责校验与序列化。
红线：`delta_build.py` 一旦引入 web 依赖，双解释器里的 v2 侧就整块失效。

三条硬约束（来自 TL 裁定）
------------------------
1. **绝不静默降级**：没有基准快照 → `REJECTED / NO_BASELINE_SNAPSHOT`；delta 失败 →
   `FAILED` 带原因。**任何情况都不自动改走 full**。
2. **`auto` 不等于 canary 的 `full`**（D-11）：`canary.DEFAULT_MODE = "full"`，
   而 L7 刚停掉全库重建。若 `mode`/`default` 仍来自**默认值**（`sources` 里是
   `"default"`），`auto` 一律按 `delta` 处理，并在响应里写明 `canary_source="default->delta"`。
   只有运维**显式**配了 `full`（文件或环境变量）才允许走全量。
3. **DELTA 后四文件必须由本次输入重算**：`rebuild_delta` 先 `copytree` 基准快照，
   新目录里带着旧的 `sources.json` / `community.json` / `kb.json` / `fence.json`。
   不重算就是"把旧文件当新结果"，`_finalize_snapshot()` 专门收口这件事。
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Iterable, List, Optional

from . import canary, global_report
from .fence import FENCE_FILE, FenceState
from .rebuild import (RebuildFailed, check_freshness, pointer_path, read_pointer,
                      rebuild, rebuild_delta)

SCHEMA = "llmke.graph-delta.v1"
DEFAULT_ROOT = ".artifacts/api-root"

# 响应里的三档结论（与设计包 §6.2 的状态机对齐）
STATUS_BUILT = "BUILT"
STATUS_SKIPPED_FRESH = "SKIPPED_FRESH"
STATUS_REJECTED = "REJECTED"
STATUS_FAILED = "FAILED"

MODES = ("auto", "delta", "full", "skip_if_fresh")

# 四个必须由本次输入重算的文件（copytree 会把旧的那份带进来）
FINAL_FILES = ("sources.json", "community.json", "fence.json", "kb.json")


# --------------------------------------------------------------------------- 路径/状态
def _kb_root(kb: str, root: Optional[str] = None) -> str:
    """库级根目录：`<root>/<kb>`；与 `/v2/graph/build` 的落盘口径一致。

    原先这段逻辑内联在 `api.py` 的 build 路由里（`api.py:371-375`）与
    `_resolve_snapshot`（`:136`）各写一遍；本 loop 只把它抽成**供 delta 路径使用**的
    私有 helper，**不改 build 路由**（L1~L8 已验收行为）。
    """
    base = root or os.environ.get("LLMKE_V2_ROOT") or DEFAULT_ROOT
    kbid = (kb or "").strip()
    return os.path.join(base, kbid) if kbid else base


def _load_fence(snapshot_dir: Optional[str]) -> FenceState:
    """从快照目录恢复撤权状态；目录缺失/文件坏 → 空 fence（由 `rebuild` 再按需处理）。"""
    if not snapshot_dir:
        return FenceState()
    return FenceState.load(os.path.join(snapshot_dir, FENCE_FILE))


def _base_snapshot(root: str) -> Optional[str]:
    """当前指针指向的基准快照目录（不存在就返回 None，**不猜**）。"""
    pointer = read_pointer(root)
    directory = (pointer or {}).get("dir")
    if directory and os.path.isdir(directory):
        return directory
    return None


# --------------------------------------------------------------------------- 四文件重算
def _text_to_idx(engine: Any) -> Dict[str, str]:
    """块文本 → openie idx（与 `api.py:159` 同一口径：块 id 是文本哈希）。"""
    out: Dict[str, str] = {}
    for doc in engine.openie_docs():
        passage, idx = doc.get("passage"), doc.get("idx")
        if passage and idx:
            out.setdefault(passage, idx)
    return out


def _write_sources(target: str, live: Iterable[Dict[str, Any]],
                   engine: Any) -> Dict[str, List[Dict[str, Any]]]:
    """重写 `sources.json`（idx → [{file_id, locator, title, pk, parse_artifact_id}]）。

    与 `_default_build` 的内联写法**逐字节等价**（单测对拍）：同一 `indent=1` /
    `ensure_ascii=False`、同样省略空值、同样按 `live` 顺序累积。
    """
    by_text = _text_to_idx(engine)
    sources: Dict[str, List[Dict[str, Any]]] = {}
    for item in live:
        idx = by_text.get(item["text"])
        if not idx:
            continue
        sources.setdefault(idx, []).append(
            {k: v for k, v in (("file_id", item["file_id"]), ("locator", item["locator"]),
                               ("title", item.get("title")), ("pk", item.get("pk")),
                               ("parse_artifact_id", item.get("parse_artifact_id")))
             if v is not None and v != ""}
        )
    with open(os.path.join(target, "sources.json"), "w", encoding="utf-8") as fh:
        json.dump(sources, fh, ensure_ascii=False, indent=1)
    return sources


def _write_kb_json(target: str, kb: str) -> None:
    """写快照归属标记 `kb.json`（查询侧据此确认"这份图属于哪个库"）。"""
    if not kb or not target:
        return
    with open(os.path.join(target, "kb.json"), "w", encoding="utf-8") as fh:
        json.dump({"kb_id": kb}, fh, ensure_ascii=False)


def _file_sha(path: str) -> Optional[str]:
    import hashlib

    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _finalize_snapshot(target: str, kb: str, live: List[Dict[str, Any]],
                       fence: FenceState, *, engine: Any) -> Dict[str, Any]:
    """把刚 DAG 好的快照目录收口成"可被查询侧认领"的样子：四文件全部重算。

    顺序与 `api.py` build 路由一致：先 fence / sources（数据面），再 kb.json（归属），
    最后 community（报告依赖前两者）。任一步失败都抛出，由调用方如实报错——
    「半收口的快照」比「没有快照」更危险：查询侧会读到旧的 sources 配新的图。
    """
    # 已撤权文件不能进 sources / community：快照里本来就没有它们的块（`rebuild_*` 已剔除），
    # 若这里按**请求里的** live 写，sources 就会指向不存在的块 —— 查询侧拿 idx 回查必然落空。
    surviving = [d for d in live if not fence.is_revoked(str(d.get("file_id", "")))]
    fence.save(os.path.join(target, FENCE_FILE))
    sources = _write_sources(target, surviving, engine)
    _write_kb_json(target, kb)
    community = global_report.write(target, [str(d["file_id"]) for d in surviving])
    shas = {name: _file_sha(os.path.join(target, name)) for name in FINAL_FILES}
    return {"sources": len(sources), "community": community, "shas": shas}


# --------------------------------------------------------------------------- 模式解析
def _canary_info(policy: Any) -> Dict[str, Any]:
    info = policy.describe() if hasattr(policy, "describe") else {}
    stored = dict(getattr(policy, "sources", ()) or ())
    info["sources"] = {name: stored.get(name, "explicit")
                       for name in ("scope", "mode", "default")}
    return info


def _resolve_mode(requested: str, policy: Any, kb: str) -> Dict[str, Any]:
    """把 `requested_mode` 解析成实际执行模式，并留下可审计的来源说明。

    D-11 的核心：canary 的 `DEFAULT_MODE` 是 `full`，若照它跑，`auto` 会把 L7 刚停掉的
    **全库重建**悄悄恢复（kb_1004 有 4520 块，小时级）。所以「来源是默认值」时按 delta 处理；
    只有**显式配置**（file/env）才采纳 canary 的 full。
    """
    if requested == "delta":
        return {"effective": "DELTA", "canary_source": "explicit:delta"}
    if requested == "full":
        return {"effective": "FULL", "canary_source": "explicit:full"}

    info = _canary_info(policy)
    sources = info.get("sources") or {}
    from_default = sources.get("mode") == "default" and sources.get("default") == "default"
    if from_default:
        # 无任何 canary 配置：canary 的 full 只是 dataclass 默认值，不代表运维意图
        return {"effective": "DELTA", "canary_source": "default->delta",
                "canary": info}
    mode = policy.mode_for(kb) if hasattr(policy, "mode_for") else "delta"
    return {"effective": "FULL" if mode == "full" else "DELTA",
            "canary_source": f"canary:{mode}", "canary": info}


# --------------------------------------------------------------------------- 默认实现
def _default_apply(target: str, texts: List[str]) -> Any:
    from .engine_hipporag import HippoRAGEngine
    from .api import _ensure_cjk_compat, _urls

    _ensure_cjk_compat()
    urls = _urls()
    engine = HippoRAGEngine(save_dir=target, llm_base_url=urls["llm"],
                            embedding_base_url=urls["embed"])
    return engine.apply_delta(texts)


def _default_full_build(urls: Dict[str, str]) -> Callable[[List[Dict[str, Any]], str], Any]:
    def full_build(items, target):
        from .api import _ensure_cjk_compat
        from .engine_hipporag import HippoRAGEngine

        _ensure_cjk_compat()
        engine = HippoRAGEngine(save_dir=target, llm_base_url=urls["llm"],
                                embedding_base_url=urls["embed"])
        return engine.build([x["text"] for x in items])

    return full_build


def _engine_at(target: str) -> Any:
    from .engine_hipporag import HippoRAGEngine
    from .api import _urls

    urls = _urls()
    return HippoRAGEngine(save_dir=target, llm_base_url=urls["llm"],
                          embedding_base_url=urls["embed"])


def _doc_file_ids(get: Callable[[str], Any]) -> List[str]:
    """取一条 doc 的 `file_ids`：契约 §2.1 是**数组**（1:N 同文异源）。

    兼容单值 `file_id`（旧形态/内部 dict），但**输出统一成 list**；
    两者都没有时返回 `[""]` —— 宁可留空 id，也不让正文静默消失。
    """
    ids = get("file_ids")
    if ids is None:
        single = get("file_id")
        ids = [single] if single not in (None, "") else None
    if isinstance(ids, (str, bytes)):
        ids = [ids]
    cleaned = [str(i).strip() for i in (ids or []) if str(i).strip()]
    return cleaned or [""]


def _as_live(docs: Iterable[Any]) -> List[Dict[str, Any]]:
    """把 `BuildDoc` / dict / 任意带属性的对象统一成 `rebuild` 要的 live 列表。

    **一条 doc 有 N 个 `file_ids` 就产出 N 行**（同一 text）：`rebuild` 的 `live`
    多行同 text，`_write_sources` 会把这些行 append 到同一个 idx 下，
    正是契约 §2.1 要求的「引擎合并成一块、`sources.json` 保留 1:N」。
    """
    live: List[Dict[str, Any]] = []
    for doc in docs or []:
        get = doc.get if isinstance(doc, dict) else (lambda k, _d=doc: getattr(_d, k, None))
        text = str(get("text") or "")
        for fid in _doc_file_ids(get):
            live.append({"file_id": fid,
                         "text": text,
                         "locator": get("locator"),
                         "title": get("title"),
                         "pk": get("pk"),
                         "parse_artifact_id": get("parse_artifact_id")})
    return live


# --------------------------------------------------------------------------- 主编排
def delta_build(req: Any, *, apply_fn: Optional[Callable] = None,
                full_builder: Optional[Callable] = None,
                engine_factory: Optional[Callable] = None,
                policy: Any = None) -> Dict[str, Any]:
    """按 `requested_mode` 编排增量/全量/跳过；**任何分支都不静默降级**。

    `req` 只要求有 `kb` / `docs` / `requested_mode` 三个属性（鸭子类型），
    其余可选：`root` / `fallback_reason` / `fencing`。HTTP 层在 `api.py` 里做校验。
    """
    kb = str(getattr(req, "kb", "") or "").strip()
    requested = str(getattr(req, "requested_mode", "auto") or "auto").strip().lower()
    if requested not in MODES:
        return {"schema": SCHEMA, "status": STATUS_REJECTED, "kb": kb,
                "reason": f"UNKNOWN_REQUESTED_MODE: {requested!r}", "requested_mode": requested}
    if requested == "full" and not str(getattr(req, "fallback_reason", "") or "").strip():
        return {"schema": SCHEMA, "status": STATUS_REJECTED, "kb": kb,
                "reason": "FULL_REQUIRES_FALLBACK_REASON", "requested_mode": requested}

    root = _kb_root(kb, getattr(req, "root", None))
    live = _as_live(getattr(req, "docs", None))
    if not live:
        return {"schema": SCHEMA, "status": STATUS_REJECTED, "kb": kb,
                "reason": "DOCS_EMPTY", "requested_mode": requested}

    base_dir = _base_snapshot(root)
    fence = _load_fence(base_dir)
    pointer = read_pointer(root)
    freshness = check_freshness(pointer, live, fence)

    resolved = _resolve_mode(requested, policy if policy is not None else canary.load(None), kb)
    effective = resolved["effective"]
    fencing = getattr(req, "fencing", None)

    common = {"schema": SCHEMA, "kb": kb, "root": root,
              "requested_mode": requested, "canary_source": resolved["canary_source"],
              "freshness": freshness, "fencing_requested": fencing}
    if resolved.get("canary"):
        common["canary"] = resolved["canary"]

    # J2：不 stale 且只要求「新就跳过」→ 零引擎调用
    if requested in ("auto", "skip_if_fresh") and not freshness.get("stale"):
        return {**common, "status": STATUS_SKIPPED_FRESH, "effective_mode": "SKIPPED",
                "reason": freshness.get("reason")}

    # J4-A（D-9）：delta 必须有基准快照；**判空前置**，不靠 RebuildFailed 的字符串
    if effective == "DELTA" and base_dir is None:
        return {**common, "status": STATUS_REJECTED, "effective_mode": "DELTA",
                "reason": "NO_BASELINE_SNAPSHOT"}

    try:
        if effective == "DELTA":
            out = rebuild_delta(root, fence, live, apply_fn or _default_apply,
                                fencing=fencing)
        else:
            build_fn = full_builder or _default_full_build(_urls_for_build())
            out = rebuild(root, fence, live, build_fn, fencing=fencing)
    except RebuildFailed as exc:
        # J4-C：delta 失败**不**改走 full，原样带回原因
        return {**common, "status": STATUS_FAILED, "effective_mode": effective,
                "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001 - 失败必须可见
        return {**common, "status": STATUS_FAILED, "effective_mode": effective,
                "reason": f"{type(exc).__name__}: {exc}"}

    target = str((out.get("current") or {}).get("dir") or "")
    if not target or not os.path.isdir(target):
        return {**common, "status": STATUS_FAILED, "effective_mode": effective,
                "reason": "SNAPSHOT_DIR_MISSING"}

    # J3：四文件由本次输入重算（copytree 带进来的旧文件必须被覆盖）
    engine = (engine_factory or _engine_at)(target)
    try:
        final = _finalize_snapshot(target, kb, live, fence, engine=engine)
    except Exception as exc:  # noqa: BLE001 - 收口失败要带原因，不能报 BUILT
        return {**common, "status": STATUS_FAILED, "effective_mode": effective,
                "reason": f"FINALIZE_FAILED: {type(exc).__name__}: {exc}",
                "snapshot": target}

    return {**common, "status": STATUS_BUILT, "effective_mode": effective,
            # 契约 §2.2：`apply_result{deleted,added,reused,duplicates,remaining,expected,consistent}`。
            # 数据一直是引擎算的（`engine.apply_delta` → `rebuild.py:294` 放进
            # `out["apply_result"]`），这里只是**透传**，不新造统计；
            # §2.3 不变式 #2 依赖它（`consistent == true` 且 `remaining == expected`）。
            "apply_result": out.get("apply_result"),
            "snapshot": target, "documents": len(live),
            "generation": (out.get("current") or {}).get("generation"),
            "fencing_used": (out.get("current") or {}).get("fencing"),
            "pointer": pointer_path(root),
            "dropped_revoked": (out.get("current") or {}).get("dropped_revoked"),
            "community": final["community"], "file_shas": final["shas"],
            "sources": final["sources"]}


def _urls_for_build() -> Dict[str, str]:
    from .api import _urls

    return _urls()
