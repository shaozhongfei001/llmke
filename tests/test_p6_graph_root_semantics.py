"""P6-L17 设计判定的可复跑依据：`graph_root` 语义与 B-2 根因。

对应 `STEP2-L` 的判定（技术判定由 integration-agent 给出，可推翻）：
  D-1 `graph_root` 是容纳多库的落盘根/环境命名空间，实际落点 `<root>/<kb>`；
      `kb` 才是「一个库」。两者不得混用。
  D-2 「按库检索」由 `kb` 解析，且 `_resolve_snapshot` 原生支持 `root` 参数；
      B-2 的根因是 18094 未设 `LLMKE_V2_ROOT`，**不是** `QueryRequest` 缺字段。
  D-3 因此否决「`QueryRequest` 增 root」，采用重启 18094 设 `LLMKE_V2_ROOT`。

纯单元测试：只用 tmp_path 构造图根，不依赖本机生产路径、不碰任何服务。
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi", reason="需 fastapi/pydantic")


def _make_kb(root, kb: str, snap_name: str):
    kb_dir = root / kb
    kb_dir.mkdir(parents=True)
    snap = kb_dir / snap_name
    snap.mkdir()
    (kb_dir / "current.json").write_text(json.dumps({
        "schema": "llmke.graph-engine.rebuild.v1", "dir": str(snap),
        "generation": 0, "fencing": 1, "documents": 0,
        "fingerprint": {"files": [], "per_file": {}, "digest": ""},
        "mode": "FULL"}), encoding="utf-8")
    return snap


def test_d1_actual_landing_point_is_root_plus_kb():
    from graph_engine_adapter.delta_build import _kb_root

    assert _kb_root("kb_9", root="/env/graph-root") == "/env/graph-root/kb_9"
    assert _kb_root("kb_1004", root="/env/graph-root") == "/env/graph-root/kb_1004"


def test_d1_one_graph_root_holds_multiple_kbs(tmp_path, monkeypatch):
    root = tmp_path / "graph-root"
    snap9 = _make_kb(root, "kb_9", "snap-9")
    snap1004 = _make_kb(root, "kb_1004", "snap-1004")
    monkeypatch.setenv("LLMKE_V2_ROOT", str(root))
    monkeypatch.delenv("LLMKE_V2_SNAPSHOT", raising=False)

    from graph_engine_adapter.api import _resolve_snapshot

    assert _resolve_snapshot("kb_9") == str(snap9)
    assert _resolve_snapshot("kb_1004") == str(snap1004)


def test_d2_missing_root_reproduces_not_built(tmp_path, monkeypatch):
    """不设 LLMKE_V2_ROOT → 按库指针解析失败（B-2 根因）。

    反证：此时给 QueryRequest 加 root 也无济于事 —— 缺的是服务端图根配置。
    """
    single = tmp_path / "single-snapshot"   # 无 kb.json 归属标记
    single.mkdir()
    monkeypatch.delenv("LLMKE_V2_ROOT", raising=False)
    monkeypatch.setenv("LLMKE_V2_SNAPSHOT", str(single))

    from graph_engine_adapter.api import _resolve_snapshot

    assert _resolve_snapshot("kb_9") is None


def test_d2_kb_ownership_prevents_cross_kb_fallback(tmp_path, monkeypatch):
    """单快照回退必须校验 kb.json 归属 —— 领域范围由 kb 界定，不是 root。"""
    single = tmp_path / "single-snapshot"
    single.mkdir()
    (single / "kb.json").write_text(json.dumps({"kb_id": "kb_1004"}),
                                    encoding="utf-8")
    monkeypatch.delenv("LLMKE_V2_ROOT", raising=False)
    monkeypatch.setenv("LLMKE_V2_SNAPSHOT", str(single))

    from graph_engine_adapter.api import _resolve_snapshot

    assert _resolve_snapshot("kb_9") is None
    assert _resolve_snapshot("kb_1004") == str(single)
