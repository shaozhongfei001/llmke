# 重建调度器：让协调器自己跑（2026-10-31）

模块 `graph_engine_adapter/rebuild_scheduler.py`（5 项测试），真实演练
`scripts/v2_scheduler_drill.py`。

## 为什么还需要一层

协调器只提供"取一批、建一次"，退避参数也只是参数——**没有循环就不会生效**。
上一轮加了退避却没人调用 `run_once()`，等于买了个定时器不插电。

## 两个入口，一个可测一个可用

- `run_cycle()`：跑**一轮**并返回决策（`IDLE` / `BACKOFF_WAIT` / `BUILT` / `FAILED` /
  `ALREADY_RUNNING` / `STOPPED`）。测试靠它断言"什么时候不该调模型"；
- `run(stop_event, max_cycles=None)`：真实循环，pending 出现后先等 `debounce` 让突发合并。

三条自保措施：

1. **单次睡眠上限 `max_sleep`**：退避可能长达 300s，若整段睡过去，停机信号要等到睡醒才收到；
   所以按上限切片睡，保证 stop 能被及时看到；
2. **退避期只睡不打模型**：`BACKOFF_WAIT` 分支不调用 `run_once()`；
3. **停机检查点**：每轮开头检查 stop，返回 `STOPPED` 并记录状态。

## 真实演练结果

```
{"passed": true, "builds": [5, 5], "stopped": true,
 "no_build_after_stop": true, "documents": 5,
 "debounce_waits": 2, "idle": 3}
```

- 3 条突发请求 → **1 次构建**（5 个块），debounce 生效；
- 再 1 条 → 第 2 次构建；
- 停机后线程退出，**1 秒内没有新构建**；
- 指针文档数 5、新鲜度通过。

## Q 的变化

新增 `graph:重建调度器`（真实后台线程 + 突发合并 + 停机），Q 现
**34 PASS / 0 FAIL / 0 NOT_IMPLEMENTED**。

## 还没做

- **进程守护**：调度器跑在进程内线程里，进程挂了不会自愈；没有 systemd/supervisor 集成；
- **多实例**：两个副本会各自调度、各自重建，需要外部协调；
- **监控**：`stats()` 只有计数，没接指标导出；
- **定时全量重建**：没有"每天凌晨重建一次"这类策略；
- **真实故障时长下的退避调参**：本地演练都是毫秒级失败。
