"""构建期可见集合隔离：不该看到的，**压根不在那份索引里**。

这里只测规划/路由（纯函数）：真跑两份索引见证据文档。
关键判据是 fail-closed——范围查不到时必须拒绝，而不是回退到全量索引。
"""

import json
import os

from graph_engine_adapter import partition


def doc(fid, visibility=None):
    d = {"file_id": fid, "chunks": [{"text": fid + "-1"}, {"text": fid + "-2"}]}
    if visibility is not None:
        d["visibility"] = visibility
    return d


def test_public_is_visible_everywhere():
    plan = partition.build_plan([doc("a")], ["dept-a", "dept-b"])
    assert [d["file_id"] for d in plan["dept-a"]] == ["a"]
    assert [d["file_id"] for d in plan["dept-b"]] == ["a"]


def test_scoped_doc_only_in_its_scope():
    plan = partition.build_plan([doc("pub"), doc("secret", ["dept-b"])], ["dept-a", "dept-b"])
    assert [d["file_id"] for d in plan["dept-a"]] == ["pub"]
    assert sorted(d["file_id"] for d in plan["dept-b"]) == ["pub", "secret"]


def test_visibility_can_be_read_from_metadata():
    d = {"file_id": "x", "chunks": [], "metadata": {"visibility": "dept-c"}}
    assert partition.doc_visibility(d) == ["dept-c"]


def test_summarize_counts_exclusive_and_shared():
    plan = partition.build_plan([doc("pub"), doc("secret", ["dept-b"])],
                                ["dept-a", "dept-b"])
    s = partition.summarize(plan)
    assert s["exclusive_documents"] == 1      # secret 只在一个范围
    assert s["shared_documents"] == 1         # pub 在两个范围
    assert s["scopes"]["dept-b"]["chunks"] == 2   # 两份文档各 1 条（docs 已按块展开）
    assert s["scopes"]["dept-b"]["documents"] == 2


def test_scope_dir_is_traversal_safe():
    evil = partition.scope_dir("/root", "../../etc")
    assert ".." not in os.path.normpath(evil).replace("/root", "")
    assert evil.startswith("/root/scopes/")


def test_resolve_is_fail_closed(tmp_path):
    """查不到范围必须返回 None——回退到默认索引等于把隔离作废。"""
    assert partition.resolve(str(tmp_path), "dept-a") is None


def test_manifest_roundtrip_and_stale_snapshot(tmp_path):
    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    path = partition.write_manifest(str(tmp_path), {
        "dept-a": {"snapshot": str(snapshot), "documents": 2}})
    assert os.path.isfile(path)
    assert partition.resolve(str(tmp_path), "dept-a")["documents"] == 2
    snapshot.rmdir()                            # 快照被清理
    assert partition.resolve(str(tmp_path), "dept-a") is None


def test_unknown_scope_is_not_widened(tmp_path):
    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    partition.write_manifest(str(tmp_path), {"dept-a": {"snapshot": str(snapshot)}})
    assert partition.resolve(str(tmp_path), "dept-z") is None


def test_worker_load_docs_preserves_visibility(tmp_path):
    """可见范围要在读取阶段就带下来；丢了它 --scope 会把所有人当 public。"""
    import importlib.util

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "worker_mod", os.path.join(repo, "scripts", "v2_graph_worker.py"))
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)

    payload = tmp_path / "p.json"
    payload.write_text(json.dumps({"chunks": [
        {"page_content": "公开块", "metadata": {"file_id": "a"}},
        {"page_content": "机密块", "metadata": {"file_id": "b", "visibility": ["dept-b"]}},
    ]}, ensure_ascii=False), encoding="utf-8")

    docs = worker.load_docs([str(payload)])
    plan = partition.build_plan(docs, ["dept-a"])
    assert [d["text"] for d in plan["dept-a"]] == ["公开块"]


def test_manifest_stores_absolute_snapshot(tmp_path, monkeypatch):
    """清单是给**另一个进程**读的：存相对路径时它的 cwd 未必相同，
    解析失败会被误认为“该范围本来就查不到”，极难排查。"""
    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    partition.write_manifest(str(root), {"dept-a": {"snapshot": "relative/snap"}})
    data = json.loads((root / "scopes.json").read_text(encoding="utf-8"))
    assert os.path.isabs(data["scopes"]["dept-a"]["snapshot"])


def test_resolve_handles_legacy_relative_manifest(tmp_path, monkeypatch):
    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    legacy = {"schema": partition.SCHEMA,
              "scopes": {"dept-a": {"snapshot": str(snapshot)}}}
    (root / "scopes.json").write_text(json.dumps(legacy), encoding="utf-8")
    assert partition.resolve(str(root), "dept-a")["snapshot"] == str(snapshot)
