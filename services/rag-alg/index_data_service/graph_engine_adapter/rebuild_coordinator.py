"""重建合并（coalescing）：短时间内的多次变更合成一次全量重建。

为什么必须合并：每次上传都触发一次全量重建，真实库规模下会把机器打满，
而且后一次重建会覆盖前一次的产出——等于白烧算力。

规则：
1. `request()` 只登记"有待重建"，**不立刻构建**；
2. `run_once()` 先取走到当前为止的全部待处理请求（形成一个批次），构建成功后
   才把它们标记为已完成；构建失败则**整批保留**，下次重试（不能丢请求）；
3. 构建期间新来的请求**不并入本批**，留给下一轮（否则无法判断本批快照是否完整）；
4. 同一时刻只允许一个构建（single-flight）：并发调用 `run_once()` 的第二个直接返回
   `ALREADY_RUNNING`，而不是排队再建一次。

这不是分布式锁：单进程语义。多实例需要外部协调（未做，见证据）。
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

SCHEMA = "llmke.graph-engine.rebuild-coordinator.v1"


@dataclass
class _State:
    pending: List[Dict[str, Any]] = field(default_factory=list)
    batches: int = 0
    builds: int = 0
    failed: int = 0
    running: bool = False
    consecutive_failures: int = 0
    next_attempt_at: float = 0.0
    rejected: int = 0
    alerts: int = 0


class RebuildCoordinator:
    def __init__(self, build_once: Callable[[List[Dict[str, Any]]], Any], *,
                 clock: Callable[[], float] = time.time,
                 max_pending: int = 200,
                 backoff_base: float = 2.0,
                 backoff_factor: float = 2.0,
                 backoff_max: float = 300.0,
                 alert_after: int = 3,
                 on_alert: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        """`build_once(requests)` 执行一次真实重建，返回任意结果；抛异常表示失败。

        三个"故障下不失控"的开关：
        - `max_pending`：背压。堆积超过上限就**拒绝**新请求，别把队列堆进内存；
        - `backoff_*`：连续失败后指数退避，退避期内 `run_once()` 直接返回 BACKOFF；
        - `alert_after` + `on_alert`：连续失败到阈值时回调一次告警（回调在锁外执行）。
        """
        self._build_once = build_once
        self._clock = clock
        self._state = _State()
        self._lock = threading.Lock()
        self.max_pending = max_pending
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
        self.alert_after = alert_after
        self.on_alert = on_alert

    # ---------- 请求侧 ----------
    def request(self, reason: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        with self._lock:
            if len(self._state.pending) >= self.max_pending:
                self._state.rejected += 1
                return {"schema": SCHEMA, "status": "BACKPRESSURE",
                        "pending": len(self._state.pending), "max_pending": self.max_pending,
                        "rejected": self._state.rejected,
                        "hint": "重建积压已满，拒绝新请求；先排空再上传"}
            item = {"reason": reason, "files": sorted(files or []), "at": self._clock()}
            self._state.pending.append(item)
            return {"schema": SCHEMA, "pending": len(self._state.pending),
                    "queued": item, "generation_hint": self._state.batches}

    def pending_count(self) -> int:
        with self._lock:
            return len(self._state.pending)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"pending": len(self._state.pending), "batches": self._state.batches,
                    "builds": self._state.builds, "failed": self._state.failed,
                    "running": self._state.running,
                    "consecutive_failures": self._state.consecutive_failures,
                    "retry_in_s": round(max(0.0, self._state.next_attempt_at - self._clock()), 2),
                    "rejected": self._state.rejected, "alerts": self._state.alerts}

    # ---------- 构建侧 ----------
    def run_once(self) -> Dict[str, Any]:
        with self._lock:
            if self._state.running:
                return {"schema": SCHEMA, "status": "ALREADY_RUNNING",
                        "pending": len(self._state.pending)}
            now = self._clock()
            if self._state.next_attempt_at > now:
                return {"schema": SCHEMA, "status": "BACKOFF",
                        "retry_in_s": round(self._state.next_attempt_at - now, 2),
                        "consecutive_failures": self._state.consecutive_failures,
                        "pending": len(self._state.pending)}
            if not self._state.pending:
                return {"schema": SCHEMA, "status": "NOTHING_TO_DO", "pending": 0}
            batch = list(self._state.pending)     # 取走本批
            self._state.pending = []              # 必须真的取走，否则构建期间 pending 会把本批再算一次
            self._state.running = True

        try:
            result = self._build_once(batch)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._state.failed += 1
                self._state.consecutive_failures += 1
                self._state.running = False
                # 整批放回队首：失败不能把请求丢掉
                self._state.pending = batch + self._state.pending
                delay = min(self.backoff_base * (self.backoff_factor ** (self._state.consecutive_failures - 1)),
                            self.backoff_max)
                self._state.next_attempt_at = self._clock() + delay
                should_alert = self._state.consecutive_failures == self.alert_after
                if should_alert:
                    self._state.alerts += 1
                payload = {"consecutive_failures": self._state.consecutive_failures,
                           "retry_in_s": round(delay, 2), "pending": len(self._state.pending)}
            if should_alert and self.on_alert is not None:
                try:
                    self.on_alert("REBUILD_FAILING", payload)   # 回调放锁外，避免与业务锁互等
                except Exception:  # noqa: BLE001
                    pass
            return {"schema": SCHEMA, "status": "FAILED", "requests": len(batch),
                    "error": f"{type(exc).__name__}: {exc}", **payload}

        with self._lock:
            self._state.batches += 1
            self._state.builds += 1
            self._state.running = False
            self._state.consecutive_failures = 0
            self._state.next_attempt_at = 0.0
            remaining = len(self._state.pending)
        return {"schema": SCHEMA, "status": "BUILT", "requests": len(batch),
                "files": sorted({f for item in batch for f in item["files"]}),
                "result": _safe(result), "pending_after": remaining,
                "batches": self._state.batches}


def _safe(value: Any) -> Any:
    try:
        import json
        json.dumps(value)
        return value
    except TypeError:
        return {"type": type(value).__name__}
