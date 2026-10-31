"""指标导出：名字/前缀/类型/只出一次/缺值跳过/fencing 随租约出现。

这一组测试的靶子是"面板不撒谎"，所以不只断言"输出非空"：
- 名字与类型错 → 面板查询直接空，或者明明在涨的计数器被当成 gauge 被 `rate()` 吃掉；
- HELP/TYPE 出两次 → Prometheus 抓取报错，整份输出作废；
- 把 None 导成 `nan` → 查询能跑但全是空值，比缺指标更难发现。
"""

import threading

from graph_engine_adapter.metrics import CONTENT_TYPE, PREFIX, render, render_with_lease
from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator
from graph_engine_adapter.rebuild_scheduler import RebuildScheduler


class StubScheduler:
    """只提供 stats()（外加可选的 lease_fencing），钉住"导出只依赖 stats 契约"。"""

    def __init__(self, stats, fencing=None):
        self._stats = stats
        if fencing is not None:
            self.lease_fencing = fencing

    def stats(self):
        return dict(self._stats)


def parse(text):
    """拆成 (样本, 类型声明, HELP 声明)；每条声明都保留列表以检测重复。"""
    samples, types, helps = {}, {}, {}
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("# TYPE "):
            _, _, name, kind = line.split()
            types.setdefault(name, []).append(kind)
            continue
        if line.startswith("# HELP "):
            name = line.split()[2]
            helps.setdefault(name, []).append(line)
            continue
        assert not line.startswith("#"), f"未知注释行: {line!r}"
        name, _, value = line.partition(" ")
        assert value, f"样本行缺值: {line!r}"
        samples.setdefault(name, []).append(value)
    return samples, types, helps


FULL_STATS = {
    # RebuildScheduler._state
    "cycles": 7, "debounce_waits": 3, "idle": 2, "backoff_waits": 1,
    "not_leader": 4, "lost_lease": 1, "lease_errors": 2,
    "slow_lease_ops": 5, "alerts_sent": 6, "alert_sink_errors": 1,
    "slept_s": 0.5, "stopped": False,
    # RebuildCoordinator.stats() 透传
    "pending": 2, "batches": 3, "builds": 4, "failed": 1, "running": True,
    "consecutive_failures": 1, "retry_in_s": 0.0, "rejected": 9, "alerts": 1,
    "fencing": 42,
}


def test_all_names_use_the_single_prefix():
    samples, types, helps = parse(render(StubScheduler(FULL_STATS)))
    assert samples, "不该是空输出"
    for name in list(samples) + list(types) + list(helps):
        assert name.startswith(PREFIX), f"{name} 没有统一前缀"


def test_expected_names_and_values_are_exported():
    samples, _, _ = parse(render(StubScheduler(FULL_STATS)))
    assert samples[PREFIX + "scheduler_cycles_total"] == ["7"]
    assert samples[PREFIX + "rebuild_pending"] == ["2"]
    assert samples[PREFIX + "lease_errors_total"] == ["2"]
    assert samples[PREFIX + "lease_fencing"] == ["42"]
    # 整数不写小数点，浮点保留原值
    assert samples[PREFIX + "scheduler_slept_seconds_total"] == ["0.5"]
    assert samples[PREFIX + "rebuild_retry_in_seconds"] == ["0"]


def test_type_lines_are_declared_exactly_once_and_kind_matches_name():
    _, types, helps = parse(render(StubScheduler(FULL_STATS), ))
    assert types, "至少要有一条 TYPE"
    for name, kinds in types.items():
        assert len(kinds) == 1, f"{name} 的 TYPE 出了 {len(kinds)} 次"
    for name, lines in helps.items():
        assert len(lines) == 1, f"{name} 的 HELP 出了 {len(lines)} 次"
    assert set(types) == set(helps), "HELP 与 TYPE 必须成对出现"

    for name, kinds in types.items():
        if name.endswith("_total"):
            assert kinds == ["counter"], f"{name} 是累加量，应为 counter"
        else:
            assert kinds == ["gauge"], f"{name} 不是 _total 后缀，应为 gauge"
    # 计数器本来就有非 _total 的例外吗？没有——有的话上面就会失败，这是刻意的。


def test_each_series_is_emitted_once():
    samples, _, _ = parse(render(StubScheduler(FULL_STATS)))
    for name, values in samples.items():
        assert len(values) == 1, f"{name} 出了 {len(values)} 条样本（重复序列会被拒收）"


def test_bool_is_exported_as_zero_or_one():
    samples, types, _ = parse(render(StubScheduler(FULL_STATS)))
    assert samples[PREFIX + "rebuild_running"] == ["1"]      # running=True
    assert samples[PREFIX + "scheduler_stopped"] == ["0"]    # stopped=False
    assert types[PREFIX + "rebuild_running"] == ["gauge"]


def test_none_and_non_numeric_are_skipped_not_rendered_as_nan():
    stats = {"cycles": 1, "fencing": None, "pending": None,
             "last_alert_sink_error": "RuntimeError: webhook 500",
             "retry_in_s": "0.5", "slept_s": float("nan"), "failed": float("inf")}
    text = render(StubScheduler(stats))
    samples, types, helps = parse(text)

    assert samples[PREFIX + "scheduler_cycles_total"] == ["1"]
    for skipped in ("lease_fencing", "rebuild_pending", "rebuild_retry_in_seconds",
                    "scheduler_slept_seconds_total", "rebuild_failed_total"):
        assert PREFIX + skipped not in samples, f"{skipped} 应整条跳过"
        assert PREFIX + skipped not in types, f"{skipped} 连 TYPE 都不该出现"
        assert PREFIX + skipped not in helps
    assert "nan" not in text.lower()
    assert "inf" not in text.lower()


def test_fencing_is_omitted_when_there_is_no_lease():
    stats = {k: v for k, v in FULL_STATS.items() if k != "fencing"}
    text = render(StubScheduler(stats))
    assert PREFIX + "lease_fencing" not in text

    # render_with_lease 会回落到 scheduler.lease_fencing 属性
    with_attr = render_with_lease(StubScheduler(stats, fencing=7))
    samples, types, _ = parse(with_attr)
    assert samples[PREFIX + "lease_fencing"] == ["7"]
    assert types[PREFIX + "lease_fencing"] == ["gauge"]

    # 两者都没有 → 仍然省略（不输出 0 假装有个 fencing=0 的主）
    assert PREFIX + "lease_fencing" not in render_with_lease(StubScheduler(stats))


def test_lease_object_metrics_only_when_passed():
    class StubLease:
        slow_ops = 3
        last_op_s = 4.2
        op_budget_s = 5.0

    stats = {k: v for k, v in FULL_STATS.items() if k != "fencing"}
    without = parse(render(StubScheduler(stats)))[0]
    assert PREFIX + "lease_last_op_seconds" not in without

    samples, types, _ = parse(render(StubScheduler(stats), lease=StubLease()))
    assert samples[PREFIX + "lease_driver_slow_ops_total"] == ["3"]
    assert types[PREFIX + "lease_driver_slow_ops_total"] == ["counter"]
    assert samples[PREFIX + "lease_last_op_seconds"] == ["4.2"]
    assert samples[PREFIX + "lease_op_budget_seconds"] == ["5"]

    class NoSample(StubLease):
        last_op_s = None

    missing = parse(render(StubScheduler(stats), lease=NoSample()))[0]
    assert PREFIX + "lease_last_op_seconds" not in missing


def test_real_scheduler_and_coordinator_round_trip():
    """用真的调度器跑一轮，钉住字段名对得上（改名就会红）。"""
    calls = []
    coord = RebuildCoordinator(lambda batch: (calls.append(len(batch)), {})[1])
    sched = RebuildScheduler(coord, debounce=0.0, idle_poll=0.0, sleep=lambda s: None)

    coord.request("upload", files=["f-1", "f-2"])
    assert sched.run_cycle()["action"] == "BUILT"

    samples, types, _ = parse(render_with_lease(sched))
    assert samples[PREFIX + "scheduler_cycles_total"] == ["1"]
    assert samples[PREFIX + "rebuild_builds_total"] == ["1"]
    assert samples[PREFIX + "rebuild_pending"] == ["0"]
    assert samples[PREFIX + "scheduler_slept_seconds_total"] == ["0"]
    assert types[PREFIX + "rebuild_builds_total"] == ["counter"]
    assert PREFIX + "lease_fencing" not in samples          # 没租约就不该出现
    assert calls == [1]                     # 两条文件合成一个请求、只建一次


def test_scheduler_with_stop_event_still_renders():
    coord = RebuildCoordinator(lambda batch: {}, clock=lambda: 0.0)
    sched = RebuildScheduler(coord, debounce=0.0, sleep=lambda s: None)
    stop = threading.Event()
    stop.set()
    sched.run_cycle(stop)
    samples, _, _ = parse(render(sched))
    assert samples[PREFIX + "scheduler_cycles_total"] == ["1"]
    assert samples[PREFIX + "scheduler_stopped"] == ["1"]


def test_stats_failure_does_not_blow_up_the_endpoint():
    class Broken:
        def stats(self):
            raise RuntimeError("stats 自己炸了")

    assert render(Broken()) == ""
    assert render(None) == ""


def test_content_type_is_prometheus_text_format():
    assert "text/plain" in CONTENT_TYPE and "version=0.0.4" in CONTENT_TYPE
