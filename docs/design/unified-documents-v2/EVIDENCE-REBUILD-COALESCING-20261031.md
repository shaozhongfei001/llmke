# 重建合并：连续变更只构建一次（2026-10-31）

模块 `graph_engine_adapter/rebuild_coordinator.py`（5 项测试），真实演练
`scripts/v2_rebuild_coalesce_drill.py`。

## 为什么必须合并

每次上传都触发一次全量重建，真实库规模下会把机器打满，而且后一次会覆盖前一次的产出——
等于白烧算力。合并的意义是**省重建次数**，不是"看起来更快"。

## 四条规则

1. `request()` 只登记待重建，**不立刻构建**；
2. `run_once()` 取走截至当前的全部请求形成一个批次，**成功后才算完成**；
3. 构建期间新来的请求**不并入本批**（否则无法判断本批快照是否完整），留给下一轮；
4. 同一时刻只允许一个构建（single-flight）：并发调用第二个直接返回 `ALREADY_RUNNING`，
   而不是排队再建一次。失败时**整批放回队首**，一条请求都不能丢。

## 实测（真实引擎）

```
{"passed": true, "builds": 2, "first_requests": 3,
 "documents": 5, "fresh1": false, "fresh2": false}
```

3 次快速变更 → **1 次构建**；再来 1 次变更 → 第 2 次构建；快照覆盖 5 个块，
两次之后新鲜度检查都通过。

## 一个真实 bug（本轮自己写出来的）

第一版 `run_once()` 里 `batch = list(self._state.pending)` **只复制没清空**，
于是构建期间 `pending` 仍包含本批：新到的请求让计数变 2（期望 1），
失败回滚时变成 4（期望 2）——请求被重复计数，重试会重复构建。

修法：取批次时同时 `self._state.pending = []`。测试 `test_request_arriving_during_build_goes_to_next_batch`
与 `test_failure_keeps_whole_batch_for_retry` 正是钉这个的。

## 顺带查出的测试污染

Q 里的 `graph:重建窗口并发` 突然 FAIL：原因是它复用固定目录 `/tmp/q-window`，
上一轮留下的快照让"撤权后仍被拒"的判定失真（旧指针代次已经等于新 fence 代次）。
改为每次运行用 `--root /tmp/q-window-<timestamp>` 独立目录。

这类问题不影响产品，但会让验收结论随机翻转——**目录必须按运行隔离**。

## 状态

Q 现 **32 PASS / 0 FAIL / 0 NOT_IMPLEMENTED**。

## 还没做

- **单进程协调器**：多实例部署需要外部协调（分布式锁/队列），未做；
- 没有积压上限与背压：长时间失败会无限堆积请求；
- 没有"合并窗口"时间参数：当前是"调用 run_once 时一次性取走"，
  真实的定时/触发策略（如 5 秒窗口）未接调度器；
- 重建失败告警与重试退避未做。
