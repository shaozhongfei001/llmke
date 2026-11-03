# D3 更新统一图谱：稳定性门禁方案（2026-11-03）

## 已落地

- `graph_engine_adapter/stability.py`：同问句两次检索的 top1/ordered/overlap 度量 + STABLE/REVIEW
  判定（top1 一致率阈值默认 0.8，纯函数，5 tests）。
- 已知数据点（历史证据）：`EVIDENCE-DELTA-REBUILD-20261031.md`（5 块语料 full-vs-delta 一致）；
  `docs/NEXT.md:447`（10 块高相似语料 top1=0.667 → 按默认阈值判 REVIEW）。

## 接入点（发布前硬判据）

1. 增量重建（`rebuild_delta`）完成后：对固定问句集分别在旧/新快照跑 `/v2/graph/query`
   （同一 seeds、同一 top_k），收集两版命中列表；
2. 调 `stability.evaluate(pairs)`：
   - `STABLE` → 允许 `_promote` 发布；
   - `REVIEW` → 阻断发布并输出 per_query 明细（哪些问句漂了、漂到哪）；
3. 变更文档导致的漂移要**可归因**：把"问句×变更文档"相关矩阵写进报告（漂移集中在变更文档
   命中区 = 可接受；无关文档漂移 = 必须查）。
4. 问句集固化：`tests/fixtures/stability_queries.json`（8–10 条，覆盖跨文档/数值/方向类）。

## 未做（如实）

- 未接入 `rebuild_delta`/发布流程（需服务运行做真机两版对照）；
- 问句集未固化；阈值 0.8 是默认值，最终口径待业务确认。
