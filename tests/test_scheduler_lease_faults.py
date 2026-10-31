"""租约故障可见性：存储不可用时"不重建 + 不打死循环 + 必须有人知道"。

文件租约不会抛（本地 FS），MySQL 租约会（连接拒绝/超时）。这一组钉住：
1. acquire 抛异常 → LEASE_ERROR，`run()` 连续多轮不向外抛；
2. 告警边沿触发：首次立即、持续按 alert_every_s 节流、恢复发一次 LEASE_RECOVERED；
3. 告警通道自己抛异常 → 只记 alert_sink_errors，主循环照跑；
4. renew 抛异常 → 当作失去租约（无法确认是主就不能写）；
5. 故障期间 build 一次都没被调用（fail-closed），且统计里 build 数为 0。
"""

import pytest

from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator
from graph_engine_adapter.rebuild_scheduler import RebuildScheduler


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class BrokenLease:
    """模拟 MySQL 不可用：acquire/renew 都抛 OSError。"""

    def __init__(self):
        self.calls = 0

    def acquire(self):
        self.calls += 1
        raise OSError("(2003, \"Can't connect to MySQL server on '127.0.0.1'\")")

    def renew(self):
        raise OSError("server has gone away")


class FlakyLease:
    def __init__(self, clock, ok=True):
        self.clock = clock
        self.ok = ok
        self.fencing = 0

    def acquire(self):
        if not self.ok:
            raise OSError("connection refused")
        self.fencing += 1 if self.fencing == 0 else 0
        return {"acquired": True, "fencing": 1}

    def renew(self):
        if not self.ok:
            raise OSError("connection refused")
        return True


def make_scheduler(lease, alerts, clock, alert_every_s=60.0):
    coord = RebuildCoordinator(lambda batch: {"written": 0}, clock=clock)
    sched = RebuildScheduler(coord, debounce=0, idle_poll=0, sleep=lambda s: None,
                             clock=clock, lease=lease, on_alert=alerts.append,
                             alert_every_s=alert_every_s)
    coord.request("upload", ["f-1"])        # 有 pending，才会走到租约判断
    return sched


def test_acquire_exception_does_not_kill_loop_and_never_builds():
    clock, alerts = Clock(), []
    lease = BrokenLease()
    sched = make_scheduler(lease, alerts, clock)

    out = sched.run(max_cycles=3)      # 关键：不向外抛

    assert out["cycles"] == 3
    assert sched.stats()["lease_errors"] == 3
    assert sched.stats()["builds"] == 0          # fail-closed，一次都没构建
    assert lease.calls == 3


def test_lease_error_action_shape():
    clock, alerts = Clock(), []
    sched = make_scheduler(BrokenLease(), alerts, clock)
    cycle = sched.run_cycle()
    assert cycle["action"] == "LEASE_ERROR"
    assert "Can't connect" in cycle["error"]
    assert cycle["pending"] == 1


def test_alert_is_edge_triggered_and_throttled():
    clock, alerts = Clock(), []
    sched = make_scheduler(BrokenLease(), alerts, clock)

    sched.run_cycle()                       # 首次失败 → 立即告警
    assert [a["kind"] for a in alerts] == ["LEASE_UNAVAILABLE"]

    clock.now += 10
    sched.run_cycle()                       # 未到节流窗口 → 不再刷
    assert len(alerts) == 1

    clock.now += 60
    sched.run_cycle()                       # 超过 alert_every_s → 再报一次
    assert len(alerts) == 2
    assert alerts[-1]["consecutive"] == 3


def test_recovery_emits_once_after_failure():
    clock, alerts = Clock(), []
    lease = FlakyLease(clock, ok=False)
    sched = make_scheduler(lease, alerts, clock)

    sched.run_cycle()
    assert alerts[-1]["kind"] == "LEASE_UNAVAILABLE"

    lease.ok = True
    sched.run_cycle()
    assert alerts[-1]["kind"] == "LEASE_RECOVERED"
    sched.run_cycle()                       # 已恢复，不该重复发
    assert [a["kind"] for a in alerts].count("LEASE_RECOVERED") == 1


def test_alert_sink_failure_does_not_break_scheduler():
    clock = Clock()

    def boom(event):
        raise RuntimeError("webhook 500")

    sched = make_scheduler(BrokenLease(), [], clock)
    sched.on_alert = boom

    sched.run_cycle()                            # 首次失败：投递一次，炸一次
    clock.now += 61                              # 越过节流窗口：再投递一次
    out = sched.run(max_cycles=1)
    stats = sched.stats()
    assert stats["cycles"] == 2                  # 告警通道坏了，主循环照跑
    assert stats["alert_sink_errors"] == 2
    assert stats["alerts_sent"] == 0
    assert "webhook 500" in stats["last_alert_sink_error"]


def test_renew_exception_blocks_build():
    clock, alerts = Clock(), []

    class RenewBroken(FlakyLease):
        def renew(self):
            raise OSError("server has gone away")

    sched = make_scheduler(RenewBroken(clock), alerts, clock)
    cycle = sched.run_cycle()
    assert cycle["action"] == "LOST_LEASE"
    assert "续租时存储不可用" in cycle["hint"]
    assert sched.stats()["builds"] == 0
