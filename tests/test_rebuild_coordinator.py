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


class FakeClock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_backpressure_rejects_when_pending_is_full():
    clock = FakeClock()
    c = RebuildCoordinator(lambda batch: {}, clock=clock, max_pending=2)
    assert c.request("u", files=["a"])["pending"] == 1
    assert c.request("u", files=["b"])["pending"] == 2
    out = c.request("u", files=["c"])
    assert out["status"] == "BACKPRESSURE"
    assert out["rejected"] == 1
    assert c.pending_count() == 2          # 超额的那条没进队列


def test_failure_enters_backoff_and_skips_attempts_until_due():
    clock = FakeClock()
    c = RebuildCoordinator(lambda batch: (_ for _ in ()).throw(RuntimeError("boom")),
                           clock=clock, backoff_base=2.0)
    c.request("u", files=["a"])
    out = c.run_once()
    assert out["status"] == "FAILED" and out["retry_in_s"] == 2.0

    during = c.run_once()                  # 退避期内不再打模型
    assert during["status"] == "BACKOFF" and during["retry_in_s"] > 0

    clock.advance(2.1)
    assert c.run_once()["status"] == "FAILED"   # 到点才重试


def test_backoff_grows_and_is_capped():
    clock = FakeClock()
    c = RebuildCoordinator(lambda batch: (_ for _ in ()).throw(RuntimeError("boom")),
                           clock=clock, backoff_base=1.0, backoff_factor=3.0, backoff_max=5.0)
    delays = []
    for _ in range(4):
        c.request("u", files=["a"])
        out = c.run_once()
        delays.append(out["retry_in_s"])
        clock.advance(out["retry_in_s"] + 0.1)
    assert delays == [1.0, 3.0, 5.0, 5.0]   # 指数增长但不超过上限


def test_success_resets_backoff():
    clock = FakeClock()
    state = {"fail": True}

    def build(batch):
        if state["fail"]:
            raise RuntimeError("boom")
        return {}

    c = RebuildCoordinator(build, clock=clock, backoff_base=2.0)
    c.request("u", files=["a"])
    c.run_once()
    clock.advance(2.1)
    state["fail"] = False
    c.request("u", files=["b"])
    assert c.run_once()["status"] == "BUILT"
    assert c.stats()["consecutive_failures"] == 0
    assert c.stats()["retry_in_s"] == 0


def test_alert_fires_once_at_threshold():
    clock = FakeClock()
    alerts = []
    c = RebuildCoordinator(lambda batch: (_ for _ in ()).throw(RuntimeError("boom")),
                           clock=clock, backoff_base=0.1, alert_after=2,
                           on_alert=lambda event, payload: alerts.append((event, payload)))
    for _ in range(3):
        c.request("u", files=["a"])
        out = c.run_once()
        clock.advance(out["retry_in_s"] + 0.1)
    assert len(alerts) == 1                          # 只在跨过阈值那次告警
    assert alerts[0][0] == "REBUILD_FAILING"
    assert alerts[0][1]["consecutive_failures"] == 2
