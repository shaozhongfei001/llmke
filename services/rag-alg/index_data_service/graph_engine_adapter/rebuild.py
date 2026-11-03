"""隔离快照重建编排：撤权 → 用存活文件建新快照 → 提升代次 → 切读。

为什么要有编排而不是"手工跑一遍重建"：
- 重建的**目标目录必须是新的**（隔离快照），不能原地改旧索引——旧索引在重建期间还要能被
  fence 拦着读；
- 切换必须**原子**：先写好指针文件，再让读者看到；失败时指针不变，旧索引继续（被 fence 挡着）；
- 代次必须单调：新快照的代次 == 重建时 fence 的代次，读者据此判断"够不够新"。

`build_fn(docs, target_dir)` 由调用方注入（真实实现用 HippoRAGEngine + save_dir），
测试用假实现即可验证编排顺序与失败语义。
"""

import hashlib
import json
import os
import shutil
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from .fence import FenceState

SCHEMA = "llmke.graph-engine.rebuild.v1"


class RebuildFailed(RuntimeError):
    pass


class StaleFencingError(RuntimeError):
    """fencing 值落后于当前指针：说明这是被接管的旧主，写入必须拒绝。

    只靠租约 TTL 不够：旧主从"实际失去租约"到"发现自己失去"之间存在窗口，
    这期间它可能已经写完指针。fencing 让旧主的写入在**落盘那一刻**被拒。
    """


def pointer_path(root: str) -> str:
    return os.path.join(root, "current.json")


def read_pointer(root: str) -> Optional[Dict[str, Any]]:
    path = pointer_path(root)
    if not os.path.isfile(path):
        return None
    return json.loads(open(path, encoding="utf-8").read())


def docs_fingerprint(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """文档集合指纹：文件名 + 内容哈希。用于判断"重建期间有没有新文件/改动"。"""
    per_file: Dict[str, List[str]] = {}
    for doc in docs:
        fid = str(doc.get("file_id", ""))
        digest = hashlib.sha256(str(doc.get("text", "")).encode("utf-8")).hexdigest()
        per_file.setdefault(fid, []).append(digest)
    frozen = {fid: sorted(v) for fid, v in per_file.items()}
    blob = json.dumps(frozen, sort_keys=True).encode()
    return {"files": sorted(frozen), "per_file": frozen,
            "digest": hashlib.sha256(blob).hexdigest()}


def check_freshness(pointer: Optional[Dict[str, Any]],
                    live_docs: List[Dict[str, Any]],
                    fence: Optional[FenceState] = None) -> Dict[str, Any]:
    """快照是否覆盖当前存活文档。

    注意语义：**缺文件 = 数据缺失，不是越权**。所以这里只报告 stale，不阻止读；
    越权由 fence 管。两者不能混——把"缺数据"当"不安全"会让系统在无关故障时整体不可用。
    """
    # 已撤权文件不该算"缺失"：否则撤权后每次新鲜度检查都会误报 stale
    if fence is not None:
        live_docs = [d for d in live_docs if not fence.is_revoked(str(d.get("file_id", "")))]
    current = docs_fingerprint(live_docs)
    if not pointer:
        return {"stale": True, "reason": "NO_POINTER", "missing": current["files"],
                "changed": []}
    recorded = pointer.get("fingerprint") or {}
    recorded_files = set(recorded.get("files") or [])
    missing = sorted(set(current["files"]) - recorded_files)
    removed = sorted(recorded_files - set(current["files"]))
    changed = []
    for fid in sorted(set(recorded.get("per_file") or {}) & set(current["per_file"])):
        if (recorded["per_file"][fid] != current["per_file"][fid]):
            changed.append(fid)
    fresh = not missing and not removed and not changed
    return {"stale": not fresh,
            "reason": "OK" if fresh else "SNAPSHOT_OUT_OF_DATE",
            "missing": missing, "removed": removed, "changed": changed}


def _write_pointer(root: str, payload: Dict[str, Any]) -> str:
    """先写临时文件再 rename：避免读者看到半个 JSON。"""
    path = pointer_path(root)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


def rebuild(root: str, fence: FenceState, docs: Iterable[Dict[str, Any]],
            build_fn: Callable[[List[Dict[str, Any]], str], Any], *,
            keep_last: int = 2, fencing: Optional[int] = None) -> Dict[str, Any]:
    """执行一次隔离重建。失败时**不改指针**，旧索引继续由 fence 挡着。

    `docs` 里凡是来源已撤权的条目会在这里被剔除——重建不能依赖调用方自觉。
    """
    live = [d for d in docs if not fence.is_revoked(str(d.get("file_id", "")))]
    dropped = [d.get("file_id") for d in docs if fence.is_revoked(str(d.get("file_id", "")))]
    if not live:
        raise RebuildFailed("没有存活文件可重建（全部撤权），拒绝生成空快照")

    # 秒级时间戳会在同一秒内两次重建时撞名，加纳秒尾巴保证唯一
    stamp = f"{time.strftime('%Y%m%d%H%M%S')}-{time.time_ns() % 1000000:06d}"
    target = os.path.join(root, f"snapshot-{stamp}-g{fence.generation}")
    os.makedirs(root, exist_ok=True)
    os.makedirs(target, exist_ok=False)

    previous = read_pointer(root)
    try:
        result = build_fn(live, target)
    except Exception as exc:  # noqa: BLE001
        # 失败即回滚目录，指针保持旧值：宁可继续用被 fence 挡住的旧索引，也不切到半成品
        shutil.rmtree(target, ignore_errors=True)
        raise RebuildFailed(f"重建失败，指针未切换：{type(exc).__name__}: {exc}") from exc

    payload = _promote(root, fence, live, target, previous, result,
                       fencing=fencing, dropped=dropped, keep_last=keep_last,
                       mode="FULL")
    return {"schema": SCHEMA, "status": "BUILT", "pointer": pointer_path(root),
            "current": payload, "build_result": _safe(result), "previous": previous}


def _cas_write_pointer(root: str, payload: Dict[str, Any]) -> None:
    """D8：指针 CAS 写——flock 内重读当前 fencing，落后即拒绝，再原子替换写指针。

    诚实边界：这是**宿主机内的**文件锁 CAS（flock），不跨机；跨机租约仍由 lease_mysql 负责。
    用途是把 `_promote` 的"先读后写"变成"锁内校验+写"，旧主晚到写会被拒绝。
    """
    import fcntl

    lock_path = os.path.join(root, ".pointer.lock")
    with open(lock_path, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            current = read_pointer(root)
            current_fencing = int((current or {}).get("fencing", 0) or 0)
            fencing = int(payload.get("fencing", current_fencing) or 0)
            if current_fencing > fencing:
                raise StaleFencingError(
                    f"fencing {fencing} 落后于当前指针 {current_fencing}：本实例已被接管，拒绝写入")
            _write_pointer(root, payload)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _promote(root: str, fence: FenceState, live: List[Dict[str, Any]], target: str,
             previous: Optional[Dict[str, Any]], result: Any, *,
             fencing: Optional[int], dropped: List[Any], keep_last: int,
             mode: str) -> Dict[str, Any]:
    """把已建好的 target 目录提升为当前快照：校验 fencing → 写指针 → 清理旧快照。

    全量与增量共用这一段：**无论哪条路径，写入前的 fencing 校验都不能省**，
    否则被接管的旧主可以通过"增量"这条路绕开保护。
    """
    current_pointer = read_pointer(root)
    current_fencing = int((current_pointer or {}).get("fencing", 0) or 0)
    if fencing is not None and current_fencing > fencing:
        shutil.rmtree(target, ignore_errors=True)
        raise StaleFencingError(
            f"fencing {fencing} 落后于当前指针 {current_fencing}：本实例已被接管，拒绝写入")

    payload = {"schema": SCHEMA, "dir": target, "generation": fence.generation,
               "fencing": fencing if fencing is not None else current_fencing,
               "documents": len(live), "dropped_revoked": dropped,
               "fingerprint": docs_fingerprint(live),
               "mode": mode,
               "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "previous": (previous or {}).get("dir")}
    _cas_write_pointer(root, payload)

    # 只保留最近 keep_last 个快照目录，避免磁盘无限增长（不删当前指针指向的那个）
    snapshots = sorted(d for d in os.listdir(root) if d.startswith("snapshot-"))
    for stale in snapshots[:-keep_last]:
        path = os.path.join(root, stale)
        if path != target:
            shutil.rmtree(path, ignore_errors=True)
    return payload


def rebuild_delta(root: str, fence: FenceState, docs: Iterable[Dict[str, Any]],
                  apply_fn: Callable[[str, List[str]], Any], *,
                  keep_last: int = 2, fencing: Optional[int] = None) -> Dict[str, Any]:
    """增量重建：**复制上一份快照**再就地应用差异，不重新抽取已存在的内容。

    为什么不在原目录上改：旧快照在切换前还要被读者按 fence 代次读，改它等于边读边写。
    复制的代价是磁盘 IO，而全量重建的代价是**每块都重新过一遍 LLM**——差着数量级。

    为什么必须传 `docs` 全量而不是差异：快照要能自证"我就是当前存活文档的样子"，
    指纹、documents、dropped_revoked 都从全量算；差异由 apply_fn 自己按文本比出来
    （见 HippoRAGEngine.apply_delta），调用方不用拼两份清单，也就不会拼错。

    没有上一份快照时**拒绝**而不是偷偷全量：静默降级会让"增量"这个名字失去意义，
    调用方应当显式走 rebuild()。
    """
    previous = read_pointer(root)
    base_dir = (previous or {}).get("dir")
    if not base_dir or not os.path.isdir(base_dir):
        raise RebuildFailed("没有可复用的上一份快照（或目录不存在），增量重建拒绝执行；"
                            "请先做一次全量重建")

    live = [d for d in docs if not fence.is_revoked(str(d.get("file_id", "")))]
    dropped = [d.get("file_id") for d in docs if fence.is_revoked(str(d.get("file_id", "")))]
    if not live:
        raise RebuildFailed("没有存活文件可重建（全部撤权），拒绝生成空快照")

    stamp = f"{time.strftime('%Y%m%d%H%M%S')}-{time.time_ns() % 1000000:06d}"
    target = os.path.join(root, f"snapshot-{stamp}-g{fence.generation}")
    try:
        shutil.copytree(base_dir, target)          # 目录必须不存在，copytree 会自己建
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(target, ignore_errors=True)
        raise RebuildFailed(f"复制基准快照失败：{type(exc).__name__}: {exc}") from exc

    try:
        result = apply_fn(target, [str(d.get("text", "")) for d in live])
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(target, ignore_errors=True)
        raise RebuildFailed(f"增量应用失败，指针未切换：{type(exc).__name__}: {exc}") from exc

    payload = _promote(root, fence, live, target, previous, result,
                       fencing=fencing, dropped=dropped, keep_last=keep_last,
                       mode="DELTA")
    return {"schema": SCHEMA, "status": "BUILT", "mode": "DELTA",
            "pointer": pointer_path(root), "current": payload,
            "apply_result": _safe(result), "previous": previous}


def rebuild_if_stale(root: str, fence: FenceState, docs: List[Dict[str, Any]],
                     build_fn: Callable[[List[Dict[str, Any]], str], Any],
                     *, fencing: Optional[int] = None) -> Dict[str, Any]:
    """快照已经覆盖当前存活文档就跳过重建。

    多实例场景下这一条很关键：租约让多个实例**串行**，但如果第二个实例进来时
    第一个已经建好了同样的内容，再建一次纯属浪费。所以先比指纹，跳过并说明原因。
    """
    pointer = read_pointer(root)
    fresh = check_freshness(pointer, docs, fence)
    if not fresh["stale"]:
        return {"schema": SCHEMA, "status": "SKIPPED_FRESH", "pointer": pointer,
                "documents": pointer.get("documents")}
    return rebuild(root, fence, docs, build_fn, fencing=fencing)


def rebuild_by_policy(root: str, fence: FenceState, docs: Iterable[Dict[str, Any]],
                      kb_id: str, policy: Any,
                      full_build: Callable[[List[Dict[str, Any]], str], Any],
                      delta_apply: Callable[[str, List[str]], Any], *,
                      keep_last: int = 2, fencing: Optional[int] = None) -> Dict[str, Any]:
    """按灰度策略选 `full` 或 `delta` 重建。

    **没有"delta 失败自动退回 full"**：那会让"配置说的是 delta、实际跑的是 full"变得不可见，
    而灰度最怕的就是"以为在灰度、其实没灰度"。没有基准快照就明确报错，让人先做一次全量。

    返回里带 `requested_mode`（策略要求）与 `effective_mode`（实际执行），两者不等就是 bug。
    """
    mode = policy.mode_for(kb_id)
    if mode == "delta":
        out = rebuild_delta(root, fence, docs, delta_apply,
                            keep_last=keep_last, fencing=fencing)
        out["effective_mode"] = "delta"
    elif mode == "full":
        out = rebuild(root, fence, docs, full_build,
                      keep_last=keep_last, fencing=fencing)
        out["effective_mode"] = "full"
    else:                                   # pragma: no cover - 策略层已校验
        raise RebuildFailed(f"未知的重建模式：{mode!r}（支持 full / delta）")
    out["requested_mode"] = mode
    out["kb_id"] = kb_id
    return out


def _safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return {"type": type(value).__name__}
