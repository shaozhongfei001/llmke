"""图引擎指标导出：把"重建循环现在是什么状态"翻译成 Prometheus 文本（0.0.4）。

为什么手写而不用 `prometheus_client`：本仓是离线交付，多一个依赖就多一条要锁版本、
要审供应链的链路；而这里真正需要的只是"把几个计数器/仪表值写成几行文本"，标准库足够。
代价是要自己守住格式约束（HELP/TYPE 只能出一次）——下面的实现就是为了守住这些约束。

三条刻意的取舍（都是为了让面板不撒谎）：

1. **缺值就整条不出现**，而不是输出 0。没有租约的单实例部署不该出现 `lease_fencing 0`
   ——那会让人以为"有一个 fencing=0 的主"，而真相是这条序列根本不存在。
2. **None / 非数字整条跳过，绝不输出 `nan`**。Prometheus 确实能收 `nan`，但 `nan` 会穿过
   `rate()` / `avg()` 污染整个查询结果，面板看起来"有数据"实际全是空值——比缺指标更难排查。
   `inf` 同理跳过。
3. **bool 显式转 0/1**（Python 里 `bool` 是 `int` 子类，不特殊处理就会变成 "True"/"False"
   这种非法样本值）。

不做的事：不做直方图/摘要（重建耗时分布暂无一手的分桶依据，编分桶边界等于编数据）、
不做 push 网关、不做 label 维度（当前是单实例语义，加了 `instance` label 反而会掩盖
"多实例其实是各自统计"这件事）。
"""

from typing import Any, Dict, List, Optional, Set, Tuple

PREFIX = "llmke_graph_"
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

COUNTER = "counter"
GAUGE = "gauge"

# (stats 键, 指标名后缀, 类型, help)
# 顺序即输出顺序：先计数器再仪表，便于人肉 diff。
_SCHEDULER_METRICS: List[Tuple[str, str, str, str]] = [
    # ---- 调度循环（RebuildScheduler._state）----
    ("cycles", "scheduler_cycles_total", COUNTER,
     "Scheduler cycles executed."),
    ("debounce_waits", "scheduler_debounce_waits_total", COUNTER,
     "Cycles that waited out the debounce window before building."),
    ("idle", "scheduler_idle_total", COUNTER,
     "Cycles with nothing pending."),
    ("backoff_waits", "scheduler_backoff_waits_total", COUNTER,
     "Cycles that only slept because the coordinator is backing off."),
    ("not_leader", "scheduler_not_leader_total", COUNTER,
     "Cycles skipped because another instance holds the lease."),
    ("lost_lease", "scheduler_lost_lease_total", COUNTER,
     "Cycles that gave up because the lease was taken over or could not be renewed."),
    ("lease_errors", "lease_errors_total", COUNTER,
     "Lease storage failures (acquire/renew raised)."),
    ("slow_lease_ops", "lease_slow_ops_total", COUNTER,
     "Lease operations that exceeded the lease op budget."),
    ("alerts_sent", "scheduler_alerts_sent_total", COUNTER,
     "Alerts handed to the sink without raising."),
    ("alert_sink_errors", "scheduler_alert_sink_errors_total", COUNTER,
     "Alerts whose sink raised (sink broken, main loop kept running)."),
    ("alerts_undelivered", "scheduler_alerts_undelivered_total", COUNTER,
     "Alerts the sink explicitly reported as undelivered (returned False)."),
    ("slept_s", "scheduler_slept_seconds_total", COUNTER,
     "Cumulative seconds spent inside the scheduler's own sleeps."),
    # ---- 合并/构建（RebuildCoordinator.stats() 透传）----
    ("batches", "rebuild_batches_total", COUNTER,
     "Batches coalesced and built successfully."),
    ("builds", "rebuild_builds_total", COUNTER,
     "Successful rebuilds."),
    ("failed", "rebuild_failed_total", COUNTER,
     "Failed rebuilds (batch was kept and retried)."),
    ("rejected", "rebuild_rejected_total", COUNTER,
     "Rebuild requests rejected by backpressure."),
    ("alerts", "rebuild_alerts_total", COUNTER,
     "Failing-rebuild alerts raised by the coordinator."),
    # ---- 仪表 ----
    ("pending", "rebuild_pending", GAUGE,
     "Rebuild requests currently queued."),
    ("consecutive_failures", "rebuild_consecutive_failures", GAUGE,
     "Consecutive build failures driving the backoff."),
    ("retry_in_s", "rebuild_retry_in_seconds", GAUGE,
     "Seconds until the coordinator will allow the next attempt."),
    ("running", "rebuild_running", GAUGE,
     "1 while a rebuild is in flight."),
    ("stopped", "scheduler_stopped", GAUGE,
     "1 once the scheduler has seen a stop event."),
    ("fencing", "lease_fencing", GAUGE,
     "Lease fencing token held by this instance (absent when there is no lease)."),
]

# 从租约对象自身读的度量（不是 stats() 透传）：只在显式传入 lease 时输出。
# 与 scheduler.slow_lease_ops 的区别：后者是"调度器观察到几次慢"，这里是"驱动自己数了几次"。
_LEASE_METRICS: List[Tuple[str, str, str, str]] = [
    ("slow_ops", "lease_driver_slow_ops_total", COUNTER,
     "Slow operations counted inside the lease driver itself."),
    ("last_op_s", "lease_last_op_seconds", GAUGE,
     "Duration of the last lease operation in seconds."),
    ("op_budget_s", "lease_op_budget_seconds", GAUGE,
     "Configured per-operation budget for lease operations."),
]


# ---------------------------------------------------------------- 数值与格式
def _as_number(value: Any) -> Optional[float]:
    """转成可导出的数值；转不了就返回 None（调用方据此整条跳过）。

    bool 必须先判：`isinstance(True, int)` 为真，不拦住就会输出非法样本。
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        # nan != nan；inf 也会把下游聚合毁掉。两者都按"没有值"处理。
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    return None


def _fmt(value: float) -> str:
    """整数值不写小数点（`1` 而不是 `1.0`），其余保留 Python 的 repr 精度。"""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return repr(value)


def _escape(text: str) -> str:
    """HELP 文本里的反斜杠与换行必须转义，否则会把一行拆成两行、整份输出被拒。"""
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def _stats_of(obj: Any) -> Dict[str, Any]:
    """取 `obj.stats()`；取不到就返回空字典。

    这里吞异常是刻意的：`/metrics` 抓取不应该因为某个统计口径自己炸了而返回 500
    ——那会把"指标坏了"升级成"整个进程看起来死了"。
    """
    if obj is None:
        return {}
    stats = getattr(obj, "stats", None)
    if not callable(stats):
        return {}
    try:
        out = stats()
    except Exception:  # noqa: BLE001
        return {}
    return out if isinstance(out, dict) else {}


# ---------------------------------------------------------------- 渲染
def _render(stats: Dict[str, Any], lease: Any = None,
            labels: Optional[Dict[str, Any]] = None) -> str:
    lines: List[str] = []
    emitted: Set[str] = set()

    def emit(name: str, kind: str, help_text: str, value: float) -> None:
        full = PREFIX + name
        if full in emitted:
            return          # HELP/TYPE 与样本都只出一次，否则 Prometheus 解析报重复
        emitted.add(full)
        lines.append(f"# HELP {full} {_escape(help_text)}")
        lines.append(f"# TYPE {full} {kind}")
        lines.append(f"{full}{_label_text(labels)} {_fmt(value)}")

    for key, name, kind, help_text in _SCHEDULER_METRICS:
        if key not in stats:
            continue
        number = _as_number(stats[key])
        if number is None:
            continue
        emit(name, kind, help_text, number)

    if lease is not None:
        for attr, name, kind, help_text in _LEASE_METRICS:
            if not hasattr(lease, attr):
                continue
            number = _as_number(getattr(lease, attr, None))
            if number is None:
                continue
            emit(name, kind, help_text, number)

    return "".join(line + "\n" for line in lines)


def _label_text(labels: Optional[Dict[str, Any]]) -> str:
    """把标签渲染成 `{k="v",...}`：**排序**保证同一组标签每次输出一致（面板/快照可比），
    值按 Prometheus 文本格式转义（反斜杠、双引号、换行）。空标签返回空串（不改动原序列名）。
    """
    if not labels:
        return ""
    parts = []
    for key in sorted(labels):
        value = str(labels[key])
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        parts.append(f'{key}="{value}"')
    return "{" + ",".join(parts) + "}"


def render(scheduler: Any, lease: Any = None,
           labels: Optional[Dict[str, Any]] = None) -> str:
    """把调度器（含透传的协调器字段）渲染成 Prometheus 文本。

    `lease` 可选：传了才输出租约驱动自己的度量（慢操作次数/最近耗时/预算）。
    fencing 由 `scheduler.stats()["fencing"]` 带出；没有租约时为 None → 整条省略。

    `labels` 可选：给**所有**序列加同一组标签（典型用法：一个 worker 服务一个知识库，
    导出时带 `kb="kb_9"`，面板上才能按库切片）。不传则输出与原来逐字节一致。
    """
    return _render(_stats_of(scheduler), lease, labels)


def render_with_lease(scheduler: Any, lease: Any = None,
                      labels: Optional[Dict[str, Any]] = None) -> str:
    """`render()` 的"自动带租约"版本。

    与 `render()` 的差别只有两处，都是为了接部署侧方便：
    1. 没显式给 `lease` 时自动取 `scheduler.lease`（调度器上本来就挂着）；
    2. 若 `stats()` 里没有 fencing 键，回落到 `scheduler.lease_fencing` 属性。

    fencing 仍遵循"有就输出、无就省略"：两者都没有时这条序列（含 HELP/TYPE）完全不出现，
    而不是输出 `lease_fencing 0` 假装"有个 fencing=0 的主"。
    """
    stats = dict(_stats_of(scheduler))
    if "fencing" not in stats:
        stats["fencing"] = getattr(scheduler, "lease_fencing", None)
    return _render(stats, lease if lease is not None else getattr(scheduler, "lease", None),
                   labels)
