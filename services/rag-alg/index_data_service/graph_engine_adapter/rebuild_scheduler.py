"""重建调度器：让协调器"自己跑起来"。

协调器只提供"取一批、建一次"的动作，退避参数也只是参数——没有循环就不会生效。
这个调度器补的就是那个循环，并且刻意做成可测的：

- `run_cycle()` 只跑**一轮**，返回本轮的决策（IDLE / DEBOUNCE_WAIT / BUILT / FAILED /
  BACKOFF_WAIT / ALREADY_RUNNING），便于用假时钟断言"什么时候不该调模型"；
- `run(stop_event)` 是真实循环：pending 出现后先等 `debounce` 秒让突发请求合并，
  再取批构建；失败/退避期间按协调器给的 `retry_in_s` 睡，不空转；
- 收到 stop 事件后在下一个检查点退出（`sleep` 可注入，测试里不会真的等待）。

不做的事（避免假装）：不做定时全量重建、不内置告警通道实现（只给 `on_alert` 接缝，
Webhook/企业微信等由部署侧接，本仓未接任何真实通道）。

租约故障是**必须**处理的：`lease.acquire()` 打的是外部存储（MySQL），对端不可用会抛异常。
如果不接住，一轮异常就能把 `run()` 打死——服务进程还在、重建永远停摆，而且没人知道。
所以这里显式分成两条路：接住、记数、按退避继续跑（fail-closed 不重建），并把故障**沿边沿触发**
推给 `on_alert`（首次失败、持续失败每 N 秒一次、恢复一次）。告警通道自己抛异常也不能拖死主循环。
"""

import threading
import time
from typing import Any, Callable, Dict, Optional

from .rebuild_coordinator import RebuildCoordinator

SCHEMA = "llmke.graph-engine.rebuild-scheduler.v1"
LEASE_ERROR_BACKOFF = 5.0     # 租约不可用时的重试间隔上限（避免打爆数据库）


class RebuildScheduler:
    def __init__(self, coordinator: RebuildCoordinator, *,
                 debounce: float = 0.5,
                 idle_poll: float = 0.5,
                 max_sleep: float = 30.0,
                 sleep: Optional[Callable[[float], None]] = None,
                 clock: Optional[Callable[[], float]] = None,
                 lease: Any = None,
                 on_alert: Optional[Callable[[Dict[str, Any]], None]] = None,
                 alert_every_s: float = 60.0,
                 lease_error_backoff: float = LEASE_ERROR_BACKOFF):
        self.coordinator = coordinator
        self.debounce = debounce
        self.idle_poll = idle_poll
        self.max_sleep = max_sleep      # 单次睡眠上限：保证 stop 事件能被及时看到
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        # 可选租约：多实例部署时只让持有者真正重建（不给就是单实例行为）
        self.lease = lease
        self.on_alert = on_alert
        self.alert_every_s = alert_every_s
        self.lease_error_backoff = lease_error_backoff
        self._state = {"cycles": 0, "debounce_waits": 0, "idle": 0,
                       "backoff_waits": 0, "slept_s": 0.0, "stopped": False,
                       "not_leader": 0, "lost_lease": 0,
                       "lease_errors": 0, "alerts_sent": 0, "alert_sink_errors": 0,
                       "alerts_undelivered": 0,
                       "slow_lease_ops": 0}
        # 当前持有的 fencing 值：build 回调把它写进快照，旧主的晚到写入才会被拒
        self.lease_fencing: Optional[int] = None
        self._lock = threading.Lock()
        self._alert_state = {"failing": False, "last_at": 0.0, "last_error": None}
        self._slow_state = {"last_at": None}   # None = 还没报过；用 0.0 会在 clock 起点附近被判"没到窗口"

    # ---------- 告警：边沿触发 ----------
    def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        """告警通道抛异常不能拖死主循环（否则"发不出告警"会变成"服务停摆"）。"""
        if self.on_alert is None:
            return
        event = {"schema": "llmke.graph-engine.alert.v1", "kind": kind,
                 # `at` 用注入的时钟（多为 monotonic）做节流判断；告警里要的是**墙钟**，
                 # 否则发到群里的时间是 "1970-01-01"（实测踩过）。
                 "at": self._clock(), "wall_time": time.time(), **payload}
        try:
            result = self.on_alert(event)
            # `alerts_sent` 只表示"交给了通道且没抛"；通道明确返回 False 才是"投递失败"。
            # 两个数刻意分开：webhook 全 500 时 sent 照样涨，只看它会以为告警都送到了。
            delivered = result is not False
            with self._lock:
                self._state["alerts_sent"] += 1
                if not delivered:
                    self._state["alerts_undelivered"] += 1
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._state["alert_sink_errors"] += 1
                self._state["last_alert_sink_error"] = f"{type(exc).__name__}: {exc}"

    def _note_lease_slow(self, op: str, elapsed: float) -> None:
        """慢但没抛：说明驱动超时在兜底（勉强活着）。仍要可见——否则"每轮卡 4s"会被当成正常。"""
        budget = getattr(self.lease, "op_budget_s", None)
        if budget is None or elapsed is None or elapsed <= budget:
            return
        now = self._clock()
        with self._lock:
            self._state["slow_lease_ops"] += 1
            last_at = self._slow_state["last_at"]
            due = last_at is None or (now - last_at) >= self.alert_every_s
            if due:
                self._slow_state["last_at"] = now
            count = self._state["slow_lease_ops"]
        if due:
            self._emit("LEASE_SLOW", {"op": op, "elapsed_s": elapsed, "budget_s": budget,
                                      "count": count,
                                      "impact": "本轮仍继续，但调度节拍被拖慢；持续出现需查网络/锁等待"})

    def _note_lease_ok(self) -> None:
        with self._lock:
            if not self._alert_state["failing"]:
                return
            self._alert_state["failing"] = False
            last = self._alert_state["last_error"]
        self._emit("LEASE_RECOVERED", {"last_error": last})

    def _note_lease_error(self, exc: BaseException) -> None:
        now = self._clock()
        detail = f"{type(exc).__name__}: {exc}"
        with self._lock:
            was_failing = self._alert_state["failing"]
            due = (not was_failing) or (now - self._alert_state["last_at"] >= self.alert_every_s)
            if due:
                self._alert_state["last_at"] = now
                self._alert_state["last_error"] = detail
            self._alert_state["failing"] = True
            errors = self._state["lease_errors"]
        if due:
            # 首次失败立即告警；持续失败按 alert_every_s 节流，不刷屏
            self._emit("LEASE_UNAVAILABLE",
                       {"error": detail, "consecutive": errors,
                        "impact": "重建已暂停（fail-closed），读路径继续读旧快照"})

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {**self._state, "fencing": self.lease_fencing, **self.coordinator.stats()}

    def _sleep_bounded(self, seconds: float) -> None:
        seconds = max(0.0, min(seconds, self.max_sleep))
        with self._lock:
            self._state["slept_s"] += seconds
        if seconds:
            self._sleep(seconds)

    def run_cycle(self, stop_event: Optional[threading.Event] = None) -> Dict[str, Any]:
        """跑一轮：返回决策；不满足条件时绝不调用 build。"""
        with self._lock:
            self._state["cycles"] += 1
        if stop_event is not None and stop_event.is_set():
            with self._lock:
                self._state["stopped"] = True
            return {"schema": SCHEMA, "action": "STOPPED"}

        pending = self.coordinator.pending_count()
        if pending == 0:
            with self._lock:
                self._state["idle"] += 1
            self._sleep_bounded(self.idle_poll)
            return {"schema": SCHEMA, "action": "IDLE", "pending": 0}

        retry_in = self.coordinator.stats().get("retry_in_s", 0)
        if retry_in and retry_in > 0:
            with self._lock:
                self._state["backoff_waits"] += 1
            self._sleep_bounded(retry_in)
            return {"schema": SCHEMA, "action": "BACKOFF_WAIT",
                    "retry_in_s": retry_in, "pending": pending}

        if self.lease is not None:
            try:
                acquired = self.lease.acquire()
            except Exception as exc:  # noqa: BLE001
                # 租约存储不可用：不构建、不抛出去打死循环、按退避重试
                with self._lock:
                    self._state["lease_errors"] += 1
                    errors = self._state["lease_errors"]
                self._note_lease_error(exc)
                self._sleep_bounded(self.lease_error_backoff)
                return {"schema": SCHEMA, "action": "LEASE_ERROR", "pending": pending,
                        "error": f"{type(exc).__name__}: {exc}", "consecutive": errors,
                        "hint": "租赁存储不可用，本轮不重建（读路径继续读旧快照）"}
            self._note_lease_ok()
            self._note_lease_slow("acquire", getattr(self.lease, "last_op_s", None))
            if not acquired.get("acquired"):
                with self._lock:
                    self._state["not_leader"] += 1
                self._sleep_bounded(self.idle_poll)
                return {"schema": SCHEMA, "action": "NOT_LEADER",
                        "holder": acquired.get("holder"), "pending": pending}
            self.lease_fencing = acquired.get("fencing", self.lease_fencing)
            try:
                renewed = self.lease.renew()
            except Exception as exc:  # noqa: BLE001
                # 续租失败无法确认自己还是主：按"失去租约"处理，绝不继续构建
                with self._lock:
                    self._state["lease_errors"] += 1
                    self._state["lost_lease"] += 1
                self._note_lease_error(exc)
                self._sleep_bounded(self.lease_error_backoff)
                return {"schema": SCHEMA, "action": "LOST_LEASE", "pending": pending,
                        "error": f"{type(exc).__name__}: {exc}",
                        "hint": "续租时存储不可用，无法确认仍是主 → 本轮不构建"}
            self._note_lease_slow("renew", getattr(self.lease, "last_op_s", None))
            if not renewed:
                with self._lock:
                    self._state["lost_lease"] += 1
                return {"schema": SCHEMA, "action": "LOST_LEASE",
                        "pending": pending,
                        "hint": "租约被接管，本实例立即停手（重建本身幂等，不会写坏快照）"}

        if self.debounce > 0:
            with self._lock:
                self._state["debounce_waits"] += 1
            self._sleep_bounded(self.debounce)

        out = self.coordinator.run_once()
        action = {"BUILT": "BUILT", "FAILED": "FAILED", "ALREADY_RUNNING": "ALREADY_RUNNING",
                  "NOTHING_TO_DO": "IDLE", "BACKOFF": "BACKOFF_WAIT"}.get(out["status"], out["status"])
        if action == "BACKOFF_WAIT":
            self._sleep_bounded(out.get("retry_in_s", 0))
        return {"schema": SCHEMA, "action": action, "detail": out}

    def run(self, stop_event: Optional[threading.Event] = None,
            max_cycles: Optional[int] = None) -> Dict[str, Any]:
        """真实循环；`max_cycles` 只用于演练时限定轮数。"""
        stop_event = stop_event or threading.Event()
        cycles = 0
        last = None
        while not stop_event.is_set() and (max_cycles is None or cycles < max_cycles):
            last = self.run_cycle(stop_event)
            cycles += 1
            if last["action"] == "STOPPED":
                break
        return {"schema": SCHEMA, "cycles": cycles, "last": last, "stats": self.stats()}
