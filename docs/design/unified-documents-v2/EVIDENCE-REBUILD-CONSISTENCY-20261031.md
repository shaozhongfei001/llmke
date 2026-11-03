# 重建一致性：写并发与多进程读者（2026-10-31）

脚本 `scripts/v2_rebuild_consistency_drill.py`；`rebuild.py` 新增快照指纹与新鲜度检查。

## 两个必须回答的问题

1. **重建期间有人上传新文件怎么办？** —— 本次快照必然不含它。正确行为是**报告 stale（数据缺失）**，
   而不是假装覆盖；再重建一次应恢复 fresh。
2. **多个读者进程在窗口内看到什么？** —— 必须全部被拒；完成后必须全部看到新代次，
   不能出现某个进程还在用旧指针。

语义要先分清：**缺文件 ≠ 越权**。缺数据只报 stale、不阻断读；越权由 fence 管。
把两者混在一起，会让一次"少了个文件"演变成整体不可用。

## 实测结果

```
写并发：first_snapshot_stale=true, missing=["340"], second_snapshot_fresh=true
多读者：4 个进程，blocked=1347/1347/1348/1341，allowed=0，
        final_generation 全部 = 1（一致）
```

## 实现要点

- `docs_fingerprint()`：文件名 + 每块内容 sha256 → 集合指纹，存进指针；
- `check_freshness(pointer, docs, fence)`：比对缺失/删除/变更三类差异；
  **传 fence 时先剔除已撤权文件**——否则撤权后每次检查都误报 stale（这个 bug 本轮真出现过）；
- 读者用 `mp.Event` 收尾而不是固定时长：真实重建要调模型，耗时不可预估，
  按秒数猜窗口会把"完成后"的采样算进窗口，得出假结论（上一轮 4 次"窗口内放行"就是这么来的）。

## 两处自查纠错（都已写进过程记录）

1. **`pointer_generation_after == 1 and after.stale is False` 写成了
   `a == b is False`**：Python 链式比较被解析成 `(a == b) and (b is False)`，
   永远为假。改成两条独立断言。
2. **新鲜度检查没排除撤权文件**：撤权后 live docs 仍含 329，而新快照只含 333 →
   每次检查都报 missing 329。修法是把 fence 传进 `check_freshness`，并在比对前过滤。

## Q 的变化

新增 `graph:写并发与多读者一致性`，Q 现 **31 PASS / 0 FAIL / 0 NOT_IMPLEMENTED**。

## 还没做

- 只测**单机多进程**；跨机器多实例各自缓存指针的情况未测（部署形态相关）；
- 窗口被人为 sleep 2s 延长以便采样，**不代表真实耗时**；
- 没有"重建积压/合并"策略：连续上传会触发多次全量重建；
- 写并发只测"新增文件"，**修改与删除**在同一窗口内的行为未测。
