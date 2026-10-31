"""调度器：一轮一轮可断言——不该调模型的时候一次都不能调。"""

import threading

from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator
from graph_engine_adapter.rebuild_scheduler import RebuildScheduler


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(coordinator, clock, **kw):
    sleeps = []
    sched = RebuildScheduler(coordinator, sleep=lambda s: sleeps.append(s),
                             clock=clock, **kw)
    return sched, sleeps


def test_idle_cycle_does_not_build():
    clock = Clock()
    calls = []
    coord = RebuildCoordinator(lambda b: calls.append(len(b)), clock=clock)
    sched, sleeps = make(coord, clock, idle_poll=0.2)
    out = sched.run_cycle()
    assert out["action"] == "IDLE" and calls == []
    assert sleeps == [0.2]


def test_pending_waits_debounce_then_builds_once():
    clock = Clock()
    calls = []
    coord = RebuildCoordinator(lambda b: (calls.append(len(b)), {"ok": 1})[1], clock=clock)
    sched, sleeps = make(coord, clock, debounce=0.5)
    for i in range(3):
        coord.request("u", files=[f"f{i}"])
    out = sched.run_cycle()
    assert out["action"] == "BUILT"
    assert sleeps == [0.5]                 # 先合并窗口，再建
    assert calls == [3]                    # 一次建完三条


def test_backoff_cycle_sleeps_and_does_not_call_build():
    clock = Clock()
    attempts = []

    def broken(batch):
        attempts.append(1)
        raise RuntimeError("boom")

    coord = RebuildCoordinator(broken, clock=clock, backoff_base=4.0)
    sched, sleeps = make(coord, clock, debounce=0.0, max_sleep=2.0)
    coord.request("u", files=["a"])
    first = sched.run_cycle()              # 第一次真失败
    assert first["action"] == "FAILED" and len(attempts) == 1

    second = sched.run_cycle()             # 退避期内：只睡，不再打模型
    assert second["action"] == "BACKOFF_WAIT"
    assert len(attempts) == 1
    assert sleeps[-1] == 2.0               # 被 max_sleep 截断，保证 stop 能被及时看到


def test_stop_event_exits_promptly():
    clock = Clock()
    coord = RebuildCoordinator(lambda b: {}, clock=clock)
    sched, _ = make(coord, clock)
    stop = threading.Event()
    stop.set()
    out = sched.run_cycle(stop)
    assert out["action"] == "STOPPED"
    assert sched.stats()["stopped"] is True


def test_run_loop_is_bounded_by_max_cycles_and_respects_stop():
    clock = Clock()
    calls = []
    coord = RebuildCoordinator(lambda b: (calls.append(len(b)), {})[1], clock=clock)
    sched, _ = make(coord, clock, debounce=0.0, idle_poll=0.01)
    out = sched.run(max_cycles=3)
    assert out["cycles"] == 3
    assert out["stats"]["idle"] == 3        # 没有请求时不该构建
    assert calls == []

    coord.request("u", files=["a"])
    out2 = sched.run(max_cycles=2)
    assert out2["last"]["action"] in ("BUILT", "IDLE")
    assert calls == [1]
