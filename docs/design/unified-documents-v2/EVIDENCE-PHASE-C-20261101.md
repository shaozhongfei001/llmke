# 阶段 C：灰度开关（按 KB 选 full/delta，改配置即回退）（2026-11-01）

Q：**50 PASS / 0 FAIL / 0 SKIP / 1 NOT_IMPLEMENTED**。

## 为什么灰度要覆盖"重建路径"

`rebuild()` 与 `rebuild_delta()` 是两条完全不同的路径：前者全量重抽，后者复用已有抽取。
增量已经在真语料上跑出 4.3× 提速，但**没人敢整库切过去**——没有按 KB 灰度的机制，
就只能"全切或全不切"。这一轮补上这个中间态。

## 设计上的三个硬要求

1. **配置来自文件，每轮重建前重读**：改文件即生效，不用重启进程；
2. **未知 mode 一律报错**（构造期校验 + 分派处兜底），不静默按默认跑；
3. **请求 delta 但没基准快照 → 明确报错**，绝不偷偷跑一次全量。
   理由：灰度最怕的不是"没灰度上"，而是"以为在灰度、其实没灰度"。

`rebuild_by_policy()` 返回里同时带 `requested_mode` 与 `effective_mode`，
两者不等就是 bug——这个字段设计就是为了让"说的和做的"可对账。

## 真跑（`scripts/v2_canary_drill.py`，假 builder，1 秒内反复切）

```
1) 灰度内 kb-1，policy.scope=["kb-1"], mode=delta → requested=delta, effective=delta, 指针 mode=DELTA
2) 灰度外 kb-2（同一份配置）                    → effective=full,              指针 mode=FULL
3) 改写策略文件 scope=[] 后**不重启**再跑 kb-1  → effective=full,              指针 mode=FULL
4) 回退后读路径：指针指向的快照可读，chunks 数与 pointer.documents 一致
```

第 3 步是这一轮的核心：同一进程内、只改文件，下一次重建就换回全量。
第 4 步保证"回退不是失联"——指针不回滚，只换后端。

## 为什么用假 builder 而不是真引擎

这条验的是**调度决策**（走哪条路、配置是否即时生效），不是抽取质量。
真引擎一次几十秒，反而看不清"到底哪次走了哪条路"。抽取质量由 A2/增量重建的证据覆盖。

## 边界

- 灰度只覆盖**重建路径**；解析器（`use-mineru`）仍靠 nacos 配置切换，未纳入同一套灰度机制；
- `scope` 是静态白名单，不支持按比例/按用户分流；
- 策略文件损坏 → 抛错停止重建（fail-fast），没有"坏了就用默认"的逃生门；
- worker 已接 `--kb-id` / `--canary-file`，但**没有多 KB 单进程**场景（一进程一 KB 一 root）；
- 未做灰度期的**双写对比**（同时跑 full 与 delta、比对结果差异）——那是 C2 的事。
