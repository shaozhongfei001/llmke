"""P4-L13-C · 缺陷 10：撤权必须显式指定 `root`（fail-closed）。

事故背景（evidence `P4-L13C-C3b-C4-INCIDENT-2026081...`）：
`POST /v2/fence/revoke` 原来不带 `root`，18094 只能用它 env 的 `LLMKE_V2_ROOT`
（= **生产** `platform/r12/data/graph-root`）→ 影子测试的撤权写进了**生产** `fence.json`。

修法（TL 19:5x）：`root` **必填**；缺失 → **400 + 明确 detail**，且**不得写任何 fence.json**。
为什么必填而不是可选：默认落到 env 就是这次事故的成因，可选会让任何调用方漏传时再写一次生产。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="llmke-v2-toolenv 无 fastapi（既有环境限制）")
pytest.importorskip("pydantic", reason="同上")

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "services/rag-alg/index_data_service"
if str(IDX) not in sys.path:
    sys.path.insert(0, str(IDX))

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter import api as A  # noqa: E402


def _root_with_snapshot(tmp: Path, kb: str = "kb_9") -> tuple[Path, Path]:
    """造一个 `<root>/<kb>/current.json → 快照目录` 的布局。"""
    root = tmp / "graph-root"
    snap = root / kb / "snapshot-test-g0"
    snap.mkdir(parents=True)
    (snap / "sources.json").write_text("{}", encoding="utf-8")
    (root / kb / "current.json").write_text(
        json.dumps({"dir": str(snap), "generation": 0}), encoding="utf-8")
    return root, snap


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """把进程 env 的 root 指到一个**受控临时目录**：这样「是否误写」可断言。"""
    env_root, snap = _root_with_snapshot(tmp_path)
    monkeypatch.setenv("LLMKE_V2_ROOT", str(env_root))
    return TestClient(A.create_app(delta_runner=lambda req: {"status": "BUILT"})), env_root, snap


# --------------------------------------------------------------- 反例：不带 root
def test_revoke_without_root_is_400_and_writes_nothing(client):
    cli, env_root, snap = client
    resp = cli.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["291"]})

    assert resp.status_code == 400, f"缺失 root 必须 400，实际 {resp.status_code}: {resp.text}"
    detail = json.dumps(resp.json(), ensure_ascii=False)
    assert "root" in detail, "detail 必须明写「revoke 必须显式指定 root」"
    assert not (snap / "fence.json").exists(), (
        "缺 root 时**不得**回落到 env root 写盘 —— 那正是生产被污染的路径")


def test_revoke_with_blank_root_is_400(client):
    cli, _env_root, snap = client
    resp = cli.post("/v2/fence/revoke", json={"kb": "kb_9", "file_ids": ["291"], "root": "   "})
    assert resp.status_code == 400
    assert not (snap / "fence.json").exists()


# --------------------------------------------------------------- 正例：带 root
def test_revoke_with_root_writes_only_that_root(client, tmp_path):
    cli, env_root, env_snap = client
    other_root, other_snap = _root_with_snapshot(tmp_path / "shadow", kb="kb_9")

    resp = cli.post("/v2/fence/revoke",
                    json={"kb": "kb_9", "file_ids": ["291"], "root": str(other_root)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["revoked"] == ["291"]
    assert body["persisted"] is True

    written = other_snap / "fence.json"
    assert written.is_file(), "指定的 root 下必须落盘"
    assert json.loads(written.read_text(encoding="utf-8"))["revoked"].get("291")
    assert not (env_snap / "fence.json").exists(), "env root 下不得被写（这就是事故的重演）"

# --------------------------------------------------------------- 缺陷 12：影子构建不得改本进程 kb 槽
def test_shadow_build_does_not_rewrite_process_slot(tmp_path, monkeypatch):
    """`graph_build`/`graph_delta` 原来**无条件**把 `slot["snapshot"]/["fence"]` 改成
    本次响应的快照 —— 影子构建会把 18094 对生产 kb 的内存槽指向影子快照
    （实测：影子撤权后 `GET /v2/fence?kb=kb_9` 显示 `revoked=["291"]`，而生产文件是空的）。

    隔离要求：写别的 root 时**不得**动本进程的库槽。
    """
    env_root, env_snap = _root_with_snapshot(tmp_path)
    monkeypatch.setenv("LLMKE_V2_ROOT", str(env_root))

    shadow_root, shadow_snap = _root_with_snapshot(tmp_path / "shadow", kb="kb_9")
    (shadow_snap / "fence.json").write_text(
        json.dumps({"generation": 1, "revoked": {"291": {"generation": 1}}}), encoding="utf-8")

    def runner(req):
        return {"schema": "x", "status": "BUILT", "kb": "kb_9", "effective_mode": "DELTA",
                "snapshot": str(shadow_snap), "root": str(shadow_root / "kb_9")}

    cli = TestClient(A.create_app(delta_runner=runner))
    resp = cli.post("/v2/graph/delta", json={"kb": "kb_9", "docs": [{"file_ids": ["290"], "text": "x"}],
                                             "root": str(shadow_root)})
    assert resp.status_code == 200, resp.text

    fence = cli.get("/v2/fence?kb=kb_9").json()
    assert fence["count"] == 0, (
        f"影子构建后本进程的 kb 槽被改成了影子 fence：{fence}（生产视图会显示影子的撤权）")

# --------------------------------------------------------------- 同一判断，一处实现
@pytest.mark.parametrize("suffix", ["", "/", "/./", "//"])
def test_is_own_root_matches_realpath_rule(client, suffix):
    """`_is_own_root` 必须与「realpath 相等」这条规则逐点一致（含尾斜杠等写法）。"""
    _cli, env_root, _snap = client
    target = str(env_root) + suffix
    assert A._is_own_root(target) is True


def test_is_own_root_rejects_other_root(client, tmp_path):
    _cli, _env_root, _snap = client
    other, _ = _root_with_snapshot(tmp_path / "other", kb="kb_9")
    assert A._is_own_root(str(other)) is False


def test_revoke_memory_flag_uses_same_rule(client, tmp_path):
    """行为级：写 env root → `applied_to_memory=true`；写别的 root → `false`。

    这两个值由 `_is_own_root` 决定（本 loop 统一过）；若将来有人只改 revoke 那行，
    这条会红。
    """
    cli, env_root, _env_snap = client
    other, _ = _root_with_snapshot(tmp_path / "shadow", kb="kb_9")

    own = cli.post("/v2/fence/revoke",
                   json={"kb": "kb_9", "file_ids": ["290"], "root": str(env_root)}).json()
    assert own["applied_to_memory"] is True

    alien = cli.post("/v2/fence/revoke",
                     json={"kb": "kb_9", "file_ids": ["291"], "root": str(other)}).json()
    assert alien["applied_to_memory"] is False

def test_own_root_rule_has_single_implementation():
    """静态断言：同一判断只允许一份实现（防「只改一边」造成两套语义）。"""
    src = Path(A.__file__).read_text(encoding="utf-8")
    assert "applied_to_memory = _is_own_root(root)" in src, "revoke 必须复用 _is_own_root"
    assert "os.path.realpath(root) == os.path.realpath(_root_dir())" not in src, (
        "不得再出现第二份 realpath 比较实现")
