"""隔离重建：目标目录必须是新的、失败不改指针、只建存活文件。"""

import json
import os

import pytest

from graph_engine_adapter.fence import FenceState
from graph_engine_adapter.rebuild import RebuildFailed, read_pointer, rebuild


def docs(*file_ids):
    return [{"file_id": fid, "text": f"内容-{fid}"} for fid in file_ids]


def test_rebuild_creates_new_snapshot_and_switches_pointer(tmp_path):
    fence = FenceState()
    root = str(tmp_path / "index")
    built = {}

    def build_fn(items, target):
        built["docs"] = [d["file_id"] for d in items]
        built["target"] = target
        os.makedirs(target, exist_ok=True)
        return {"chunks": len(items)}

    out = rebuild(root, fence, docs("333", "329"), build_fn)
    assert built["docs"] == ["333", "329"]
    assert built["target"] == out["current"]["dir"]
    pointer = read_pointer(root)
    assert pointer["generation"] == fence.generation == 0
    assert pointer["documents"] == 2


def test_revoked_files_are_excluded_by_rebuild_itself(tmp_path):
    fence = FenceState()
    fence.revoke(["329"])
    seen = {}

    def build_fn(items, target):
        seen["docs"] = [d["file_id"] for d in items]
        return {}

    out = rebuild(str(tmp_path / "index"), fence, docs("333", "329"), build_fn)
    assert seen["docs"] == ["333"]
    assert out["current"]["dropped_revoked"] == ["329"]
    assert out["current"]["generation"] == fence.generation == 1


def test_failure_keeps_old_pointer_and_cleans_partial_dir(tmp_path):
    root = str(tmp_path / "index")
    fence = FenceState()

    rebuild(root, fence, docs("333"), lambda items, target: {"ok": True})
    first = read_pointer(root)

    def broken(items, target):
        raise RuntimeError("模型炸了")

    with pytest.raises(RebuildFailed):
        rebuild(root, fence, docs("333"), broken)
    assert read_pointer(root) == first                 # 指针没动
    snapshots = [d for d in os.listdir(root) if d.startswith("snapshot-")]
    assert len(snapshots) == 1                          # 失败留下的半成品被清掉


def test_rebuild_refuses_when_everything_revoked(tmp_path):
    fence = FenceState()
    fence.revoke(["333", "329"])
    with pytest.raises(RebuildFailed):
        rebuild(str(tmp_path / "index"), fence, docs("333", "329"), lambda i, t: {})


def test_generation_follows_fence_so_readers_can_compare(tmp_path):
    root = str(tmp_path / "index")
    fence = FenceState()
    rebuild(root, fence, docs("333"), lambda i, t: {})
    fence.revoke(["329"])
    out = rebuild(root, fence, docs("333"), lambda i, t: {})
    assert out["current"]["generation"] == 1
    # 读者拿指针代次与 fence 代次比较即可判断"能不能读"
    assert read_pointer(root)["generation"] == fence.generation


def test_fingerprint_detects_new_file_added_during_rebuild(tmp_path):
    """重建期间新增文件 → 快照 stale（数据缺失，不是越权）。"""
    from graph_engine_adapter.rebuild import check_freshness, docs_fingerprint

    base = docs("333", "329")
    rebuild(str(tmp_path / "idx"), FenceState(), base, lambda i, t: {"ok": 1})
    pointer = read_pointer(str(tmp_path / "idx"))

    fresh = check_freshness(pointer, base)
    assert fresh["stale"] is False

    with_new = base + docs("340")
    stale = check_freshness(pointer, with_new)
    assert stale["stale"] is True and stale["missing"] == ["340"]

    assert docs_fingerprint(base)["digest"] != docs_fingerprint(with_new)["digest"]


def test_fingerprint_detects_content_change(tmp_path):
    from graph_engine_adapter.rebuild import check_freshness

    base = docs("333")
    rebuild(str(tmp_path / "idx"), FenceState(), base, lambda i, t: {"ok": 1})
    pointer = read_pointer(str(tmp_path / "idx"))
    edited = [{"file_id": "333", "text": "内容-333（已改）"}]
    out = check_freshness(pointer, edited)
    assert out["stale"] is True and out["changed"] == ["333"]


def test_missing_pointer_is_stale_not_error():
    from graph_engine_adapter.rebuild import check_freshness
    out = check_freshness(None, docs("333"))
    assert out["stale"] is True and out["reason"] == "NO_POINTER"


def test_freshness_ignores_revoked_files(tmp_path):
    """撤权文件不该被算成"缺失"，否则撤权后每次检查都误报 stale。"""
    from graph_engine_adapter.rebuild import check_freshness

    fence = FenceState()
    all_docs = docs("333", "329")
    rebuild(str(tmp_path / "idx"), fence, all_docs, lambda i, t: {"ok": 1})
    fence.revoke(["329"])
    pointer = read_pointer(str(tmp_path / "idx"))
    assert check_freshness(pointer, all_docs, fence)["stale"] is True   # 还没重建
    rebuild(str(tmp_path / "idx"), fence, all_docs, lambda i, t: {"ok": 1})
    assert check_freshness(read_pointer(str(tmp_path / "idx")), all_docs, fence)["stale"] is False


def test_rebuild_if_stale_skips_when_snapshot_covers_docs(tmp_path):
    from graph_engine_adapter.rebuild import rebuild_if_stale

    fence = FenceState()
    root = str(tmp_path / "idx")
    base = docs("333", "329")
    calls = []

    def build(items, target):
        calls.append(len(items))
        return {"ok": 1}

    first = rebuild_if_stale(root, fence, base, build)
    assert first["status"] == "BUILT" and calls == [2]

    second = rebuild_if_stale(root, fence, base, build)
    assert second["status"] == "SKIPPED_FRESH" and calls == [2]      # 没有第二次构建

    third = rebuild_if_stale(root, fence, base + docs("340"), build)
    assert third["status"] == "BUILT" and calls == [2, 3]


def test_stale_fencing_write_is_rejected_and_pointer_untouched(tmp_path):
    """旧主晚到：fencing 落后于当前指针，写入必须被拒（只靠 TTL 挡不住）。"""
    from graph_engine_adapter.rebuild import StaleFencingError

    root = str(tmp_path / "idx")
    fence = FenceState()
    base = docs("333")

    rebuild(root, fence, base, lambda i, t: {"ok": 1}, fencing=2)
    pointer_before = read_pointer(root)
    assert pointer_before["fencing"] == 2

    with pytest.raises(StaleFencingError):
        rebuild(root, fence, base, lambda i, t: {"ok": 1}, fencing=1)

    assert read_pointer(root) == pointer_before          # 指针没被旧主覆盖


def test_fencing_is_monotonic_and_recorded(tmp_path):
    root = str(tmp_path / "idx")
    fence = FenceState()
    base = docs("333")
    rebuild(root, fence, base, lambda i, t: {"ok": 1}, fencing=5)
    assert read_pointer(root)["fencing"] == 5
    rebuild(root, fence, base, lambda i, t: {"ok": 1}, fencing=6)
    assert read_pointer(root)["fencing"] == 6
    rebuild(root, fence, base, lambda i, t: {"ok": 1}, fencing=6)   # 相同值允许（同一主的重试）
    assert read_pointer(root)["fencing"] == 6
