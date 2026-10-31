"""重建合并：多次变更合成一次构建；失败整批保留；构建期间新请求留给下一轮。"""

import threading
import time

from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator


def test_multiple_requests_coalesce_into_one_build():
    calls = []

    def build_once(batch):
        calls.append([item["reason"] for item in batch])
        return {"ok": True}

    c = RebuildCoordinator(build_once)
    for i in range(5):
        c.request("upload", files=[f"f{i}"])
    out = c.run_once()
    assert out["status"] == "BUILT" and out["requests"] == 5
    assert len(calls) == 1 and len(calls[0]) == 5
    assert c.stats()["builds"] == 1


def test_request_arriving_during_build_goes_to_next_batch():
    seen = []
    started = threading.Event()
    release = threading.Event()

    def build_once(batch):
        seen.append(len(batch))
        started.set()
        release.wait(timeout=5)
        return {"ok": True}

    c = RebuildCoordinator(build_once)
    c.request("upload", files=["a"])
    thread = threading.Thread(target=c.run_once)
    thread.start()
    assert started.wait(timeout=5)

    c.request("upload", files=["b"])          # 构建期间来的
    release.set()
    thread.join(timeout=5)

    assert seen == [1]                        # 第一次只处理 a
    assert c.pending_count() == 1             # b 留到下一轮
    out = c.run_once()
    assert out["requests"] == 1
    assert c.stats()["builds"] == 2


def test_failure_keeps_whole_batch_for_retry():
    attempts = []

    def build_once(batch):
        attempts.append(len(batch))
        raise RuntimeError("炸了")

    c = RebuildCoordinator(build_once)
    c.request("upload", files=["a"])
    c.request("upload", files=["b"])
    out = c.run_once()
    assert out["status"] == "FAILED" and out["requests"] == 2
    assert c.pending_count() == 2             # 一条都不能丢
    assert c.stats()["failed"] == 1 and c.stats()["builds"] == 0


def test_single_flight_prevents_concurrent_builds():
    started = threading.Event()
    release = threading.Event()

    def build_once(batch):
        started.set()
        release.wait(timeout=5)
        return {}

    c = RebuildCoordinator(build_once)
    c.request("upload", files=["a"])
    first = threading.Thread(target=c.run_once)
    first.start()
    assert started.wait(timeout=5)

    second = c.run_once()                     # 同一时刻的第二个调用
    assert second["status"] == "ALREADY_RUNNING"

    release.set()
    first.join(timeout=5)
    assert c.stats()["builds"] == 1


def test_nothing_to_do_is_not_a_failure():
    c = RebuildCoordinator(lambda batch: {})
    out = c.run_once()
    assert out["status"] == "NOTHING_TO_DO"
    assert c.stats()["failed"] == 0
