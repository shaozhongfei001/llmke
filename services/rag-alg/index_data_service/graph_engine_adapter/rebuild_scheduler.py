"""重建调度器：让协调器"自己跑起来"。

协调器只提供"取一批、建一次"的动作，退避参数也只是参数——没有循环就不会生效。
这个调度器补的就是那个循环，并且刻意做成可测的：

- `run_cycle()` 只跑**一轮**，返回本轮的决策（IDLE / DEBOUNCE_WAIT / BUILT / FAILED /
  BACKOFF_WAIT / ALREADY_RUNNING），便于用假时钟断言"什么时候不该调模型"；
- `run(stop_event)` 是真实循环：pending 出现后先等 `debounce` 秒让突发请求合并，
  再取批构建；失败/退避期间按协调器给的 `retry_in_s` 睡，不空转；
- 收到 stop 事件后在下一个检查点退出（`sleep` 可注入，测试里不会真的等待）。

不做的事（避免假装）：不做多实例协调、不做定时全量重建、不接告警通道。
"""

import threading
import time
from typing import Any, Callable, Dict, Optional

from .rebuild_coordinator import RebuildCoordinator

SCHEMA = "llmke.graph-engine.rebuild-scheduler.v1"


class RebuildScheduler:
    def __init__(self, coordinator: RebuildCoordinator, *,
                 debounce: float = 0.5,
                 idle_poll: float = 0.5,
                 max_sleep: float = 30.0,
                 sleep: Optional[Callable[[float], None]] = None,
                 clock: Optional[Callable[[], float]] = None,
                 lease: Any = None):
        self.coordinator = coordinator
        self.debounce = debounce
        self.idle_poll = idle_poll
        self.max_sleep = max_sleep      # 单次睡眠上限：保证 stop 事件能被及时看到
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        # 可选租约：多实例部署时只让持有者真正重建（不给就是单实例行为）
        self.lease = lease
        self._state = {"cycles": 0, "debounce_waits": 0, "idle": 0,
                       "backoff_waits": 0, "slept_s": 0.0, "stopped": False,
                       "not_leader": 0, "lost_lease": 0}
        self._lock = threading.Lock()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {**self._state, **self.coordinator.stats()}

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
            acquired = self.lease.acquire()
            if not acquired.get("acquired"):
                with self._lock:
                    self._state["not_leader"] += 1
                self._sleep_bounded(self.idle_poll)
                return {"schema": SCHEMA, "action": "NOT_LEADER",
                        "holder": acquired.get("holder"), "pending": pending}
            if not self.lease.renew():
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
