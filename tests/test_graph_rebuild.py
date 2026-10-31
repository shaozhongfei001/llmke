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
