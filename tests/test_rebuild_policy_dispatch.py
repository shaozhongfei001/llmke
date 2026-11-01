"""按灰度策略分派重建：delta/full 必须与实际执行一致，且**不许静默回退**。

灰度最怕的不是"没灰度上"，而是"以为在灰度、其实没灰度"——所以这里钉的是
`requested_mode` 与 `effective_mode` 必须相等，以及"请求 delta 但没有基准快照"时
明确报错，而不是偷偷做一次全量。
"""

import json
import os

import pytest

from graph_engine_adapter.fence import FenceState
from graph_engine_adapter.rebuild import (RebuildFailed, read_pointer,
                                          rebuild, rebuild_by_policy)


class StubPolicy:
    def __init__(self, mode):
        self.mode = mode

    def mode_for(self, kb_id):
        return self.mode


def docs(*pairs):
    return [{"file_id": fid, "text": text} for fid, text in pairs]


def full_build(live, target):
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "graph.json"), "w", encoding="utf-8") as fh:
        json.dump({"chunks": [d["text"] for d in live]}, fh)
    return {"chunks": len(live)}


def delta_apply(target, texts):
    with open(os.path.join(target, "graph.json"), "w", encoding="utf-8") as fh:
        json.dump({"chunks": list(texts)}, fh)
    return {"chunks": len(texts)}


def test_delta_mode_runs_delta(tmp_path):
    fence = FenceState()
    rebuild(str(tmp_path), fence, docs(("1", "a")), full_build, fencing=1)
    out = rebuild_by_policy(str(tmp_path), fence, docs(("1", "a"), ("2", "b")),
                            "kb-1", StubPolicy("delta"), full_build, delta_apply, fencing=1)
    assert out["requested_mode"] == "delta" == out["effective_mode"]
    assert read_pointer(str(tmp_path))["mode"] == "DELTA"
    assert out["kb_id"] == "kb-1"


def test_full_mode_runs_full(tmp_path):
    fence = FenceState()
    out = rebuild_by_policy(str(tmp_path), fence, docs(("1", "a")),
                            "kb-2", StubPolicy("full"), full_build, delta_apply, fencing=1)
    assert out["requested_mode"] == "full" == out["effective_mode"]
    assert read_pointer(str(tmp_path))["mode"] == "FULL"


def test_delta_without_base_is_refused_not_silently_full(tmp_path):
    """没有基准快照时必须报错：偷偷跑全量会让"灰度到底跑没跑"变成一笔糊涂账。"""
    fence = FenceState()
    with pytest.raises(RebuildFailed):
        rebuild_by_policy(str(tmp_path), fence, docs(("1", "a")),
                          "kb-1", StubPolicy("delta"), full_build, delta_apply, fencing=1)
    assert read_pointer(str(tmp_path)) is None


def test_unknown_mode_is_refused(tmp_path):
    fence = FenceState()
    with pytest.raises(RebuildFailed) as excinfo:
        rebuild_by_policy(str(tmp_path), fence, docs(("1", "a")),
                          "kb-1", StubPolicy("canary-ish"), full_build, delta_apply)
    assert "未知的重建模式" in str(excinfo.value)
