# 重建窗口演练：撤权后到新索引就绪之间，读者是否安全（2026-10-31）

脚本 `scripts/v2_concurrency_drill.py`，两段场景都真跑（真实 HippoRAG 建快照 + 线程采样读者）。

## 场景 A：重建失败

```
撤权 329（fence.generation 0→1） → 重建抛错 → 指针仍 generation=0
→ 读者 read_once() 被 StaleIndexError 拒绝
```

结果：`rebuild_failed=true, pointer_unchanged=true, pointer_generation=0, reader_allowed=false`。

要点：**重建失败不会"退回旧索引可用"**。旧的仍是撤权前的索引，放行它等于把已撤权内容
继续吐给用户。宁可整体不可用，也不泄漏。

## 场景 B：重建成功 + 重建期间采样

读者线程每 20ms 尝试"打开索引"，只在 `building` 标志置位期间计数：

```
during_rebuild: {"blocked": 588, "allowed": 0}
pointer_generation: 1, reader_allowed_after: true
snapshot_doc_count: 3（仅 333 的块）, dropped_revoked: ["329"], unexpectedly_dropped: []
```

- **重建期间一次都没有放行**（588 次采样全被拒）；
- 完成后指针代次 1 → 放行；
- 新快照只有 333 的 3 个块，被剔除的**只有** 329，没有误伤其他文件。

## 一处被我自己测错的指标（记录在此）

第一版跑出 `during_rebuild: {"blocked": 174, "allowed": 4}`，看着像"窗口内泄漏 4 次"。
排查后是**测量错误**：读者线程一直跑到 `stop.set()` 之后，那 4 次"放行"其实发生在重建完成之后。
加了 `building` 标志限定采样窗口后变为 `allowed=0`。

这件事值得写下来：**"窗口内放行"这种结论，先确认采样窗口对不对**，否则会去改一个没坏的东西。
同轮还修了另一个判据错误：把"被剔除的文件是否都在撤权列表里"写成了"是否都在存活集合里"，
导致合法剔除被判成泄漏。

## Q 的变化

新增 `graph:重建窗口并发`（跑真实演练，缺环境则 SKIP 并写明），Q 现
**30 PASS / 0 FAIL / 0 NOT_IMPLEMENTED**。

## 还没做

- 只覆盖**单进程读者**；多实例/多副本场景下各实例的指针缓存未测；
- 重建耗时在真实库规模下的窗口长度未测（本次 5 块，重建 < 1s）；
- 没有"重建超时"与"重建积压"的处理；
- 撤权期间写操作（新增文件）与重建的并发未测。
