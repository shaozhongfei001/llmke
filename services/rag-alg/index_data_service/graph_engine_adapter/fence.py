"""撤权 fence：文件被撤权后，**旧索引在重建完成前也不能再被读到**。

设计原文（§5）："首版可通过新隔离快照全量重建支持文档删除；在新索引完成前撤权 fence
必须先阻止旧索引读取。" 顺序很重要——先挡读，再重建；反过来会有一个窗口把已撤权内容返回给用户。

这里实现平台侧最小可用的三件事：
1. `revoke()` 让文件的可见性立刻失效，并推进"代次"（generation）；
2. `filter_hits()` 在检索结果回来之后**再过一遍**：引擎不认识撤权，它照样可能返回旧内容；
3. `assert_index_fresh()` 在进入检索前检查索引代次：索引比 fence 旧就直接拒绝，而不是"尽量过滤"。

第 3 条是关键：只靠第 2 条过滤，等于默认引擎一定会把撤权内容吐出来让我们拦；
一旦引擎换了行为（比如做缓存），这个假设就不成立了。
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


class StaleIndexError(RuntimeError):
    """索引代次落后于撤权代次：必须先重建，不允许继续读。"""


@dataclass
class FenceState:
    generation: int = 0
    revoked: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def revoke(self, file_ids: Iterable[str], reason: str = "REVOKED") -> int:
        """撤权并推进代次；重复撤权幂等（不重复推进）。"""
        changed = False
        for fid in file_ids:
            if fid not in self.revoked:
                self.revoked[fid] = {"reason": reason, "generation": self.generation + 1}
                changed = True
        if changed:
            self.generation += 1
        return self.generation

    def is_revoked(self, file_id: str) -> bool:
        return str(file_id) in self.revoked

    def live(self, file_ids: Iterable[str]) -> Set[str]:
        return {str(f) for f in file_ids if not self.is_revoked(str(f))}

    def snapshot(self) -> Dict[str, Any]:
        return {"generation": self.generation, "revoked": dict(self.revoked)}

    @classmethod
    def restore(cls, data: Optional[Dict[str, Any]]) -> "FenceState":
        """从 snapshot() 的字典恢复；None/坏数据 → 空 fence（fail-closed 由 assert_index_fresh 保证）。"""
        if not isinstance(data, dict):
            return cls()
        try:
            return cls(generation=int(data.get("generation", 0)),
                       revoked=dict(data.get("revoked") or {}))
        except Exception:  # noqa: BLE001
            return cls()

    def save(self, path: str) -> None:
        """持久化到快照目录 fence.json（原子替换，读者不会看到写一半的 fence）。"""
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.snapshot(), fh, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str) -> "FenceState":
        """读 fence.json；不存在/损坏 → 空 fence（不抛，交由调用方按"未知"处理）。"""
        try:
            with open(path, encoding="utf-8") as fh:
                return cls.restore(json.load(fh))
        except Exception:  # noqa: BLE001
            return cls()


FENCE_FILE = "fence.json"


def assert_index_fresh(index_generation: Optional[int], fence: FenceState) -> None:
    """索引代次低于 fence 代次 → 拒绝读。没给代次按"未知"处理，同样拒绝。"""
    if index_generation is None:
        raise StaleIndexError("索引未声明代次，无法确认是否已包含撤权，拒绝读取")
    if index_generation < fence.generation:
        raise StaleIndexError(
            f"索引代次 {index_generation} 落后于撤权代次 {fence.generation}：请先用隔离快照重建")


class SupersededSnapshotError(RuntimeError):
    """快照的 fencing 低于读者认定的当前值：这份快照是**已被接管的旧主**产出的。

    与 StaleIndexError 的区别：
    - StaleIndexError 说的是"代次不够，可能含已撤权内容"（安全语义，必须拦）；
    - 本错误说的是"这份快照来自上一轮领导权"（新鲜度语义）。
    内容本身未必有错（旧主写入已被 fencing 拒绝），所以这条校验**默认关闭**，
    由能拿到当前 fencing 的调用方显式开启——大多数读者手里没有租约，开不了。
    """


def assert_snapshot_not_superseded(snapshot_fencing: Optional[int],
                                   min_fencing: Optional[int]) -> None:
    """读者侧（可选）校验：快照 fencing 不得落后于 `min_fencing`。

    - `min_fencing is None` → 不校验（默认行为，保持兼容）；
    - 快照没记 fencing（老快照）且要求校验 → 拒绝，不猜；
    - 落后 → 拒绝，并给出"谁该负责"的提示。
    """
    if min_fencing is None:
        return
    if snapshot_fencing is None:
        raise SupersededSnapshotError(
            f"快照未记录 fencing，无法确认不是被接管的旧主产出（要求 >= {min_fencing}）")
    if int(snapshot_fencing) < int(min_fencing):
        raise SupersededSnapshotError(
            f"快照 fencing {snapshot_fencing} 落后于当前 {min_fencing}："
            "这份快照来自上一轮领导权，请等当前实例重建后再读")


def filter_hits(hits: Sequence[Dict[str, Any]], fence: FenceState) -> Dict[str, Any]:
    """按来源过滤：一个命中只要还有**未撤权**来源就保留，并把这些来源裁掉。"""
    kept, dropped = [], []
    for hit in hits or []:
        sources = hit.get("sources") or []
        alive = [s for s in sources if not fence.is_revoked(s.get("file_id", ""))]
        if alive:
            kept.append({**hit, "sources": alive})
        else:
            dropped.append({"text": (hit.get("text") or "")[:40],
                            "sources": [s.get("file_id") for s in sources],
                            "reason": "ALL_SOURCES_REVOKED"})
    return {"hits": kept, "dropped": dropped}


def revoked_visible_leak(results: Sequence[Dict[str, Any]], fence: FenceState) -> List[str]:
    """自检：结果里是否还残留撤权来源。返回泄漏点，空表示干净。"""
    leaks = []
    for item in results:
        for src in item.get("sources") or []:
            fid = str(src.get("file_id", ""))
            if fid and fence.is_revoked(fid):
                leaks.append(f"{item.get('query', '')}:{fid}")
    return leaks
