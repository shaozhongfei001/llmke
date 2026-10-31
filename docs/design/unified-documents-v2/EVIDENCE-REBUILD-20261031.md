# 撤权 → 隔离重建 → 切读（2026-10-31）

模块 `graph_engine_adapter/rebuild.py`（5 项测试），真实演练 `scripts/v2_rebuild_drill.py`。

## 编排顺序（与设计 §5 一致）

```
撤权(fence.generation+1) → 用存活文件在新目录建快照 → 写指针(dir + generation) → 切读
                         ↘ 失败：删半成品目录，指针不动，旧索引继续被 fence 挡着
```

三处刻意的设计：

1. **目标目录必须新建**（`snapshot-<stamp>-g<gen>`）：重建期间旧索引还要能被 fence 拦着读，
   原地改会让"旧内容不可见"失去依据；
2. **指针原子切换**：写 `.tmp` → `fsync` → `os.replace`，读者不会看到半个 JSON；
3. **代次单调**：指针里的 `generation` 等于重建时的 `fence.generation`，读者用它和 fence 比较。
   重建失败时指针不变——**宁可继续用被挡住的旧索引，也不切到半成品**。

另外两件小事：重建自己会剔除已撤权文件（不依赖调用方自觉）；
快照目录只保留最近 2 个，但**绝不删当前指针指向的那个**。

## 真实演练结果（333 docx + 329 xlsx，撤权 329）

```
{"fence_generation": 1, "snapshot_chunks": 3,
 "new_snapshot_has_revoked_text": [],
 "stale_index_blocked": true, "fresh_index_allowed": true, "passed": true}
```

- 撤权 329 后 fence 代次 = 1；
- 新快照只有 **3 个块**（333 的正文+表格），**没有** 329 的任何正文；
- 旧索引（代次 0）被 `StaleIndexError` 拒绝；
- 新索引（代次 1）放行。

引擎侧日志显示新快照的图规模：`num_passage_nodes=3, num_extracted_triples=5`，
与"只剩 333"一致。

## Q 的变化

新增 `graph:隔离重建（撤权→重建→切读）`，跑真实演练（缺引擎或载荷时 SKIP 并写明）。
Q 现 **29 PASS / 0 FAIL / 0 NOT_IMPLEMENTED**。

## 还没做（别把重建当删除）

- **引擎侧按文档删除图产物**：没有实现。删文档目前只能"撤权 + 全量重建"，
  语料越大代价越高；`delete_document` 仍是 NOT_IMPLEMENTED；
- **重建期间的并发查询**：只有代次校验这一层；没有验证"重建中读者被拒、重建后自动恢复"的真实行为；
- **重建失败的可观测性**：只抛 `RebuildFailed`，没有告警与重试策略；
- **大语料的时间/成本**：本次只 5 块，真实库规模未测。
