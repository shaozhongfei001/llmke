"""D8 第一版：fence 持久化、query 撤权过滤、指针 CAS 发布。"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "services" / "rag-alg" / "index_data_service"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_engine_adapter.fence import FENCE_FILE, FenceState
from graph_engine_adapter.rebuild import StaleFencingError  # noqa: E402
from graph_engine_adapter.rebuild import read_pointer, rebuild  # noqa: E402


def _fake_build(items, target):
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "x.txt"), "w", encoding="utf-8") as fh:
        fh.write("1")
    return {"chunks": 1}


LIVE = [{"file_id": "f1", "text": "t", "locator": "p1", "title": "t"}]


def test_stale_fencing_rejected(tmp_path):
    r1 = rebuild(str(tmp_path), FenceState(), LIVE, _fake_build, fencing=2)
    assert read_pointer(str(tmp_path))["fencing"] == 2
    # 旧主晚到：fencing 落后 → 拒绝且不覆盖指针
    with pytest.raises(StaleFencingError):
        rebuild(str(tmp_path), FenceState(), LIVE, _fake_build, fencing=1)
    assert read_pointer(str(tmp_path))["dir"] == r1["current"]["dir"]


def test_same_fencing_serialized_last_wins(tmp_path):
    r1 = rebuild(str(tmp_path), FenceState(), LIVE, _fake_build, fencing=3)
    r2 = rebuild(str(tmp_path), FenceState(), LIVE, _fake_build, fencing=3)
    assert read_pointer(str(tmp_path))["dir"] == r2["current"]["dir"]
    assert read_pointer(str(tmp_path))["dir"] != r1["current"]["dir"]


def test_fence_roundtrip_file(tmp_path):
    f = FenceState()
    f.revoke(["r9"], reason="REVOKED")
    p = str(tmp_path / FENCE_FILE)
    f.save(p)
    g = FenceState.load(p)
    assert g.generation == 1 and g.is_revoked("r9")
    assert g.revoked["r9"]["reason"] == "REVOKED"
