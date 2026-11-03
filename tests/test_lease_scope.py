"""租约粒度：全局单租约 vs 每知识库一个租约。

kb 粒度让不同库并行重建互不阻塞；代价是它们会同时写盘，所以 root 必须分目录。
这两条都是"配置错了不会报错、只会在生产上互相踩"的类型，必须用测试钉住。
"""

import importlib.util
import os
from types import SimpleNamespace

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "worker", os.path.join(REPO, "scripts", "v2_graph_worker.py"))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)

from graph_engine_adapter.lease import FileLease  # noqa: E402


def args(**over):
    base = dict(lease_key="rebuild", lease_scope="global", kb_id="kb_1",
                root="/srv/root/{kb}", lease="/srv/locks/rebuild.lock")
    base.update(over)
    return SimpleNamespace(**base)


def test_global_scope_keeps_single_key():
    assert worker.resolve_lease_key(args()) == "rebuild"


def test_kb_scope_namespaces_key():
    assert worker.resolve_lease_key(args(lease_scope="kb")) == "rebuild:kb_1"
    assert worker.resolve_lease_key(args(lease_scope="kb", kb_id="kb_2")) == "rebuild:kb_2"


def test_kb_scope_requires_placeholder_root():
    """两个库共用一个 root 会互相覆盖快照——宁可启动失败，也不要静默踩。"""
    with pytest.raises(SystemExit) as exc:
        worker.resolve_lease_key(args(lease_scope="kb", root="/srv/root"))
    assert "{kb}" in str(exc.value)


def test_kb_scoped_file_leases_are_independent(tmp_path):
    """不同库的租约落不同文件：同一个文件里换 key 等于没隔离（mkdir 互斥）。"""
    a = FileLease(str(tmp_path / "kb_1.lock"), owner="A", ttl=30)
    b = FileLease(str(tmp_path / "kb_2.lock"), owner="B", ttl=30)
    assert a.acquire()["acquired"] is True
    assert b.acquire()["acquired"] is True        # 互不阻塞
    assert a.acquire()["acquired"] is True        # 自己重入
    assert b.acquire()["acquired"] is True
    a.release()
    b.release()


def test_same_file_lease_still_blocks(tmp_path):
    """对照组：同一文件就是互斥，别把“隔离”当成“租约失效”。"""
    a = FileLease(str(tmp_path / "same.lock"), owner="A", ttl=30)
    b = FileLease(str(tmp_path / "same.lock"), owner="B", ttl=30)
    assert a.acquire()["acquired"] is True
    assert b.acquire()["acquired"] is False
    a.release()
