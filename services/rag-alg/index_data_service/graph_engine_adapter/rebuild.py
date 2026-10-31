"""隔离快照重建编排：撤权 → 用存活文件建新快照 → 提升代次 → 切读。

为什么要有编排而不是"手工跑一遍重建"：
- 重建的**目标目录必须是新的**（隔离快照），不能原地改旧索引——旧索引在重建期间还要能被
  fence 拦着读；
- 切换必须**原子**：先写好指针文件，再让读者看到；失败时指针不变，旧索引继续（被 fence 挡着）；
- 代次必须单调：新快照的代次 == 重建时 fence 的代次，读者据此判断"够不够新"。

`build_fn(docs, target_dir)` 由调用方注入（真实实现用 HippoRAGEngine + save_dir），
测试用假实现即可验证编排顺序与失败语义。
"""

import json
import os
import shutil
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from .fence import FenceState

SCHEMA = "llmke.graph-engine.rebuild.v1"


class RebuildFailed(RuntimeError):
    pass


def pointer_path(root: str) -> str:
    return os.path.join(root, "current.json")


def read_pointer(root: str) -> Optional[Dict[str, Any]]:
    path = pointer_path(root)
    if not os.path.isfile(path):
        return None
    return json.loads(open(path, encoding="utf-8").read())


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
            keep_last: int = 2) -> Dict[str, Any]:
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

    payload = {"schema": SCHEMA, "dir": target, "generation": fence.generation,
               "documents": len(live), "dropped_revoked": dropped,
               "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "previous": (previous or {}).get("dir")}
    pointer = _write_pointer(root, payload)

    # 只保留最近 keep_last 个快照目录，避免磁盘无限增长（不删当前指针指向的那个）
    snapshots = sorted(d for d in os.listdir(root) if d.startswith("snapshot-"))
    for stale in snapshots[:-keep_last]:
        path = os.path.join(root, stale)
        if path != target:
            shutil.rmtree(path, ignore_errors=True)

    return {"schema": SCHEMA, "pointer": pointer, "current": payload,
            "build_result": _safe(result),
            "previous": previous}


def _safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return {"type": type(value).__name__}
