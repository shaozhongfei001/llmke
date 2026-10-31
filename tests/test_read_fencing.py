"""读路径 leadership 校验：默认关、开了就必须拦。

为什么默认关：读者手里通常没有租约，也就拿不到"当前应有的 fencing"。
硬开会让所有没配租约的部署直接读不了——把可选加固变成强制阻断。
但它不能是"配了也不生效"的装饰，所以这组测试盯住：
- 落后就抛，且不返回半个结果；
- 相等放行，fencing=None 的老快照在被要求校验时**拒绝**（不猜）；
- 未配置时不改变任何现有行为。
"""

import pytest

from graph_engine_adapter.fence import SupersededSnapshotError, assert_snapshot_not_superseded


def test_superseded_snapshot_is_rejected():
    with pytest.raises(SupersededSnapshotError) as excinfo:
        assert_snapshot_not_superseded(1, 2)
    assert "上一轮领导权" in str(excinfo.value)


def test_equal_or_newer_snapshot_passes():
    assert assert_snapshot_not_superseded(2, 2) is None
    assert assert_snapshot_not_superseded(3, 2) is None


def test_unknown_snapshot_fencing_is_refused_when_check_required():
    """老快照没记 fencing：要求校验时拒绝，而不是把 None 当成 0 放过去。"""
    with pytest.raises(SupersededSnapshotError) as excinfo:
        assert_snapshot_not_superseded(None, 1)
    assert "未记录 fencing" in str(excinfo.value)


def test_check_is_off_by_default():
    assert assert_snapshot_not_superseded(0, None) is None
    assert assert_snapshot_not_superseded(None, None) is None


def test_pipeline_reports_snapshot_fencing_and_can_enforce():
    """接到检索编排上：开校验时拦、关校验时照常返回并把 fencing 带进结果。"""
    from graph_engine_adapter.pipeline import retrieve

    class Retriever:
        def graph(self, query, seeds, top_k):
            return [{"text": "t", "sources": [{"file_id": "1", "source": "s"}]}]

        def dense(self, query, top_k):
            return []

    from graph_engine_adapter import Assertion, AssertionStore, SourceRef

    store = AssertionStore()
    store.register_entity("p", "产品甲")
    store.add(Assertion(subject="p", predicate="额度", object_value=8000, unit="万元",
                        key="额度", sources=[SourceRef("1", "a" * 64)]))

    def run(**kwargs):
        return retrieve("产品甲的额度", retriever=Retriever(), store=store,
                        known_files={"1"}, graph_enabled=True, **kwargs)

    with pytest.raises(SupersededSnapshotError):
        run(snapshot_fencing=1, min_snapshot_fencing=2)

    ok = run(snapshot_fencing=2, min_snapshot_fencing=2)
    assert ok["fence"]["snapshot_fencing"] == 2        # 结果里能看出读的是哪一轮快照
    assert ok["hit_count"] == 1
