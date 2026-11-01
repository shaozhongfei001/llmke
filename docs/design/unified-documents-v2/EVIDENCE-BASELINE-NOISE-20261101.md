# 同语料波动分布：给灰度判定一个可量化的容差（2026-11-01）

## 为什么需要

10 块高相似语料上实测：**同一语料两份独立全量构建**，抽取事实就不同（6 vs 5），
检索 top1 只有 0.667。任何 full-vs-delta 的单次对比都无法归因——
差异是"改坏了"还是"这一次抽得不一样"，只有**同一个语料自身的分布**能回答。

## 做法

`scripts/v2_baseline_distribution.py`：把同语料 N 份快照两两比较，统计

- 事实差异（`facts_only_a/b` 的最大值）
- 检索一致率（top1 / ordered / jaccard 的最小值）
- **路线翻转次数**（GRAPH ↔ DENSE_FALLBACK）

给出 `tolerance`：`{facts_diff_max, top1_min, route_change_max}`，取"观测到的最坏情况"。

真跑（stress 语料，2 份独立构建，1 对）：

```
facts_diff_max = 6      （观测值 6）
top1_min       = 0.667  （观测值 0.667）
route_change_max = 1    （6 条 query 里有 1 条路线翻转）
```

## 判定怎么用（`v2_canary_verdict.py --baseline-distribution`）

基线不稳时不再一律 INCONCLUSIVE，而是把 a-vs-b 的差异放进区间：

| 场景 | 判定 | 理由 |
|---|---|---|
| 同内容两份构建，差异 6 ≤ 6、未超路线翻转上限 | **REVIEW** | "落在噪声范围内"：不能判回归，也不能判等价 |
| 同样基线不稳，但事实差异 20 > 6 | **INCONCLUSIVE** | 超出观测噪声，现有证据说不清 |
| 块集合不一致（内容真变了） | **UNSAFE** | 块集合是**确定性**的（不经 LLM 采样），不受噪声影响 |

最后一条是这轮加的：之前块集合不同也会被"基线不稳"吞成 INCONCLUSIVE，
把一个确定的结论说成"测不出来"，等于放走了真变化。

## 实测

```
同内容对照 (stress vs stress_b) → verdict=REVIEW  exit=1
  reasons: 差异落在噪声范围内：事实差异 6 ≤ 噪声上限 6，检索未低于下限
真实变更 (stress vs stress_delta) → verdict=UNSAFE  exit=2
  reasons: 块集合不一致：only_a=1 only_b=1（结构变化与抽取噪声无关）
```

## 诚实边界

- 样本只有 2 份快照（1 对）→ 容差是**下界**，不是统计意义上的置信区间；
- 换语料必须重跑：10 块的分布不能套到 3 块或 100 块上；
- 容差只覆盖"事实条数/一致率/路线"，**不覆盖内容正确性**——噪声范围内的差异仍需人工看清单；
- `route_change_max` 用的是观测最大值，样本少时会偏严格（更容易判超出噪声）。
