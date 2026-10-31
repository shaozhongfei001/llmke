"""增量重建：复制上一份快照 → 就地应用差异 → 原子切指针。

这一组钉住的都是"省时间不能省正确性"的地方：
- 基准快照被复制而不是原地改（否则读者会读到边改边读的目录）；
- 没有基准快照时**拒绝**，不偷偷降级成全量（否则"增量"这两个字就没有意义了）；
- 增量路径同样要过 fencing 校验（被接管的旧主不能从这条路绕进写入）；
- apply 失败时指针不动、半成品目录不留下。
"""

import json
import os

import pytest

from graph_engine_adapter.fence import FenceState
from graph_engine_adapter.rebuild import (RebuildFailed, StaleFencingError, read_pointer,
                                          rebuild, rebuild_delta)


def docs(*items):
    return [{"file_id": fid, "text": text} for fid, text in items]


def full_build(live, target):
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "graph.json"), "w", encoding="utf-8") as fh:
        json.dump({"chunks": [d["text"] for d in live]}, fh)
    return {"chunks": len(live)}


def make_base(tmp_path):
    fence = FenceState()
    out = rebuild(str(tmp_path), fence, docs(("1", "a"), ("2", "b")), full_build, fencing=1)
    return fence, out


def test_delta_copies_base_and_applies_texts(tmp_path):
    fence, base = make_base(tmp_path)
    seen = {}

    def apply_fn(target, texts):
        seen["target"] = target
        seen["texts"] = list(texts)
        # 复制过来的基准文件必须已经在新目录里
        seen["seeded"] = os.path.isfile(os.path.join(target, "graph.json"))
        return {"deleted": 1, "added": 2}

    out = rebuild_delta(str(tmp_path), fence, docs(("1", "a"), ("2", "c")),
                        apply_fn, fencing=1)

    assert seen["seeded"] is True
    assert seen["texts"] == ["a", "c"]          # 全量存活文本交给 apply 自己算差异
    assert out["mode"] == "DELTA"
    pointer = read_pointer(str(tmp_path))
    assert pointer["mode"] == "DELTA"
    assert pointer["documents"] == 2
    assert pointer["dir"] != base["current"]["dir"]
    # 基准目录保持原样（不能被原地改）
    assert os.path.isfile(os.path.join(base["current"]["dir"], "graph.json"))


def test_delta_without_base_snapshot_is_refused(tmp_path):
    fence = FenceState()
    with pytest.raises(RebuildFailed) as excinfo:
        rebuild_delta(str(tmp_path), fence, docs(("1", "a")), lambda t, x: {})
    assert "没有可复用的上一份快照" in str(excinfo.value)
    assert read_pointer(str(tmp_path)) is None


def test_delta_failure_keeps_pointer_and_removes_target(tmp_path):
    fence, base = make_base(tmp_path)
    before = read_pointer(str(tmp_path))

    def boom(target, texts):
        raise RuntimeError("引擎删除失败")

    with pytest.raises(RebuildFailed) as excinfo:
        rebuild_delta(str(tmp_path), fence, docs(("1", "a")), boom, fencing=1)

    assert "指针未切换" in str(excinfo.value)
    assert read_pointer(str(tmp_path)) == before
    # 半成品目录必须清掉，否则下次 copytree 或磁盘都会被污染
    leftovers = [d for d in os.listdir(str(tmp_path))
                 if d.startswith("snapshot-") and d != os.path.basename(before["dir"])]
    assert leftovers == []


def test_delta_rejects_stale_fencing(tmp_path):
    """被接管的旧主不能靠"增量"绕开保护：校验点必须在写指针之前。"""
    fence, base = make_base(tmp_path)
    with pytest.raises(StaleFencingError):
        rebuild_delta(str(tmp_path), fence, docs(("1", "a")), lambda t, x: {}, fencing=0)
    assert read_pointer(str(tmp_path))["dir"] == base["current"]["dir"]


def test_delta_excludes_revoked_files(tmp_path):
    fence, base = make_base(tmp_path)
    fence.revoke("2")
    seen = {}

    def apply_fn(target, texts):
        seen["texts"] = list(texts)
        return {"deleted": 1}

    out = rebuild_delta(str(tmp_path), fence, docs(("1", "a"), ("2", "b")),
                        apply_fn, fencing=1)
    assert seen["texts"] == ["a"]                 # 撤权文件不进快照
    assert out["current"]["dropped_revoked"] == ["2"]


def test_delta_generation_matches_fence(tmp_path):
    fence, base = make_base(tmp_path)
    fence.revoke("2")                             # 撤权推进代次
    out = rebuild_delta(str(tmp_path), fence, docs(("1", "a")),
                        lambda t, x: {"deleted": 0}, fencing=1)
    assert out["current"]["generation"] == fence.generation


def test_delta_all_revoked_is_refused(tmp_path):
    fence, base = make_base(tmp_path)
    fence.revoke("1")
    fence.revoke("2")
    with pytest.raises(RebuildFailed) as excinfo:
        rebuild_delta(str(tmp_path), fence, docs(("1", "a"), ("2", "b")),
                      lambda t, x: {}, fencing=1)
    assert "拒绝生成空快照" in str(excinfo.value)
