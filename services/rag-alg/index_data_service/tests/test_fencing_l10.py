"""P3-L10 · `rebuild.py` 层断言：fencing 单调递增 / 旧主拒绝 / per-kb 锁粒度。

K2 / K3 的**决定性验证**放在这一层（`llmke-v2-toolenv` 可跑，不依赖 fastapi）。

本文件按 TL 13:2x 的要求**先写反例跑红**，重点守一个地雷：
`_cas_write_pointer` 里 `int(payload.get("fencing", current_fencing) or 0)`
—— `payload["fencing"] = None` 时会被算成 **0**，而 `current_fencing >= 1` 时
`current > 0` **恒真** → 全量建图第一次提升就抛 `StaleFencingError`。
所以「首次传 None 必须成功且 fencing >= 1」是守门断言。

`fencing` 语义 = **单调递增序号**，不是重建计数：`floor = fence.generation`，
撤权多次而重建少时会跳变（`max(1,100)+1=101`）。断言只测单调，不测连续。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
IDX = ROOT / "services/rag-alg/index_data_service"
if str(IDX) not in sys.path:
    sys.path.insert(0, str(IDX))

from graph_engine_adapter import rebuild as R  # noqa: E402
from graph_engine_adapter.fence import FenceState  # noqa: E402

DOCS = [{"file_id": "A", "text": "甲"}, {"file_id": "B", "text": "乙"}]


def _build_fn(items, target):
    """最简全量构建：建目录 + 写四件套标记（够 rebuild/_promote 跑通）。"""
    os.makedirs(target, exist_ok=True)
    for name in ("openie_results_ner.json", "sources.json", "kb.json"):
        Path(target, name).write_text("{}", encoding="utf-8")
    return {"chunks": len(items)}


def _apply_fn(target, texts):
    for name in ("openie_results_ner.json", "sources.json", "kb.json"):
        Path(target, name).write_text("{}", encoding="utf-8")
    return {"chunks": len(texts)}


def _pointer(root):
    return json.loads(Path(root, "current.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- K2 守门（or-0 地雷）
def test_k2_first_build_with_none_fencing_succeeds_and_is_positive(tmp_path) -> None:
    """**守门断言**：首次建图传 `fencing=None` 必须成功，且结果 fencing **>= 1**。

    现状（`or 0` 地雷）会得到 `fencing=0`；若照 Q2 字面把 `_default_build` 改成不传，
    第二次提升就会因为 `current(1) > int(None or 0)=0` 被拒 —— 全量建图当场全废。
    """
    root = str(tmp_path / "kb_9")
    out = R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)
    assert out["current"]["fencing"] >= 1
    assert _pointer(root)["fencing"] == out["current"]["fencing"]


def test_k2_pointer_write_with_none_fencing_on_nonzero_current(tmp_path) -> None:
    """`cur=1` + payload `fencing=None` 必须**自增**，不得被当成 0 而拒绝。"""
    root = tmp_path / "kb_9"
    root.mkdir(parents=True)
    snap = root / "snapshot-manual"
    snap.mkdir()
    Path(root, "current.json").write_text(json.dumps({"dir": str(snap), "fencing": 1}),
                                         encoding="utf-8")
    payload = R._cas_write_pointer(str(root), {"dir": str(snap), "fencing": None})
    assert payload["fencing"] == 2
    assert _pointer(str(root))["fencing"] == 2


# --------------------------------------------------------------------------- K2 单调递增
def test_k2_fencing_strictly_increases_across_rebuilds(tmp_path) -> None:
    """反例 R-2：连续两次全量重建，`f2 > f1`（现状两者都是 0/1 → FAIL）。"""
    root = str(tmp_path / "kb_9")
    f1 = R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)["current"]["fencing"]
    f2 = R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)["current"]["fencing"]
    assert f2 > f1
    assert f1 >= 1


def test_k2_delta_also_increments(tmp_path) -> None:
    """FULL 与 DELTA **都**走 `_promote`，两条路径都要严格递增（TL 追加约束）。"""
    root = str(tmp_path / "kb_9")
    f1 = R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)["current"]["fencing"]
    f2 = R.rebuild_delta(root, FenceState(), DOCS, _apply_fn,
                         fencing=None)["current"]["fencing"]
    f3 = R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)["current"]["fencing"]
    assert f1 < f2 < f3


def test_k2_stale_owner_is_rejected(tmp_path) -> None:
    """反例 R-5：旧主（fencing 落后）的写入必须被拒，**相等也拒不了但落后必拒**。"""
    root = str(tmp_path / "kb_9")
    R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)
    latest = R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)["current"]["fencing"]
    assert latest >= 2
    with pytest.raises(R.StaleFencingError):
        R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=latest - 1)


def test_k2_floor_makes_fencing_monotonic_but_not_consecutive(tmp_path) -> None:
    """`floor = fence.generation`：撤权代次领先时 fencing 跳变，但仍严格大于旧值。"""
    root = str(tmp_path / "kb_9")
    fence = FenceState()
    fence.revoke(["X"] * 1)                      # generation = 1
    f1 = R.rebuild(root, fence, DOCS, _build_fn, fencing=None)["current"]["fencing"]
    assert f1 >= fence.generation + 1

    many = FenceState(generation=100, revoked={})
    f2 = R.rebuild(root, many, DOCS, _build_fn, fencing=None)["current"]["fencing"]
    assert f2 > f1
    assert f2 == max(f1, 100) + 1                # 单调但不连续
    assert f2 != f1 + 1


# --------------------------------------------------------------------------- K3 锁粒度
def test_k3_cross_kb_pointer_writes_not_blocked(tmp_path) -> None:
    """反例 R-3：锁必须是 per-kb；持有 kb_A 的锁不得阻塞 kb_B（全局锁 → FAIL）。"""
    a, b = tmp_path / "kb_A", tmp_path / "kb_B"
    for root in (a, b):
        root.mkdir(parents=True)
        (root / "snapshot-manual").mkdir()
    # 在主线程独占 A 的指针锁
    import fcntl

    holder = open(a / ".pointer.lock", "w")
    fcntl.flock(holder, fcntl.LOCK_EX)
    done = {}
    try:
        def write_b():
            t0 = time.perf_counter()
            R._cas_write_pointer(str(b), {"dir": str(b / "snapshot-manual"), "fencing": None})
            done["elapsed"] = time.perf_counter() - t0

        th = threading.Thread(target=write_b)
        th.start()
        th.join(timeout=3)
        assert not th.is_alive(), "B 被 A 的锁阻塞了 → 锁粒度退化成全局"
        assert done["elapsed"] < 1.0
    finally:
        fcntl.flock(holder, fcntl.LOCK_UN)
        holder.close()


def test_k3_same_kb_concurrent_pointer_writes_serialize(tmp_path) -> None:
    """同 kb 两个写者并发 → 指针 fencing **严格**推进到 2，不丢更新。"""
    root = tmp_path / "kb_9"
    root.mkdir(parents=True)
    (root / "snapshot-manual").mkdir()
    seen = []
    errors = []

    def write():
        try:
            payload = R._cas_write_pointer(str(root),
                                           {"dir": str(root / "snapshot-manual"),
                                            "fencing": None})
            seen.append(payload["fencing"])
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=write) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sorted(seen) == [1, 2]                 # 锁内自增 → 两个不同代号
    assert _pointer(str(root))["fencing"] == 2


def test_k3_concurrent_rebuilds_leave_one_complete_snapshot(tmp_path) -> None:
    """并发重建：target 目录天然唯一；最终指针指向**存在且完整**的快照，fencing 严格递增。

    「同 kb 并发会浪费一次建图（后到者胜、前者被 keep_last 清理）」是**已知代价**，不是缺陷。
    """
    root = str(tmp_path / "kb_9")
    R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)
    errors = []

    def run():
        try:
            R.rebuild(root, FenceState(), DOCS, _build_fn, fencing=None)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    pointer = _pointer(root)
    assert pointer["fencing"] >= 3                # 1(基准) + 2 次并发，各自 +1
    snap = Path(pointer["dir"])
    assert snap.is_dir()
    for name in ("openie_results_ner.json", "sources.json", "kb.json"):
        assert (snap / name).is_file(), f"最终快照缺 {name}"


def test_k3_cleanup_never_deletes_building_or_live_dir(tmp_path) -> None:
    """**确定性**验证清理规则（并发用例只能概率命中，这里把规则钉死）：

    - 有 `.building` 标记的目录（另一个写者正在建）不得被"保留 N 个"清理删掉；
    - 指针当前指向的目录不得被删（即使它已不在"最近 N 个"里）。
    """
    root = tmp_path / "kb_9"
    root.mkdir(parents=True)
    old = root / "snapshot-20260101000000-000001-g0"
    live = root / "snapshot-20260101000000-000002-g0"
    building = root / "snapshot-20260101000000-000003-g0"
    target = root / "snapshot-20260101000000-000004-g0"
    for d in (old, live, building, target):
        d.mkdir()
    (building / ".building").write_text("building\n", encoding="utf-8")
    (root / "current.json").write_text(
        json.dumps({"dir": str(live), "fencing": 5}), encoding="utf-8")

    fence = FenceState()
    payload = {"schema": R.SCHEMA, "dir": str(target), "generation": 0,
               "fencing": None, "documents": 1, "dropped_revoked": [],
               "fingerprint": {}, "mode": "FULL", "built_at": "x", "previous": str(live)}
    R._promote(str(root), fence, DOCS, str(target), {"dir": str(live)},
               {"chunks": 1}, fencing=None, dropped=[], keep_last=1, mode="FULL")

    assert target.is_dir(), "本次 target 被自己删了"
    assert building.is_dir(), "在建目录（.building）被清理删掉了"
    assert not old.is_dir(), "最旧的快照应被清理掉（keep_last=1）"
    # 注：`live` 是 promote **之前**的指针；promote 成功后它已不是当前快照，
    # 在 keep_last=1 下被清掉是正确的（回归里会显式确认当前指针目录始终存在）。


def test_r6_protected_regions_untouched() -> None:
    """R-6：禁改区与公开入口仍在；`fence.py` 未新增「重建代次」字段（Q3）。"""
    from graph_engine_adapter.fence import FenceState as FS

    assert set(FS().__dict__) == {"generation", "revoked"}
    assert callable(R.rebuild) and callable(R.rebuild_delta) and callable(R.rebuild_by_policy)
    assert callable(R._cas_write_pointer) and callable(R._promote)
